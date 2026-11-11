import os
import logging
from faster_whisper import WhisperModel
from config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceSTT")

class SpeechToText:
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

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file to text."""
        if not self.model:
            self._init_model()
        
        if not os.path.exists(audio_path):
            logger.error(f"Audio file '{audio_path}' does not exist.")
            return ""

        try:
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            full_text = " ".join([segment.text.strip() for segment in segments])
            logger.info(f"Transcribed ({info.language}): '{full_text}'")
            return full_text.strip()
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""
