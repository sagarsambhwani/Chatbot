"""Session CRUD operations for SQLite persistence."""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.db.schema import get_db_connection

def create_session(title: str = "New Chat") -> str:
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    with conn:
        conn.execute("INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)", (session_id, title, now, now))
    conn.close()
    return session_id

def get_or_create_session(session_id: Optional[str] = None, first_message: str = "") -> str:
    if session_id:
        conn = get_db_connection()
        row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        conn.close()
        if row: return session_id
    title = first_message.strip()[:40] if first_message else "New Chat"
    return create_session(title=title or "New Chat")

def list_sessions() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_session_title(session_id: str, title: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    with conn:
        cur = conn.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
        ok = cur.rowcount > 0
    conn.close()
    return ok

def delete_session(session_id: str) -> bool:
    conn = get_db_connection()
    with conn:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        ok = cur.rowcount > 0
    conn.close()
    return ok

