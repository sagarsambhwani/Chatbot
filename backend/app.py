"""FastAPI backend application for Local AI Voice Assistant.
Provides high-performance asynchronous SSE streaming, SQLite session persistence,
Whisper STT, Piper TTS, and dynamic local RAG / web search routing.
"""

import os
import sys
import io
import time
import json
import logging
import asyncio
import threading
import subprocess
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import (
    DATA_DIR,
    TEMPLATES_DIR,
    STATIC_DIR,
    AUDIO_CACHE_DIR,
    BASE_DIR,
    LLM_MODEL,
    EMBED_MODEL,
    DB_PATH
)
from backend.database import DatabaseManager
from backend.assistant import LocalAssistant
from ai_infra.voice_stt import SpeechToText
from ai_infra.voice_tts import TextToSpeech
from intelligence.schemas import (
    ChatRequest,
    SessionCreateRequest,
    SessionTitleUpdateRequest,
    SessionResponse,
    MessageResponse,
    SystemStatusResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FastAPI-App")

# Initialize FastAPI application
app = FastAPI(
    title="Local AI Assistant API",
    version="2.0.0",
    description="Asynchronous local AI assistant with SQLite persistence, streaming SSE, Piper TTS, Whisper STT, and dynamic RAG/Web routing."
)

# Enable CORS for frontend development (e.g. Vite React on localhost:5173, localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core AI & Assistant services
assistant = LocalAssistant()
stt = SpeechToText()
tts = TextToSpeech()

# Mount static asset folders
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
app.mount("/static/audio", StaticFiles(directory=AUDIO_CACHE_DIR), name="audio")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_system_vram() -> str:
    """Get real-time GPU VRAM usage."""
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            text=True
        ).strip()
        used, total = output.split(",")
        return f"{used.strip()} MB / {total.strip()} MB"
    except Exception:
        return "N/A"


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize to speech")


# ==========================================
# Root & Health Endpoints
# ==========================================

@app.get("/", include_in_schema=False)
async def root():
    """Serve legacy UI template if present, or redirect to API documentation."""
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "ok", "message": "Local AI Assistant API running. Visit /docs for OpenAPI specifications."}


@app.get("/api/system_status", response_model=SystemStatusResponse)
async def system_status():
    """Retrieve real-time GPU VRAM, active LLM/Embedding models, and document count."""
    return SystemStatusResponse(
        vram=get_system_vram(),
        llm_model=f"{LLM_MODEL} (100% on GPU)",
        embed_model=f"{EMBED_MODEL} (GPU)",
        rag_docs_count=len(assistant.rag.index)
    )


# ==========================================
# Session Management Endpoints (CRUD)
# ==========================================

@app.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """List all saved chat sessions ordered by most recent activity."""
    return DatabaseManager.list_sessions()


