"""Dynamic in-context few-shot exemplar loader."""

import os
import json
from typing import Optional, Dict
from backend.config import BASE_DIR

_EXEMPLARS_CACHE: Optional[Dict[str, Dict[str, str]]] = None

def _load_exemplars() -> Dict[str, Dict[str, str]]:
    global _EXEMPLARS_CACHE
    if _EXEMPLARS_CACHE is None:
        path = os.path.join(BASE_DIR, "prompts", "exemplars.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _EXEMPLARS_CACHE = json.load(f)
        except Exception:
            _EXEMPLARS_CACHE = {}
    return _EXEMPLARS_CACHE

def get_exemplar(intent: str, has_rag: bool = False) -> Optional[Dict[str, str]]:
    """Select a high-quality demonstration pair to anchor small model generation."""
    exemplars = _load_exemplars()
    if has_rag and "rag" in exemplars:
        return exemplars["rag"]
    if intent == "coding" and "coding" in exemplars:
        return exemplars["coding"]
    if intent in ("casual", "factual") and "casual" in exemplars:
        return exemplars["casual"]
    if intent == "conceptual_learning" and "conceptual_learning" in exemplars:
        return exemplars["conceptual_learning"]
    return None

