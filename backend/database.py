"""Backward-compatible facade for DatabaseManager."""

from backend.db import DatabaseManager
from backend.db.schema import get_db_connection, init_db

__all__ = ["DatabaseManager", "get_db_connection", "init_db"]
