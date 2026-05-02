"""
SQLite-based conversation memory.
Stores message history per sessionId in /data/memory.db.
Also stores skills and agent configurations.
"""

import os
import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

MEMORY_DIR = os.getenv("MEMORY_DIR", "/data")
DB_PATH = os.path.join(MEMORY_DIR, "memory.db")

_local = threading.local()


logger = logging.getLogger(__name__)


def _get_conn() -> sqlite3.Connection:
    """One connection per thread, with automatic recovery from corrupted connections."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    else:
        # Validate cached connection is still usable
        try:
            _local.conn.execute("SELECT 1")
        except sqlite3.DatabaseError:
            logger.warning("Stale/corrupted SQLite connection detected, reconnecting")
            try:
                _local.conn.close()
            except Exception:
                pass
            _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
    return _local.conn


def _reset_conn():
    """Close and discard the cached connection so next call creates a fresh one."""
    if hasattr(_local, "conn") and _local.conn is not None:
        try:
            _local.conn.close()
        except Exception:
            pass
        _local.conn = None


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            timestamp  TEXT NOT NULL
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_summaries (
            session_id TEXT PRIMARY KEY,
            summary    TEXT NOT NULL,
            turn_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """)
    conn.execute("""
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
        """)
    conn.execute("""
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
            sub_agent_ids   TEXT DEFAULT '[]',
            kb_collection   TEXT DEFAULT 'agentic_docs',
            max_iterations  INTEGER DEFAULT 5,
            memory_enabled  INTEGER DEFAULT 1,
            is_default      INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """)
    # ── Migration: add top_p column if missing (existing DBs) ──
    try:
        conn.execute("ALTER TABLE agents ADD COLUMN top_p REAL DEFAULT 1.0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    # ── Migration: add sub_agent_ids column if missing ──
    try:
        conn.execute("ALTER TABLE agents ADD COLUMN sub_agent_ids TEXT DEFAULT '[]'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    # ── A2A Peers table ──
    conn.execute("""
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
        """)
    # ── MCP Servers table ──
    conn.execute("""
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
        """)
    # ── Prompts Library table ──
    conn.execute("""
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
        """)
    # ── Data Connectors table ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS connectors (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            connector_type  TEXT NOT NULL,
            config          TEXT DEFAULT '{}',
            enabled         INTEGER DEFAULT 1,
            schedule        TEXT DEFAULT '',
            auto_index      INTEGER DEFAULT 0,
            last_sync       TEXT DEFAULT '',
            last_status     TEXT DEFAULT '',
            doc_count       INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """)
    # ── Sync Jobs table ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_jobs (
            id              TEXT PRIMARY KEY,
            connector_id    TEXT NOT NULL,
            status          TEXT DEFAULT 'pending',
            started_at      TEXT DEFAULT '',
            completed_at    TEXT DEFAULT '',
            docs_pulled     INTEGER DEFAULT 0,
            docs_indexed    INTEGER DEFAULT 0,
            error           TEXT DEFAULT '',
            created_at      TEXT NOT NULL
        )
        """)
    # Ensure default agent exists
    existing = conn.execute("SELECT id FROM agents WHERE is_default = 1").fetchone()
    if not existing:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO agents (id, name, description, provider, model, temperature, system_prompt, skill_ids, tool_ids, kb_collection, max_iterations, memory_enabled, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "default",
                "Assistant",
                "Default general-purpose AI assistant",
                "ollama",
                os.getenv("OLLAMA_MODEL", "llama3"),
                0.7,
                "",
                "[]",
                "[]",
                "agentic_docs",
                5,
                1,
                1,
                now,
                now,
            ),
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
    total_messages = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()[
        "c"
    ]
    total_sessions = conn.execute(
        "SELECT COUNT(DISTINCT session_id) as c FROM conversations"
    ).fetchone()["c"]
    sessions_with_summary = conn.execute(
        "SELECT COUNT(*) as c FROM session_summaries"
    ).fetchone()["c"]
    return {
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "sessions_with_summary": sessions_with_summary,
    }


def get_db_stats() -> dict:
    """Return database path and record counts for all tables."""
    conn = _get_conn()
    tables = [
        "agents",
        "skills",
        "prompts",
        "conversations",
        "documents",
        "mcp_servers",
        "a2a_peers",
        "guardrails",
        "custom_tools",
        "session_summaries",
        "version_history",
        "audit_log",
    ]
    counts = {}
    for table in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
            counts[table] = row["c"]
        except Exception:
            counts[table] = 0
    db_size = 0
    try:
        db_size = os.path.getsize(DB_PATH)
    except Exception:
        pass
    return {
        "db_path": DB_PATH,
        "db_size_bytes": db_size,
        **counts,
    }


def export_all_data() -> dict:
    """Export all data from all tables as a JSON-serializable dict."""
    conn = _get_conn()
    tables = [
        "agents",
        "skills",
        "prompts",
        "guardrails",
        "custom_tools",
        "mcp_servers",
        "a2a_peers",
        "documents",
        "conversations",
        "session_summaries",
        "version_history",
        "audit_log",
    ]
    result = {}
    for table in tables:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            result[table] = [dict(r) for r in rows]
        except Exception:
            result[table] = []
    return result


def import_all_data(data: dict, merge: bool = True) -> dict:
    """Import data into all tables. If merge=True, skip existing records; if False, replace all."""
    conn = _get_conn()
    stats = {}
    for table, rows in data.items():
        if not rows:
            stats[table] = {"imported": 0, "skipped": 0}
            continue
        if not merge:
            conn.execute(f"DELETE FROM {table}")
        imported = 0
        skipped = 0
        for row in rows:
            cols = ", ".join(row.keys())
            placeholders = ", ".join(["?"] * len(row))
            try:
                conn.execute(
                    f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})",
                    list(row.values()),
                )
                imported += 1
            except Exception:
                skipped += 1
        stats[table] = {"imported": imported, "skipped": skipped}
    conn.commit()
    return stats


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


