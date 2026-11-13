import os
import time
import logging
from faster_whisper import WhisperModel
from backend.config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceSTT")

class SpeechToText:
    """Local Speech-to-Text engine using faster-whisper on CPU int8 mode."""

    def __init__(self):
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            logger.info(f"Loading Whisper '{WHISPER_MODEL}' on {WHISPER_DEVICE} ({WHISPER_COMPUTE_TYPE})...")
            self.model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.warning(f"Error loading on preferred device: {e}. Fallback to CPU int8.")
            self.model = WhisperModel("base", device="cpu", compute_type="int8")

    def transcribe(self, audio_input) -> tuple:
        """Transcribe audio file path or in-memory binary stream to text. Returns (transcribed_text, elapsed_seconds)."""
        if isinstance(audio_input, str) and not os.path.exists(audio_input):
            return "", 0.0

        t0 = time.time()
        try:
            segments, info = self.model.transcribe(
                audio_input,
                beam_size=3,
                language="en",
                condition_on_previous_text=False
            )
            text = " ".join([seg.text.strip() for seg in segments]).strip()
            elapsed = round(time.time() - t0, 3)
            logger.info(f"Transcribed in {elapsed}s: '{text}'")
            return text, elapsed
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return "", round(time.time() - t0, 3)
