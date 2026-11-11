import os
import json
import math
import logging
from typing import List, Dict, Any
from pypdf import PdfReader
from backend.config import OLLAMA_BASE_URL, EMBED_MODEL, DATA_DIR, VECTOR_INDEX_FILE
from ai_infra.llm_client import OllamaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGEngine")

_llm_client = OllamaClient(base_url=OLLAMA_BASE_URL, embed_model=EMBED_MODEL)

def get_embedding(text: str) -> List[float]:
    """Get vector embedding from Ollama nomic-embed-text."""
    return _llm_client.get_embedding(text)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Break long documents into overlapping passages for accurate retrieval."""
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
        if i >= len(words) and len(chunks) > 0:
            break
    return chunks

class RAGEngine:
    """Local vector store using Ollama nomic-embed-text embeddings."""

    def __init__(self, data_dir: str = DATA_DIR, index_file: str = VECTOR_INDEX_FILE):
        self.data_dir = data_dir
        self.index_file = index_file
        self.index = []
        self.load_index()

    def load_index(self):
        """Load cached vector index from disk."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
                logger.info(f"Loaded {len(self.index)} chunks from index cache.")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self.index = []
        else:
            self.index_documents()

    def save_index(self):
        """Save vector index to disk."""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.index)} chunks to {self.index_file}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def extract_text(self, filepath: str) -> str:
        """Extract plain text from .pdf, .txt, or .md files."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in [".txt", ".md"]:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            try:
                reader = PdfReader(filepath)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text
            except Exception as e:
                logger.error(f"Failed reading PDF {filepath}: {e}")
                return ""
        return ""

    def index_documents(self) -> int:
        """Parse all documents in DATA_DIR, compute embeddings, and build index."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            return 0

        logger.info(f"Indexing documents in {self.data_dir}...")
        new_index = []
        for filename in os.listdir(self.data_dir):
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.isfile(filepath):
                continue

            raw_text = self.extract_text(filepath)
            if not raw_text.strip():
                continue

            chunks = chunk_text(raw_text)
            logger.info(f"Indexing '{filename}' ({len(chunks)} chunks)...")
            for idx, chunk in enumerate(chunks):
                emb = get_embedding(chunk)
                if emb:
                    new_index.append({
                        "source": filename,
                        "chunk_id": idx,
                        "text": chunk,
                        "embedding": emb
                    })

        self.index = new_index
        self.save_index()
        logger.info(f"Indexing complete. Total indexed chunks: {len(self.index)}")
        return len(self.index)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search top-K relevant chunks using vector cosine similarity."""
        if not self.index:
            return []

        q_emb = get_embedding(query)
        if not q_emb:
            return []

        scored = []
        for item in self.index:
            score = cosine_similarity(q_emb, item["embedding"])
            scored.append({
                "source": item["source"],
                "chunk_id": item["chunk_id"],
                "text": item["text"],
                "score": score
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        # Filter by threshold (e.g., minimum 0.35 similarity)
        relevant = [item for item in scored[:top_k] if item["score"] >= 0.35]
        return relevant

def format_rag_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved document chunks with citation instructions for the LLM."""
    if not chunks:
        return ""
    lines = ["\n[LOCAL DOCUMENT KNOWLEDGE BASE]"]
    for i, c in enumerate(chunks, 1):
        lines.append(f"{i}. Document: {c['source']} (Relevance Score: {c['score']:.2f})")
        lines.append(f"   Excerpt: {c['text']}\n")
    lines.append("Instructions for citations: When stating facts from the documents above, cite the document name inline: [Doc: filename.ext].\n")
    return "\n".join(lines)
