"""
SQLite-based platform state + PostgreSQL document datastore.

Two databases:
  - platform.db  (SQLite, embedded) — config, conversation memory, audit
  - datastore-db (PostgreSQL, container :5433) — document registry

Platform.db tables: conversations, session_summaries, agents, skills, prompts,
  guardrails, custom_tools, a2a_peers, mcp_servers, connectors, sync_jobs,
  version_history, audit_log.

Datastore (Postgres) tables: documents.
"""

import json
import logging
import os
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

import bcrypt

MEMORY_DIR = os.getenv("MEMORY_DIR", "/data")
DB_PATH = os.path.join(MEMORY_DIR, "platform.db")
DATASTORE_DB_URL = os.getenv(
    "DATASTORE_DB_URL",
    "postgresql://agentic:agentic@datastore-db:5432/datastore",
)

_local = threading.local()
_ds_pool = None


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


# ── Datastore (PostgreSQL) connection pool ──────────────────────────────────


def _get_ds_pool():
    """Lazy-init a connection pool for the document datastore."""
    global _ds_pool
    if _ds_pool is None:
        import psycopg2
        from psycopg2 import pool as pg_pool
        from psycopg2.extras import RealDictCursor  # noqa: F401

        _ds_pool = pg_pool.SimpleConnectionPool(1, 5, DATASTORE_DB_URL)
    return _ds_pool


def _get_datastore_conn():
    """Get a connection from the Postgres datastore pool."""
    return _get_ds_pool().getconn()


