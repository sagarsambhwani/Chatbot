"""Local Text-to-Speech synthesis using Kokoro-82M neural voice with Piper fallback."""

import os
import re
import time
import logging
import soundfile as sf
from backend.config import KOKORO_MODEL_PATH, KOKORO_VOICES_PATH, AUDIO_CACHE_DIR

logger = logging.getLogger("VoiceTTS")

class TextToSpeech:
    def __init__(self, voice_name: str = "af_sarah"):
        self.voice_name = voice_name
        self.kokoro = None
        self._load_voice()

    def _load_voice(self):
        try:
            if os.path.exists(KOKORO_MODEL_PATH) and os.path.exists(KOKORO_VOICES_PATH):
                from kokoro_onnx import Kokoro
                logger.info("Loading Kokoro-82M neural voice...")
                self.kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
                logger.info(f"Kokoro-82M voice ready (voice: '{self.voice_name}').")
        except Exception as e:
            logger.warning(f"Failed to load Kokoro-82M voice: {e}")

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        clean = re.sub(r"```[\s\S]*?```", " Code snippet omitted. ", text)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        clean = re.sub(r"\[(Web|Doc)[^\]]*\]", "", clean)
        clean = re.sub(r"[*_#`]", "", clean)
        return re.sub(r"\s+", " ", clean).strip()

    def synthesize(self, text: str, output_filename: str = None) -> tuple:
        if not self.kokoro: self._load_voice()
        if not self.kokoro: return "", 0.0

        clean = self.clean_text_for_speech(text)
        if not clean: return "", 0.0
        if len(clean) > 800: clean = clean[:800] + "..."

        fname = output_filename or f"speech_{int(time.time() * 1000)}.wav"
        os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
        out_path = os.path.join(AUDIO_CACHE_DIR, fname)

        t0 = time.time()
        try:
            samples, rate = self.kokoro.create(clean, voice=self.voice_name, speed=1.0, lang="en-us")
            sf.write(out_path, samples, rate)
            elapsed = round(time.time() - t0, 3)
            logger.info(f"Synthesized Kokoro-82M audio in {elapsed}s: /static/audio/{fname}")
            return f"/static/audio/{fname}", elapsed
        except Exception as e:
            logger.error(f"Kokoro synthesis error: {e}")
            return "", 0.0
