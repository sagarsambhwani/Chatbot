import os
import wave
import inspect
from piper.voice import PiperVoice

def test_tts():
    model_path = os.path.join("voices", "en_US-lessac-medium.onnx")
    config_path = os.path.join("voices", "en_US-lessac-medium.onnx.json")
    
    print("Loading Piper voice model...")
    voice = PiperVoice.load(model_path, config_path=config_path)
    print("Voice config sample rate:", voice.config.sample_rate)
    print("Methods:", [m for m in dir(voice) if not m.startswith("_")])
    
    output_wav = "test_output.wav"
    text = "Hello! I am your local voice assistant powered by Ollama and Qwen 2.5."
    
    print(f"Synthesizing: '{text}'...")
    with wave.open(output_wav, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
        
    print(f"Synthesis successful! Created '{output_wav}' ({os.path.getsize(output_wav)} bytes)")

if __name__ == "__main__":
    test_tts()
