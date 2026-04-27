"""
SQLite-based conversation memory.
Stores message history per sessionId in /data/memory.db.
Also stores skills and agent configurations.
"""
import os
import json
import sqlite3
import threading
import uuid
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_summaries (
            session_id TEXT PRIMARY KEY,
            summary    TEXT NOT NULL,
            turn_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skills (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            system_prompt TEXT DEFAULT '',
            tool_ids    TEXT DEFAULT '[]',
            constraints TEXT DEFAULT '[]',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL UNIQUE,
            description     TEXT DEFAULT '',
            provider        TEXT DEFAULT 'ollama',
            model           TEXT DEFAULT 'llama3',
            temperature     REAL DEFAULT 0.7,
            top_p           REAL DEFAULT 1.0,
            system_prompt   TEXT DEFAULT '',
            skill_ids       TEXT DEFAULT '[]',
            tool_ids        TEXT DEFAULT '[]',
            kb_collection   TEXT DEFAULT 'agentic_docs',
            max_iterations  INTEGER DEFAULT 5,
            memory_enabled  INTEGER DEFAULT 1,
            is_default      INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """
    )
    # ── Migration: add top_p column if missing (existing DBs) ──
    try:
        conn.execute("ALTER TABLE agents ADD COLUMN top_p REAL DEFAULT 1.0")
        conn.commit()
    except Exception:
        pass  # column already exists
    # ── A2A Peers table ──
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS a2a_peers (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            url         TEXT NOT NULL,
            description TEXT DEFAULT '',
            status      TEXT DEFAULT 'unknown',
            capabilities TEXT DEFAULT '[]',
            agent_card  TEXT DEFAULT '{}',
            last_seen   TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    # ── MCP Servers table ──
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            url         TEXT NOT NULL,
            transport   TEXT DEFAULT 'stdio',
            description TEXT DEFAULT '',
            status      TEXT DEFAULT 'unknown',
            tools       TEXT DEFAULT '[]',
            enabled     INTEGER DEFAULT 1,
            last_seen   TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    # ── Prompts Library table ──
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prompts (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            category    TEXT DEFAULT 'general',
            content     TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT '',
            tags        TEXT DEFAULT '[]',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    # Ensure default agent exists
    existing = conn.execute("SELECT id FROM agents WHERE is_default = 1").fetchone()
    if not existing:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO agents (id, name, description, provider, model, temperature, system_prompt, skill_ids, tool_ids, kb_collection, max_iterations, memory_enabled, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("default", "Assistant", "Default general-purpose AI assistant", "ollama", os.getenv("OLLAMA_MODEL", "llama3"), 0.7, "", "[]", "[]", "agentic_docs", 5, 1, 1, now, now),
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
    conn.execute("DELETE FROM session_summaries WHERE session_id = ?", (session_id,))
    conn.commit()
    return cursor.rowcount


def get_session_summary(session_id: str) -> str | None:
    """Return the rolling summary for a session, or None."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT summary FROM session_summaries WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["summary"] if row else None


def update_session_summary(session_id: str, user_msg: str, assistant_msg: str):
    """Append a compact turn summary to the session's rolling summary."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT summary, turn_count FROM session_summaries WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    user_short = user_msg[:200].replace("\n", " ")
    asst_short = assistant_msg[:300].replace("\n", " ")
    turn_line = f"Turn {(row['turn_count'] if row else 0) + 1}: User asked about '{user_short}' → Assistant: {asst_short}"

    if row:
        # Keep summary under ~2000 chars by trimming oldest turns
        existing = row["summary"]
        new_summary = existing + "\n" + turn_line
        if len(new_summary) > 2000:
            lines = new_summary.split("\n")
            while len("\n".join(lines)) > 2000 and len(lines) > 3:
                lines.pop(0)
            new_summary = "\n".join(lines)
        conn.execute(
            "UPDATE session_summaries SET summary = ?, turn_count = turn_count + 1, updated_at = ? WHERE session_id = ?",
            (new_summary, datetime.now(timezone.utc).isoformat(), session_id),
        )
    else:
        conn.execute(
            "INSERT INTO session_summaries (session_id, summary, turn_count, updated_at) VALUES (?, ?, 1, ?)",
            (session_id, turn_line, datetime.now(timezone.utc).isoformat()),
        )
    conn.commit()


def get_memory_stats() -> dict:
    """Return global memory statistics."""
    conn = _get_conn()
    total_messages = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
    total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) as c FROM conversations").fetchone()["c"]
    sessions_with_summary = conn.execute("SELECT COUNT(*) as c FROM session_summaries").fetchone()["c"]
    return {
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "sessions_with_summary": sessions_with_summary,
    }


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


# ── Skills CRUD ────────────────────────────────────────────────────────────

def _row_to_skill(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "system_prompt": row["system_prompt"],
        "tool_ids": json.loads(row["tool_ids"]),
        "constraints": json.loads(row["constraints"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_skills() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM skills ORDER BY name").fetchall()
    return [_row_to_skill(r) for r in rows]


def get_skill(skill_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
    return _row_to_skill(row) if row else None


def create_skill(name: str, description: str = "", system_prompt: str = "",
                 tool_ids: list[str] | None = None, constraints: list[str] | None = None) -> dict:
    conn = _get_conn()
    skill_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO skills (id, name, description, system_prompt, tool_ids, constraints, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (skill_id, name, description, system_prompt, json.dumps(tool_ids or []), json.dumps(constraints or []), now, now),
    )
    conn.commit()
    return get_skill(skill_id)


def update_skill(skill_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_skill(skill_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "description", "system_prompt"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    for key in ("tool_ids", "constraints"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(skill_id)
        conn.execute(f"UPDATE skills SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_skill(skill_id)


def delete_skill(skill_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── Agents CRUD ────────────────────────────────────────────────────────────

def _row_to_agent(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "provider": row["provider"],
        "model": row["model"],
        "temperature": row["temperature"],
        "top_p": row["top_p"] if "top_p" in row.keys() else 1.0,
        "system_prompt": row["system_prompt"],
        "skill_ids": json.loads(row["skill_ids"]),
        "tool_ids": json.loads(row["tool_ids"]),
        "kb_collection": row["kb_collection"],
        "max_iterations": row["max_iterations"],
        "memory_enabled": bool(row["memory_enabled"]),
        "is_default": bool(row["is_default"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_agents() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM agents ORDER BY is_default DESC, name").fetchall()
    return [_row_to_agent(r) for r in rows]


def get_agent(agent_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return _row_to_agent(row) if row else None


def create_agent(name: str, description: str = "", provider: str = "ollama",
                 model: str = "llama3", temperature: float = 0.7, top_p: float = 1.0,
                 system_prompt: str = "", skill_ids: list[str] | None = None,
                 tool_ids: list[str] | None = None, kb_collection: str = "agentic_docs",
                 max_iterations: int = 5, memory_enabled: bool = True) -> dict:
    conn = _get_conn()
    agent_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO agents (id, name, description, provider, model, temperature, top_p, system_prompt, skill_ids, tool_ids, kb_collection, max_iterations, memory_enabled, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (agent_id, name, description, provider, model, temperature, top_p, system_prompt,
         json.dumps(skill_ids or []), json.dumps(tool_ids or []), kb_collection,
         max_iterations, int(memory_enabled), 0, now, now),
    )
    conn.commit()
    return get_agent(agent_id)


def update_agent(agent_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_agent(agent_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "description", "provider", "model", "system_prompt", "kb_collection"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    for key in ("temperature", "top_p"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(float(kwargs[key]))
    for key in ("max_iterations",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(int(kwargs[key]))
    for key in ("memory_enabled",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(int(kwargs[key]))
    for key in ("skill_ids", "tool_ids"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(agent_id)
        conn.execute(f"UPDATE agents SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_agent(agent_id)


def delete_agent(agent_id: str) -> bool:
    conn = _get_conn()
    # Cannot delete default agent
    row = conn.execute("SELECT is_default FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if row and row["is_default"]:
        return False
    cursor = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── A2A Peers CRUD ─────────────────────────────────────────────────────────

def _row_to_a2a_peer(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "description": row["description"],
        "status": row["status"],
        "capabilities": json.loads(row["capabilities"]),
        "agent_card": json.loads(row["agent_card"]),
        "last_seen": row["last_seen"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_a2a_peers() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM a2a_peers ORDER BY name").fetchall()
    return [_row_to_a2a_peer(r) for r in rows]


def get_a2a_peer(peer_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM a2a_peers WHERE id = ?", (peer_id,)).fetchone()
    return _row_to_a2a_peer(row) if row else None


def create_a2a_peer(name: str, url: str, description: str = "",
                    capabilities: list[str] | None = None) -> dict:
    conn = _get_conn()
    peer_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO a2a_peers (id, name, url, description, capabilities, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (peer_id, name, url, description, json.dumps(capabilities or []), now, now),
    )
    conn.commit()
    return get_a2a_peer(peer_id)


def update_a2a_peer(peer_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_a2a_peer(peer_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "url", "description", "status", "last_seen"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    for key in ("capabilities",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    for key in ("agent_card",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(peer_id)
        conn.execute(f"UPDATE a2a_peers SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_a2a_peer(peer_id)


def delete_a2a_peer(peer_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM a2a_peers WHERE id = ?", (peer_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── MCP Servers CRUD ───────────────────────────────────────────────────────

def _row_to_mcp_server(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "transport": row["transport"],
        "description": row["description"],
        "status": row["status"],
        "tools": json.loads(row["tools"]),
        "enabled": bool(row["enabled"]),
        "last_seen": row["last_seen"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_mcp_servers() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM mcp_servers ORDER BY name").fetchall()
    return [_row_to_mcp_server(r) for r in rows]


def get_mcp_server(server_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM mcp_servers WHERE id = ?", (server_id,)).fetchone()
    return _row_to_mcp_server(row) if row else None


def create_mcp_server(name: str, url: str, transport: str = "stdio",
                      description: str = "", tools: list[dict] | None = None) -> dict:
    conn = _get_conn()
    server_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO mcp_servers (id, name, url, transport, description, tools, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (server_id, name, url, transport, description, json.dumps(tools or []), now, now),
    )
    conn.commit()
    return get_mcp_server(server_id)


def update_mcp_server(server_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_mcp_server(server_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "url", "transport", "description", "status", "last_seen"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    for key in ("enabled",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(int(kwargs[key]))
    for key in ("tools",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(server_id)
        conn.execute(f"UPDATE mcp_servers SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_mcp_server(server_id)


def delete_mcp_server(server_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM mcp_servers WHERE id = ?", (server_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── Prompts CRUD ───────────────────────────────────────────────────────────

def _row_to_prompt(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "content": row["content"],
        "description": row["description"],
        "tags": json.loads(row["tags"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_prompts() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM prompts ORDER BY name").fetchall()
    return [_row_to_prompt(r) for r in rows]


def get_prompt(prompt_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    return _row_to_prompt(row) if row else None


def create_prompt(name: str, content: str, category: str = "general",
                  description: str = "", tags: list[str] | None = None) -> dict:
    conn = _get_conn()
    prompt_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO prompts (id, name, category, content, description, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (prompt_id, name, category, content, description, json.dumps(tags or []), now, now),
    )
    conn.commit()
    return get_prompt(prompt_id)


def update_prompt(prompt_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_prompt(prompt_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "category", "content", "description"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    for key in ("tags",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(prompt_id)
        conn.execute(f"UPDATE prompts SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_prompt(prompt_id)


def delete_prompt(prompt_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    conn.commit()
    return cursor.rowcount > 0
