"""Document management and local RAG indexing endpoints."""

import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.config import DATA_DIR
from backend.deps import assistant

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("")
async def list_documents():
    files = []
    if os.path.exists(DATA_DIR):
        files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith((".txt", ".md", ".pdf"))]
    return {"documents": files, "indexed_chunks": len(assistant.rag.index)}

@router.post("")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
    safe_name = os.path.basename(file.filename)
    dest_path = os.path.join(DATA_DIR, safe_name)
    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)
    indexed_count = assistant.rag.index_documents()
    return {"message": f"Successfully indexed '{safe_name}'.", "total_chunks": indexed_count}

@router.post("/reindex")
async def reindex_documents():
    count = assistant.rag.index_documents()
    return {"message": f"Re-indexed {count} document chunks."}

