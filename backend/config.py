import os

# Root project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ollama LLM & Embeddings Settings (Runs 100% in GPU VRAM)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:1.5b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

# Whisper STT Settings (Fast int8 on CPU protects VRAM for Ollama)
WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# Piper TTS Settings (Fast local neural voice on ONNX)
VOICES_DIR = os.path.join(BASE_DIR, "voices")
PIPER_MODEL_PATH = os.path.join(VOICES_DIR, "en_US-lessac-medium.onnx")
PIPER_CONFIG_PATH = os.path.join(VOICES_DIR, "en_US-lessac-medium.onnx.json")

# Document / RAG Settings
DATA_DIR = os.path.join(BASE_DIR, "data", "docs")
VECTOR_INDEX_FILE = os.path.join(BASE_DIR, "data", "vector_index.json")

# Frontend Directories
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
AUDIO_CACHE_DIR = os.path.join(STATIC_DIR, "audio")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VOICES_DIR, exist_ok=True)
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