def _release_datastore_conn(conn):
    """Return a connection to the pool."""
    _get_ds_pool().putconn(conn)


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
            input_parameters TEXT DEFAULT '[]',
            files       TEXT DEFAULT '[]',
            scope       TEXT DEFAULT 'global',
            workspace_id TEXT DEFAULT 'default',
            created_by  TEXT DEFAULT 'system',
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
            constraints     TEXT DEFAULT '[]',
            mcp_server_ids  TEXT DEFAULT '[]',
            kb_collection   TEXT DEFAULT 'agentic_docs',
            retrieval_mode  TEXT DEFAULT 'basic',
            max_iterations  INTEGER DEFAULT 5,
            memory_enabled  INTEGER DEFAULT 1,
            is_default      INTEGER DEFAULT 0,
            scope           TEXT DEFAULT 'global',
            workspace_id    TEXT DEFAULT 'default',
            created_by      TEXT DEFAULT 'system',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """)
    # ── Migration: add input_parameters column to skills if missing ──
    try:
        conn.execute("ALTER TABLE skills ADD COLUMN input_parameters TEXT DEFAULT '[]'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
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
    # ── Migration: add retrieval_mode column if missing ──
    try:
        conn.execute(
            "ALTER TABLE agents ADD COLUMN retrieval_mode TEXT DEFAULT 'basic'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    # ── Migration: add constraints column to agents if missing ──
    try:
        conn.execute("ALTER TABLE agents ADD COLUMN constraints TEXT DEFAULT '[]'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    # ── Migration: add mcp_server_ids column if missing ──
    try:
        conn.execute("ALTER TABLE agents ADD COLUMN mcp_server_ids TEXT DEFAULT '[]'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    # ── Migration: add files column to skills if missing ──
    try:
        conn.execute("ALTER TABLE skills ADD COLUMN files TEXT DEFAULT '[]'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    # ── Migration: add model + validation columns to prompts if missing ──
    for col, default in [
        ("model", "''"),
        ("validation_score", "NULL"),
        ("validation_details", "'{}'"),
        ("validated_at", "''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE prompts ADD COLUMN {col} TEXT DEFAULT {default}")
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
            scope       TEXT DEFAULT 'global',
            workspace_id TEXT DEFAULT 'default',
            created_by  TEXT DEFAULT 'system',
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
            managed     TEXT DEFAULT '0',
            server_type TEXT DEFAULT 'external',
            config      TEXT DEFAULT '{}',
            container_id TEXT DEFAULT '',
            container_name TEXT DEFAULT '',
            container_status TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            scope       TEXT DEFAULT 'global',
            workspace_id TEXT DEFAULT 'default',
            created_by  TEXT DEFAULT 'system',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """)
    # ── Migration: add managed MCP server columns if missing ──
    for col, default in [
        ("managed", "0"),
        ("server_type", "'external'"),
        ("config", "'{}'"),
        ("container_id", "''"),
        ("container_name", "''"),
        ("container_status", "''"),
        ("error_message", "''"),
    ]:
        try:
            conn.execute(
                f"ALTER TABLE mcp_servers ADD COLUMN {col} TEXT DEFAULT {default}"
            )
            conn.commit()
        except sqlite3.OperationalError:
            pass
    # ── Prompts Library table ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            category    TEXT DEFAULT 'general',
            content     TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT '',
            tags        TEXT DEFAULT '[]',
            model       TEXT DEFAULT '',
            validation_score TEXT DEFAULT NULL,
            validation_details TEXT DEFAULT '{}',
            validated_at TEXT DEFAULT '',
            scope       TEXT DEFAULT 'global',
            workspace_id TEXT DEFAULT 'default',
            created_by  TEXT DEFAULT 'system',
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
    # ── Platform Settings table (global constraints, etc.) ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS platform_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '[]'
        )
        """)
    # Seed global constraints if not present
    existing_gc = conn.execute(
        "SELECT key FROM platform_settings WHERE key = 'global_constraints'"
    ).fetchone()
    if not existing_gc:
        conn.execute(
            "INSERT INTO platform_settings (key, value) VALUES (?, ?)",
            ("global_constraints", "[]"),
        )
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

    # ── Workspaces & RBAC ──────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            created_by  TEXT DEFAULT 'system',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workspace_members (
            workspace_id TEXT NOT NULL,
            user_id      TEXT NOT NULL,
            role         TEXT NOT NULL DEFAULT 'member',
            added_at     TEXT NOT NULL,
            PRIMARY KEY (workspace_id, user_id)
        )
    """)
    # Seed default workspace
    if not conn.execute("SELECT id FROM workspaces WHERE id = 'default'").fetchone():
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO workspaces (id, name, description, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "default",
                "Default",
                "Default workspace — shared by all users",
                "system",
                now,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, user_id, role, added_at) VALUES (?, ?, ?, ?)",
            ("default", "system", "admin", now),
        )

    # ── Migration: add scope/workspace_id/created_by to resource tables ──
    _SCOPED_TABLES = [
        "agents",
        "skills",
        "prompts",
        "mcp_servers",
        "custom_tools",
        "a2a_peers",
    ]
    for tbl in _SCOPED_TABLES:
        for col, default_val in [
            ("scope", "'global'"),
            ("workspace_id", "'default'"),
            ("created_by", "'system'"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE {tbl} ADD COLUMN {col} TEXT DEFAULT {default_val}"
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass  # column already exists

    # ── Users & Authentication ─────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              TEXT PRIMARY KEY,
            username        TEXT NOT NULL UNIQUE,
            password_hash   TEXT NOT NULL,
            display_name    TEXT DEFAULT '',
            email           TEXT DEFAULT '',
            role            TEXT NOT NULL DEFAULT 'member',
            default_workspace TEXT DEFAULT 'default',
            is_active       INTEGER DEFAULT 1,
            email_verified  INTEGER DEFAULT 0,
            verification_code TEXT DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)
    # Migration: add email_verified / verification_code if missing
    for col, default_val in [("email_verified", "0"), ("verification_code", "''")]:
        try:
            conn.execute(
                f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT {default_val}"
            )
            conn.commit()
        except sqlite3.OperationalError:
            pass
    # Seed default users if table is empty — passwords read from env vars
    if not conn.execute("SELECT id FROM users LIMIT 1").fetchone():
        now = datetime.now(timezone.utc).isoformat()
        _seed_users = [
            (
                "admin",
                os.environ.get("ADMIN_SEED_PASSWORD", "admin"),
                "admin",
                "Platform Administrator",
                "admin@agentic.local",
            ),
            (
                "rachit",
                os.environ.get("RACHIT_SEED_PASSWORD", "rachit123"),
                "member",
                "Rachit Gupta",
                "rachit@agentic.local",
            ),
        ]
        for uname, pwd, role, display, email in _seed_users:
            uid = uname  # use username as id for seed users
            phash = _hash_password(pwd)
            conn.execute(
                "INSERT INTO users (id, username, password_hash, display_name, email, role, default_workspace, is_active, email_verified, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
                (uid, uname, phash, display, email, role, "default", now, now),
            )
            # Also add seed users as members of default workspace
            try:
                conn.execute(
                    "INSERT INTO workspace_members (workspace_id, user_id, role, added_at) VALUES (?, ?, ?, ?)",
                    ("default", uname, role, now),
                )
            except sqlite3.IntegrityError:
                pass  # already exists

    conn.commit()

    # ── Personas (role-based access profiles) ──────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            permissions TEXT DEFAULT '{}',
            is_system   INTEGER DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_personas (
            user_id    TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            PRIMARY KEY (user_id, persona_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE
        )
    """)
    # Seed default personas if table is empty
    if not conn.execute("SELECT id FROM personas LIMIT 1").fetchone():
        now = datetime.now(timezone.utc).isoformat()
        _default_personas = [
            (
                "admin",
                "Admin",
                "Full platform access — user management, configuration, all features",
                '{"nav":["overview","run-agent","agent-builder","agent-hub","agents","skills","prompts","tools","ai-studio","documents","data-ingestion","workflows","pipelines","a2a","mcp","rest","intelligence-hub","llm-activity","traceability","evaluation","observability","guardrails","marketplace","docs","admin"],"actions":["create_agents","run_agents","manage_tools","manage_users","access_admin","view_observability","ingest_data","manage_workflows","manage_pipelines","access_protocols","manage_guardrails","create_global"]}',
            ),
            (
                "developer",
                "Developer",
                "Build and test agents, manage tools and skills, run workflows",
                '{"nav":["overview","run-agent","agent-builder","agent-hub","agents","skills","prompts","tools","ai-studio","documents","data-ingestion","workflows","pipelines","a2a","mcp","rest","intelligence-hub","llm-activity","traceability","evaluation","observability","guardrails","marketplace","docs"],"actions":["create_agents","run_agents","manage_tools","ingest_data","manage_workflows","manage_pipelines","access_protocols","view_observability"]}',
            ),
            (
                "analyst",
                "Analyst",
                "Run agents, explore data, view observability and evaluation reports",
                '{"nav":["overview","run-agent","documents","intelligence-hub","llm-activity","traceability","evaluation","observability","docs"],"actions":["run_agents","view_observability"]}',
            ),
            (
                "viewer",
                "Viewer",
                "Read-only access — view dashboards, docs, and reports",
                '{"nav":["overview","intelligence-hub","llm-activity","observability","docs"],"actions":["view_observability"]}',
            ),
        ]
        for pid, name, desc, perms in _default_personas:
            conn.execute(
                "INSERT INTO personas (id, name, description, permissions, is_system, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 1, ?, ?)",
                (pid, name, desc, perms, now, now),
            )
        # Assign personas to seed users
        conn.execute(
            "INSERT OR IGNORE INTO user_personas (user_id, persona_id) VALUES (?, ?)",
            ("admin", "admin"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_personas (user_id, persona_id) VALUES (?, ?)",
            ("admin", "developer"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_personas (user_id, persona_id) VALUES (?, ?)",
            ("rachit", "developer"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_personas (user_id, persona_id) VALUES (?, ?)",
            ("rachit", "analyst"),
        )
    conn.commit()

    # ── Pipelines (multi-agent workflow pipelines) ─────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipelines (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            strategy    TEXT DEFAULT 'sequential',
            steps       TEXT DEFAULT '[]',
            status      TEXT DEFAULT 'draft',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id           TEXT PRIMARY KEY,
            pipeline_id  TEXT NOT NULL,
            status       TEXT DEFAULT 'pending',
            strategy     TEXT DEFAULT 'sequential',
            steps        TEXT DEFAULT '[]',
            step_results TEXT DEFAULT '[]',
            started_at   TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            created_at   TEXT NOT NULL,
            FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
        )
    """)
    conn.commit()


# ── Password Hashing (bcrypt — enterprise standard) ──────────────────────


def _hash_password(password: str) -> str:
    """Hash password using bcrypt with auto-generated salt (cost factor 12)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode(
        "utf-8"
    )


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored bcrypt hash (constant-time comparison)."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


# ── User CRUD ─────────────────────────────────────────────────────────────


def authenticate_user(username: str, password: str) -> dict | None:
    """Verify credentials and return user dict (without password_hash) or None.
    Returns {"error": "email_not_verified"} if the email is not yet verified
    (seed/test accounts admin/rachit/Test are exempt)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
    ).fetchone()
    if not row:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    # Seed/admin/test accounts bypass verification
    exempt = (
        row["id"] in ("admin", "rachit")
        or row["username"] == "Test"
        or row["role"] == "admin"
    )
    try:
        verified = bool(int(row["email_verified"]))
    except (KeyError, IndexError):
        verified = False
    if not exempt and not verified:
        return {
            "error": "email_not_verified",
            "user_id": row["id"],
            "email": row["email"],
        }
    return _row_to_user(row)


def _row_to_user(row) -> dict:
    """Convert a SQLite Row to a user dict (excluding password_hash)."""
    d = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "email": row["email"],
        "role": row["role"],
        "default_workspace": row["default_workspace"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    try:
        d["email_verified"] = bool(int(row["email_verified"]))
    except (KeyError, IndexError):
        d["email_verified"] = False
    # Attach assigned personas
    conn = _get_conn()
    persona_rows = conn.execute(
        "SELECT p.id, p.name, p.description, p.permissions FROM personas p "
        "JOIN user_personas up ON up.persona_id = p.id WHERE up.user_id = ?",
        (row["id"],),
    ).fetchall()
    d["personas"] = [
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "permissions": json.loads(r["permissions"]),
        }
        for r in persona_rows
    ]
    return d


