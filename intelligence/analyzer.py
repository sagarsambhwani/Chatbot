import os
import json
import logging
import asyncio
from typing import List, Dict, Optional, Any
from intelligence.schemas import ConversationAnalysis

logger = logging.getLogger("ConversationAnalyzer")

class ConversationAnalyzer:
    """Understands user intent and conversation context using a structured LLM call."""

    def __init__(
        self,
        model: str,
        llm_client,
        prompt_path: Optional[str] = None,
    ):
        self.model = model
        self.llm_client = llm_client
        self.prompt_path = prompt_path or self._default_prompt_path()
        self.system_prompt = self._load_system_prompt()
        self.schema = ConversationAnalysis.model_json_schema()
        # Explicitly enforce required fields in the JSON schema for local model grammar guidance
        self.schema["required"] = [
            "intent",
            "topic",
            "knowledge_level",
            "desired_depth",
            "needs_example",
            "needs_analogy",
            "needs_code",
            "needs_web_search",
            "needs_rag",
            "needs_clarification"
        ]

    def _default_prompt_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "prompts", "analyzer.txt")

    def _load_system_prompt(self) -> str:
        try:
            if os.path.exists(self.prompt_path):
                with open(self.prompt_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not load prompt from {self.prompt_path}: {e}")

        # Fallback default prompt if file cannot be read
        return (
            "You are a conversational intent analyzer. "
            "Analyze the user's message and context and return structured JSON matching the schema."
        )

    def _build_messages(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]

        # Bound history to last 6 relevant turns
        if history:
            bounded_history = history[-6:]
            for turn in bounded_history:
                role = turn.get("role", "user")
                content = turn.get("content", "").strip()
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": f"Analyze this user message:\n{message}"})
        return messages

    def _create_fallback_analysis(self, message: str) -> ConversationAnalysis:
        """Conservative fallback when analyzer model call or parsing fails."""
        logger.info("Using conservative fallback ConversationAnalysis.")
        # Minimal keyword heuristics for fallback
        q = message.lower().strip()
        needs_search = any(k in q for k in ["weather", "latest", "price", "news", "current", "who won", "today"])
        needs_rag = any(k in q for k in ["document", "pdf", "file", "manual", "guide"])

        return ConversationAnalysis(
            intent="factual" if not needs_search else "factual",
            topic=message[:60].strip(),
            knowledge_level="unknown",
            desired_depth="normal",
            needs_example=False,
            needs_analogy=False,
            needs_code="python" in q or "code" in q or "function" in q,
            needs_web_search=needs_search,
            needs_rag=needs_rag,
            needs_clarification=False,
            clarification_question=None
        )

    def analyze_sync(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> ConversationAnalysis:
        """Synchronous analysis execution."""
        clean_msg = (message or "").strip()
        if not clean_msg:
            return self._create_fallback_analysis("")

        messages = self._build_messages(clean_msg, history)

        try:
            raw_json = self.llm_client.chat_structured(
                messages=messages,
                schema=self.schema,
                temperature=0.0,
                num_predict=256,
                timeout=25.0
            )

            if not raw_json or not raw_json.strip():
                logger.warning("Empty response received from LLM structured chat.")
                return self._create_fallback_analysis(clean_msg)

            # Validate against Pydantic schema
            analysis = ConversationAnalysis.model_validate_json(raw_json)
            logger.info(
                f"Analysis completed: intent='{analysis.intent}', topic='{analysis.topic}', "
                f"web={analysis.needs_web_search}, rag={analysis.needs_rag}"
            )
            return analysis

        except Exception as e:
            logger.warning(f"ConversationAnalyzer failed with error: {e}. Falling back safely.")
            return self._create_fallback_analysis(clean_msg)

    async def analyze(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> ConversationAnalysis:
        """Asynchronous analysis execution without blocking Flask/async loops."""
        return await asyncio.to_thread(self.analyze_sync, message, history)
