import time
import logging
import math
import re
from typing import List, Dict, Optional, Any
from intelligence.schemas import ConversationAnalysis
from ai_infra.llm_client import OllamaClient
from backend.config import OLLAMA_BASE_URL, EMBED_MODEL

logger = logging.getLogger("SemanticRouter")


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SemanticRouter:
    """
    High-performance GPU Semantic Embedding Router.
    Uses nomic-embed-text embeddings (~40ms on GPU, 0 MB extra VRAM).
    Replaces slow LLM / CPU transformer routing with instant vector similarity.
    """
    _instance: Optional["SemanticRouter"] = None

    EXEMPLARS = {
        "web_search": [
            "current stock price of Apple right now",
            "what is the price of Bitcoin today",
            "live weather in Tokyo right now",
            "latest breaking news today",
            "current score of the game right now",
            "today's currency exchange rate USD to INR",
            "what is the weather like outside right now",
            "who won the cricket match yesterday sports score",
            "who is the current prime minister or president",
            "latest news updates and announcements",
            "do a web search on this topic online",
            "search the web for latest information",
            "look this up online on google",
            "search online for this query"
        ],
        "technical_concepts": [
            "explain Kafka and Flink streaming architecture",
            "how does Transformer self attention and flash attention work",
            "deep learning neural network architectures and models",
            "economic inflation monetary policy and interest rates",
            "distributed database consensus raft and paxos protocols"
        ],
        "rag_docs": [
            "in the uploaded welcome guide",
            "check the household appliance purchase list PDF",
            "what does the uploaded document say",
            "specifications written in the local manual",
            "what are the prices in the purchase list",
            "look up the information in the attached file",
            "from the document what is the budget"
        ],
        "casual": [
            "hello",
            "hi there",
            "hey how are you doing",
            "good morning",
            "thanks a lot",
            "thank you so much for your help",
            "goodbye see you later",
            "bye"
        ],
        "coding": [
            "write a python function to compute something",
            "implement quicksort in python or c++",
            "fix this syntax error in my script",
            "write a function that takes an array",
            "how to implement a linked list in python"
        ],
        "troubleshooting": [
            "Flask app gives KeyError or 500 error",
            "why is my code throwing an exception",
            "how to debug this stack trace error"
        ],
        "conceptual_learning": [
            "explain how transformer self-attention works",
            "how does alternating current work in physics",
            "explain backpropagation in neural networks"
        ],
        "research": [
            "compare the trade-offs between int8 quantization and fp16",
            "compare postgresql vs mongodb architectures",
            "evaluate different machine learning approaches"
        ],
        "creative": [
            "write a funny haiku about debugging",
            "write a short fictional story about space",
            "tell me a funny creative joke"
        ]
    }

    def __init__(self, client: Optional[OllamaClient] = None):
        logger.info("Initializing GPU Semantic Router (nomic-embed-text)...")
        self.client = client or OllamaClient(base_url=OLLAMA_BASE_URL, embed_model=EMBED_MODEL)
        self.exemplar_vectors: Dict[str, List[List[float]]] = {}
        self._build_exemplar_index()

    @classmethod
    def get_instance(cls, client: Optional[OllamaClient] = None) -> "SemanticRouter":
        if cls._instance is None:
            cls._instance = cls(client=client)
        return cls._instance

    def _build_exemplar_index(self):
        """Pre-compute embeddings for all category exemplars once at startup."""
        total = 0
        t0 = time.time()
        for category, texts in self.EXEMPLARS.items():
            self.exemplar_vectors[category] = []
            for t in texts:
                emb = self.client.get_embedding(t)
                if emb:
                    self.exemplar_vectors[category].append(emb)
                    total += 1
        logger.info(f"Semantic Router pre-computed {total} exemplar embeddings in {time.time()-t0:.2f}s.")

    def _get_max_similarity(self, q_emb: List[float], category: str) -> float:
        vectors = self.exemplar_vectors.get(category, [])
        if not vectors:
            return 0.0
        return max(cosine_similarity(q_emb, v) for v in vectors)

    def analyze(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ConversationAnalysis:
        """Analyze message intent and tool requirements via GPU semantic embeddings."""
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
                needs_clarification=False
            )

        # 0. Check for explicit search command directives
        explicit_search = bool(re.search(
            r"\b(do\s+(a\s+)?web\s+search|search\s+(the\s+)?web|search\s+online|look\s+(this\s+)?up\s+online|google\s+(this|it)|browse\s+(the\s+)?web)\b",
            clean_msg,
            re.IGNORECASE
        ))

        # 1. Compute query embedding (~40ms on GPU)
        q_emb = self.client.get_embedding(clean_msg)
        if not q_emb:
            # Fallback if Ollama embeddings fail
            return ConversationAnalysis(
                intent="factual",
                topic=clean_msg[:60],
                knowledge_level="unknown",
                desired_depth="normal",
                needs_example=False,
                needs_analogy=False,
                needs_code=False,
                needs_web_search=explicit_search,
                needs_rag=False,
                needs_clarification=False
            )

        # 2. Score against all clusters
        scores: Dict[str, float] = {}
        for cat in self.EXEMPLARS.keys():
            scores[cat] = self._get_max_similarity(q_emb, cat)

        # Determine primary intent
        intent_candidates = [
            ("casual", scores.get("casual", 0.0)),
            ("coding", scores.get("coding", 0.0)),
            ("troubleshooting", scores.get("troubleshooting", 0.0)),
            ("conceptual_learning", scores.get("conceptual_learning", 0.0)),
            ("research", scores.get("research", 0.0)),
            ("creative", scores.get("creative", 0.0)),
        ]
        intent_candidates.sort(key=lambda x: x[1], reverse=True)
        top_intent, top_score = intent_candidates[0]

        if top_score >= 0.52:
            intent = top_intent
        else:
            intent = "factual"

        # 3. Tool thresholding
        web_score = scores.get("web_search", 0.0)
        tech_score = scores.get("technical_concepts", 0.0)

        # Web search triggers:
        # a) Explicit user search directive
        # b) Live volatile web data (prices, weather, news, scores)
        # c) In-depth technical/economic architectures needing fast factual grounding
        needs_web = (
            explicit_search
            or (web_score >= 0.60)
            or (tech_score >= 0.58 and intent in ("research", "conceptual_learning", "factual"))
        )

        # Document RAG requires high semantic closeness to doc/list references
        needs_rag = scores.get("rag_docs", 0.0) >= 0.58
        # Code detection
        needs_code = scores.get("coding", 0.0) >= 0.58

        # Special case: if query is very short and matches casual strongly
        words = clean_msg.split()
        if len(words) <= 5 and scores.get("casual", 0.0) >= 0.44:
            intent = "casual"
            if not explicit_search:
                needs_web = False
            needs_rag = False

        # Desired depth
        if intent in ("casual", "factual"):
            depth = "brief" if len(words) < 12 else "normal"
        elif intent in ("research", "conceptual_learning"):
            depth = "deep"
        else:
            depth = "normal"

        analysis = ConversationAnalysis(
            intent=intent,
            topic=clean_msg[:60].strip(),
            knowledge_level="unknown",
            desired_depth=depth,
            needs_example=intent in ("coding", "conceptual_learning"),
            needs_analogy=intent == "conceptual_learning" and depth == "deep",
            needs_code=needs_code or intent == "coding",
            needs_web_search=needs_web,
            needs_rag=needs_rag,
            needs_clarification=False,
            clarification_question=None
        )

        logger.info(
            f"Semantic Router (GPU): intent='{analysis.intent}', "
            f"web={analysis.needs_web_search} (explicit={explicit_search}, web_sim={web_score:.2f}, tech_sim={tech_score:.2f}), "
            f"rag={analysis.needs_rag} ({scores.get('rag_docs',0.0):.2f}), "
            f"code={analysis.needs_code}"
        )
        return analysis

    def analyze_sync(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ConversationAnalysis:
        """Drop-in compatibility with ConversationAnalyzer."""
        return self.analyze(message, history=history)
