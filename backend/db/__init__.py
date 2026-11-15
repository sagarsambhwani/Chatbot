"""Database Manager unifying sessions, messages, and schema."""

from backend.db.schema import get_db_connection, init_db
from backend.db import sessions, messages

class DatabaseManager:
    create_session = staticmethod(sessions.create_session)
    get_or_create_session = staticmethod(sessions.get_or_create_session)
    list_sessions = staticmethod(sessions.list_sessions)
    get_session = staticmethod(sessions.get_session)
    update_session_title = staticmethod(sessions.update_session_title)
    delete_session = staticmethod(sessions.delete_session)

    add_message = staticmethod(messages.add_message)
    get_messages = staticmethod(messages.get_messages)
    get_chat_history_for_llm = staticmethod(messages.get_chat_history_for_llm)

