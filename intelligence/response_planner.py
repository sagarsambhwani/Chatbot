"""Deterministic Response Planner.

Transforms a ConversationAnalysis into an actionable ResponsePlan
without performing any LLM calls.
"""

from intelligence.schemas import ConversationAnalysis, ResponsePlan, ResponseType, ExplanationStyle, TargetLength


class ResponsePlanner:
    """Converts structured conversation analysis into a deterministic response blueprint."""

    def create_plan(self, analysis: ConversationAnalysis) -> ResponsePlan:
        # 1. Map Target Length from Desired Depth
        depth_to_length: dict[str, TargetLength] = {
            "brief": "short",
            "normal": "medium",
            "deep": "long"
        }
        target_length = depth_to_length.get(analysis.desired_depth, "medium")

        # 2. Intent to Response Type & Style Mapping
        intent = analysis.intent

        if intent == "conceptual_learning":
            response_type: ResponseType = "conceptual_explanation"
            style: ExplanationStyle = "progressive"
            opening = "Provide a direct, intuitive definition or explanation of the concept."
            sections = ["Direct explanation", "How it works", "Practical example", "Important limitations"]

        elif intent == "coding":
            response_type = "technical_solution"
            style = "technical"
            opening = "State the approach and prerequisites before presenting the solution."
            sections = ["Understand the requirement", "Explain the approach", "Implementation", "Code walkthrough", "Important considerations"]

        elif intent == "troubleshooting":
            response_type = "troubleshooting"
            style = "progressive"
            opening = "Identify the likely issue or error cause immediately."
            sections = ["Identify the problem", "Likely cause", "Proposed solution", "Verification"]

        elif intent == "research":
            response_type = "step_by_step"
            style = "technical"
            opening = "Frame the central inquiry and current state of knowledge."
            sections = ["Research question", "Available evidence", "Analysis", "Conclusions", "Limitations"]

        elif intent == "technical_help":
            response_type = "technical_solution"
            style = "technical"
            opening = "State the direct recommendation or solution clearly."
            sections = ["Direct recommendation", "Technical explanation", "Implementation considerations", "Trade-offs"]

        elif intent == "creative":
            response_type = "creative_response"
            style = "conversational"
            opening = "Engage creatively while honoring all user constraints."
            sections = ["Creative response"]

        elif intent == "casual":
            response_type = "direct_answer"
            style = "conversational"
            opening = "Respond naturally and warmly to maintain conversation continuity."
            sections = ["Direct answer"]

        elif intent == "ambiguous":
            response_type = "direct_answer"
            style = "conversational"
            opening = "Answer what can be deduced, or politely seek clarification."
            sections = ["Direct answer"]

        else:  # factual / default
            response_type = "direct_answer"
            style = "simple"
            opening = "Answer the question directly in the very first sentence."
            sections = ["Direct answer", "Relevant context"]

        # 3. Dynamic Section Pruning based on Depth & Style
        if analysis.desired_depth == "brief":
            if response_type in ("direct_answer", "creative_response"):
                sections = ["Direct answer"]
            elif response_type == "troubleshooting":
                sections = ["Cause and solution"]
            elif response_type == "technical_solution":
                sections = ["Implementation"]
            else:
                sections = sections[:2]

        elif analysis.desired_depth == "deep":
            if "Important limitations" not in sections and response_type != "creative_response":
                sections.append("Important limitations and edge cases")

        # 4. Contextual Features
        include_example = analysis.needs_example or (intent == "conceptual_learning" and analysis.desired_depth != "brief")
        include_analogy = analysis.needs_analogy
        include_code = analysis.needs_code or (intent == "coding")
        include_caveats = (
            analysis.desired_depth == "deep"
            or intent in ("troubleshooting", "research", "technical_help")
        )

        # 5. Clean up sections: remove practical example if examples disabled
        if not include_example and "Practical example" in sections:
            sections.remove("Practical example")

        return ResponsePlan(
            response_type=response_type,
            opening_strategy=opening,
            sections=sections,
            explanation_style=style,
            include_example=include_example,
            include_analogy=include_analogy,
            include_code=include_code,
            include_caveats=include_caveats,
            target_length=target_length
        )
