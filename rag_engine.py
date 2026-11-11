import os
import json
import math
import logging
import requests
from pypdf import PdfReader
from config import OLLAMA_BASE_URL, EMBED_MODEL, DATA_DIR, VECTOR_INDEX_FILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGEngine")

def get_embedding(text: str) -> list:
    """Get vector embedding from Ollama nomic-embed-text."""
    try:
        url = f"{OLLAMA_BASE_URL}/api/embeddings"
        payload = {"model": EMBED_MODEL, "prompt": text, "keep_alive": -1}
        res = requests.post(url, json=payload, timeout=60).json()
        return res.get("embedding", [])
    except Exception as e:
        logger.error(f"Error fetching embedding: {e}")
        return []

def cosine_similarity(v1: list, v2: list) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def extract_text_from_file(file_path: str) -> str:
    """Extract plain text from .txt, .md, or .pdf files."""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif ext == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
    return text

def chunk_text(text: str, chunk_size: int = 250, overlap: int = 40) -> list:
    """Split text into overlapping word chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

class RAGEngine:
    def __init__(self):
        self.index = []
        self.load_index()

    def load_index(self):
        if os.path.exists(VECTOR_INDEX_FILE):
            try:
                with open(VECTOR_INDEX_FILE, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
                logger.info(f"Loaded {len(self.index)} chunks from index cache.")
            except Exception as e:
                logger.error(f"Failed to load index cache: {e}")
                self.index = []

    def save_index(self):
        try:
            with open(VECTOR_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self.index, f, indent=2)
            logger.info("Saved vector index to disk.")
        except Exception as e:
            logger.error(f"Failed to save index cache: {e}")

    def index_documents(self) -> int:
        """Scan DATA_DIR, chunk all documents, and compute embeddings."""
        new_index = []
        files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith((".txt", ".md", ".pdf"))]
        
        for filename in files:
            file_path = os.path.join(DATA_DIR, filename)
            content = extract_text_from_file(file_path)
            chunks = chunk_text(content)
            logger.info(f"Processing '{filename}': {len(chunks)} chunks...")
            
            for idx, chunk in enumerate(chunks, 1):
                emb = get_embedding(chunk)
                if emb:
                    new_index.append({
                        "file": filename,
                        "chunk_id": idx,
                        "content": chunk,
                        "embedding": emb
                    })
        
        self.index = new_index
        self.save_index()
        return len(self.index)

    def search(self, query: str, top_k: int = 3, threshold: float = 0.45) -> list:
        """Find most relevant document chunks for query."""
        if not self.index:
            return []
        
        query_emb = get_embedding(query)
        if not query_emb:
            return []

        scored = []
        for item in self.index:
            score = cosine_similarity(query_emb, item["embedding"])
            if score >= threshold:
                scored.append({
                    "file": item["file"],
                    "chunk_id": item["chunk_id"],
                    "content": item["content"],
                    "score": round(score, 4)
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

def format_rag_context(chunks: list) -> str:
    """Format retrieved document chunks for LLM."""
    if not chunks:
        return ""
    lines = ["### Local Document Knowledge:"]
    for c in chunks:
        lines.append(f"- **[Doc: {c['file']}] (Section {c['chunk_id']}, Relevance: {int(c['score']*100)}%)**\n  {c['content']}")
    return "\n\n".join(lines)
