import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_infra.search_engine import search_web, format_web_context

def test_search():
    print("=" * 60)
    print("Testing AI Infra Hybrid Search Engine")
    print("=" * 60)

    queries = [
        "what is the latest price of bitcoin?",
        "who won the 2024 ICC T20 World Cup?"
    ]

    for q in queries:
        results, elapsed = search_web(q, max_results=2)
        print(f"\nQuery: '{q}' -> Results fetched in {elapsed}s (count: {len(results)}):")
        for r in results:
            print(f"  - [{r['title']}]({r['link']})")
            print(f"    {r['snippet'][:100]}...")

if __name__ == "__main__":
    test_search()
