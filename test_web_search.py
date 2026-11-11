from ddgs import DDGS
import requests
import json

def search_web(query: str, max_results: int = 3):
    print(f"Searching web for: '{query}'...")
    results = []
    try:
        ddgs = DDGS()
        raw_results = ddgs.text(query, max_results=max_results)
        for i, r in enumerate(raw_results, 1):
            results.append({
                "id": i,
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", "")
            })
    except Exception as e:
        print(f"Search error: {e}")
    return results

def ask_with_web_search(user_query: str):
    search_results = search_web(user_query, max_results=3)
    
    if not search_results:
        print("No search results found.")
        return

    # Build reference context for LLM
    context_text = "Here are the web search results:\n\n"
    for item in search_results:
        context_text += f"[Web Source {item['id']}]: {item['title']}\nURL: {item['url']}\nContent: {item['snippet']}\n\n"

    system_prompt = (
        "You are an intelligent voice-ready AI assistant. "
        "Answer the user's question accurately using the provided Web Sources. "
        "Rules:\n"
        "1. Provide a well-structured, clear markdown answer.\n"
        "2. When stating facts from a source, cite it inline like [Web: Title](URL) or [Web Source X].\n"
        "3. Include a 'Sources Used' section at the end with markdown links.\n"
        "4. Keep the tone concise and conversational."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{context_text}\nUser Question: {user_query}"}
    ]

    print("\nQuerying Qwen2.5 with live web context...")
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
    print("ASSISTANT ANSWER WITH WEB CITATIONS:")
    print("=" * 60)
    print(answer)
    print("=" * 60)

if __name__ == "__main__":
    ask_with_web_search("What are the latest developments in James Webb Space Telescope discoveries?")