def get_user(user_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return _row_to_user(row) if row else None


def reset_user_password(user_id: str, new_password: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    phash = _hash_password(new_password)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (phash, now, user_id),
    )
    conn.commit()
    return get_user(user_id)


def list_users() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
    return [_row_to_user(r) for r in rows]


def create_user(
    username: str,
    password: str,
    display_name: str = "",
    email: str = "",
    role: str = "member",
    default_workspace: str = "default",
    pre_verified: bool = False,
) -> dict:
    conn = _get_conn()
    # Unique email check (skip empty emails)
    if email:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? AND email != ''", (email,)
        ).fetchone()
        if existing:
            return {"error": "email_already_used"}
    uid = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    phash = _hash_password(password)
    if pre_verified:
        # Admin-created / seed users: skip verification
        code = ""
        verified = 1
    else:
        # Self-registered users: require email verification
        import random

        code = f"{random.randint(100000, 999999)}"
        verified = 0
    conn.execute(
        "INSERT INTO users (id, username, password_hash, display_name, email, role, default_workspace, is_active, email_verified, verification_code, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)",
        (
            uid,
            username,
            phash,
            display_name,
            email,
            role,
            default_workspace,
            verified,
            code,
            now,
            now,
        ),
    )
    conn.commit()
    user = get_user(uid)
    if code:
        user["verification_code"] = code
    return user


def verify_user_email(user_id: str, code: str) -> dict | None:
    """Verify a user's email with the 6-digit code. Returns user dict on success."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    stored_code = row["verification_code"] if "verification_code" in row.keys() else ""
    if stored_code != code:
        return {"error": "invalid_code"}
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET email_verified = 1, verification_code = '', updated_at = ? WHERE id = ?",
        (now, user_id),
    )
    conn.commit()
    return get_user(user_id)


def resend_verification_code(user_id: str) -> dict | None:
    """Generate a new 6-digit verification code for the user."""
    import random

    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    code = f"{random.randint(100000, 999999)}"
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET verification_code = ?, updated_at = ? WHERE id = ?",
        (code, now, user_id),
    )
    conn.commit()
    return {"user_id": user_id, "verification_code": code, "email": row["email"]}


def update_user(user_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    allowed = {"display_name", "email", "role", "default_workspace", "is_active"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    # Handle password change separately
    if "password" in kwargs and kwargs["password"]:
        updates["password_hash"] = _hash_password(kwargs["password"])
    # Unique email check when changing email
    if "email" in updates and updates["email"]:
        dup = conn.execute(
            "SELECT id FROM users WHERE email = ? AND email != '' AND id != ?",
            (updates["email"], user_id),
        ).fetchone()
        if dup:
            return {"error": "email_already_used"}
    if not updates:
        return _row_to_user(row)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE users SET {set_clause} WHERE id = ?",
        (*updates.values(), user_id),
    )
    conn.commit()
    return get_user(user_id)


def delete_user(user_id: str) -> bool:
    """Delete a user. Cannot delete the admin seed user."""
    if user_id == "admin":
        return False
    conn = _get_conn()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.execute("DELETE FROM workspace_members WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_personas WHERE user_id = ?", (user_id,))
    conn.commit()
    return True


# ── Persona CRUD ───────────────────────────────────────────────────────────


def list_personas() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM personas ORDER BY name").fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "permissions": json.loads(r["permissions"]),
            "is_system": bool(r["is_system"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def get_persona(persona_id: str) -> dict | None:
    conn = _get_conn()
    r = conn.execute("SELECT * FROM personas WHERE id = ?", (persona_id,)).fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "name": r["name"],
        "description": r["description"],
        "permissions": json.loads(r["permissions"]),
        "is_system": bool(r["is_system"]),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def create_persona(
    name: str, description: str = "", permissions: dict | None = None
) -> dict:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    pid = str(uuid4())[:8]
    perms_json = json.dumps(permissions or {"nav": [], "actions": []})
    conn.execute(
        "INSERT INTO personas (id, name, description, permissions, is_system, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 0, ?, ?)",
        (pid, name, description, perms_json, now, now),
    )
    conn.commit()
    return get_persona(pid)


def update_persona(
    persona_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    permissions: dict | None = None,
) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM personas WHERE id = ?", (persona_id,)).fetchone()
    if not row:
        return None
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if permissions is not None:
        updates["permissions"] = json.dumps(permissions)
    if not updates:
        return get_persona(persona_id)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE personas SET {set_clause} WHERE id = ?",
        (*updates.values(), persona_id),
    )
    conn.commit()
    return get_persona(persona_id)


def delete_persona(persona_id: str) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT is_system FROM personas WHERE id = ?", (persona_id,)
    ).fetchone()
    if not row or row["is_system"]:
        return False
    conn.execute("DELETE FROM user_personas WHERE persona_id = ?", (persona_id,))
    conn.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
    conn.commit()
    return True


def get_user_personas(user_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT p.id, p.name, p.description, p.permissions FROM personas p "
        "JOIN user_personas up ON up.persona_id = p.id WHERE up.user_id = ?",
        (user_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "permissions": json.loads(r["permissions"]),
        }
        for r in rows
    ]


def assign_persona(user_id: str, persona_id: str) -> bool:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO user_personas (user_id, persona_id) VALUES (?, ?)",
            (user_id, persona_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def unassign_persona(user_id: str, persona_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM user_personas WHERE user_id = ? AND persona_id = ?",
        (user_id, persona_id),
    )
    conn.commit()
    return cur.rowcount > 0


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


def _scope_fields(row) -> dict:
    """Extract scope/workspace/created_by from a row, with safe defaults for old DBs."""
    keys = row.keys() if hasattr(row, "keys") else []
    return {
        "scope": row["scope"] if "scope" in keys else "global",
        "workspace_id": row["workspace_id"] if "workspace_id" in keys else "default",
        "created_by": row["created_by"] if "created_by" in keys else "system",
    }


def _row_to_skill(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "system_prompt": row["system_prompt"],
        "tool_ids": json.loads(row["tool_ids"]),
        "constraints": json.loads(row["constraints"]),
        "input_parameters": json.loads(row["input_parameters"] or "[]"),
        "files": json.loads(row["files"]) if "files" in row.keys() else [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        **_scope_fields(row),
    }


def list_skills() -> list[dict]:
    from agent.workspace import visibility_filter_sql, visibility_params

    conn = _get_conn()
    rows = conn.execute(
        f"SELECT * FROM skills WHERE {visibility_filter_sql()} ORDER BY name",
        visibility_params(),
    ).fetchall()
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
    input_parameters: list[dict] | None = None,
    scope: str = "private",
) -> dict:
    from agent.workspace import effective_scope, get_user_id, get_workspace_id

    conn = _get_conn()
    skill_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO skills (id, name, description, system_prompt, tool_ids, constraints, input_parameters, scope, workspace_id, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            skill_id,
            name,
            description,
            system_prompt,
            json.dumps(tool_ids or []),
            json.dumps(constraints or []),
            json.dumps(input_parameters or []),
            effective_scope(scope),
            get_workspace_id(),
            get_user_id(),
            now,
            now,
        ),
    )
    conn.commit()
    log_audit("create", "skill", skill_id, name)
    return get_skill(skill_id)


def update_skill(skill_id: str, **kwargs) -> dict | None:
    from agent.workspace import effective_scope

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
    if "scope" in kwargs:
        fields.append("scope = ?")
        values.append(effective_scope(kwargs["scope"]))
    for key in ("tool_ids", "constraints", "input_parameters"):
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
        # Clean up files on disk
        _delete_skill_files_dir(skill_id)
    return cursor.rowcount > 0


# ── Global Constraints (platform-level) ────────────────────────────────────


def get_global_constraints() -> list[str]:
    """Return the list of global constraints that apply to all agents and skills."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM platform_settings WHERE key = 'global_constraints'"
    ).fetchone()
    if not row:
        return []
    return json.loads(row["value"])


