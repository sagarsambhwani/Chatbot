import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_infra.voice_tts import TextToSpeech

def test_tts():
    print("=" * 60)
    print("Testing AI Infra TextToSpeech (Piper TTS ONNX)")
    print("=" * 60)

    tts = TextToSpeech()
    text = "Hello! I am your local voice assistant, refactored into modular backend, frontend, and AI infrastructure."
    out_path, elapsed = tts.synthesize(text)
    print(f"Synthesized speech in {elapsed}s: {out_path}")

if __name__ == "__main__":
    test_tts()
