"""Message turn storage, telemetry recording, and LLM context history."""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.db.schema import get_db_connection

def add_message(session_id: str, role: str, content: str, intent: Optional[str] = None,
                needs_web_search: bool = False, needs_rag: bool = False, needs_code: bool = False,
                desired_depth: Optional[str] = None, audio_url: str = "", latencies: Optional[Dict[str, Any]] = None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    lat_json = json.dumps(latencies or {})
    conn = get_db_connection()
    with conn:
        cur = conn.execute(
            """INSERT INTO messages (session_id, role, content, intent, needs_web_search, needs_rag,
               needs_code, desired_depth, audio_url, latencies_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, role, content, intent, int(needs_web_search), int(needs_rag),
             int(needs_code), desired_depth, audio_url, lat_json, now)
        )
        msg_id = cur.lastrowid
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.close()
    return msg_id

def get_messages(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?", (session_id, limit)
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["needs_web_search"], d["needs_rag"], d["needs_code"] = bool(d["needs_web_search"]), bool(d["needs_rag"]), bool(d["needs_code"])
        try: d["latencies"] = json.loads(d.get("latencies_json") or "{}")
        except Exception: d["latencies"] = {}
        results.append(d)
    return results

def get_chat_history_for_llm(session_id: str, last_k: int = 6) -> List[Dict[str, str]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, last_k)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