def set_global_constraints(constraints: list[str]) -> list[str]:
    """Replace the global constraints list."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO platform_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("global_constraints", json.dumps(constraints)),
    )
    conn.commit()
    log_audit(
        "update",
        "platform_settings",
        "global_constraints",
        f"{len(constraints)} constraints",
    )
    return constraints


# ── Security Considerations (platform-level) ──────────────────────────────


def get_security_considerations() -> list[str]:
    """Return the list of organisational security considerations."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM platform_settings WHERE key = 'security_considerations'"
    ).fetchone()
    if not row:
        return []
    return json.loads(row["value"])


def set_security_considerations(items: list[str]) -> list[str]:
    """Replace the security considerations list."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO platform_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("security_considerations", json.dumps(items)),
    )
    conn.commit()
    log_audit(
        "update",
        "platform_settings",
        "security_considerations",
        f"{len(items)} items",
    )
    return items


# ── Best Practices (platform-level) ────────────────────────────────────────


def get_best_practices() -> list[str]:
    """Return the list of organisational best practices."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM platform_settings WHERE key = 'best_practices'"
    ).fetchone()
    if not row:
        return []
    return json.loads(row["value"])


def set_best_practices(practices: list[str]) -> list[str]:
    """Replace the best practices list."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO platform_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("best_practices", json.dumps(practices)),
    )
    conn.commit()
    log_audit(
        "update",
        "platform_settings",
        "best_practices",
        f"{len(practices)} practices",
    )
    return practices


# ── Tool Settings ──────────────────────────────────────────────────────────


def get_disabled_tools() -> list[str]:
    """Return list of disabled built-in tool names."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM platform_settings WHERE key = 'disabled_tools'"
    ).fetchone()
    if not row:
        return []
    return json.loads(row["value"])


