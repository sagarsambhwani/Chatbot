"""Background worker thread for asynchronous SSE token streaming and persistence."""

import asyncio
from backend.deps import assistant, tts
from backend.database import DatabaseManager
from intelligence.schemas import ChatRequest

def run_stream_worker(req: ChatRequest, session_id: str, history: list, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Bridge synchronous generator events into async SSE queue."""
    full_answer, final_latencies, analysis_dict = "", {}, {}
    try:
        for event in assistant.generate_stream(req.message.strip(), chat_history=history, use_web=req.use_web, use_rag=req.use_rag):
            event["session_id"] = session_id
            if event.get("type") == "metadata":
                analysis_dict = event.get("analysis", {})
            elif event.get("type") == "done":
                full_answer = event.get("answer", "")
                final_latencies = {**event.get("latencies", {}), "stt_seconds": req.stt_seconds, "tts_seconds": 0.0}
                event["latencies"] = final_latencies
                loop.call_soon_threadsafe(queue.put_nowait, event)

                audio_url = ""
                if req.enable_tts and full_answer:
                    audio_url, tts_time = tts.synthesize(full_answer)
                    final_latencies["tts_seconds"] = tts_time
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "audio", "session_id": session_id, "audio_url": audio_url, "tts_seconds": tts_time})

                DatabaseManager.add_message(
                    session_id, "user", req.message.strip(), intent=analysis_dict.get("intent"),
                    needs_web_search=bool(analysis_dict.get("needs_web_search")), needs_rag=bool(analysis_dict.get("needs_rag")),
                    needs_code=bool(analysis_dict.get("needs_code")), desired_depth=analysis_dict.get("desired_depth"),
                    latencies={"stt_seconds": req.stt_seconds}
                )
                DatabaseManager.add_message(session_id, "assistant", full_answer, audio_url=audio_url, latencies=final_latencies)
                return
            loop.call_soon_threadsafe(queue.put_nowait, event)
    except Exception as exc:
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(exc), "session_id": session_id})
    finally:
        loop.call_soon_threadsafe(queue.put_nowait, None)
