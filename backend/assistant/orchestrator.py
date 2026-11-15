"""Main assistant orchestrator combining intelligence, RAG, and LLM reasoning."""

import time
import requests
from typing import Optional, Dict, Any, Generator
from backend.config import OLLAMA_BASE_URL, LLM_MODEL
from ai_infra.llm_client import OllamaClient
from ai_infra.rag_engine import RAGEngine
from intelligence.semantic_router import SemanticRouter
from intelligence.response_planner import ResponsePlanner
from backend.assistant.prompt_builder import load_generator_prompt, build_messages
from backend.assistant.context_retriever import retrieve_contexts
from backend.assistant.streamer import stream_llm
from backend.assistant.exemplars import get_exemplar

class LocalAssistant:
    def __init__(self, llm_client: Optional[OllamaClient] = None, rag_engine: Optional[RAGEngine] = None):
        self.client = llm_client or OllamaClient()
        self.rag = rag_engine or RAGEngine()
        self.analyzer = SemanticRouter.get_instance(client=self.client)
        self.planner = ResponsePlanner()
        self.generator_prompt = load_generator_prompt()

    def generate_stream(self, user_prompt: str, chat_history: list = None, use_web: bool = True, use_rag: bool = True) -> Generator[Dict[str, Any], None, None]:
        analysis, plan, web_res, s_time, rag_chunks, r_time, a_time, contexts, t_start = retrieve_contexts(
            self.analyzer, self.planner, self.rag, user_prompt, chat_history, use_web, use_rag
        )
        if use_web and analysis.needs_web_search:
            yield {"type": "status", "message": "Searching the web..."}
        yield {"type": "metadata", "analysis": analysis.model_dump(), "web_sources": web_res, "doc_sources": rag_chunks, "latencies": {"analyzer_seconds": a_time, "search_seconds": s_time, "rag_seconds": r_time}}
        exemplar = get_exemplar(analysis.intent, has_rag=bool(rag_chunks))
        msgs = build_messages(self.generator_prompt, user_prompt, chat_history, plan, contexts, exemplar=exemplar)
        yield from stream_llm(msgs, t_start, a_time, s_time, r_time)

    def generate_response(self, user_prompt: str, chat_history: list = None, use_web: bool = True, use_rag: bool = True) -> Dict[str, Any]:
        analysis, plan, web_res, s_time, rag_chunks, r_time, a_time, contexts, t_start = retrieve_contexts(
            self.analyzer, self.planner, self.rag, user_prompt, chat_history, use_web, use_rag
        )
        exemplar = get_exemplar(analysis.intent, has_rag=bool(rag_chunks))
        msgs = build_messages(self.generator_prompt, user_prompt, chat_history, plan, contexts, exemplar=exemplar)
        t_llm = time.time()
        try:
            resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json={"model": LLM_MODEL, "messages": msgs, "stream": False, "keep_alive": -1, "options": {"num_gpu": 99, "temperature": 0.6}}, timeout=90).json()
            reply = resp.get("message", {}).get("content", "No response generated.")
            cnt, dur = resp.get("eval_count", 0), resp.get("eval_duration", 0)
            tps = round(cnt / (dur / 1e9), 1) if cnt and dur else 0.0
        except Exception as e:
            reply, tps = f"Error: {e}", 0.0
        return {
            "answer": reply, "web_sources": web_res, "doc_sources": rag_chunks, "analysis": analysis.model_dump(), "plan": plan.model_dump(),
            "latencies": {"analyzer_seconds": a_time, "search_seconds": s_time, "rag_seconds": r_time, "llm_seconds": round(time.time() - t_llm, 3), "tokens_per_sec": tps, "total_seconds": round(time.time() - t_start, 3)}
        }
