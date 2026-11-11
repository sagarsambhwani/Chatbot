import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_infra.rag_engine import RAGEngine

if __name__ == "__main__":
    print("Indexing documents in data/docs...")
    rag = RAGEngine()
    count = rag.index_documents()
    print(f"Indexing complete! Total chunks indexed: {count}")
