"""Voice synthesis (Piper TTS) and audio transcription (Whisper STT)."""

import io
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from backend.deps import tts, stt

router = APIRouter(prefix="/api", tags=["Audio"])

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize to speech")

@router.post("/tts")
async def synthesize_tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    audio_url, tts_time = tts.synthesize(text)
    return {"audio_url": audio_url, "tts_seconds": tts_time}

@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio payload")
    text, stt_time = stt.transcribe(io.BytesIO(content))
    return {"text": text, "stt_seconds": stt_time}

