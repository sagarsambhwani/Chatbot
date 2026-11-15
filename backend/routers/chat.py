"""Chat endpoints for real-time SSE streaming and synchronous responses."""

import json
import asyncio
import threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.deps import assistant, tts, get_system_vram
from backend.database import DatabaseManager
from backend.routers.stream_worker import run_stream_worker
from intelligence.schemas import ChatRequest

router = APIRouter(prefix="/api", tags=["Chat"])

@router.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    session_id = DatabaseManager.get_or_create_session(req.session_id, first_message=req.message.strip())
    history = DatabaseManager.get_chat_history_for_llm(session_id, last_k=6)
    queue: asyncio.Queue = asyncio.Queue()
    threading.Thread(target=run_stream_worker, args=(req, session_id, history, queue, asyncio.get_running_loop()), daemon=True).start()

    async def sse_gen():
        while True:
            ev = await queue.get()
            if ev is None: break
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(sse_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.post("/chat")
async def chat_batch(req: ChatRequest):
    msg = req.message.strip()
    if not msg: raise HTTPException(status_code=400, detail="Empty message")
    session_id = DatabaseManager.get_or_create_session(req.session_id, first_message=msg)
    history = DatabaseManager.get_chat_history_for_llm(session_id, last_k=6)
    res = assistant.generate_response(msg, chat_history=history, use_web=req.use_web, use_rag=req.use_rag)

    audio_url, tts_time = ("", 0.0)
    if req.enable_tts and res.get("answer"):
        audio_url, tts_time = tts.synthesize(res["answer"])
    lat = {**res.get("latencies", {}), "tts_seconds": tts_time, "stt_seconds": req.stt_seconds}
    analysis = res.get("analysis") or {}

    DatabaseManager.add_message(session_id, "user", msg, intent=analysis.get("intent"), needs_web_search=bool(analysis.get("needs_web_search")),
        needs_rag=bool(analysis.get("needs_rag")), needs_code=bool(analysis.get("needs_code")), desired_depth=analysis.get("desired_depth"), latencies={"stt_seconds": req.stt_seconds})
    DatabaseManager.add_message(session_id, "assistant", res.get("answer", ""), audio_url=audio_url, latencies=lat)
    return {"session_id": session_id, "reply": res.get("answer", ""), "audio_url": audio_url, "web_sources": res.get("web_sources", []), "doc_sources": res.get("doc_sources", []), "latencies": lat, "vram": get_system_vram()}
