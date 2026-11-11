import time
import json
import requests
import logging
from typing import List, Dict, Any, Generator, Tuple
from backend.config import OLLAMA_BASE_URL, LLM_MODEL
from ai_infra.search_engine import search_web, format_web_context, should_search_web
from ai_infra.rag_engine import RAGEngine, format_rag_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Assistant")

class LocalAssistant:
    """Orchestration layer: combines Intent Filter, Web Search, Document RAG, and LLM reasoning."""

    def __init__(self):
        self.rag = RAGEngine()

    def _prepare_messages(
        self,
        user_prompt: str,
        chat_history: list = None,
        use_web: bool = True,
        use_rag: bool = True
    ) -> Tuple[List[Dict[str, str]], List[Dict], float, List[Dict], float, float]:
        t_start = time.time()
        web_results = []
        search_time = 0.0
        rag_chunks = []
        rag_time = 0.0
        contexts = []

        # 1. Document RAG lookup (skip for simple chitchat)
        if use_rag and should_search_web(user_prompt):
            t_rag_start = time.time()
            rag_chunks = self.rag.search(user_prompt, top_k=3)
            rag_time = round(time.time() - t_rag_start, 3)
            rag_context = format_rag_context(rag_chunks)
            if rag_context:
                contexts.append(rag_context)

        # 2. Web search lookup with smart intent filter
        if use_web:
            web_results, search_time = search_web(user_prompt, max_results=3)
            web_context = format_web_context(web_results)
            if web_context:
                contexts.append(web_context)

        # 3. Assemble System Prompt with strict citation instructions
        system_instructions = (
            "You are a helpful, intelligent local AI voice assistant powered by Ollama and Qwen2.5.\n"
            "Your answers will be displayed visually in a web chat and also read out loud.\n\n"
            "GUIDELINES FOR ANSWERS:\n"
            "1. STRUCTURE: Use clear, organized markdown with bullet points, short paragraphs, or bold highlights.\n"
            "2. CITATIONS: If you use information from the provided Web Search or Document Knowledge, ALWAYS cite the source inline:\n"
            "   - For web sources: [Web: Source Title](URL)\n"
            "   - For local documents: [Doc: filename.ext]\n"
            "3. If both sources are relevant, compare or combine them cleanly and cite both.\n"
            "4. Keep the explanation conversational, clear, and direct."
        )

        messages = [{"role": "system", "content": system_instructions}]

        # Append previous conversation history (last 6 turns)
        if chat_history:
            for turn in chat_history[-6:]:
                messages.append({"role": turn["role"], "content": turn["content"]})

        # Append current user prompt with injected contexts
        current_user_content = user_prompt
        if contexts:
            full_context_block = "\n\n".join(contexts)
            current_user_content = f"{full_context_block}\n\nUser Question: {user_prompt}"

        messages.append({"role": "user", "content": current_user_content})

        return messages, web_results, search_time, rag_chunks, rag_time, t_start

    def generate_response(
        self,
        user_prompt: str,
        chat_history: list = None,
        use_web: bool = True,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """Non-streaming batch response generator."""
        messages, web_results, search_time, rag_chunks, rag_time, t_start = self._prepare_messages(
            user_prompt, chat_history, use_web, use_rag
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
            "latencies": {
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
        messages, web_results, search_time, rag_chunks, rag_time, t_start = self._prepare_messages(
            user_prompt, chat_history, use_web, use_rag
        )

        # 1. Yield retrieved sources & search latencies immediately
        yield {
            "type": "metadata",
            "web_sources": web_results,
            "doc_sources": rag_chunks,
            "latencies": {
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
