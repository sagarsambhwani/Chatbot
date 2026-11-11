import re
import time
import logging
import requests
from ddgs import DDGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SearchEngine")

# Patterns where web search is unnecessary (conversations, greetings, coding, math)
SKIP_SEARCH_PATTERNS = [
    r"^(hi|hello|hey|greetings|howdy|good\s+(morning|afternoon|evening))\b",
    r"\b(who\s+are\s+you|what(\'s|\s+is)\s+your\s+name|what\s+are\s+you|who(\'s|\s+is)\s+this|introduce\s+yourself)\b",
    r"\b(how\s+are\s+you|how\s+are\s+you\s+doing|how\'s\s+it\s+going|what\'s\s+up)\b",
    r"\b(thank\s+you|thanks|bye|goodbye|see\s+you)\b",
    r"\b((tell|give)\s+(me\s+)?(a\s+)?([\w\s]+\s+)?joke|make\s+me\s+laugh)\b",
    r"^(write\s+a\s+(python\s+|javascript\s+|c\+\+\s+)?(function|script|code|poem|story|essay))\b",
    r"^(calculate|solve|what\s+is\s+\d+[\+\-\*\/])\b"
]

# Patterns where live web search is strictly required
FORCE_SEARCH_PATTERNS = [
    r"\b(weather|temperature|forecast|rain|climate)\b",
    r"\b(current|currently|now|latest|recent|news|headlines)\b",
    r"\b(price|stock|crypto|bitcoin|market|share\s+price)\b",
    r"\b(who\s+won|score|match|game|election|championship)\b",
    r"\b(search\s+for|search\s+web|look\s+up|google)\b"
]

def should_search_web(query: str) -> bool:
    """Intelligently classifies whether a query needs external web search."""
    q = query.strip().lower()
    if not q:
        return False

    # 1. Check conversational / chitchat FIRST!
    for pattern in SKIP_SEARCH_PATTERNS:
        if re.search(pattern, q):
            return False

    # 2. Force search if real-time indicators are present
    for pattern in FORCE_SEARCH_PATTERNS:
        if re.search(pattern, q):
            return True

    # 3. Skip very short conversational phrases (<= 3 words without factual interrogatives)
    words = q.split()
    if len(words) <= 3 and not any(k in q for k in ["who", "what", "where", "when", "why"]):
        return False

    # Default to search if it looks like a specific informational question
    return True

def search_web(query: str, max_results: int = 3) -> tuple[list, float]:
    """
    Fast Web Search with Smart Intent Filter and strict timeouts.
    Returns: (list_of_results, elapsed_seconds)
    """
    t0 = time.time()
    
    # 1. Smart Intent Check
    if not should_search_web(query):
        logger.info(f"[Intent Router] Conversational query '{query}' - skipping web search (0.00s)")
        return [], 0.0

    logger.info(f"[Intent Router] Web search needed for query: '{query}'")
    results = []

    # 2. Fast Path: DuckDuckGo Instant Answer API (< 400ms)
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=1.5
        ).json()
        abstract = r.get("AbstractText") or r.get("Abstract")
        heading = r.get("Heading")
        url = r.get("AbstractURL")
        if abstract and heading:
            results.append({
                "id": 1,
                "title": heading,
                "url": url or "https://duckduckgo.com",
                "snippet": abstract
            })
            duration = round(time.time() - t0, 3)
            logger.info(f"[Search Engine] DDG Instant Answer retrieved in {duration}s")
            return results, duration
    except Exception:
        pass

    # 3. DuckDuckGo Text Search with strict 3-second timeout
    try:
        ddgs = DDGS(timeout=3)
        raw_results = ddgs.text(query, max_results=max_results)
        for i, item in enumerate(raw_results, 1):
            results.append({
                "id": i,
                "title": item.get("title", "").strip(),
                "url": item.get("href", "").strip(),
                "snippet": item.get("body", "").strip()
            })
        if results:
            duration = round(time.time() - t0, 3)
            logger.info(f"[Search Engine] DDGS retrieved {len(results)} results in {duration}s")
            return results, duration
    except Exception as e:
        logger.warning(f"[Search Engine] DDGS timeout/error: {e}")

    # 4. Fallback: Wikipedia API (fast & reliable, ~0.8s)
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 2
        }
        headers = {"User-Agent": "LocalVoiceAssistant/1.0"}
        r = requests.get(url, params=params, headers=headers, timeout=2.0).json()
        wiki_items = r.get("query", {}).get("search", [])
        for i, it in enumerate(wiki_items, 1):
            clean_snippet = re.sub(r'<[^>]+>', '', it.get("snippet", ""))
            results.append({
                "id": i,
                "title": f"Wikipedia: {it.get('title')}",
                "url": f"https://en.wikipedia.org/wiki/{it.get('title').replace(' ', '_')}",
                "snippet": clean_snippet
            })
        if results:
            duration = round(time.time() - t0, 3)
            logger.info(f"[Search Engine] Wikipedia fallback retrieved {len(results)} results in {duration}s")
            return results, duration
    except Exception as e:
        logger.warning(f"[Search Engine] Wikipedia fallback error: {e}")

    duration = round(time.time() - t0, 3)
    return results, duration

def format_web_context(results: list) -> str:
    """Formats web results into a markdown context block for LLM."""
    if not results:
        return ""
    lines = ["### Web Search Results:"]
    for r in results:
        lines.append(f"- **[Web: {r['title']}]({r['url']})**\n  {r['snippet']}")
    return "\n\n".join(lines)
