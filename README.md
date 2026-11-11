# Chatbot - Local AI Voice Assistant (Ollama + Qwen2.5)

A voice-controlled local AI assistant with **live Web Search**, **Document RAG**, **Speech-to-Text (STT)**, and **Neural Text-to-Speech (TTS)** that runs completely on your machine with **zero cloud dependencies** and **zero RAM overload**.

---

## 3-Tier Modular Architecture

```
Chatbot/
├── ai_infra/                  # AI & ML Infrastructure Engines
│   ├── llm_client.py          # Ollama client with GPU VRAM persistence
│   ├── rag_engine.py          # Vector embedding & similarity retrieval
│   ├── search_engine.py       # 3-tier resilient web search & intent filter
│   ├── voice_stt.py           # Speech-To-Text (faster-whisper CPU int8)
│   └── voice_tts.py           # Text-To-Speech (Piper neural TTS ONNX)
├── backend/                   # Server & API Layer
│   ├── app.py                 # Flask server & SSE token streaming
│   ├── assistant.py           # Context synthesis & orchestration
│   └── config.py              # Centralized environment & paths
├── frontend/                  # Web Client & Assets
│   ├── templates/
│   │   └── index.html         # Antigravity linen UI with real-time SSE
│   └── static/
│       └── audio/             # Generated TTS speech cache
├── tests/                     # Verification test suite
│   ├── test_ollama.py
│   ├── test_rag.py
│   ├── test_stt.py
│   ├── test_tts.py
│   ├── test_web_search.py
│   └── verify_e2e.py
├── data/docs/                 # Local RAG knowledge base
├── voices/                    # Piper ONNX neural voice models
├── run.py                     # Root entry point
├── start_assistant.bat        # 1-click launcher
└── requirements.txt
```

---

## Hardware Optimization & Resource Allocation

| Component | Technology | Target Device | Memory Usage |
| :--- | :--- | :--- | :--- |
| **LLM** | Ollama (`qwen2.5:1.5b`) | **100% GPU VRAM** | ~1.15 GB VRAM |
| **Vector Embeddings** | Ollama (`nomic-embed-text`) | **GPU VRAM** | ~274 MB VRAM |
| **Speech-to-Text (STT)** | `faster-whisper` (`base`) | **CPU int8** | < 80 MB RAM |
| **Text-to-Speech (TTS)** | `piper-tts` (`en_US-lessac-medium`) | **ONNX runtime** | ~60 MB RAM |
| **Web Search** | DuckDuckGo (`ddgs` / API fallback) | **Network** | 0 MB RAM |
| **Document RAG** | Vector Index (`pypdf` + cosine sim) | **Local DB** | < 20 MB RAM |
| **Total VRAM / RAM** | | | **~1.7 GB / 4.0 GB VRAM** (~150 MB RAM) |

---

## Features

1. **Push-to-Talk Voice STT:** Real-time microphone capture in the web UI using `faster-whisper` running lightweight `int8` on CPU.
2. **Neural Spoken Responses (TTS):** Automatic speech playback with Piper's neural voice model (`lessac-medium`).
3. **Resilient Live Web Search:** 3-tier fallback (DuckDuckGo Instant API $\to$ DDGS $\to$ Wikipedia) with inline markdown citations `[Web: Title](URL)`.
4. **Document Knowledge Base (RAG):** Upload `.pdf`, `.txt`, and `.md` files through the UI. Passages are embedded using Ollama's `nomic-embed-text` on GPU and cited as `[Doc: filename.ext]`.
5. **Real-time Streaming & Collapsible Thought Steps:** Server-Sent Events (SSE) token-by-token streaming with collapsible reasoning steps and live GPU VRAM telemetry.

---

## How to Run

Double-click:
```bat
start_assistant.bat
```
Or start manually via virtual environment:
```powershell
.\.venv\Scripts\python.exe run.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.
