"""Background worker thread for asynchronous SSE token streaming and persistence."""

import asyncio
from backend.deps import assistant
from backend.database import DatabaseManager
from backend.routers.audio_streamer import AudioStreamQueue
from intelligence.schemas import ChatRequest

def run_stream_worker(req: ChatRequest, session_id: str, history: list, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Bridge synchronous generator events into async SSE queue with streaming audio."""
    full_answer, final_latencies, analysis_dict = "", {}, {}
    emit = lambda evt: loop.call_soon_threadsafe(queue.put_nowait, evt)
    audio_stream = AudioStreamQueue(session_id, emit, req.enable_tts)

    try:
        for event in assistant.generate_stream(req.message.strip(), chat_history=history, use_web=req.use_web, use_rag=req.use_rag):
            event["session_id"] = session_id
            if event.get("type") == "token":
                audio_stream.feed(event.get("token", ""))
            elif event.get("type") == "metadata":
                analysis_dict = event.get("analysis", {})
            elif event.get("type") == "done":
                full_answer = event.get("answer", "")
                final_audio = audio_stream.finish()
                final_latencies = {**event.get("latencies", {}), "stt_seconds": req.stt_seconds, "tts_seconds": round(audio_stream.total_time, 3)}
                event["latencies"] = final_latencies
                emit(event)
                if final_audio:
                    emit({"type": "audio", "session_id": session_id, "audio_url": final_audio, "tts_seconds": final_latencies["tts_seconds"]})

                DatabaseManager.add_message(
                    session_id, "user", req.message.strip(), intent=analysis_dict.get("intent"),
                    needs_web_search=bool(analysis_dict.get("needs_web_search")), needs_rag=bool(analysis_dict.get("needs_rag")),
                    needs_code=bool(analysis_dict.get("needs_code")), desired_depth=analysis_dict.get("desired_depth"),
                    latencies={"stt_seconds": req.stt_seconds}
                )
                DatabaseManager.add_message(session_id, "assistant", full_answer, audio_url=final_audio, latencies=final_latencies)
                return
            emit(event)
    except Exception as exc:
        emit({"type": "error", "error": str(exc), "session_id": session_id})
    finally:
        emit(None)