def set_disabled_tools(disabled: list[str]) -> list[str]:
    """Replace the disabled tools list."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO platform_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("disabled_tools", json.dumps(disabled)),
    )
    conn.commit()
    log_audit(
        "update",
        "platform_settings",
        "disabled_tools",
        f"{len(disabled)} tools disabled",
    )
    return disabled


# ── Skill File Management ──────────────────────────────────────────────────

SKILL_FILES_ROOT = os.path.join(
    os.getenv("FILESTORE_ROOT", "/data/filestore"), "skills"
)
ALLOWED_FILE_EXTENSIONS = {
    ".py",
    ".sh",
    ".bash",
    ".js",
    ".ts",
    ".ps1",
    ".md",
    ".txt",
    ".pdf",
    ".docx",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".html",
    ".xml",
    ".tmpl",
    ".jinja",
    ".j2",
}
VALID_CATEGORIES = {"scripts", "references", "assets"}
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB per file
MAX_SKILL_FILES_SIZE = 5 * 1024 * 1024  # 5 MB total per skill


def _skill_file_dir(skill_id: str, category: str) -> str:
    return os.path.join(SKILL_FILES_ROOT, skill_id, category)


def _delete_skill_files_dir(skill_id: str):
    import shutil

    d = os.path.join(SKILL_FILES_ROOT, skill_id)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def add_skill_file(skill_id: str, category: str, filename: str, content: bytes) -> dict:
    """Save a file to a skill and update file metadata in DB. Returns file info."""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise ValueError(
            f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_FILE_EXTENSIONS))}"
        )
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"File exceeds {MAX_FILE_SIZE // 1024}KB limit")

    skill = get_skill(skill_id)
    if not skill:
        raise ValueError("Skill not found")

    # Check total size
    existing_files = skill.get("files", [])
    total = sum(f.get("size_bytes", 0) for f in existing_files)
    if total + len(content) > MAX_SKILL_FILES_SIZE:
        raise ValueError(
            f"Total file size would exceed {MAX_SKILL_FILES_SIZE // (1024*1024)}MB limit"
        )

    # Sanitize filename: only allow safe characters
    import re

    safe_name = re.sub(r"[^\w.\-]", "_", filename)
    if not safe_name:
        raise ValueError("Invalid filename")

    # Write to disk
    d = _skill_file_dir(skill_id, category)
    os.makedirs(d, exist_ok=True)
    filepath = os.path.join(d, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    # Update metadata in DB
    file_meta = {
        "name": safe_name,
        "category": category,
        "size_bytes": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    # Remove existing entry with same name+category, then append
    existing_files = [
        f
        for f in existing_files
        if not (f["name"] == safe_name and f["category"] == category)
    ]
    existing_files.append(file_meta)
    conn = _get_conn()
    conn.execute(
        "UPDATE skills SET files = ?, updated_at = ? WHERE id = ?",
        (json.dumps(existing_files), datetime.now(timezone.utc).isoformat(), skill_id),
    )
    conn.commit()
    return file_meta


def remove_skill_file(skill_id: str, category: str, filename: str) -> bool:
    """Delete a file from a skill."""
    skill = get_skill(skill_id)
    if not skill:
        return False
    filepath = os.path.join(_skill_file_dir(skill_id, category), filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    existing = skill.get("files", [])
    new_files = [
        f for f in existing if not (f["name"] == filename and f["category"] == category)
    ]
    if len(new_files) == len(existing):
        return False
    conn = _get_conn()
    conn.execute(
        "UPDATE skills SET files = ?, updated_at = ? WHERE id = ?",
        (json.dumps(new_files), datetime.now(timezone.utc).isoformat(), skill_id),
    )
    conn.commit()
    return True


def get_skill_file_path(skill_id: str, category: str, filename: str) -> str | None:
    """Return the disk path of a skill file, or None."""
    p = os.path.join(_skill_file_dir(skill_id, category), filename)
    return p if os.path.exists(p) else None


def read_skill_file_text(skill_id: str, category: str, filename: str) -> str | None:
    """Read a skill file as text. Returns None if not found or binary."""
    p = get_skill_file_path(skill_id, category, filename)
    if not p:
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, OSError):
        return None


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
        "constraints": (
            json.loads(row["constraints"]) if "constraints" in row.keys() else []
        ),
        "mcp_server_ids": (
            json.loads(row["mcp_server_ids"]) if "mcp_server_ids" in row.keys() else []
        ),
        "kb_collection": row["kb_collection"],
        "max_iterations": row["max_iterations"],
        "memory_enabled": bool(row["memory_enabled"]),
        "is_default": bool(row["is_default"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        **_scope_fields(row),
    }


def list_agents() -> list[dict]:
    from agent.workspace import visibility_filter_sql, visibility_params

    conn = _get_conn()
    rows = conn.execute(
        f"SELECT * FROM agents WHERE {visibility_filter_sql()} ORDER BY is_default DESC, name",
        visibility_params(),
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
    constraints: list[str] | None = None,
    mcp_server_ids: list[str] | None = None,
    kb_collection: str = "agentic_docs",
    retrieval_mode: str = "basic",
    max_iterations: int = 5,
    memory_enabled: bool = True,
    scope: str = "private",
) -> dict:
    from agent.workspace import effective_scope, get_user_id, get_workspace_id

    conn = _get_conn()
    agent_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO agents (id, name, description, provider, model, temperature, top_p, system_prompt, skill_ids, tool_ids, sub_agent_ids, constraints, mcp_server_ids, kb_collection, retrieval_mode, max_iterations, memory_enabled, is_default, scope, workspace_id, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            json.dumps(constraints or []),
            json.dumps(mcp_server_ids or []),
            kb_collection,
            retrieval_mode,
            max_iterations,
            int(memory_enabled),
            0,
            effective_scope(scope),
            get_workspace_id(),
            get_user_id(),
            now,
            now,
        ),
    )
    conn.commit()
    log_audit("create", "agent", agent_id, name)
    return get_agent(agent_id)


def update_agent(agent_id: str, **kwargs) -> dict | None:
    from agent.workspace import effective_scope

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
        "retrieval_mode",
    ):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    if "scope" in kwargs:
        fields.append("scope = ?")
        values.append(effective_scope(kwargs["scope"]))
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
    for key in (
        "skill_ids",
        "tool_ids",
        "sub_agent_ids",
        "constraints",
        "mcp_server_ids",
    ):
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
        **_scope_fields(row),
    }


def list_a2a_peers() -> list[dict]:
    from agent.workspace import visibility_filter_sql, visibility_params

    conn = _get_conn()
    rows = conn.execute(
        f"SELECT * FROM a2a_peers WHERE {visibility_filter_sql()} ORDER BY name",
        visibility_params(),
    ).fetchall()
    return [_row_to_a2a_peer(r) for r in rows]


def get_a2a_peer(peer_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM a2a_peers WHERE id = ?", (peer_id,)).fetchone()
    return _row_to_a2a_peer(row) if row else None


def create_a2a_peer(
    name: str,
    url: str,
    description: str = "",
    capabilities: list[str] | None = None,
    scope: str = "private",
) -> dict:
    from agent.workspace import effective_scope, get_user_id, get_workspace_id

    conn = _get_conn()
    peer_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO a2a_peers (id, name, url, description, capabilities, scope, workspace_id, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            peer_id,
            name,
            url,
            description,
            json.dumps(capabilities or []),
            effective_scope(scope),
            get_workspace_id(),
            get_user_id(),
            now,
            now,
        ),
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
    d = {
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
    keys = row.keys()
    d["managed"] = bool(int(row["managed"])) if "managed" in keys else False
    d["server_type"] = row["server_type"] if "server_type" in keys else "external"
    d["config"] = (
        json.loads(row["config"]) if "config" in keys and row["config"] else {}
    )
    d["container_id"] = row["container_id"] if "container_id" in keys else ""
    d["container_name"] = row["container_name"] if "container_name" in keys else ""
    d["container_status"] = (
        row["container_status"] if "container_status" in keys else ""
    )
    d["error_message"] = row["error_message"] if "error_message" in keys else ""
    d.update(_scope_fields(row))
    return d


def _ensure_default_mcp_servers():
    """Seed pre-configured MCP servers on first run."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()

    # ── Open Tools MCP (zero-config, no API key) ───────────────────────
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM mcp_servers WHERE id = ?", ("mcp-open-tools",)
    ).fetchone()
    if row["cnt"] == 0:
        open_tools = [
            {
                "name": "wikipedia_search",
                "description": "Search Wikipedia and get a concise summary of any topic. No API key required.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Topic to search for on Wikipedia",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_weather",
                "description": "Get current weather conditions for any city worldwide. No API key required.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name (e.g. London, New York, Tokyo)",
                        },
                    },
                    "required": ["location"],
                },
            },
            {
                "name": "dictionary_lookup",
                "description": "Look up the definition and usage of an English word. No API key required.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "word": {
                            "type": "string",
                            "description": "English word to look up",
                        },
                    },
                    "required": ["word"],
                },
            },
        ]
        conn.execute(
            "INSERT INTO mcp_servers (id, name, url, transport, description, tools, enabled, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "mcp-open-tools",
                "Open Tools (Wikipedia, Weather, Dictionary)",
                "http://open-tools-mcp:8080",
                "http",
                "Zero-config MCP server with Wikipedia search, weather, and dictionary lookup. No API key needed.",
                json.dumps(open_tools),
                1,
                "configured",
                now,
                now,
            ),
        )
        conn.commit()
        logger.info("Seeded pre-configured MCP server: Open Tools")

    # ── Brave Search MCP (requires BRAVE_API_KEY) ──────────────────────
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM mcp_servers WHERE id = ?", ("mcp-brave-search",)
    ).fetchone()
    if row["cnt"] == 0:
        brave_tools = [
            {
                "name": "brave_web_search",
                "description": "Search the web using Brave Search API. Returns relevant results with titles, URLs, and descriptions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "q": {"type": "string", "description": "Search query"},
                        "count": {
                            "type": "integer",
                            "description": "Number of results (default 5, max 20)",
                        },
                    },
                    "required": ["q"],
                },
            },
            {
                "name": "brave_local_search",
                "description": "Search for local businesses and places using Brave Search API.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "q": {
                            "type": "string",
                            "description": "Local search query (e.g. 'pizza near me')",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of results",
                        },
                    },
                    "required": ["q"],
                },
            },
        ]
        conn.execute(
            "INSERT INTO mcp_servers (id, name, url, transport, description, tools, enabled, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "mcp-brave-search",
                "Brave Search",
                "http://brave-search-mcp:8080",
                "http",
                "Web search via Brave Search API — requires BRAVE_API_KEY in .env",
                json.dumps(brave_tools),
                0,
                "configured",
                now,
                now,
            ),
        )
        conn.commit()
        logger.info(
            "Seeded pre-configured MCP server: Brave Search (disabled — needs API key)"
        )


