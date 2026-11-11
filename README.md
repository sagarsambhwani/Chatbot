# Chatbot - Local AI Voice Assistant (Ollama + Qwen2.5)

A voice-controlled local AI assistant with **live Web Search**, **Document RAG**, **Speech-to-Text (STT)**, and **Neural Text-to-Speech (TTS)** that runs completely on your machine with **zero cloud dependencies** and **zero RAM overload**.

---

## Architecture & Hardware Optimization

| Component | Technology | Target Device | Memory Usage |
| :--- | :--- | :--- | :--- |
| **LLM** | Ollama (`qwen2.5:1.5b`) | **100% GPU VRAM** | ~1.15 GB VRAM |
| **Vector Embeddings** | Ollama (`nomic-embed-text`) | **GPU VRAM** | ~274 MB VRAM |
| **Speech-to-Text (STT)** | `faster-whisper` (`base`) | **CPU int8** | < 80 MB RAM |
| **Text-to-Speech (TTS)** | `piper-tts` (`en_US-lessac-medium`) | **ONNX runtime** | ~60 MB RAM |
| **Web Search** | DuckDuckGo (`ddgs`) | **Network** | 0 MB RAM |
| **Document RAG** | Vector Index (`pypdf` + cosine sim) | **Local DB** | < 20 MB RAM |
| **Total VRAM / RAM** | | | **~1.7 GB / 4.0 GB VRAM** (~150 MB RAM) |

---

## Features

1. **Voice Control:** Push-to-talk microphone button directly in the web UI. Speak your questions naturally; `faster-whisper` transcribes in under a second.
2. **Neural Spoken Responses:** Responses are automatically spoken aloud with Piper's neural voice model (`lessac-medium`).
3. **Live Web Search & Inline Citations:** The assistant searches DuckDuckGo for real-time information and generates clickable citations `[Web: Title](URL)`.
4. **Document Knowledge Base (RAG):** Upload `.pdf`, `.txt`, and `.md` files through the UI. Documents are chunked and embedded using Ollama's `nomic-embed-text` on GPU. The assistant cites the document name `[Doc: filename.ext]`.
5. **Real-time VRAM Monitor:** The top navigation bar displays live GPU VRAM usage.

---

## How to Run

Simply double-click:
```bat
start_assistant.bat
```
Or start manually:
```powershell
.\.venv\Scripts\python.exe app.py
```
Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.
