import os
import time
import json
import requests
import logging
from typing import List, Dict, Any, Generator, Tuple, Optional
from backend.config import OLLAMA_BASE_URL, LLM_MODEL, BASE_DIR
from ai_infra.llm_client import OllamaClient
from ai_infra.search_engine import search_web, format_web_context
from ai_infra.rag_engine import RAGEngine, format_rag_context
from intelligence.semantic_router import SemanticRouter
from intelligence.response_planner import ResponsePlanner
from intelligence.schemas import ConversationAnalysis, ResponsePlan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Assistant")

class LocalAssistant:
    """Orchestration layer: combines Conversational Intelligence, Search, RAG, and LLM reasoning."""

    def __init__(self, llm_client: Optional[OllamaClient] = None, rag_engine: Optional[RAGEngine] = None):
        self.client = llm_client or OllamaClient()
        self.rag = rag_engine or RAGEngine()
        self.analyzer = SemanticRouter.get_instance(client=self.client)
        self.planner = ResponsePlanner()
        self.generator_prompt = self._load_generator_prompt()

    def _load_generator_prompt(self) -> str:
        prompt_path = os.path.join(BASE_DIR, "prompts", "response_generator.txt")
        try:
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not load generator prompt from {prompt_path}: {e}")

        return (
            "You are a helpful, intelligent conversational assistant.\n"
            "Answer the user's actual question clearly, accurately, and naturally."
        )

    def _build_messages(
        self,
        user_prompt: str,
        chat_history: Optional[list],
        plan: ResponsePlan,
        contexts: List[str]
    ) -> List[Dict[str, str]]:
        system_instructions = self.generator_prompt
        if plan.target_length == "short":
            system_instructions += "\nGuidance: Keep the answer concise and direct (1-3 sentences)."
        elif plan.include_code:
            system_instructions += "\nGuidance: Include a clean, well-commented code implementation."

        messages = [{"role": "system", "content": system_instructions}]

        # Append bounded conversation history (last 6 turns)
        if chat_history:
            for turn in chat_history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "").strip()
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        # Append current user prompt with injected contexts
        current_user_content = user_prompt
        if contexts:
            full_context_block = "\n\n".join(contexts)
            current_user_content = f"{full_context_block}\n\nUser Question: {user_prompt}"

        messages.append({"role": "user", "content": current_user_content})
        return messages

    def _prepare_messages(
        self,
        user_prompt: str,
        chat_history: list = None,
        use_web: bool = True,
        use_rag: bool = True
    ) -> Tuple[List[Dict[str, str]], List[Dict], float, List[Dict], float, float, ConversationAnalysis, ResponsePlan, float]:
        t_start = time.time()

        # 1. Conversation Analyzer (Structured LLM call, temp 0)
        t_analyzer_start = time.time()
        analysis = self.analyzer.analyze_sync(user_prompt, history=chat_history)
        analyzer_time = round(time.time() - t_analyzer_start, 3)

        # 2. Deterministic Response Planner (Zero LLM calls)
        plan = self.planner.create_plan(analysis)

        # 3. Tool Routing Policy (Analyzer recommendations as policy input; respect caller overrides)
        route_web = bool(use_web and analysis.needs_web_search)
        route_rag = bool(use_rag and (analysis.needs_rag or len(self.rag.index) > 0))

        web_results = []
        search_time = 0.0
        rag_chunks = []
        rag_time = 0.0
        contexts = []

        if route_rag:
            t_rag_start = time.time()
            min_score = 0.40 if analysis.needs_rag else 0.48
            rag_chunks = self.rag.search(user_prompt, top_k=3, min_score=min_score)
            rag_time = round(time.time() - t_rag_start, 3)
            rag_context = format_rag_context(rag_chunks)
            if rag_context:
                contexts.append(rag_context)

        if route_web:
            web_results, search_time = search_web(user_prompt, max_results=3)
            web_context = format_web_context(web_results)
            if web_context:
                contexts.append(web_context)

        messages = self._build_messages(user_prompt, chat_history, plan, contexts)
        return messages, web_results, search_time, rag_chunks, rag_time, analyzer_time, analysis, plan, t_start

    def generate_response(
        self,
        user_prompt: str,
        chat_history: list = None,
        use_web: bool = True,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """Non-streaming batch response generator."""
        messages, web_results, search_time, rag_chunks, rag_time, analyzer_time, analysis, plan, t_start = (
            self._prepare_messages(user_prompt, chat_history, use_web, use_rag)
        )

        llm_time = 0.0
        tokens_per_sec = 0.0
        t_llm_start = time.time()
        try:
            url = f"{OLLAMA_BASE_URL}/api/chat"
            payload = {
                "model": LLM_MODEL,
                "messages": messages,
                "stream": False,
                "keep_alive": -1,
                "options": {
                    "num_gpu": 99,
                    "temperature": 0.6
                }
            }
            resp = requests.post(url, json=payload, timeout=90).json()
            reply_text = resp.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
            llm_time = round(time.time() - t_llm_start, 3)

            eval_count = resp.get("eval_count", 0)
            eval_duration_ns = resp.get("eval_duration", 0)
            if eval_count and eval_duration_ns:
                tokens_per_sec = round(eval_count / (eval_duration_ns / 1e9), 1)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            reply_text = f"Error communicating with local Ollama: {str(e)}"
            llm_time = round(time.time() - t_llm_start, 3)

        total_time = round(time.time() - t_start, 3)
        return {
            "answer": reply_text,
            "web_sources": web_results,
            "doc_sources": rag_chunks,
            "analysis": analysis.model_dump(),
            "plan": plan.model_dump(),
            "latencies": {
                "analyzer_seconds": analyzer_time,
                "search_seconds": search_time,
                "rag_seconds": rag_time,
                "llm_seconds": llm_time,
                "tokens_per_sec": tokens_per_sec,
                "total_seconds": total_time
            }
        }

    def generate_stream(
        self,
        user_prompt: str,
        chat_history: list = None,
        use_web: bool = True,
        use_rag: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """Streaming generator yielding Server-Sent Events JSON objects."""
        t_start = time.time()

        # 1. GPU Semantic Router (~40ms)
        t_analyzer_start = time.time()
        analysis = self.analyzer.analyze_sync(user_prompt, history=chat_history)
        analyzer_time = round(time.time() - t_analyzer_start, 3)
        plan = self.planner.create_plan(analysis)

        route_web = bool(use_web and analysis.needs_web_search)
        route_rag = bool(use_rag and (analysis.needs_rag or len(self.rag.index) > 0))

        # Immediately indicate to the UI if web search is taking place
        if route_web:
            yield {"type": "status", "message": "Searching the web..."}

        web_results = []
        search_time = 0.0
        rag_chunks = []
        rag_time = 0.0
        contexts = []

        if route_rag:
            t_rag_start = time.time()
            min_score = 0.40 if analysis.needs_rag else 0.48
            rag_chunks = self.rag.search(user_prompt, top_k=3, min_score=min_score)
            rag_time = round(time.time() - t_rag_start, 3)
            rag_context = format_rag_context(rag_chunks)
            if rag_context:
                contexts.append(rag_context)

        if route_web:
            web_results, search_time = search_web(user_prompt, max_results=3)
            web_context = format_web_context(web_results)
            if web_context:
                contexts.append(web_context)

        messages = self._build_messages(user_prompt, chat_history, plan, contexts)

        # 2. Yield retrieved sources & latencies immediately (do not leak internal planning JSON to user)
        yield {
            "type": "metadata",
            "web_sources": web_results,
            "doc_sources": rag_chunks,
            "latencies": {
                "analyzer_seconds": analyzer_time,
                "search_seconds": search_time,
                "rag_seconds": rag_time
            }
        }

        # 2. Stream tokens from Ollama on GPU
        url = f"{OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "stream": True,
            "keep_alive": -1,
            "options": {
                "num_gpu": 99,
                "temperature": 0.6
            }
        }

        t_llm_start = time.time()
        full_tokens = []
        tokens_per_sec = 0.0
        ttft = 0.0

        try:
            resp = requests.post(url, json=payload, stream=True, timeout=90)
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        if ttft == 0.0:
                            ttft = round(time.time() - t_llm_start, 3)
                        full_tokens.append(content)
                        yield {"type": "token", "token": content}
                    if chunk.get("done"):
                        eval_count = chunk.get("eval_count", 0)
                        eval_dur = chunk.get("eval_duration", 0)
                        if eval_count and eval_dur:
                            tokens_per_sec = round(eval_count / (eval_dur / 1e9), 1)

            llm_time = round(time.time() - t_llm_start, 3)
            total_time = round(time.time() - t_start, 3)
            full_text = "".join(full_tokens)

            yield {
                "type": "done",
                "answer": full_text,
                "latencies": {
                    "analyzer_seconds": analyzer_time,
                    "search_seconds": search_time,
                    "rag_seconds": rag_time,
                    "llm_seconds": llm_time,
                    "ttft_seconds": ttft,
                    "tokens_per_sec": tokens_per_sec,
                    "total_seconds": total_time
                }
            }
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {"type": "error", "error": str(e)}
