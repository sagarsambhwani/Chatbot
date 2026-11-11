import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_infra.voice_stt import SpeechToText

def test_stt():
    print("=" * 60)
    print("Testing AI Infra SpeechToText (faster-whisper CPU int8)")
    print("=" * 60)

    stt = SpeechToText()
    audio_file = os.path.join(BASE_DIR, "test_output.wav")
    if not os.path.exists(audio_file):
        print(f"Sample audio file '{audio_file}' not found.")
        return

    text, elapsed = stt.transcribe(audio_file)
    print(f"Transcribed Text ({elapsed}s): '{text}'")

if __name__ == "__main__":
    test_stt()
