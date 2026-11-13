import os
import logging
from typing import Dict, Any, List, Optional
import torch
from intelligence.schemas import ConversationAnalysis

logger = logging.getLogger("DecisionEngine")


class DecisionEngine:
    """
    System 1 Fast Decision Engine powered by Laya.
    Runs on multi-threaded CPU (~150ms-500ms) to preserve 100% GPU VRAM for Ollama generation.
    Handles intent detection and tool routing (Web Search & RAG).
    """
    _instance: Optional["DecisionEngine"] = None

    def __init__(self, threads: int = 4):
        logger.info(f"Initializing System 1 Decision Engine (Laya) on CPU (threads={threads})...")
        torch.set_num_threads(threads)
        from laya import Router

        self.router = Router(default="english", device="cpu")
        self.router.load("english")
        self._warm_engine()

    @classmethod
    def get_instance(cls, threads: int = 4) -> "DecisionEngine":
        """Singleton accessor."""
        if cls._instance is None:
            cls._instance = cls(threads=threads)
        return cls._instance

    def _warm_engine(self):
        """Execute a warmup prediction pass to absorb PyTorch JIT graph compilation overhead."""
        try:
            warmup_state = {"instance": "warmup ping"}
            warmup_q = {
                "warmup": {
                    "type": "choice",
                    "instructions": "Is this a warmup ping?",
                    "criteria": ["yes", "no"]
                }
            }
            self.router.predict(warmup_state, warmup_q, model="english")
            logger.info("System 1 Decision Engine pre-warmed successfully.")
        except Exception as e:
            logger.warning(f"System 1 warmup non-critical notice: {e}")

    def analyze(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ConversationAnalysis:
        """Perform fast System 1 triage on user prompt and return structured ConversationAnalysis."""
        clean_msg = (message or "").strip()
        if not clean_msg:
            return ConversationAnalysis(
                intent="casual",
                topic="greeting",
                knowledge_level="unknown",
                desired_depth="brief",
                needs_example=False,
                needs_analogy=False,
                needs_code=False,
                needs_web_search=False,
                needs_rag=False,
                needs_clarification=False,
                clarification_question=None
            )

        # Fast heuristic checks for casual / greeting / thanks
        lower_msg = clean_msg.lower()
        words = lower_msg.split()
        if any(g in lower_msg for g in ["hello", "hi ", "hey", "good morning", "good evening", "how are you"]):
            if len(words) <= 7:
                return ConversationAnalysis(
                    intent="casual",
                    topic="greeting",
                    knowledge_level="unknown",
                    desired_depth="brief",
                    needs_example=False,
                    needs_analogy=False,
                    needs_code=False,
                    needs_web_search=False,
                    needs_rag=False,
                    needs_clarification=False
                )

        if any(t in lower_msg for t in ["thanks", "thank you", "bye", "see you"]):
            if len(words) <= 7:
                return ConversationAnalysis(
                    intent="casual",
                    topic="acknowledgement",
                    knowledge_level="unknown",
                    desired_depth="brief",
                    needs_example=False,
                    needs_analogy=False,
                    needs_code=False,
                    needs_web_search=False,
                    needs_rag=False,
                    needs_clarification=False
                )

        # Laya Questions for Structured Routing
        state = {"query": clean_msg}
        questions = {
            "intent": {
                "type": "choice",
                "instructions": "What is the primary conversational intent of this query?",
                "criteria": [
                    "coding",
                    "troubleshooting",
                    "conceptual_learning",
                    "research",
                    "creative",
                    "technical_help",
                    "factual"
                ]
            },
            "needs_web_search": {
                "type": "choice",
                "instructions": "Does this query strictly require real-time volatile information (e.g. current live stock/crypto prices today, live weather right now)? Not static world facts, physics, or code.",
                "criteria": ["yes", "no"]
            },
            "needs_rag": {
                "type": "choice",
                "instructions": "Does the user refer to uploaded documents, local manuals, purchase lists, or PDF files?",
                "criteria": ["yes", "no"]
            },
            "needs_code": {
                "type": "choice",
                "instructions": "Does this query ask to write, debug, or implement programming code or algorithms?",
                "criteria": ["yes", "no"]
            }
        }

        try:
            res = self.router.predict(state, questions, model="english")
            answers = res.get("answers", {})

            intent = answers.get("intent", {}).get("choice", "factual")
            needs_web = answers.get("needs_web_search", {}).get("choice", "no") == "yes"
            needs_rag = answers.get("needs_rag", {}).get("choice", "no") == "yes"
            needs_code = answers.get("needs_code", {}).get("choice", "no") == "yes"

            # Derive depth
            if intent in ("casual", "factual"):
                depth = "brief" if len(words) < 10 else "normal"
            elif intent in ("research", "conceptual_learning"):
                depth = "deep"
            else:
                depth = "normal"

            # Determine topic snippet
            topic = clean_msg[:60].strip()

            analysis = ConversationAnalysis(
                intent=intent,
                topic=topic,
                knowledge_level="unknown",
                desired_depth=depth,
                needs_example=intent in ("coding", "conceptual_learning"),
                needs_analogy=intent == "conceptual_learning" and depth == "deep",
                needs_code=needs_code,
                needs_web_search=needs_web,
                needs_rag=needs_rag,
                needs_clarification=False,
                clarification_question=None
            )
            logger.info(
                f"System 1 (Laya) Analysis: intent='{analysis.intent}', "
                f"web={analysis.needs_web_search}, rag={analysis.needs_rag}, code={analysis.needs_code}"
            )
            return analysis

        except Exception as e:
            logger.error(f"Laya Decision Engine prediction error: {e}. Falling back to default.")
            return ConversationAnalysis(
                intent="factual",
                topic=clean_msg[:60],
                knowledge_level="unknown",
                desired_depth="normal",
                needs_example=False,
                needs_analogy=False,
                needs_code="python" in lower_msg or "code" in lower_msg,
                needs_web_search=any(k in lower_msg for k in ["price", "weather", "today", "current"]),
                needs_rag=any(k in lower_msg for k in ["document", "pdf", "file", "list"]),
                needs_clarification=False
            )

    def analyze_sync(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ConversationAnalysis:
        """Alias for analyze() to maintain drop-in compatibility with ConversationAnalyzer."""
        return self.analyze(message, history=history)
