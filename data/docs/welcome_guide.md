# Local Voice Assistant Manual & Architecture

## System Specifications
- **Host LLM**: Qwen2.5 1.5B running on local Ollama server (listening at `127.0.0.1:11434`).
- **GPU Acceleration**: 100% of inference layers run on NVIDIA GeForce GTX 1650 (4GB VRAM). Host system RAM is completely protected and remains under 2GB.
- **Voice Transcription (STT)**: faster-whisper (Base model) running lightweight int8 inference.
- **Voice Synthesis (TTS)**: Piper neural TTS model (en_US-lessac-medium) running offline ONNX synthesis.
- **Vector Search (RAG)**: GPU vector embeddings powered by Ollama nomic-embed-text.

## Supported File Types for Knowledge Base
You can drop `.txt`, `.md`, and `.pdf` files into the `data/docs/` folder or upload them directly via the web interface.
The assistant segments the documents into 250-word passages and indexes them into vector space.
When you ask a question about these documents, the assistant retrieves relevant excerpts and cites them using `[Doc: filename.ext]`.

## Web Search Integration
When the Web Search toggle is enabled, the assistant queries DuckDuckGo for live real-time information, extracts key snippets, and generates answers citing the online articles with clickable links `[Web: Title](URL)`.
