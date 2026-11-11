"""Conversational Intelligence Layer package."""

from intelligence.schemas import (
    ConversationAnalysis,
    ResponsePlan,
    IntelligenceResult,
    IntentType,
    KnowledgeLevel,
    DesiredDepth,
    ResponseType,
    ExplanationStyle,
    TargetLength
)
from intelligence.analyzer import ConversationAnalyzer
from intelligence.response_planner import ResponsePlanner

__all__ = [
    "ConversationAnalysis",
    "ResponsePlan",
    "IntelligenceResult",
    "ConversationAnalyzer",
    "ResponsePlanner",
    "IntentType",
    "KnowledgeLevel",
    "DesiredDepth",
    "ResponseType",
    "ExplanationStyle",
    "TargetLength"
]
