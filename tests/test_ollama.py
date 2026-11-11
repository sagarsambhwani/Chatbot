import sys
import os
import requests
import json
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import OLLAMA_BASE_URL, LLM_MODEL

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

def test_ollama():
    print("=" * 60)
    print(f"Testing Ollama with {LLM_MODEL}")
    print(f"Initial VRAM Usage: {check_vram()}")
    print("=" * 60)

    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Always format your responses clearly with markdown and cite sources using [Source: Name]."
            },
            {
                "role": "user",
                "content": "What is Python and why is it popular? Cite [Source: PythonDocs]."
            }
        ],
        "stream": False,
        "keep_alive": -1,
        "options": {
            "num_gpu": 99
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        data = response.json()
        print("\n--- LLM Response ---")
        print(data.get("message", {}).get("content", ""))
        print("\n" + "=" * 60)
        print(f"VRAM Usage during/after inference: {check_vram()}")
        print("=" * 60)
    except Exception as e:
        print(f"Error calling Ollama: {e}")

if __name__ == "__main__":
    test_ollama()