def list_mcp_servers() -> list[dict]:
    _ensure_default_mcp_servers()
    from agent.workspace import visibility_filter_sql, visibility_params

    conn = _get_conn()
    rows = conn.execute(
        f"SELECT * FROM mcp_servers WHERE {visibility_filter_sql()} ORDER BY name",
        visibility_params(),
    ).fetchall()
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
    scope: str = "private",
) -> dict:
    from agent.workspace import effective_scope, get_user_id, get_workspace_id

    conn = _get_conn()
    server_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO mcp_servers (id, name, url, transport, description, tools, scope, workspace_id, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            server_id,
            name,
            url,
            transport,
            description,
            json.dumps(tools or []),
            effective_scope(scope),
            get_workspace_id(),
            get_user_id(),
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
    for key in (
        "name",
        "url",
        "transport",
        "description",
        "status",
        "last_seen",
        "server_type",
        "container_id",
        "container_name",
        "container_status",
        "error_message",
    ):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    for key in ("enabled", "managed"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(int(kwargs[key]))
    for key in ("tools", "config"):
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
    d = {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "content": row["content"],
        "description": row["description"],
        "tags": json.loads(row["tags"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    # validation fields (may be absent on old DBs before migration runs)
    try:
        score_raw = row["validation_score"]
        d["validation_score"] = (
            int(score_raw) if score_raw not in (None, "", "NULL") else None
        )
    except (IndexError, KeyError):
        d["validation_score"] = None
    try:
        details_raw = row["validation_details"]
        d["validation_details"] = (
            json.loads(details_raw) if details_raw and details_raw != "{}" else {}
        )
    except (IndexError, KeyError, json.JSONDecodeError):
        d["validation_details"] = {}
    try:
        d["validated_at"] = row["validated_at"] or None
    except (IndexError, KeyError):
        d["validated_at"] = None
    d.update(_scope_fields(row))
    return d


def list_prompts() -> list[dict]:
    from agent.workspace import visibility_filter_sql, visibility_params

    conn = _get_conn()
    rows = conn.execute(
        f"SELECT * FROM prompts WHERE {visibility_filter_sql()} ORDER BY name",
        visibility_params(),
    ).fetchall()
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
    model: str = "",
    scope: str = "private",
) -> dict:
    from agent.workspace import effective_scope, get_user_id, get_workspace_id

    conn = _get_conn()
    prompt_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO prompts (id, name, category, content, description, tags, model, scope, workspace_id, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            prompt_id,
            name,
            category,
            content,
            description,
            json.dumps(tags or []),
            model,
            effective_scope(scope),
            get_workspace_id(),
            get_user_id(),
            now,
            now,
        ),
    )
    conn.commit()
    log_audit("create", "prompt", prompt_id, name)
    return get_prompt(prompt_id)


def update_prompt(prompt_id: str, **kwargs) -> dict | None:
    from agent.workspace import effective_scope

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
    for key in ("name", "category", "content", "description", "model"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    if "scope" in kwargs:
        fields.append("scope = ?")
        values.append(effective_scope(kwargs["scope"]))
    for key in ("tags",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    for key in ("validation_details",):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(json.dumps(kwargs[key]))
    for key in ("validation_score", "validated_at"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(str(kwargs[key]) if kwargs[key] is not None else None)
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
            "Detects and redacts personally identifiable information (emails, phone numbers, SSNs, credit cards, DOB, BSN, IBAN, passport numbers, IP addresses) from inputs and outputs",
            1,
            "high",
            json.dumps(
                {
                    "patterns": [
                        "email",
                        "phone",
                        "ssn",
                        "credit_card",
                        "date_of_birth",
                        "bsn",
                        "iban",
                        "passport",
                        "ip_address",
                    ],
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
            labels      TEXT DEFAULT '[]',
            enabled     INTEGER DEFAULT 1,
            scope       TEXT DEFAULT 'global',
            workspace_id TEXT DEFAULT 'default',
            created_by  TEXT DEFAULT 'system',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """)
    # Migration: add labels column if missing
    cols = {r[1] for r in conn.execute("PRAGMA table_info(custom_tools)").fetchall()}
    if "labels" not in cols:
        conn.execute("ALTER TABLE custom_tools ADD COLUMN labels TEXT DEFAULT '[]'")
    conn.commit()


def _row_to_custom_tool(row) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []
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
        "labels": json.loads(row["labels"]) if "labels" in keys else [],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        **_scope_fields(row),
    }


def list_custom_tools() -> list[dict]:
    _init_custom_tools_table()
    from agent.workspace import visibility_filter_sql, visibility_params

    conn = _get_conn()
    rows = conn.execute(
        f"SELECT * FROM custom_tools WHERE {visibility_filter_sql()} ORDER BY name",
        visibility_params(),
    ).fetchall()
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
    scope: str = "private",
    labels: list[str] | None = None,
) -> dict:
    from agent.workspace import effective_scope, get_user_id, get_workspace_id

    _init_custom_tools_table()
    conn = _get_conn()
    tool_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO custom_tools (id, name, description, category, endpoint, method, headers, body_template, parameters, labels, scope, workspace_id, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            json.dumps(labels or []),
            effective_scope(scope),
            get_workspace_id(),
            get_user_id(),
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
    for key in ("headers", "body_template", "parameters", "labels"):
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


# ── Workspace CRUD ─────────────────────────────────────────────────────────


def list_workspaces() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM workspaces ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_workspace(workspace_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
    ).fetchone()
    return dict(row) if row else None


def create_workspace(name: str, description: str = "") -> dict:
    from agent.workspace import get_user_id

    conn = _get_conn()
    workspace_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO workspaces (id, name, description, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (workspace_id, name, description, get_user_id(), now, now),
    )
    # Creator becomes admin
    conn.execute(
        "INSERT INTO workspace_members (workspace_id, user_id, role, added_at) VALUES (?, ?, ?, ?)",
        (workspace_id, get_user_id(), "admin", now),
    )
    conn.commit()
    return get_workspace(workspace_id)


def update_workspace(workspace_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = get_workspace(workspace_id)
    if not existing:
        return None
    fields = []
    values = []
    for key in ("name", "description"):
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(workspace_id)
        conn.execute(f"UPDATE workspaces SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_workspace(workspace_id)


def delete_workspace(workspace_id: str) -> bool:
    if workspace_id == "default":
        return False  # Cannot delete default workspace
    conn = _get_conn()
    conn.execute(
        "DELETE FROM workspace_members WHERE workspace_id = ?", (workspace_id,)
    )
    cursor = conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
    conn.commit()
    return cursor.rowcount > 0


def list_workspace_members(workspace_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM workspace_members WHERE workspace_id = ? ORDER BY role, user_id",
        (workspace_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def add_workspace_member(workspace_id: str, user_id: str, role: str = "member") -> dict:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO workspace_members (workspace_id, user_id, role, added_at) VALUES (?, ?, ?, ?)",
        (workspace_id, user_id, role, now),
    )
    conn.commit()
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role": role,
        "added_at": now,
    }


def remove_workspace_member(workspace_id: str, user_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
        (workspace_id, user_id),
    )
    conn.commit()
    return cursor.rowcount > 0


# ── Document Registry (PostgreSQL datastore) ──────────────────────────────


def _init_documents_table():
    conn = _get_datastore_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id            TEXT PRIMARY KEY,
                    name          TEXT NOT NULL,
                    source        TEXT NOT NULL,
                    collection    TEXT NOT NULL DEFAULT 'agentic_docs',
                    folder        TEXT DEFAULT '/',
                    agent_tags    JSONB DEFAULT '[]',
                    file_type     TEXT DEFAULT '',
                    file_size     INTEGER DEFAULT 0,
                    chunk_count   INTEGER DEFAULT 0,
                    metadata      JSONB DEFAULT '{}',
                    status        TEXT DEFAULT 'uploaded',
                    storage_path  TEXT DEFAULT '',
                    source_type   TEXT DEFAULT 'upload',
                    shortcut_ref  TEXT DEFAULT '',
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder)
            """)
        conn.commit()
    finally:
        _release_datastore_conn(conn)


def _row_to_doc(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "source": row["source"],
        "collection": row["collection"],
        "folder": row["folder"],
        "agent_tags": (
            row["agent_tags"]
            if isinstance(row["agent_tags"], list)
            else json.loads(row["agent_tags"] or "[]")
        ),
        "file_type": row["file_type"],
        "file_size": row["file_size"],
        "chunk_count": row["chunk_count"],
        "metadata": (
            row["metadata"]
            if isinstance(row["metadata"], dict)
            else json.loads(row["metadata"] or "{}")
        ),
        "status": row.get("status", "uploaded"),
        "storage_path": row.get("storage_path", ""),
        "source_type": row.get("source_type", "upload"),
        "shortcut_ref": row.get("shortcut_ref", ""),
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
    conn = _get_datastore_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM documents WHERE true"
            params: list = []
            if folder and folder != "/":
                query += " AND folder = %s"
                params.append(folder)
            if collection:
                query += " AND collection = %s"
                params.append(collection)
            if agent_id:
                query += " AND agent_tags @> %s::jsonb"
                params.append(json.dumps([agent_id]))
            if search:
                query += " AND (name ILIKE %s OR source ILIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
            query += " ORDER BY folder, name"
            cur.execute(query, params)
            rows = cur.fetchall()
        return [_row_to_doc(r) for r in rows]
    finally:
        _release_datastore_conn(conn)


def get_document_registry(doc_id: str) -> dict | None:
    _init_documents_table()
    conn = _get_datastore_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
            row = cur.fetchone()
        return _row_to_doc(row) if row else None
    finally:
        _release_datastore_conn(conn)


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
    conn = _get_datastore_conn()
    try:
        doc_id = str(uuid.uuid4())[:12]
        now = datetime.now(timezone.utc).isoformat()
        if not folder.startswith("/"):
            folder = "/" + folder
        if not folder.endswith("/"):
            folder = folder + "/"
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO documents
                   (id, name, source, collection, folder, agent_tags, file_type,
                    file_size, chunk_count, metadata, status, storage_path,
                    source_type, shortcut_ref, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
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
    finally:
        _release_datastore_conn(conn)
    return get_document_registry(doc_id)


def update_document_registry(doc_id: str, **kwargs) -> dict | None:
    _init_documents_table()
    conn = _get_datastore_conn()
    try:
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
            if k == "agent_tags":
                v = json.dumps(v) if isinstance(v, list) else v
            if k == "metadata":
                v = json.dumps(v) if isinstance(v, dict) else v
            if k == "folder":
                if not v.startswith("/"):
                    v = "/" + v
                if not v.endswith("/"):
                    v = v + "/"
            fields.append(f"{k} = %s")
            values.append(v)
        if fields:
            fields.append("updated_at = %s")
            values.append(datetime.now(timezone.utc).isoformat())
            values.append(doc_id)
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE documents SET {', '.join(fields)} WHERE id = %s", values
                )
            conn.commit()
    finally:
        _release_datastore_conn(conn)
    return get_document_registry(doc_id)


def delete_document_registry(doc_id: str) -> bool:
    _init_documents_table()
    conn = _get_datastore_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            count = cur.rowcount
        conn.commit()
        return count > 0
    finally:
        _release_datastore_conn(conn)


def delete_document_registry_by_source(
    source: str, collection: str = "agentic_docs"
) -> int:
    """Delete registry records matching a source + collection."""
    _init_documents_table()
    conn = _get_datastore_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM documents WHERE source = %s AND collection = %s",
                (source, collection),
            )
            count = cur.rowcount
        conn.commit()
        return count
    finally:
        _release_datastore_conn(conn)


def list_folders() -> list[dict]:
    """Return all unique folder paths with document counts."""
    _init_documents_table()
    conn = _get_datastore_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT folder, COUNT(*) as count FROM documents GROUP BY folder ORDER BY folder"
            )
            rows = cur.fetchall()
        return [{"path": r["folder"], "count": r["count"]} for r in rows]
    finally:
        _release_datastore_conn(conn)


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
    conn = _get_datastore_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, agent_tags FROM documents WHERE agent_tags @> %s::jsonb",
                (json.dumps([agent_id]),),
            )
            rows = cur.fetchall()
            count = 0
            now = datetime.now(timezone.utc).isoformat()
            for row in rows:
                tags = (
                    row["agent_tags"]
                    if isinstance(row["agent_tags"], list)
                    else json.loads(row["agent_tags"] or "[]")
                )
                tags = [t for t in tags if t != agent_id]
                cur.execute(
                    "UPDATE documents SET agent_tags = %s, updated_at = %s WHERE id = %s",
                    (json.dumps(tags), now, row["id"]),
                )
                count += 1
        conn.commit()
        return count
    finally:
        _release_datastore_conn(conn)


def delete_documents_by_collection(collection: str) -> int:
    """Delete all registry records for a given collection."""
    _init_documents_table()
    conn = _get_datastore_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE collection = %s", (collection,))
            count = cur.rowcount
        conn.commit()
        return count
    finally:
        _release_datastore_conn(conn)


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


# ── LLM Usage Log ──────────────────────────────────────────────────────────


def _init_llm_usage_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_usage_log (
            id              TEXT PRIMARY KEY,
            request_id      TEXT NOT NULL,
            session_id      TEXT NOT NULL,
            agent_id        TEXT DEFAULT '',
            provider        TEXT NOT NULL,
            model           TEXT NOT NULL,
            prompt_tokens   INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens    INTEGER DEFAULT 0,
            estimated_cost  REAL DEFAULT 0.0,
            latency_ms      INTEGER DEFAULT 0,
            tools_used      TEXT DEFAULT '[]',
            guardrail_status TEXT DEFAULT 'passed',
            created_at      TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_usage_time ON llm_usage_log(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_usage_session ON llm_usage_log(session_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_usage_model ON llm_usage_log(model)"
    )
    conn.commit()


# Pricing table: [input_per_1M_tokens, output_per_1M_tokens]
# Ordered longest-key-first within each prefix group to avoid substring
# collisions (e.g. "gpt-4o" must not match before "gpt-4o-mini").
_LLM_PRICING = [
    # OpenAI / Azure OpenAI
    ("gpt-4o-mini", [0.15, 0.60]),
    ("gpt-4o", [2.50, 10.00]),
    ("gpt-4.1-nano", [0.10, 0.40]),
    ("gpt-4.1-mini", [0.40, 1.60]),
    ("gpt-4.1", [2.00, 8.00]),
    ("gpt-4-turbo", [10.00, 30.00]),
    ("gpt-4", [30.00, 60.00]),
    ("gpt-5.4-mini", [0.40, 1.60]),
    ("gpt-5-nano", [0.10, 0.40]),
    ("gpt-3.5-turbo", [0.50, 1.50]),
    ("o4-mini", [1.10, 4.40]),
    ("o3-mini", [1.10, 4.40]),
    ("o3", [10.00, 40.00]),
    ("o1-mini", [3.00, 12.00]),
    ("o1", [15.00, 60.00]),
    # Azure AI Foundry / open models
    ("phi-4", [0.07, 0.14]),
    ("phi-3", [0.05, 0.10]),
    ("mistral-large", [2.00, 6.00]),
    ("mistral-small", [0.10, 0.30]),
    ("mistral-medium", [2.70, 8.10]),
    ("command-r-plus", [3.00, 15.00]),
    ("command-r", [0.50, 1.50]),
    ("jamba-1.5-large", [2.00, 8.00]),
    ("jamba-1.5-mini", [0.20, 0.40]),
    ("deepseek-r1", [0.55, 2.19]),
    ("deepseek-v3", [0.27, 1.10]),
    # Meta (via Azure Foundry or local)
    ("llama-4-maverick", [0.20, 0.60]),
    ("llama-4-scout", [0.15, 0.40]),
    ("llama-3.3", [0.0, 0.0]),
    ("llama-3.1", [0.0, 0.0]),
    ("llama3", [0.0, 0.0]),
    # Local / self-hosted (free)
    ("mistral", [0.0, 0.0]),
    ("qwen", [0.0, 0.0]),
    ("gemma", [0.0, 0.0]),
    ("codellama", [0.0, 0.0]),
]


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD for a given model and token counts."""
    m = model.lower()
    for key, rates in _LLM_PRICING:
        if key in m:
            return (prompt_tokens * rates[0] / 1e6) + (
                completion_tokens * rates[1] / 1e6
            )
    return 0.0


def log_llm_usage(
    request_id: str,
    session_id: str,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: int = 0,
    tools_used: list | None = None,
    guardrail_status: str = "passed",
    agent_id: str = "",
) -> dict:
    """Record an LLM usage entry and return it."""
    _init_llm_usage_table()
    conn = _get_conn()
    uid = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    cost = estimate_cost(model, prompt_tokens, completion_tokens)
    conn.execute(
        "INSERT INTO llm_usage_log (id, request_id, session_id, agent_id, provider, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost, latency_ms, tools_used, guardrail_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            uid,
            request_id,
            session_id,
            agent_id,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            cost,
            latency_ms,
            json.dumps(tools_used or []),
            guardrail_status,
            now,
        ),
    )
    conn.commit()
    return {
        "id": uid,
        "request_id": request_id,
        "session_id": session_id,
        "agent_id": agent_id,
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms,
        "tools_used": tools_used or [],
        "guardrail_status": guardrail_status,
        "created_at": now,
    }


def list_llm_usage(
    limit: int = 200,
    session_id: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    since: str | None = None,
) -> list[dict]:
    """Query LLM usage logs with optional filters."""
    _init_llm_usage_table()
    conn = _get_conn()
    query = "SELECT * FROM llm_usage_log WHERE 1=1"
    params: list = []
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if model:
        query += " AND model LIKE ?"
        params.append(f"%{model}%")
    if provider:
        query += " AND provider = ?"
        params.append(provider)
    if since:
        query += " AND created_at >= ?"
        params.append(since)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": r["id"],
            "request_id": r["request_id"],
            "session_id": r["session_id"],
            "agent_id": r["agent_id"],
            "provider": r["provider"],
            "model": r["model"],
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
            "total_tokens": r["total_tokens"],
            "estimated_cost": r["estimated_cost"],
            "latency_ms": r["latency_ms"],
            "tools_used": json.loads(r["tools_used"]),
            "guardrail_status": r["guardrail_status"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_llm_usage_summary() -> dict:
    """Return aggregated LLM usage statistics."""
    _init_llm_usage_table()
    conn = _get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) as total_requests,
            COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
            COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
            COALESCE(SUM(total_tokens), 0) as total_tokens,
            COALESCE(SUM(estimated_cost), 0) as total_cost,
            COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
            COALESCE(AVG(total_tokens), 0) as avg_tokens_per_request
        FROM llm_usage_log
    """).fetchone()
    # Per-model breakdown
    model_rows = conn.execute("""
        SELECT model, provider,
            COUNT(*) as requests,
            SUM(total_tokens) as tokens,
            SUM(estimated_cost) as cost,
            AVG(latency_ms) as avg_latency
        FROM llm_usage_log
        GROUP BY model, provider
        ORDER BY requests DESC
    """).fetchall()
    return {
        "total_requests": row["total_requests"],
        "total_prompt_tokens": row["total_prompt_tokens"],
        "total_completion_tokens": row["total_completion_tokens"],
        "total_tokens": row["total_tokens"],
        "total_cost": round(row["total_cost"], 6),
        "avg_latency_ms": round(row["avg_latency_ms"]),
        "avg_tokens_per_request": round(row["avg_tokens_per_request"]),
        "by_model": [
            {
                "model": r["model"],
                "provider": r["provider"],
                "requests": r["requests"],
                "tokens": r["tokens"],
                "cost": round(r["cost"], 6),
                "avg_latency": round(r["avg_latency"]),
            }
            for r in model_rows
        ],
    }


# ── Connectors CRUD (continued) ───────────────────────────────────────────


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


# ── Pipeline CRUD ──────────────────────────────────────────────────────────


def list_pipelines() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM pipelines ORDER BY updated_at DESC").fetchall()
    return [_pipeline_row(r) for r in rows]


def get_pipeline(pipeline_id: str) -> dict | None:
    conn = _get_conn()
    r = conn.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)).fetchone()
    if not r:
        return None
    return _pipeline_row(r)


def create_pipeline(
    name: str,
    description: str = "",
    strategy: str = "sequential",
    steps: list | None = None,
) -> dict:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    pid = str(uuid.uuid4())[:8]
    steps_json = json.dumps(steps or [])
    conn.execute(
        "INSERT INTO pipelines (id, name, description, strategy, steps, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'draft', ?, ?)",
        (pid, name, description, strategy, steps_json, now, now),
    )
    conn.commit()
    return get_pipeline(pid)


def update_pipeline(pipeline_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
    ).fetchone()
    if not row:
        return None
    updates = {}
    for key in ("name", "description", "strategy", "status"):
        if key in kwargs and kwargs[key] is not None:
            updates[key] = kwargs[key]
    if "steps" in kwargs and kwargs["steps"] is not None:
        updates["steps"] = json.dumps(kwargs["steps"])
    if not updates:
        return get_pipeline(pipeline_id)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE pipelines SET {set_clause} WHERE id = ?",
        (*updates.values(), pipeline_id),
    )
    conn.commit()
    return get_pipeline(pipeline_id)


def delete_pipeline(pipeline_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
    conn.execute("DELETE FROM pipeline_runs WHERE pipeline_id = ?", (pipeline_id,))
    conn.commit()
    return cur.rowcount > 0


def create_pipeline_run(pipeline_id: str, strategy: str, steps: list) -> dict:
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO pipeline_runs (id, pipeline_id, status, strategy, steps, step_results, started_at, created_at) "
        "VALUES (?, ?, 'running', ?, ?, '[]', ?, ?)",
        (run_id, pipeline_id, strategy, json.dumps(steps), now, now),
    )
    conn.commit()
    return {
        "id": run_id,
        "pipeline_id": pipeline_id,
        "status": "running",
        "strategy": strategy,
        "steps": steps,
        "step_results": [],
        "started_at": now,
        "completed_at": "",
        "created_at": now,
    }


def update_pipeline_run(run_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    updates = {}
    for key in ("status", "completed_at"):
        if key in kwargs and kwargs[key] is not None:
            updates[key] = kwargs[key]
    if "step_results" in kwargs:
        updates["step_results"] = json.dumps(kwargs["step_results"])
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE pipeline_runs SET {set_clause} WHERE id = ?",
            (*updates.values(), run_id),
        )
        conn.commit()
    return _pipeline_run_row(
        conn.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)).fetchone()
    )


def list_pipeline_runs(pipeline_id: str = "", limit: int = 50) -> list[dict]:
    conn = _get_conn()
    if pipeline_id:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs WHERE pipeline_id = ? ORDER BY created_at DESC LIMIT ?",
            (pipeline_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_pipeline_run_row(r) for r in rows]


def _pipeline_row(r) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "description": r["description"],
        "strategy": r["strategy"],
        "steps": json.loads(r["steps"]),
        "status": r["status"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def _pipeline_run_row(r) -> dict:
    return {
        "id": r["id"],
        "pipeline_id": r["pipeline_id"],
        "status": r["status"],
        "strategy": r["strategy"],
        "steps": json.loads(r["steps"]),
        "step_results": json.loads(r["step_results"]),
        "started_at": r["started_at"] or "",
        "completed_at": r["completed_at"] or "",
        "created_at": r["created_at"],
    }
