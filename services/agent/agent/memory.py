"""
SQLite-based conversation memory.
Stores message history per sessionId in /data/memory.db.
"""
import os
import sqlite3
import threading
from datetime import datetime, timezone

MEMORY_DIR = os.getenv("MEMORY_DIR", "/data")
DB_PATH = os.path.join(MEMORY_DIR, "memory.db")

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """One connection per thread (SQLite is not thread-safe by default)."""
    if not hasattr(_local, "conn"):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            timestamp  TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)"
    )
    conn.commit()


def get_history(session_id: str, limit: int = 20) -> list[dict]:
    """Return the last *limit* messages for a session."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content FROM conversations "
        "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def save_message(session_id: str, role: str, content: str):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) "
        "VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def list_sessions(limit: int = 50) -> list[dict]:
    """Return recent sessions with their last message timestamp."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT session_id,
               COUNT(*) as message_count,
               MIN(timestamp) as first_message,
               MAX(timestamp) as last_message
        FROM conversations
        GROUP BY session_id
        ORDER BY MAX(timestamp) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "session_id": r["session_id"],
            "message_count": r["message_count"],
            "first_message": r["first_message"],
            "last_message": r["last_message"],
        }
        for r in rows
    ]


def delete_session(session_id: str) -> int:
    """Delete all messages for a session. Returns count of deleted rows."""
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM conversations WHERE session_id = ?", (session_id,)
    )
    conn.commit()
    return cursor.rowcount


def get_relevant_context(query: str, k: int = 3) -> list[dict]:
    """
    Retrieve relevant context from ChromaDB vector store.
    Falls back gracefully if ChromaDB is not available.
    """
    try:
        from agent.vectorstore import search_similar
        results = search_similar(query, k=k)
        return results
    except Exception:
        return []
