"""Streams tokens from local Ollama and calculates generation latencies."""

import time
import json
import requests
from typing import Generator, Dict, Any, List
from backend.config import OLLAMA_BASE_URL, LLM_MODEL

def stream_llm(
    messages: List[Dict[str, str]],
    t_start: float,
    analyzer_time: float,
    search_time: float,
    rag_time: float
) -> Generator[Dict[str, Any], None, None]:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {"model": LLM_MODEL, "messages": messages, "stream": True, "keep_alive": -1, "options": {"num_gpu": 99, "temperature": 0.6}}
    t_llm, tokens, ttft, tps = time.time(), [], 0.0, 0.0

    try:
        resp = requests.post(url, json=payload, stream=True, timeout=90)
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                txt = chunk.get("message", {}).get("content", "")
                if txt:
                    if ttft == 0.0: ttft = round(time.time() - t_llm, 3)
                    tokens.append(txt)
                    yield {"type": "token", "token": txt}
                if chunk.get("done"):
                    cnt, dur = chunk.get("eval_count", 0), chunk.get("eval_duration", 0)
                    if cnt and dur: tps = round(cnt / (dur / 1e9), 1)

        llm_t = round(time.time() - t_llm, 3)
        yield {
            "type": "done",
            "answer": "".join(tokens),
            "latencies": {
                "analyzer_seconds": analyzer_time, "search_seconds": search_time,
                "rag_seconds": rag_time, "llm_seconds": llm_t, "ttft_seconds": ttft,
                "tokens_per_sec": tps, "total_seconds": round(time.time() - t_start, 3)
            }
        }
    except Exception as e:
        yield {"type": "error", "error": str(e)}

