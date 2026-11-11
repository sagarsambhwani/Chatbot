from rag_engine import RAGEngine

if __name__ == "__main__":
    print("Indexing documents in data/docs...")
    rag = RAGEngine()
    count = rag.index_documents()
    print(f"Indexing complete! Total chunks indexed: {count}")
