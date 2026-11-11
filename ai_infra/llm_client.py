import json
import logging
import requests
from typing import Generator, List, Dict, Any
from backend.config import OLLAMA_BASE_URL, LLM_MODEL, EMBED_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMClient")

class OllamaClient:
    """Client for local Ollama LLM and Embeddings with GPU VRAM persistence."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, llm_model: str = LLM_MODEL, embed_model: str = EMBED_MODEL):
        self.base_url = base_url.rstrip("/")
        self.llm_model = llm_model
        self.embed_model = embed_model

    def is_healthy(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def stream_chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> Generator[str, None, None]:
        """Stream response tokens from Ollama LLM."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.llm_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            },
            "keep_alive": -1  # Keep model persistently in GPU VRAM
        }

        try:
            response = requests.post(url, json=payload, stream=True, timeout=120)
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
        except Exception as e:
            logger.error(f"Error streaming from Ollama: {e}")
            yield f"\n[Error communicating with local LLM: {e}]"

    def chat_complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """Non-streaming complete chat response."""
        tokens = list(self.stream_chat(messages, temperature=temperature))
        return "".join(tokens)

    def get_embedding(self, text: str) -> List[float]:
        """Get vector embedding using Ollama nomic-embed-text."""
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.embed_model,
            "prompt": text,
            "keep_alive": -1
        }
        try:
            res = requests.post(url, json=payload, timeout=60).json()
            return res.get("embedding", [])
        except Exception as e:
            logger.error(f"Error fetching embedding from Ollama: {e}")
            return []
