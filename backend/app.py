"""FastAPI application entry point."""

import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import AUDIO_CACHE_DIR, STATIC_DIR
from backend.routers import system, sessions, chat, audio, documents

app = FastAPI(
    title="Local AI Assistant API",
    version="2.0.0",
    description="Asynchronous local AI assistant with SQLite persistence, Piper TTS, and Whisper STT."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
app.mount("/static/audio", StaticFiles(directory=AUDIO_CACHE_DIR), name="audio")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(system.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(audio.router)
app.include_router(documents.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=5000, reload=False, log_level="info")
