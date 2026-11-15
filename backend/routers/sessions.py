"""Chat session management and persistence endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from backend.database import DatabaseManager
from intelligence.schemas import (
    SessionResponse,
    SessionCreateRequest,
    SessionTitleUpdateRequest
)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

@router.get("", response_model=List[SessionResponse])
async def list_sessions():
    return DatabaseManager.list_sessions()

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(req: Optional[SessionCreateRequest] = None):
    title = req.title if (req and req.title) else "New Chat"
    session_id = DatabaseManager.create_session(title=title)
    session = DatabaseManager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to initialize session")
    return session

@router.get("/{session_id}")
async def get_session(session_id: str):
    session = DatabaseManager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session, "messages": DatabaseManager.get_messages(session_id)}

@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session_title(session_id: str, req: SessionTitleUpdateRequest):
    if not DatabaseManager.update_session_title(session_id, req.title):
        raise HTTPException(status_code=404, detail="Session not found")
    return DatabaseManager.get_session(session_id)

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    if not DatabaseManager.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": f"Session '{session_id}' deleted"}

