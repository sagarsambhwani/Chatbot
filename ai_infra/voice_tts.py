import os
import re
import wave
import time
import logging
from piper.voice import PiperVoice
from backend.config import PIPER_MODEL_PATH, PIPER_CONFIG_PATH, AUDIO_CACHE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceTTS")

class TextToSpeech:
    """Local Text-to-Speech synthesis using Piper TTS on ONNX Runtime."""

    def __init__(self):
        self.voice = None
        self._load_voice()

    def _load_voice(self):
        try:
            if os.path.exists(PIPER_MODEL_PATH) and os.path.exists(PIPER_CONFIG_PATH):
                logger.info(f"Loading Piper voice from {PIPER_MODEL_PATH}...")
                self.voice = PiperVoice.load(PIPER_MODEL_PATH, config_path=PIPER_CONFIG_PATH)
                logger.info("Piper voice model ready.")
            else:
                logger.warning(f"Piper voice files not found at {PIPER_MODEL_PATH}")
        except Exception as e:
            logger.error(f"Failed to load Piper voice: {e}")

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        """Strip markdown syntax and raw URLs so spoken output sounds natural."""
        # Code snippets
        clean = re.sub(r"```[\s\S]*?```", " Code snippet omitted. ", text)
        clean = re.sub(r"`.*?`", "", clean)
        # Convert markdown links [Text](URL) -> Text
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        # Remove markdown headers and bullets
        clean = re.sub(r"^[#\-\*]+\s*", "", clean, flags=re.MULTILINE)
        # Remove inline citation tags like [Web: ...] or [Doc: ...] for smoother voice
        clean = re.sub(r"\[(Web|Doc)[^\]]*\]", "", clean)
        # Remove extra asterisks and underscores
        clean = clean.replace("**", "").replace("*", "").replace("_", "")
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def synthesize(self, text: str, output_filename: str = None) -> tuple:
        """Synthesize text into WAV audio. Returns (audio_url, elapsed_seconds)."""
        if not self.voice:
            self._load_voice()
        if not self.voice:
            logger.error("TTS voice model is not loaded.")
            return "", 0.0

        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return "", 0.0

        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + "..."

        if not output_filename:
            output_filename = f"speech_{int(time.time() * 1000)}.wav"

        os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
        out_path = os.path.join(AUDIO_CACHE_DIR, output_filename)

        t0 = time.time()
        try:
            with wave.open(out_path, "wb") as wav_file:
                self.voice.synthesize_wav(clean_text, wav_file)
            elapsed = round(time.time() - t0, 3)
            audio_url = f"/static/audio/{output_filename}"
            logger.info(f"Synthesized TTS audio in {elapsed}s: {audio_url}")
            return audio_url, elapsed
        except Exception as e:
            logger.error(f"TTS Synthesis error: {e}")
            return "", 0.0
