import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ollama Settings
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
LLM_MODEL = "qwen2.5:1.5b"  # Runs 100% in 4GB VRAM
EMBED_MODEL = "nomic-embed-text"

# Whisper STT Settings
WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"  # Fast int8 on CPU keeps all VRAM free for Ollama
WHISPER_COMPUTE_TYPE = "int8"

# Piper TTS Settings
PIPER_MODEL_PATH = os.path.join(BASE_DIR, "voices", "en_US-lessac-medium.onnx")
PIPER_CONFIG_PATH = os.path.join(BASE_DIR, "voices", "en_US-lessac-medium.onnx.json")

# Document / RAG Settings
DATA_DIR = os.path.join(BASE_DIR, "data", "docs")
VECTOR_INDEX_FILE = os.path.join(BASE_DIR, "data", "vector_index.json")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static", "audio"), exist_ok=True)
