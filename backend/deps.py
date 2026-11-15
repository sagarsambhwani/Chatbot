"""Shared dependencies and singletons for FastAPI services."""

import time
import subprocess
from backend.assistant import LocalAssistant
from ai_infra.voice_stt import SpeechToText
from ai_infra.voice_tts import TextToSpeech

assistant = LocalAssistant()
stt = SpeechToText()
tts = TextToSpeech()
_vram_cache = ("", 0.0)

def get_system_vram() -> str:
    """Retrieve real-time GPU VRAM utilization (cached 15s, fully windowless)."""
    global _vram_cache
    now = time.time()
    if now - _vram_cache[1] < 15.0 and _vram_cache[0]:
        return _vram_cache[0]
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            text=True, creationflags=flags
        ).strip()
        used, total = out.split(",")
        val = f"{used.strip()} MB / {total.strip()} MB"
        _vram_cache = (val, now)
        return val
    except Exception:
        return _vram_cache[0] or "N/A"
