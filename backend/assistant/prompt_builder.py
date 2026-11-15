"""System prompts and in-context message assembly."""

import os
from typing import List, Dict, Optional
from backend.config import BASE_DIR
from intelligence.schemas import ResponsePlan

def load_generator_prompt() -> str:
    path = os.path.join(BASE_DIR, "prompts", "response_generator.txt")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "You are a helpful local assistant. Answer clearly, accurately, and naturally."

def build_messages(
    generator_prompt: str,
    user_prompt: str,
    chat_history: Optional[list],
    plan: ResponsePlan,
    contexts: List[str],
    exemplar: Optional[Dict[str, str]] = None
) -> List[Dict[str, str]]:
    sys_inst = generator_prompt
    if plan.target_length == "short":
        sys_inst += "\nGuidance: Keep the answer concise and direct (1-3 sentences)."
    elif plan.include_code:
        sys_inst += "\nGuidance: Include a clean, well-commented code implementation."

    messages = [{"role": "system", "content": sys_inst}]

    if exemplar:
        messages.append({"role": "user", "content": exemplar["user"]})
        messages.append({"role": "assistant", "content": exemplar["assistant"]})

    if chat_history:
        for turn in chat_history[-6:]:
            role, content = turn.get("role", "user"), turn.get("content", "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    content = f"{chr(10).join(contexts)}\n\nUser Question: {user_prompt}" if contexts else user_prompt
    messages.append({"role": "user", "content": content})
    return messages
