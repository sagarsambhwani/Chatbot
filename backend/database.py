"""SQLite database engine for session persistence, message history, and routing telemetry."""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    """Create a thread-safe connection to the local SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables with indexes for fast retrieval."""
    conn = get_db_connection()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            intent TEXT,
            needs_web_search INTEGER DEFAULT 0,
            needs_rag INTEGER DEFAULT 0,
            needs_code INTEGER DEFAULT 0,
            desired_depth TEXT,
            audio_url TEXT DEFAULT '',
            latencies_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
        """)
    conn.close()

# Ensure schema exists on module load
init_db()

class DatabaseManager:
    """Manager for Chat Sessions, Turn History, and Routing Telemetry."""

    @staticmethod
    def create_session(title: str = "New Chat") -> str:
        """Create a new chat session and return its UUID."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection()
        with conn:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now)
            )
        conn.close()
        return session_id

    @staticmethod
    def get_or_create_session(session_id: Optional[str] = None, first_message: str = "") -> str:
        """Return existing session_id or create a new session with an intuitive title."""
        if session_id:
            conn = get_db_connection()
            row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
            conn.close()
            if row:
                return session_id

        # Generate title from first query (up to 40 chars)
        title = first_message.strip()[:40] if first_message else "New Chat"
        if not title:
            title = "New Chat"
        return DatabaseManager.create_session(title=title)

    @staticmethod
    def list_sessions() -> List[Dict[str, Any]]:
        """Return all sessions sorted by recent activity."""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch session metadata."""
        conn = get_db_connection()
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_session_title(session_id: str, title: str) -> bool:
        """Update session title."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection()
        with conn:
            cur = conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id)
            )
            affected = cur.rowcount > 0
        conn.close()
        return affected

    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete session and cascade delete all messages."""
        conn = get_db_connection()
        with conn:
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            affected = cur.rowcount > 0
        conn.close()
        return affected

    @staticmethod
    def add_message(
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        needs_web_search: bool = False,
        needs_rag: bool = False,
        needs_code: bool = False,
        desired_depth: Optional[str] = None,
        audio_url: str = "",
        latencies: Optional[Dict[str, Any]] = None
    ) -> int:
        """Record a conversation turn with telemetry."""
        now = datetime.now(timezone.utc).isoformat()
        lat_json = json.dumps(latencies or {})
        conn = get_db_connection()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO messages (
                    session_id, role, content, intent,
                    needs_web_search, needs_rag, needs_code, desired_depth,
                    audio_url, latencies_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, role, content, intent,
                    int(needs_web_search), int(needs_rag), int(needs_code), desired_depth,
                    audio_url, lat_json, now
                )
            )
            msg_id = cur.lastrowid
            # Touch session updated_at
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        conn.close()
        return msg_id

    @staticmethod
    def get_messages(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch chronological messages for a session."""
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, intent,
                   needs_web_search, needs_rag, needs_code, desired_depth,
                   audio_url, latencies_json, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (session_id, limit)
        ).fetchall()
        conn.close()

        results = []
        for r in rows:
            d = dict(r)
            d["needs_web_search"] = bool(d["needs_web_search"])
            d["needs_rag"] = bool(d["needs_rag"])
            d["needs_code"] = bool(d["needs_code"])
            try:
                d["latencies"] = json.loads(d.get("latencies_json") or "{}")
            except Exception:
                d["latencies"] = {}
            results.append(d)
        return results

    @staticmethod
    def get_chat_history_for_llm(session_id: str, last_k: int = 6) -> List[Dict[str, str]]:
        """Fetch bounded conversation history for LLM prompt context."""
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, last_k)
        ).fetchall()
        conn.close()
        # Reverse to chronological order
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