def create_skill(
    name: str,
    description: str = "",
    system_prompt: str = "",
    tool_ids: list[str] | None = None,
    constraints: list[str] | None = None,
) -> dict:
    conn = _get_conn()
    skill_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO skills (id, name, description, system_prompt, tool_ids, constraints, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            skill_id,
            name,
            description,
            system_prompt,
            json.dumps(tool_ids or []),
            json.dumps(constraints or []),
            now,
            now,
        ),
    )
    conn.commit()
    log_audit("create", "skill", skill_id, name)
    return get_skill(skill_id)


def update_skill(skill_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_skill(skill_id)
    if not existing:
        return None
    save_version("skill", skill_id, existing)
    log_audit(
        "update",
        "skill",
        skill_id,
        existing.get("name", ""),
        {"fields": list(kwargs.keys())},
    )
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
    existing = get_skill(skill_id)
    cursor = conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
    conn.commit()
    if cursor.rowcount > 0 and existing:
        log_audit("delete", "skill", skill_id, existing.get("name", ""))
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
        "sub_agent_ids": (
            json.loads(row["sub_agent_ids"]) if "sub_agent_ids" in row.keys() else []
        ),
        "kb_collection": row["kb_collection"],
        "max_iterations": row["max_iterations"],
        "memory_enabled": bool(row["memory_enabled"]),
        "is_default": bool(row["is_default"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_agents() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM agents ORDER BY is_default DESC, name"
    ).fetchall()
    return [_row_to_agent(r) for r in rows]


def get_agent(agent_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return _row_to_agent(row) if row else None


def create_agent(
    name: str,
    description: str = "",
    provider: str = "ollama",
    model: str = "llama3",
    temperature: float = 0.7,
    top_p: float = 1.0,
    system_prompt: str = "",
    skill_ids: list[str] | None = None,
    tool_ids: list[str] | None = None,
    sub_agent_ids: list[str] | None = None,
    kb_collection: str = "agentic_docs",
    max_iterations: int = 5,
    memory_enabled: bool = True,
) -> dict:
    conn = _get_conn()
    agent_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO agents (id, name, description, provider, model, temperature, top_p, system_prompt, skill_ids, tool_ids, sub_agent_ids, kb_collection, max_iterations, memory_enabled, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            agent_id,
            name,
            description,
            provider,
            model,
            temperature,
            top_p,
            system_prompt,
            json.dumps(skill_ids or []),
            json.dumps(tool_ids or []),
            json.dumps(sub_agent_ids or []),
            kb_collection,
            max_iterations,
            int(memory_enabled),
            0,
            now,
            now,
        ),
    )
    conn.commit()
    log_audit("create", "agent", agent_id, name)
    return get_agent(agent_id)


def update_agent(agent_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_agent(agent_id)
    if not existing:
        return None
    # Save version before update
    save_version("agent", agent_id, existing)
    log_audit(
        "update",
        "agent",
        agent_id,
        existing.get("name", ""),
        {"fields": list(kwargs.keys())},
    )
    fields = []
    values = []
    for key in (
        "name",
        "description",
        "provider",
        "model",
        "system_prompt",
        "kb_collection",
    ):
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
    for key in ("skill_ids", "tool_ids", "sub_agent_ids"):
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
    row = conn.execute(
        "SELECT is_default FROM agents WHERE id = ?", (agent_id,)
    ).fetchone()
    if row and row["is_default"]:
        return False
    existing = get_agent(agent_id)
    cursor = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
    conn.commit()
    if cursor.rowcount > 0 and existing:
        log_audit("delete", "agent", agent_id, existing.get("name", ""))
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


def create_a2a_peer(
    name: str, url: str, description: str = "", capabilities: list[str] | None = None
) -> dict:
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
    row = conn.execute(
        "SELECT * FROM mcp_servers WHERE id = ?", (server_id,)
    ).fetchone()
    return _row_to_mcp_server(row) if row else None


def create_mcp_server(
    name: str,
    url: str,
    transport: str = "stdio",
    description: str = "",
    tools: list[dict] | None = None,
) -> dict:
    conn = _get_conn()
    server_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO mcp_servers (id, name, url, transport, description, tools, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            server_id,
            name,
            url,
            transport,
            description,
            json.dumps(tools or []),
            now,
            now,
        ),
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


def create_prompt(
    name: str,
    content: str,
    category: str = "general",
    description: str = "",
    tags: list[str] | None = None,
) -> dict:
    conn = _get_conn()
    prompt_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO prompts (id, name, category, content, description, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            prompt_id,
            name,
            category,
            content,
            description,
            json.dumps(tags or []),
            now,
            now,
        ),
    )
    conn.commit()
    log_audit("create", "prompt", prompt_id, name)
    return get_prompt(prompt_id)


def update_prompt(prompt_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_prompt(prompt_id)
    if not existing:
        return None
    save_version("prompt", prompt_id, existing)
    log_audit(
        "update",
        "prompt",
        prompt_id,
        existing.get("name", ""),
        {"fields": list(kwargs.keys())},
    )
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
    existing = get_prompt(prompt_id)
    cursor = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    conn.commit()
    if cursor.rowcount > 0 and existing:
        log_audit("delete", "prompt", prompt_id, existing.get("name", ""))
    return cursor.rowcount > 0


# ── Guardrails ──────────────────────────────────────────────────────────────


def _init_guardrails_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guardrails (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            category    TEXT DEFAULT 'content_safety',
            description TEXT DEFAULT '',
            enabled     INTEGER DEFAULT 1,
            severity    TEXT DEFAULT 'medium',
            config      TEXT DEFAULT '{}',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """)
    conn.commit()


def _ensure_default_guardrails():
    conn = _get_conn()
    existing = conn.execute("SELECT COUNT(*) as cnt FROM guardrails").fetchone()
    if existing["cnt"] > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    defaults = [
        (
            "gr-pii",
            "PII Detection",
            "content_safety",
            "Detects and redacts personally identifiable information (emails, phone numbers, SSNs, credit cards) from inputs and outputs",
            1,
            "high",
            json.dumps(
                {
                    "patterns": ["email", "phone", "ssn", "credit_card"],
                    "action": "redact",
                }
            ),
        ),
        (
            "gr-toxicity",
            "Toxicity Filter",
            "content_safety",
            "Blocks or flags toxic, harmful, hateful, or violent content in user prompts and agent responses",
            1,
            "high",
            json.dumps(
                {
                    "threshold": 0.7,
                    "action": "block",
                    "categories": ["hate", "violence", "self_harm", "sexual"],
                }
            ),
        ),
        (
            "gr-prompt-injection",
            "Prompt Injection Guard",
            "content_safety",
            "Detects and blocks prompt injection attempts that try to override system instructions",
            1,
            "critical",
            json.dumps(
                {
                    "action": "block",
                    "patterns": [
                        "ignore previous",
                        "disregard above",
                        "new instructions",
                    ],
                }
            ),
        ),
        (
            "gr-hallucination",
            "Hallucination Detection",
            "quality",
            "Flags responses that may contain fabricated facts not grounded in the knowledge base or tool results",
            0,
            "medium",
            json.dumps({"action": "warn", "confidence_threshold": 0.5}),
        ),
        (
            "gr-bias",
            "Bias Detection",
            "fairness",
            "Monitors for biased language or stereotyping across protected categories",
            0,
            "medium",
            json.dumps(
                {"categories": ["gender", "race", "age", "religion"], "action": "flag"}
            ),
        ),
        (
            "gr-topic-restrict",
            "Topic Restriction",
            "compliance",
            "Restricts conversations to approved topics and prevents off-topic discussions",
            0,
            "low",
            json.dumps(
                {"allowed_topics": [], "blocked_topics": [], "action": "redirect"}
            ),
        ),
        (
            "gr-output-length",
            "Output Length Limit",
            "quality",
            "Enforces maximum response length to prevent excessively long outputs",
            1,
            "low",
            json.dumps({"max_tokens": 2048, "action": "truncate"}),
        ),
        (
            "gr-data-leak",
            "Data Leakage Prevention",
            "compliance",
            "Prevents the agent from revealing system prompts, internal configurations, or training data details",
            1,
            "high",
            json.dumps(
                {
                    "action": "block",
                    "protected": ["system_prompt", "config", "api_keys"],
                }
            ),
        ),
        (
            "gr-citation",
            "Source Citation Required",
            "quality",
            "Requires the agent to cite sources when using knowledge base content",
            0,
            "low",
            json.dumps({"action": "enforce", "format": "inline"}),
        ),
        (
            "gr-rate-limit",
            "Rate Limiting",
            "operational",
            "Limits the number of agent calls per session to prevent abuse",
            1,
            "medium",
            json.dumps(
                {
                    "max_calls_per_minute": 20,
                    "max_calls_per_session": 100,
                    "action": "throttle",
                }
            ),
        ),
    ]
    for d in defaults:
        conn.execute(
            "INSERT INTO guardrails (id, name, category, description, enabled, severity, config, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*d, now, now),
        )
    conn.commit()


def list_guardrails() -> list[dict]:
    _init_guardrails_table()
    _ensure_default_guardrails()
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM guardrails ORDER BY category, name").fetchall()
    return [_row_to_guardrail(r) for r in rows]


def get_guardrail(guardrail_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM guardrails WHERE id = ?", (guardrail_id,)
    ).fetchone()
    return _row_to_guardrail(row) if row else None


def update_guardrail(guardrail_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_guardrail(guardrail_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "category", "description", "severity"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    if "enabled" in kwargs:
        fields.append("enabled = ?")
        values.append(1 if kwargs["enabled"] else 0)
    if "config" in kwargs:
        fields.append("config = ?")
        values.append(
            json.dumps(kwargs["config"])
            if isinstance(kwargs["config"], dict)
            else kwargs["config"]
        )
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(guardrail_id)
        conn.execute(f"UPDATE guardrails SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_guardrail(guardrail_id)


def _row_to_guardrail(row) -> dict:
    d = dict(row)
    d["enabled"] = bool(d["enabled"])
    try:
        d["config"] = json.loads(d.get("config", "{}"))
    except (json.JSONDecodeError, TypeError):
        d["config"] = {}
    return d


# ── Custom Tools CRUD ──────────────────────────────────────────────────────


def _init_custom_tools_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_tools (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            category    TEXT DEFAULT 'proxy',
            endpoint    TEXT DEFAULT '',
            method      TEXT DEFAULT 'POST',
            headers     TEXT DEFAULT '{}',
            body_template TEXT DEFAULT '{}',
            parameters  TEXT DEFAULT '[]',
            enabled     INTEGER DEFAULT 1,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """)
    conn.commit()


def _row_to_custom_tool(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "endpoint": row["endpoint"],
        "method": row["method"],
        "headers": json.loads(row["headers"]),
        "body_template": json.loads(row["body_template"]),
        "parameters": json.loads(row["parameters"]),
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_custom_tools() -> list[dict]:
    _init_custom_tools_table()
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM custom_tools ORDER BY name").fetchall()
    return [_row_to_custom_tool(r) for r in rows]


def get_custom_tool(tool_id: str) -> dict | None:
    _init_custom_tools_table()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM custom_tools WHERE id = ?", (tool_id,)).fetchone()
    return _row_to_custom_tool(row) if row else None


def create_custom_tool(
    name: str,
    description: str = "",
    category: str = "proxy",
    endpoint: str = "",
    method: str = "POST",
    headers: dict | None = None,
    body_template: dict | None = None,
    parameters: list[dict] | None = None,
) -> dict:
    _init_custom_tools_table()
    conn = _get_conn()
    tool_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO custom_tools (id, name, description, category, endpoint, method, headers, body_template, parameters, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tool_id,
            name,
            description,
            category,
            endpoint,
            method,
            json.dumps(headers or {}),
            json.dumps(body_template or {}),
            json.dumps(parameters or []),
            now,
            now,
        ),
    )
    conn.commit()
    return get_custom_tool(tool_id)


def update_custom_tool(tool_id: str, **kwargs) -> dict | None:
    _init_custom_tools_table()
    conn = _get_conn()
    existing = get_custom_tool(tool_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "description", "category", "endpoint", "method"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    for key in ("headers", "body_template", "parameters"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    if "enabled" in kwargs:
        fields.append("enabled = ?")
        values.append(1 if kwargs["enabled"] else 0)
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(tool_id)
        conn.execute(
            f"UPDATE custom_tools SET {', '.join(fields)} WHERE id = ?", values
        )
        conn.commit()
    return get_custom_tool(tool_id)


def delete_custom_tool(tool_id: str) -> bool:
    _init_custom_tools_table()
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM custom_tools WHERE id = ?", (tool_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── Document Registry ──────────────────────────────────────────────────────


def _init_documents_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            source        TEXT NOT NULL,
            collection    TEXT NOT NULL DEFAULT 'agentic_docs',
            folder        TEXT DEFAULT '/',
            agent_tags    TEXT DEFAULT '[]',
            file_type     TEXT DEFAULT '',
            file_size     INTEGER DEFAULT 0,
            chunk_count   INTEGER DEFAULT 0,
            metadata      TEXT DEFAULT '{}',
            status        TEXT DEFAULT 'uploaded',
            storage_path  TEXT DEFAULT '',
            source_type   TEXT DEFAULT 'upload',
            shortcut_ref  TEXT DEFAULT '',
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL
        )
        """)
    # Migrations for existing databases
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'uploaded'")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN storage_path TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        conn.execute(
            "ALTER TABLE documents ADD COLUMN source_type TEXT DEFAULT 'upload'"
        )
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN shortcut_ref TEXT DEFAULT ''")
    except Exception:
        pass
    conn.commit()


def _row_to_doc(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "source": row["source"],
        "collection": row["collection"],
        "folder": row["folder"],
        "agent_tags": json.loads(row["agent_tags"] or "[]"),
        "file_type": row["file_type"],
        "file_size": row["file_size"],
        "chunk_count": row["chunk_count"],
        "metadata": json.loads(row["metadata"] or "{}"),
        "status": row["status"] if "status" in row.keys() else "uploaded",
        "storage_path": row["storage_path"] if "storage_path" in row.keys() else "",
        "source_type": row["source_type"] if "source_type" in row.keys() else "upload",
        "shortcut_ref": row["shortcut_ref"] if "shortcut_ref" in row.keys() else "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_documents_registry(
    folder: str | None = None,
    agent_id: str | None = None,
    search: str | None = None,
    collection: str | None = None,
) -> list[dict]:
    _init_documents_table()
    conn = _get_conn()
    query = "SELECT * FROM documents WHERE 1=1"
    params: list = []
    if folder and folder != "/":
        query += " AND folder = ?"
        params.append(folder)
    if collection:
        query += " AND collection = ?"
        params.append(collection)
    if agent_id:
        query += " AND agent_tags LIKE ?"
        params.append(f'%"{agent_id}"%')
    if search:
        query += " AND (name LIKE ? OR source LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY folder, name"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_doc(r) for r in rows]


def get_document_registry(doc_id: str) -> dict | None:
    _init_documents_table()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return _row_to_doc(row) if row else None


def create_document_registry(
    name: str,
    source: str,
    collection: str = "agentic_docs",
    folder: str = "/",
    agent_tags: list | None = None,
    file_type: str = "",
    file_size: int = 0,
    chunk_count: int = 0,
    metadata: dict | None = None,
    status: str = "uploaded",
    storage_path: str = "",
    source_type: str = "upload",
    shortcut_ref: str = "",
) -> dict:
    _init_documents_table()
    conn = _get_conn()
    doc_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    # Normalize folder path
    if not folder.startswith("/"):
        folder = "/" + folder
    if not folder.endswith("/"):
        folder = folder + "/"
    conn.execute(
        "INSERT INTO documents (id, name, source, collection, folder, agent_tags, file_type, file_size, chunk_count, metadata, status, storage_path, source_type, shortcut_ref, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            doc_id,
            name,
            source,
            collection,
            folder,
            json.dumps(agent_tags or []),
            file_type,
            file_size,
            chunk_count,
            json.dumps(metadata or {}),
            status,
            storage_path,
            source_type,
            shortcut_ref,
            now,
            now,
        ),
    )
    conn.commit()
    return get_document_registry(doc_id)


def update_document_registry(doc_id: str, **kwargs) -> dict | None:
    _init_documents_table()
    conn = _get_conn()
    allowed = {
        "name",
        "source",
        "folder",
        "agent_tags",
        "file_type",
        "chunk_count",
        "metadata",
        "status",
        "storage_path",
        "source_type",
        "shortcut_ref",
    }
    fields, values = [], []
    for k, v in kwargs.items():
        if k not in allowed:
            continue
        if k in ("agent_tags",):
            v = json.dumps(v) if isinstance(v, list) else v
        if k == "metadata":
            v = json.dumps(v) if isinstance(v, dict) else v
        if k == "folder":
            if not v.startswith("/"):
                v = "/" + v
            if not v.endswith("/"):
                v = v + "/"
        fields.append(f"{k} = ?")
        values.append(v)
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(doc_id)
        conn.execute(f"UPDATE documents SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_document_registry(doc_id)


def delete_document_registry(doc_id: str) -> bool:
    _init_documents_table()
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    return cursor.rowcount > 0


def delete_document_registry_by_source(
    source: str, collection: str = "agentic_docs"
) -> int:
    """Delete registry records matching a source + collection."""
    _init_documents_table()
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM documents WHERE source = ? AND collection = ?",
        (source, collection),
    )
    conn.commit()
    return cursor.rowcount


def list_folders() -> list[dict]:
    """Return all unique folder paths with document counts."""
    _init_documents_table()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT folder, COUNT(*) as count FROM documents GROUP BY folder ORDER BY folder"
    ).fetchall()
    return [{"path": r["folder"], "count": r["count"]} for r in rows]


def tag_document_to_agent(doc_id: str, agent_id: str) -> dict | None:
    """Add an agent tag to a document."""
    doc = get_document_registry(doc_id)
    if not doc:
        return None
    tags = doc["agent_tags"]
    if agent_id not in tags:
        tags.append(agent_id)
        return update_document_registry(doc_id, agent_tags=tags)
    return doc


def untag_document_from_agent(doc_id: str, agent_id: str) -> dict | None:
    """Remove an agent tag from a document."""
    doc = get_document_registry(doc_id)
    if not doc:
        return None
    tags = [t for t in doc["agent_tags"] if t != agent_id]
    return update_document_registry(doc_id, agent_tags=tags)


def untag_all_for_agent(agent_id: str) -> int:
    """Remove an agent tag from ALL documents that reference it."""
    _init_documents_table()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, agent_tags FROM documents WHERE agent_tags LIKE ?",
        (f'%"{agent_id}"%',),
    ).fetchall()
    count = 0
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        tags = json.loads(row["agent_tags"] or "[]")
        tags = [t for t in tags if t != agent_id]
        conn.execute(
            "UPDATE documents SET agent_tags = ?, updated_at = ? WHERE id = ?",
            (json.dumps(tags), now, row["id"]),
        )
        count += 1
    conn.commit()
    return count


def delete_documents_by_collection(collection: str) -> int:
    """Delete all registry records for a given collection."""
    _init_documents_table()
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM documents WHERE collection = ?", (collection,))
    conn.commit()
    return cursor.rowcount


# ── Version History ────────────────────────────────────────────────────────


def _init_version_history_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS version_history (
            id          TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id   TEXT NOT NULL,
            version     INTEGER NOT NULL,
            snapshot    TEXT NOT NULL,
            changed_by  TEXT DEFAULT 'system',
            created_at  TEXT NOT NULL
        )
        """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_vh_entity ON version_history(entity_type, entity_id)"
    )
    conn.commit()


def save_version(
    entity_type: str, entity_id: str, snapshot: dict, changed_by: str = "system"
):
    """Save a versioned snapshot of an entity before it is modified."""
    _init_version_history_table()
    conn = _get_conn()
    # Determine next version number
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) as max_v FROM version_history WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id),
    ).fetchone()
    next_version = row["max_v"] + 1
    vid = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO version_history (id, entity_type, entity_id, version, snapshot, changed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            vid,
            entity_type,
            entity_id,
            next_version,
            json.dumps(snapshot),
            changed_by,
            now,
        ),
    )
    conn.commit()
    return {"id": vid, "version": next_version}


