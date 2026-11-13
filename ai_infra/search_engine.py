import re
import time
import logging
import threading
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from ddgs import DDGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SearchEngine")

# Patterns to strip out command prefixes so search engines get clean keywords
COMMAND_PREFIX_PATTERNS = [
    r"^(can you\s+)?(please\s+)?(do\s+(a\s+)?web\s+search\s+(on|for|about)?\s*(this)?\s*[:\-\?]?\s*)",
    r"^(can you\s+)?(please\s+)?(search\s+(the\s+web|online|google)\s+(for|on|about)?\s*[:\-\?]?\s*)",
    r"^(can you\s+)?(please\s+)?(look\s+(this\s+)?up\s+(online|on\s+google|on\s+the\s+web)\s*(for|about)?\s*[:\-\?]?\s*)",
    r"^(can you\s+)?(please\s+)?(google\s+(this|for)?\s*[:\-\?]?\s*)",
    r"^(check\s+(the\s+web|online)\s+(for|about)?\s*[:\-\?]?\s*)",
]

def clean_search_query(query: str) -> str:
    """Strip conversational command boilerplate from query before searching."""
    cleaned = (query or "").strip()
    for pat in COMMAND_PREFIX_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else query.strip()


class HybridSearchEngine:
    """
    Tiered Low-Latency Grounding Engine:
    - Tier 1 (Fast-Path, ~180ms-350ms): Concurrent DDG Instant Answers + Wikipedia REST API
    - Tier 2 (Deep-Path, ~2s-4s): Multi-engine text scrape (DDGS)
    - Persistent LRU In-Memory Cache (0ms on repeat/related technical terms)
    """

    def __init__(self, timeout: float = 3.5):
        self.timeout = timeout
        self.ddgs = DDGS(timeout=timeout)
        self._cache: Dict[str, Tuple[List[Dict], float]] = {}
        self._cache_lock = threading.Lock()

    def _search_ddg_instant(self, query: str) -> List[Dict]:
        try:
            url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1&skip_disambig=1"
            res = requests.get(url, timeout=1.5).json()
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

    def _search_wikipedia(self, query: str) -> List[Dict]:
        try:
            cleaned = re.sub(r"^(who is|what is|where is|tell me about|explain|how does)\s+", "", query.lower()).strip()
            cleaned = re.sub(r"\s+(work|function|architecture|flow)\b.*", "", cleaned).strip()
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(cleaned)}"
            headers = {"User-Agent": "LocalVoiceAssistant/1.0 (contact@local.internal)"}
            res = requests.get(url, timeout=1.8, headers=headers).json()
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

    def _search_fast_path(self, query: str) -> List[Dict]:
        """Run DDG Instant and Wikipedia REST concurrently (~200ms)."""
        results = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_ddg = executor.submit(self._search_ddg_instant, query)
            future_wiki = executor.submit(self._search_wikipedia, query)

            for future in as_completed([future_ddg, future_wiki], timeout=2.0):
                try:
                    res = future.result()
                    if res:
                        results.extend(res)
                except Exception as e:
                    logger.debug(f"Fast-path worker failed: {e}")

        # Deduplicate by link
        seen = set()
        deduped = []
        for r in results:
            if r.get("link") and r["link"] not in seen:
                seen.add(r["link"])
                deduped.append(r)
        return deduped

    def _search_ddgs(self, query: str, max_results: int = 3) -> List[Dict]:
        """Deep-path fallback text scrape."""
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
            logger.warning(f"DDGS text search timed out/failed: {e}")
            return []

    def search(self, query: str, max_results: int = 3) -> Tuple[List[Dict], float]:
        clean_q = clean_search_query(query)
        if not clean_q:
            return [], 0.0

        # 1. Check in-memory cache (0.000s)
        cache_key = clean_q.lower()
        with self._cache_lock:
            if cache_key in self._cache:
                cached_res, _ = self._cache[cache_key]
                logger.info(f"Search cache HIT for: '{clean_q}' (0ms)")
                return cached_res[:max_results], 0.001

        t0 = time.time()

        # 2. Fast-Path (Concurrent DDG Instant + Wikipedia REST, ~200ms)
        results = self._search_fast_path(clean_q)
        total_snippet_len = sum(len(r.get("snippet", "")) for r in results)

        # If Fast-Path returned verified, non-trivial context (≥ 120 chars), short-circuit!
        if results and total_snippet_len >= 120:
            elapsed = round(time.time() - t0, 3)
            logger.info(f"Search Fast-Path SUCCESS for '{clean_q}' in {elapsed}s ({len(results)} snippets)")
            with self._cache_lock:
                self._cache[cache_key] = (results, elapsed)
            return results[:max_results], elapsed

        # 3. Deep-Path Fallback (DDGS multi-engine scrape, ~2-4s)
        logger.info(f"Fast-path empty/short for '{clean_q}'. Falling back to Deep-Path...")
        deep_results = self._search_ddgs(clean_q, max_results=max_results)
        if deep_results:
            results.extend(deep_results)

        elapsed = round(time.time() - t0, 3)
        final_results = results[:max_results]
        with self._cache_lock:
            self._cache[cache_key] = (final_results, elapsed)

        return final_results, elapsed


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
