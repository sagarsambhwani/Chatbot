"""Pydantic v2 schemas for the Conversational Intelligence Layer."""

from typing import Literal, Optional, List
from pydantic import BaseModel, Field

IntentType = Literal[
    "factual",
    "conceptual_learning",
    "technical_help",
    "coding",
    "troubleshooting",
    "creative",
    "research",
    "casual",
    "ambiguous"
]

KnowledgeLevel = Literal[
    "beginner",
    "intermediate",
    "advanced",
    "unknown"
]

DesiredDepth = Literal[
    "brief",
    "normal",
    "deep"
]

ResponseType = Literal[
    "direct_answer",
    "conceptual_explanation",
    "step_by_step",
    "technical_solution",
    "comparison",
    "troubleshooting",
    "creative_response"
]

ExplanationStyle = Literal[
    "simple",
    "progressive",
    "technical",
    "conversational"
]

TargetLength = Literal[
    "short",
    "medium",
    "long"
]


class ConversationAnalysis(BaseModel):
    """Structured analysis of a user message and its conversation context."""

    intent: IntentType = Field(
        default="factual",
        description="The primary category of assistance the user is seeking."
    )
    topic: str = Field(
        default="",
        description="The central subject matter or entity of the user's message."
    )
    knowledge_level: KnowledgeLevel = Field(
        default="unknown",
        description="Estimated user familiarity with the subject based solely on context; default to unknown if uncertain."
    )
    desired_depth: DesiredDepth = Field(
        default="normal",
        description="Level of detail requested: brief (concise), normal (balanced), or deep (exhaustive)."
    )
    needs_example: bool = Field(
        default=False,
        description="Whether a concrete example would materially improve comprehension."
    )
    needs_analogy: bool = Field(
        default=False,
        description="Whether an analogy is genuinely helpful to explain an abstract concept."
    )
    needs_code: bool = Field(
        default=False,
        description="Whether code or script implementation is explicitly requested or required."
    )
    needs_web_search: bool = Field(
        default=False,
        description="Whether live external or current factual data (news, prices, current events) is needed."
    )
    needs_rag: bool = Field(
        default=False,
        description="Whether uploaded or local document knowledge is required."
    )
    needs_clarification: bool = Field(
        default=False,
        description="True ONLY when an essential detail is missing and the task cannot reasonably proceed."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Single focused clarifying question if needs_clarification is True."
    )


class ResponsePlan(BaseModel):
    """Deterministic blueprint for generating an optimal response."""

    response_type: ResponseType = Field(
        default="direct_answer",
        description="The structural type of response to produce."
    )
    opening_strategy: str = Field(
        default="",
        description="Directive on how to begin the response (e.g., direct answer, problem acknowledgement)."
    )
    sections: List[str] = Field(
        default_factory=list,
        description="Planned progression of sections or themes to address."
    )
    explanation_style: ExplanationStyle = Field(
        default="conversational",
        description="Tone and didactic approach for the answer."
    )
    include_example: bool = Field(
        default=False,
        description="Whether to incorporate a practical example."
    )
    include_analogy: bool = Field(
        default=False,
        description="Whether to incorporate a conceptual analogy."
    )
    include_code: bool = Field(
        default=False,
        description="Whether to provide code blocks."
    )
    include_caveats: bool = Field(
        default=False,
        description="Whether to mention limitations, trade-offs, or prerequisites."
    )
    target_length: TargetLength = Field(
        default="medium",
        description="Overall target length: short, medium, or long."
    )


class IntelligenceResult(BaseModel):
    """Container holding both the contextual analysis and the deterministic response plan."""

    analysis: ConversationAnalysis
    plan: ResponsePlan