def list_versions(entity_type: str, entity_id: str) -> list[dict]:
    """List all versions for an entity, newest first."""
    _init_version_history_table()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM version_history WHERE entity_type = ? AND entity_id = ? ORDER BY version DESC",
        (entity_type, entity_id),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "version": r["version"],
            "snapshot": json.loads(r["snapshot"]),
            "changed_by": r["changed_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_version(version_id: str) -> dict | None:
    """Get a specific version snapshot."""
    _init_version_history_table()
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM version_history WHERE id = ?", (version_id,)
    ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "version": row["version"],
        "snapshot": json.loads(row["snapshot"]),
        "changed_by": row["changed_by"],
        "created_at": row["created_at"],
    }


# ── Audit Log ──────────────────────────────────────────────────────────────


def _init_audit_log_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          TEXT PRIMARY KEY,
            action      TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id   TEXT DEFAULT '',
            entity_name TEXT DEFAULT '',
            details     TEXT DEFAULT '{}',
            performed_by TEXT DEFAULT 'system',
            created_at  TEXT NOT NULL
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at)")
    conn.commit()


def log_audit(
    action: str,
    entity_type: str,
    entity_id: str = "",
    entity_name: str = "",
    details: dict | None = None,
    performed_by: str = "system",
):
    """Record an audit log entry."""
    _init_audit_log_table()
    conn = _get_conn()
    aid = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO audit_log (id, action, entity_type, entity_id, entity_name, details, performed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            aid,
            action,
            entity_type,
            entity_id,
            entity_name,
            json.dumps(details or {}),
            performed_by,
            now,
        ),
    )
    conn.commit()


