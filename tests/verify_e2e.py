import requests
import json

def test_api():
    url = "http://127.0.0.1:5000/api/chat"
    payload = {
        "message": "What is the GPU used in this assistant and how does it prevent RAM overload? Also, mention what the weather is like in Tokyo right now.",
        "history": [],
        "use_web": True,
        "use_rag": True,
        "enable_tts": True
    }

    print("Sending request to Assistant API on http://127.0.0.1:5000...")
    res = requests.post(url, json=payload, timeout=90)
    data = res.json()

    print("\n" + "=" * 60)
    print("ASSISTANT REPLY:")
    print("=" * 60)
    print(data.get("reply"))
    print("\n" + "=" * 60)
    print("CITATIONS & METADATA:")
    print("=" * 60)
    print("Web Sources:", len(data.get("web_sources", [])))
    for w in data.get("web_sources", []):
        print(f" - [Web: {w['title']}] ({w['link']})")

    print("\nDocument Sources:", len(data.get("doc_sources", [])))
    for d in data.get("doc_sources", []):
        print(f" - [Doc: {d['source']}] (Score: {d['score']:.2f})")

    print("\nAudio URL:", data.get("audio_url"))
    print("VRAM Status:", data.get("vram"))

if __name__ == "__main__":
    test_api()