@app.post("/api/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(req: Optional[SessionCreateRequest] = None):
    """Create a new chat session thread."""
    title = req.title if (req and req.title) else "New Chat"
    session_id = DatabaseManager.create_session(title=title)
    session = DatabaseManager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to initialize session")
    return session


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Fetch session metadata and full chronological turn history."""
    session = DatabaseManager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = DatabaseManager.get_messages(session_id)
    return {
        "session": session,
        "messages": messages
    }


@app.patch("/api/sessions/{session_id}", response_model=SessionResponse)
async def update_session_title(session_id: str, req: SessionTitleUpdateRequest):
    """Rename a session thread."""
    success = DatabaseManager.update_session_title(session_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return DatabaseManager.get_session(session_id)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session thread and cascade delete its messages."""
    success = DatabaseManager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": f"Session '{session_id}' deleted successfully"}


# ==========================================
# Chat & Streaming SSE Endpoints
# ==========================================

@app.post("/api/chat_stream")
async def chat_stream(req: ChatRequest):
    """Stream token generation with real-time SSE events and SQLite persistence.
    
    Yields JSON events:
      - {"type": "status", "message": "..."}
      - {"type": "metadata", "session_id": "...", "analysis": {...}, "web_sources": [...], "doc_sources": [...]}
      - {"type": "token", "token": "..."}
      - {"type": "done", "session_id": "...", "answer": "...", "latencies": {...}}
      - {"type": "audio", "session_id": "...", "audio_url": "...", "tts_seconds": ...}
    """
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    logger.info(f"\n>>> [FastAPI Stream Request]: \"{user_message}\"")

    # 1. Resolve or create active session
    session_id = DatabaseManager.get_or_create_session(req.session_id, first_message=user_message)

    # 2. Retrieve multi-turn history from SQLite for LLM prompt context
    history = DatabaseManager.get_chat_history_for_llm(session_id, last_k=6)

    # 3. Non-blocking asynchronous bridge between Ollama sync generator and FastAPI SSE
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def worker_thread():
        full_answer = ""
        final_latencies: Dict[str, Any] = {}
        analysis_dict: Dict[str, Any] = {}

        try:
            for event in assistant.generate_stream(
                user_prompt=user_message,
                chat_history=history,
                use_web=req.use_web,
                use_rag=req.use_rag
            ):
                event["session_id"] = session_id

                if event.get("type") == "metadata":
                    analysis_dict = event.get("analysis", {})

                elif event.get("type") == "done":
                    full_answer = event.get("answer", "")
                    logger.info(f"<<< [FastAPI Bot Answer]: \"{full_answer}\"\n")
                    final_latencies = event.get("latencies", {})
                    final_latencies["stt_seconds"] = req.stt_seconds
                    final_latencies["tts_seconds"] = 0.0
                    event["audio_url"] = ""
                    event["latencies"] = final_latencies

                    # Deliver 'done' event immediately so client renders complete text
                    loop.call_soon_threadsafe(queue.put_nowait, event)

                    # Synthesize voice TTS asynchronously without blocking text response
                    audio_url = ""
                    if req.enable_tts and full_answer:
                        audio_url, tts_time = tts.synthesize(full_answer)
                        final_latencies["tts_seconds"] = tts_time
                        audio_event = {
                            "type": "audio",
                            "session_id": session_id,
                            "audio_url": audio_url,
                            "tts_seconds": tts_time
                        }
                        loop.call_soon_threadsafe(queue.put_nowait, audio_event)

                    # Persist user message with routing telemetry into SQLite
                    DatabaseManager.add_message(
                        session_id=session_id,
                        role="user",
                        content=user_message,
                        intent=analysis_dict.get("intent") or analysis_dict.get("primary_intent"),
                        needs_web_search=bool(analysis_dict.get("needs_web_search", False)),
                        needs_rag=bool(analysis_dict.get("needs_rag", False)),
                        needs_code=bool(analysis_dict.get("needs_code", False)),
                        desired_depth=analysis_dict.get("desired_depth"),
                        audio_url="",
                        latencies={"stt_seconds": req.stt_seconds}
                    )

                    # Persist assistant reply into SQLite
                    DatabaseManager.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=full_answer,
                        intent=None,
                        audio_url=audio_url,
                        latencies=final_latencies
                    )
                    return

                loop.call_soon_threadsafe(queue.put_nowait, event)

        except Exception as exc:
            logger.error(f"Stream generation error: {exc}", exc_info=True)
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "error", "error": str(exc), "session_id": session_id}
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=worker_thread, daemon=True).start()

    async def sse_event_stream():
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/chat")
async def chat_batch(req: ChatRequest):
    """Synchronous non-streaming chat endpoint (ideal for quick tests or CLI)."""
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    session_id = DatabaseManager.get_or_create_session(req.session_id, first_message=user_message)
    history = DatabaseManager.get_chat_history_for_llm(session_id, last_k=6)

    result = assistant.generate_response(
        user_prompt=user_message,
        chat_history=history,
        use_web=req.use_web,
        use_rag=req.use_rag
    )

    audio_url = ""
    tts_time = 0.0
    if req.enable_tts and result.get("answer"):
        audio_url, tts_time = tts.synthesize(result["answer"])

    latencies = result.get("latencies", {})
    latencies["tts_seconds"] = tts_time
    latencies["stt_seconds"] = req.stt_seconds

    analysis = result.get("analysis") or {}

    # Save turns to SQLite
    DatabaseManager.add_message(
        session_id=session_id,
        role="user",
        content=user_message,
        intent=analysis.get("intent") or analysis.get("primary_intent"),
        needs_web_search=bool(analysis.get("needs_web_search", False)),
        needs_rag=bool(analysis.get("needs_rag", False)),
        needs_code=bool(analysis.get("needs_code", False)),
        desired_depth=analysis.get("desired_depth"),
        latencies={"stt_seconds": req.stt_seconds}
    )

    DatabaseManager.add_message(
        session_id=session_id,
        role="assistant",
        content=result.get("answer", ""),
        audio_url=audio_url,
        latencies=latencies
    )

    return {
        "session_id": session_id,
        "reply": result.get("answer", ""),
        "audio_url": audio_url,
        "web_sources": result.get("web_sources", []),
        "doc_sources": result.get("doc_sources", []),
        "latencies": latencies,
        "vram": get_system_vram()
    }


# ==========================================
# Audio STT & TTS Endpoints
# ==========================================

@app.post("/api/tts")
async def synthesize_tts(req: TTSRequest):
    """Synthesize text to speech using Piper ONNX."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    audio_url, tts_time = tts.synthesize(text)
    return {"audio_url": audio_url, "tts_seconds": tts_time}


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Transcribe voice audio in memory using local Faster-Whisper."""
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    audio_stream = io.BytesIO(content)
    text, stt_time = stt.transcribe(audio_stream)
    return {"text": text, "stt_seconds": stt_time}


# ==========================================
# Documents & RAG Management Endpoints
# ==========================================

@app.get("/api/documents")
async def list_documents():
    """List indexed documents in the local knowledge base."""
    files = []
    if os.path.exists(DATA_DIR):
        files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith((".txt", ".md", ".pdf"))]
    return {
        "documents": files,
        "indexed_chunks": len(assistant.rag.index)
    }


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document to the local knowledge base and trigger vector indexing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    safe_name = os.path.basename(file.filename)
    dest_path = os.path.join(DATA_DIR, safe_name)

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    indexed_count = assistant.rag.index_documents()
    return {
        "message": f"Successfully uploaded and indexed '{safe_name}'.",
        "total_chunks": indexed_count
    }


@app.post("/api/documents/reindex")
async def reindex_documents():
    """Trigger manual re-indexing of all documents."""
    count = assistant.rag.index_documents()
    return {"message": f"Re-indexed {count} document chunks."}


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print(">> Starting Local AI Voice Assistant (FastAPI) on http://127.0.0.1:5000")
    print(f">> Initial VRAM: {get_system_vram()}")
    print("=" * 60 + "\n")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=5000, reload=False, log_level="info")
