import re
import time
import logging
import requests
from ddgs import DDGS
from typing import List, Dict, Tuple

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
    """Classify whether the user query needs web search."""
    q = query.strip().lower()
    if len(q) < 4:
        return False

    for pat in FORCE_SEARCH_PATTERNS:
        if re.search(pat, q):
            return True

    for pat in SKIP_SEARCH_PATTERNS:
        if re.search(pat, q):
            return False

    return True

class HybridSearchEngine:
    """3-tier resilient search: DuckDuckGo Instant -> DuckDuckGo HTML -> Wikipedia fallback."""

    def __init__(self, timeout: float = 3.5):
        self.timeout = timeout
        self.ddgs = DDGS(timeout=timeout)

    def _search_ddg_instant(self, query: str) -> List[Dict]:
        try:
            url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1&skip_disambig=1"
            res = requests.get(url, timeout=2.0).json()
            results = []
            if res.get("AbstractText") and res.get("AbstractURL"):
                results.append({
                    "title": res.get("Heading", query),
                    "snippet": res.get("AbstractText"),
                    "link": res.get("AbstractURL")
                })
            for topic in res.get("RelatedTopics", [])[:2]:
                if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                    results.append({
                        "title": topic.get("Text", "")[:60] + "...",
                        "snippet": topic.get("Text"),
                        "link": topic.get("FirstURL")
                    })
            return results
        except Exception as e:
            logger.debug(f"DDG Instant Answer error: {e}")
            return []

    def _search_ddgs(self, query: str, max_results: int = 3) -> List[Dict]:
        try:
            raw_results = list(self.ddgs.text(query, max_results=max_results))
            results = []
            for r in raw_results:
                title = r.get("title", "")
                snippet = r.get("body", "")
                link = r.get("href", "")
                if title and link:
                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "link": link
                    })
            return results
        except Exception as e:
            logger.warning(f"DDGS search timed out/failed: {e}")
            return []

    def _search_wikipedia(self, query: str) -> List[Dict]:
        try:
            cleaned = re.sub(r"^(who is|what is|where is|tell me about)\s+", "", query.lower()).strip()
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(cleaned)}"
            res = requests.get(url, timeout=2.5, headers={"User-Agent": "LocalVoiceAssistant/1.0"}).json()
            if "extract" in res and res.get("extract"):
                title = res.get("title", cleaned)
                link = res.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{title}")
                return [{
                    "title": f"Wikipedia: {title}",
                    "snippet": res.get("extract", ""),
                    "link": link
                }]
        except Exception as e:
            logger.debug(f"Wikipedia fallback error: {e}")
        return []

    def search(self, query: str, max_results: int = 3) -> Tuple[List[Dict], float]:
        t0 = time.time()
        if not should_search_web(query):
            return [], 0.0

        # Tier 1: DDG Instant API
        results = self._search_ddg_instant(query)

        # Tier 2: DDGS text results
        if not results:
            results = self._search_ddgs(query, max_results=max_results)

        # Tier 3: Wikipedia fallback
        if not results:
            results = self._search_wikipedia(query)

        elapsed = round(time.time() - t0, 3)
        return results[:max_results], elapsed

_default_search_engine = HybridSearchEngine()

def search_web(query: str, max_results: int = 3) -> Tuple[List[Dict], float]:
    return _default_search_engine.search(query, max_results=max_results)

def format_web_context(results: List[Dict]) -> str:
    if not results:
        return ""
    lines = ["\n[CURRENT WEB SEARCH RESULTS]"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. Title: {r['title']}")
        lines.append(f"   URL: {r['link']}")
        lines.append(f"   Snippet: {r['snippet']}\n")
    lines.append("Instructions for citations: When stating facts from the web search results above, cite them inline using markdown links with the exact URL: [Web: Title](URL).\n")
    return "\n".join(lines)