def list_audit_log(
    limit: int = 100, entity_type: str | None = None, action: str | None = None
) -> list[dict]:
    """Return recent audit log entries with optional filters."""
    _init_audit_log_table()
    conn = _get_conn()
    query = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []
    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    if action:
        query += " AND action = ?"
        params.append(action)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": r["id"],
            "action": r["action"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "entity_name": r["entity_name"],
            "details": json.loads(r["details"]),
            "performed_by": r["performed_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# ── Connectors CRUD ────────────────────────────────────────────────────────


def _row_to_connector(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "connector_type": row["connector_type"],
        "config": json.loads(row["config"]) if row["config"] else {},
        "enabled": bool(row["enabled"]),
        "schedule": row["schedule"] or "",
        "auto_index": bool(row["auto_index"]),
        "last_sync": row["last_sync"] or "",
        "last_status": row["last_status"] or "",
        "doc_count": row["doc_count"] or 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_connectors() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM connectors ORDER BY created_at DESC").fetchall()
    return [_row_to_connector(r) for r in rows]


def get_connector(connector_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM connectors WHERE id = ?", (connector_id,)
    ).fetchone()
    return _row_to_connector(row) if row else None


def create_connector(
    connector_id: str,
    name: str,
    connector_type: str,
    config: dict,
    auto_index: bool = False,
    schedule: str = "",
) -> dict:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO connectors (id, name, connector_type, config, enabled, schedule, auto_index, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)",
        (
            connector_id,
            name,
            connector_type,
            json.dumps(config),
            schedule,
            int(auto_index),
            now,
            now,
        ),
    )
    conn.commit()
    return get_connector(connector_id)


def update_connector(connector_id: str, updates: dict) -> dict | None:
    conn = _get_conn()
    allowed = {
        "name",
        "config",
        "enabled",
        "schedule",
        "auto_index",
        "last_sync",
        "last_status",
        "doc_count",
    }
    sets = []
    vals = []
    for k, v in updates.items():
        if k not in allowed:
            continue
        if k == "config":
            v = json.dumps(v)
        elif k in ("enabled", "auto_index"):
            v = int(v)
        sets.append(f"{k} = ?")
        vals.append(v)
    if not sets:
        return get_connector(connector_id)
    sets.append("updated_at = ?")
    vals.append(datetime.now(timezone.utc).isoformat())
    vals.append(connector_id)
    conn.execute(f"UPDATE connectors SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    return get_connector(connector_id)


def delete_connector(connector_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM connectors WHERE id = ?", (connector_id,))
    conn.execute("DELETE FROM sync_jobs WHERE connector_id = ?", (connector_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── Sync Jobs CRUD ─────────────────────────────────────────────────────────


def create_sync_job(job_id: str, connector_id: str) -> dict:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO sync_jobs (id, connector_id, status, started_at, created_at) VALUES (?, ?, 'running', ?, ?)",
        (job_id, connector_id, now, now),
    )
    conn.commit()
    return {
        "id": job_id,
        "connector_id": connector_id,
        "status": "running",
        "started_at": now,
    }


def update_sync_job(
    job_id: str,
    status: str,
    docs_pulled: int = 0,
    docs_indexed: int = 0,
    error: str = "",
):
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE sync_jobs SET status = ?, completed_at = ?, docs_pulled = ?, docs_indexed = ?, error = ? WHERE id = ?",
        (status, now, docs_pulled, docs_indexed, error, job_id),
    )
    conn.commit()


def list_sync_jobs(connector_id: str = "", limit: int = 20) -> list[dict]:
    conn = _get_conn()
    if connector_id:
        rows = conn.execute(
            "SELECT * FROM sync_jobs WHERE connector_id = ? ORDER BY created_at DESC LIMIT ?",
            (connector_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sync_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {
            "id": r["id"],
            "connector_id": r["connector_id"],
            "status": r["status"],
            "started_at": r["started_at"] or "",
            "completed_at": r["completed_at"] or "",
            "docs_pulled": r["docs_pulled"] or 0,
            "docs_indexed": r["docs_indexed"] or 0,
            "error": r["error"] or "",
            "created_at": r["created_at"],
        }
        for r in rows
    ]
