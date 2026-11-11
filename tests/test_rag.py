import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_infra.rag_engine import RAGEngine, format_rag_context

def test_rag():
    print("=" * 60)
    print("Testing AI Infra RAG Engine")
    print("=" * 60)

    rag = RAGEngine()
    indexed_count = rag.index_documents()
    print(f"Total indexed chunks: {indexed_count}")

    queries = [
        "What GPU is being used?",
        "How is the assistant structured?"
    ]

    for q in queries:
        print(f"\n--- Searching for: '{q}' ---")
        results = rag.search(q, top_k=2)
        print(f"Found {len(results)} matches:")
        for r in results:
            print(f"  [Doc: {r['source']}] Score: {r['score']:.3f}")
            print(f"  Snippet: {r['text'][:120]}...\n")

        formatted = format_rag_context(results)
        print("Formatted RAG Context:")
        print(formatted)

if __name__ == "__main__":
    test_rag()
