import os
import subprocess
from faster_whisper import WhisperModel

def check_vram():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            text=True
        ).strip()
        used, total = output.split(",")
        return f"{used.strip()} MB / {total.strip()} MB"
    except Exception as e:
        return f"Error reading VRAM: {e}"

def test_stt():
    print("=" * 60)
    print("Testing Speech-to-Text with faster-whisper")
    print(f"Initial VRAM: {check_vram()}")
    print("=" * 60)

    # Test CPU mode first to verify transcription speed and accuracy
    device = "cpu"
    compute_type = "int8"
    
    print(f"Loading Whisper model ('base') on {device.upper()} ({compute_type})...")
    model = WhisperModel("base", device=device, compute_type=compute_type)
    print("Whisper model loaded successfully on CPU!")

    audio_file = "test_output.wav"
    if not os.path.exists(audio_file):
        print(f"Audio file '{audio_file}' not found.")
        return

    print(f"\nTranscribing '{audio_file}'...")
    segments, info = model.transcribe(audio_file, beam_size=5)
    print(f"Detected language: '{info.language}' with probability {info.language_probability:.2f}")

    transcribed_text = ""
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        transcribed_text += segment.text

    print("\n" + "=" * 60)
    print(f"FINAL TRANSCRIBED TEXT: {transcribed_text.strip()}")
    print(f"VRAM after STT: {check_vram()}")
    print("=" * 60)

if __name__ == "__main__":
    test_stt()
