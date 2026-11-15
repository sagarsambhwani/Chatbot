"""Shared dependencies and singletons for FastAPI services."""

import subprocess
from backend.assistant import LocalAssistant
from ai_infra.voice_stt import SpeechToText
from ai_infra.voice_tts import TextToSpeech

assistant = LocalAssistant()
stt = SpeechToText()
tts = TextToSpeech()

def get_system_vram() -> str:
    """Retrieve real-time GPU VRAM utilization."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            text=True
        ).strip()
        used, total = out.split(",")
        return f"{used.strip()} MB / {total.strip()} MB"
    except Exception:
        return "N/A"

