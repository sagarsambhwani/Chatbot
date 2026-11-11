import requests
import json
import subprocess

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
    print("Testing Ollama with Qwen2.5 (1.5b)")
    print(f"Initial VRAM Usage: {check_vram()}")
    print("=" * 60)

    url = "http://127.0.0.1:11434/api/chat"
    payload = {
        "model": "qwen2.5:1.5b",
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
        "options": {
            "num_gpu": 99  # Force all layers onto GPU
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
