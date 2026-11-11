import os
import math
import requests

def get_embedding(text: str, model: str = "nomic-embed-text") -> list:
    url = "http://127.0.0.1:11434/api/embeddings"
    payload = {"model": model, "prompt": text}
    res = requests.post(url, json=payload, timeout=90).json()
    return res.get("embedding", [])

def cosine_similarity(vec1: list, vec2: list) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

# Sample knowledge base documents
sample_documents = [
    {
        "source": "quantum_computing_guide.txt",
        "title": "Quantum Computing Principles",
        "content": "Superconducting qubits require dilution refrigerators operating near absolute zero (-273.15 C) to maintain quantum coherence. Decoherence remains the primary challenge in scaling quantum hardware beyond noisy intermediate-scale quantum (NISQ) systems."
    },
    {
        "source": "server_specs_2026.md",
        "title": "Local Server Hardware Spec",
        "content": "The workstation is equipped with an NVIDIA GeForce GTX 1650 4GB GPU, running Ollama with Qwen2.5 and faster-whisper. All heavy inference layers are prioritized to VRAM to keep host RAM under 2GB."
    },
    {
        "source": "solar_flares_report.txt",
        "title": "Solar Activity Alert",
        "content": "Coronal mass ejections (CMEs) from Sunspot Region 3664 induced G5-level geomagnetic storms on Earth, sparking aurora displays at unusually low latitudes across Europe and North America."
    }
]

def test_rag_pipeline(query: str):
    print("=" * 60)
    print(f"RAG Test: Indexing sample documents with nomic-embed-text...")
    
    # Pre-embed the documents
    index = []
    for doc in sample_documents:
        emb = get_embedding(doc["content"])
        index.append({**doc, "embedding": emb})
    print(f"Indexed {len(index)} document chunks successfully on GPU.")
    
    print(f"\nUser Query: '{query}'")
    query_emb = get_embedding(query)
    
    # Rank by cosine similarity
    ranked = []
    for doc in index:
        sim = cosine_similarity(query_emb, doc["embedding"])
        ranked.append((sim, doc))
    
    ranked.sort(key=lambda x: x[0], reverse=True)
    top_docs = [doc for sim, doc in ranked[:2]]

    print("\nTop Retrieved Documents:")
    for sim, doc in ranked[:2]:
        print(f" - [{doc['source']}] (Similarity: {sim:.4f})")

    # Build context with strict citation requirements
    context_str = "You have access to the following local documents:\n\n"
    for i, doc in enumerate(top_docs, 1):
        context_str += f"[Doc {i}: {doc['source']} - '{doc['title']}']:\n{doc['content']}\n\n"

    system_prompt = (
        "You are an intelligent voice-ready AI assistant. "
        "Answer the user query strictly using the provided documents. "
        "Rules:\n"
        "1. Provide a well-structured markdown answer.\n"
        "2. Cite every fact using the exact document name like [Doc: filename.txt].\n"
        "3. Include a 'Sources Used' list at the bottom.\n"
        "4. Keep the answer clear and concise for speech output."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{context_str}\nUser Question: {query}"}
    ]

    print("\nGenerating grounded answer via Qwen2.5...")
    url = "http://127.0.0.1:11434/api/chat"
    payload = {
        "model": "qwen2.5:1.5b",
        "messages": messages,
        "stream": False,
        "options": {"num_gpu": 99}
    }
    resp = requests.post(url, json=payload, timeout=60).json()
    answer = resp.get("message", {}).get("content", "")

    print("\n" + "=" * 60)
    print("ASSISTANT GROUNDED ANSWER WITH RAG CITATIONS:")
    print("=" * 60)
    print(answer)
    print("=" * 60)

if __name__ == "__main__":
    test_rag_pipeline("What GPU does the workstation have and how does it prevent RAM overload?")
