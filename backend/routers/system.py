"""System health, root navigation, and VRAM status endpoints."""

import os
from fastapi import APIRouter
from fastapi.responses import FileResponse
from backend.config import TEMPLATES_DIR, LLM_MODEL, EMBED_MODEL
from backend.deps import assistant, get_system_vram
from intelligence.schemas import SystemStatusResponse

router = APIRouter(tags=["System"])

@router.get("/", include_in_schema=False)
async def root():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "ok", "message": "Local AI Assistant API running. Visit /docs"}

@router.get("/api/system_status", response_model=SystemStatusResponse)
async def system_status():
    return SystemStatusResponse(
        vram=get_system_vram(),
        llm_model=f"{LLM_MODEL} (100% on GPU)",
        embed_model=f"{EMBED_MODEL} (GPU)",
        rag_docs_count=len(assistant.rag.index)
    )

