# Chatbot - Local AI Voice Assistant (Ollama + Qwen2.5)

A voice-controlled local AI assistant with a **Conversational Intelligence Layer**, **Live Web Search**, **Document RAG**, **Speech-to-Text (STT)**, and **Neural Text-to-Speech (TTS)** that runs completely on your machine with **zero cloud dependencies** and **zero RAM overload**.

---

## Architecture Overview

```
Chatbot/
├── intelligence/              # Conversational Intelligence Layer
│   ├── schemas.py             # Pydantic v2 schemas (ConversationAnalysis, ResponsePlan)
│   ├── analyzer.py            # Structured LLM-powered context & intent analyzer
│   └── response_planner.py    # Deterministic (zero-LLM) response blueprint planner
│
├── prompts/                   # Externalized System Prompts
│   ├── analyzer.txt           # Intent & dimension analysis prompt
│   └── response_generator.txt # Natural conversational response generation prompt
│
├── ai_infra/                  # AI & ML Infrastructure Engines
│   ├── llm_client.py          # Persistent Ollama client with structured JSON output support
│   ├── rag_engine.py          # Vector embedding (nomic-embed-text) & cosine similarity
│   ├── search_engine.py       # 3-tier resilient search (DDG API -> DDGS -> Wikipedia)
│   ├── voice_stt.py           # Speech-To-Text (faster-whisper CPU int8)
│   └── voice_tts.py           # Text-To-Speech (Piper neural TTS ONNX)
│
├── backend/                   # Server & API Orchestration Layer
│   ├── app.py                 # Flask server, SSE streaming, file uploads, audio caching
│   ├── assistant.py           # Intelligence-driven orchestration & context synthesis
│   └── config.py              # Centralized environment configurations & path constants
│
├── frontend/                  # Web Client & Assets
│   ├── templates/
│   │   └── index.html         # Antigravity linen UI with real-time SSE
│   └── static/
│       └── audio/             # Generated TTS speech audio cache
│
├── tests/                     # Verification & Regression Test Suite
│   ├── test_planner.py        # Deterministic planner unit tests (6 key scenarios)
│   ├── test_analyzer.py       # Analyzer unit tests with mocked LLM client
│   ├── test_intelligence_integration.py # Live model integration tests
│   ├── test_rag.py            # Vector embedding & document retrieval test
│   ├── test_stt.py            # Whisper speech transcription test
│   ├── test_tts.py            # Piper neural voice synthesis test
│   ├── test_web_search.py     # Intent filter & web search test
│   └── verify_e2e.py          # Full end-to-end pipeline test
│
├── data/docs/                 # Local RAG knowledge base (.pdf, .txt, .md)
├── voices/                    # Piper ONNX neural voice model files
├── run.py                     # Root entry point: python run.py
├── start_assistant.bat        # 1-click launcher
└── requirements.txt
```

---

## Request Lifecycle

```
User Message
    │
    ▼
Bounded Conversation History (Recent 6 turns)
    │
    ▼
Conversation Analyzer (1 structured LLM call, temp=0, num_predict=256)
    │
    ▼
Response Planner (Deterministic Python logic, 0 LLM calls)
    │
    ▼
Tool Router Policy
    ├── Web Search (Triggered only if analysis.needs_web_search AND use_web)
    └── Document RAG (Triggered only if analysis.needs_rag AND use_rag)
    │
    ▼
Context Builder (Incorporate ResponsePlan + Citations + Retrieved Excerpts)
    │
    ▼
Response Generator (Single final streaming LLM generation, Qwen2.5 on GPU)
    │
    ▼
SSE Streaming UI & Neural Spoken Audio Output
```

---

## Intelligence Layer Responsibilities

### 1. Conversation Analyzer (`intelligence/analyzer.py`)
- **Single Structured Call**: Interacts with local Ollama via native JSON Schema constraints.
- **Dimensional Extraction**:
  - `intent`: factual, conceptual_learning, technical_help, coding, troubleshooting, creative, research, casual, ambiguous.
  - `topic`: Central subject or entity.
  - `knowledge_level`: beginner, intermediate, advanced, unknown (prefers unknown over unsupported assumptions).
  - `desired_depth`: brief, normal, deep.
  - `needs_example`, `needs_analogy`, `needs_code`.
  - `needs_web_search`, `needs_rag`.
  - `needs_clarification`, `clarification_question`.
- **Fault-Tolerant Fallback**: If the analyzer call times out, encounters malformed output, or fails schema validation, it safely defaults to a conservative fallback without interrupting the user.

### 2. Deterministic Response Planner (`intelligence/response_planner.py`)
- **Zero Additional LLM Calls**: Executes purely in Python (< 1ms).
- **Adaptive Structuring**:
  - Maps `desired_depth` to `target_length` (brief $\to$ short, normal $\to$ medium, deep $\to$ long).
  - Selects `explanation_style` (simple, progressive, technical, conversational).
  - Generates recommended section progressions (e.g. troubleshooting includes problem verification; coding includes approach and code walkthrough).
  - Dynamically prunes sections for brief responses to avoid unnecessary headings for simple answers.

### 3. Tool Routing Policy
- Treats analyzer flags (`needs_web_search`, `needs_rag`) as **policy recommendations**.
- Respects explicit caller overrides (`use_web=False`, `use_rag=False`).
- If neither tool is needed, external calls are bypassed entirely, saving latency and network/CPU cycles.

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
| **Total VRAM / RAM** | | | **~1.7 - 2.0 GB / 4.0 GB VRAM** (~150 MB RAM) |

---

## How to Run & Test

### Run the Application
Double-click:
```bat
start_assistant.bat
```
Or start manually via the virtual environment:
```powershell
.\.venv\Scripts\python.exe run.py
```
Then navigate to **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

### Run the Test Suite
Always execute with the project's virtual environment:

```powershell
# 1. Deterministic Planner Unit Tests (6 scenarios)
.\.venv\Scripts\python.exe tests\test_planner.py

# 2. Analyzer Unit Tests (Mocked LLM, edge cases & fallbacks)
.\.venv\Scripts\python.exe tests\test_analyzer.py

# 3. Live Model Integration Tests (Ollama Qwen2.5 structured output)
.\.venv\Scripts\python.exe tests\test_intelligence_integration.py

# 4. RAG Vector Index Test
.\.venv\Scripts\python.exe tests\test_rag.py

# 5. Hybrid Web Search Test
.\.venv\Scripts\python.exe tests\test_web_search.py

# 6. Neural TTS Voice Test
.\.venv\Scripts\python.exe tests\test_tts.py

# 7. Speech-to-Text Transcription Test
.\.venv\Scripts\python.exe tests\test_stt.py

# 8. Full End-to-End Pipeline Verification
.\.venv\Scripts\python.exe tests\verify_e2e.py
```

---

## Troubleshooting Ollama Structured Output

1. **Verify Ollama Version**: Ensure Ollama is version 0.1.48+ (structured output support via JSON Schema).
2. **Schema `required` Enforcement**: If a smaller model (such as `qwen2.5:1.5b`) omits optional fields, ensure `schema["required"]` explicitly lists the fields so the Ollama grammar engine enforces their generation.
3. **Keep-Alive Configuration**: Always set `"keep_alive": -1` in requests to prevent Ollama from repeatedly loading/unloading models from VRAM between the analysis and generation steps.
4. **VRAM Dual-Model Concurrency**: When running both `qwen2.5:1.5b` and `nomic-embed-text`, launch Ollama with `$env:OLLAMA_MAX_LOADED_MODELS='2'` to prevent thrashing.
