import os
import re
import wave
import time
import logging
from piper.voice import PiperVoice
from config import PIPER_MODEL_PATH, PIPER_CONFIG_PATH, BASE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceTTS")

class TextToSpeech:
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
                logger.warning("Piper voice files not found.")
        except Exception as e:
            logger.error(f"Failed to load Piper voice: {e}")

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        """Strip markdown syntax, URLs, citations, code blocks for speech synthesis."""
        # Remove code blocks
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
        # Remove excessive whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def synthesize(self, text: str, output_filename: str = None) -> str:
        """Synthesize text into a WAV file. Returns relative path to the generated WAV."""
        if not self.voice:
            self._load_voice()
        if not self.voice:
            logger.error("TTS voice unavailable.")
            return ""

        spoken_text = self.clean_text_for_speech(text)
        if not spoken_text:
            return ""

        # Limit spoken text length if necessary for speed
        if len(spoken_text) > 1000:
            spoken_text = spoken_text[:1000] + "..."

        if not output_filename:
            output_filename = f"speech_{int(time.time() * 1000)}.wav"

        audio_dir = os.path.join(BASE_DIR, "static", "audio")
        os.makedirs(audio_dir, exist_ok=True)
        out_path = os.path.join(audio_dir, output_filename)

        try:
            with wave.open(out_path, "wb") as wav_file:
                self.voice.synthesize_wav(spoken_text, wav_file)
            return f"/static/audio/{output_filename}"
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return ""
