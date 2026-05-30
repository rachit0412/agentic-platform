"""
Comprehensive Edge Case & Negative Test Suite
=============================================
Covers positive AND negative scenarios across all platform features.
Designed to be run periodically to catch regressions.

Run with:  pytest tests/e2e/test_edge_cases.py -v
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Check if psycopg2 is available for document registry tests
try:
    import psycopg2  # noqa: F401

    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

needs_postgres = pytest.mark.skipif(
    not HAS_PSYCOPG2,
    reason="psycopg2 not installed — document registry needs PostgreSQL",
)

# Ensure project root is importable
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "agent")
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Each test gets a fresh SQLite database."""
    db_dir = str(tmp_path / "data")
    os.makedirs(db_dir, exist_ok=True)
    monkeypatch.setenv("MEMORY_DIR", db_dir)
    import agent.memory as mem

    mem._reset_conn()
    monkeypatch.setattr(mem, "MEMORY_DIR", db_dir)
    monkeypatch.setattr(mem, "DB_PATH", os.path.join(db_dir, "platform.db"))
    mem.init_db()
    mem.list_guardrails()  # Init guardrails table + defaults
    yield
    mem._reset_conn()


@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def filestore_dir(tmp_path, monkeypatch):
    """Fresh filestore directory."""
    fs_dir = str(tmp_path / "filestore")
    os.makedirs(fs_dir, exist_ok=True)
    import agent.filestore as fs

    monkeypatch.setattr(fs, "FILESTORE_ROOT", fs_dir)
    return fs_dir


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AUTH — Login, Register, Verify, Reset Password
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthLogin:
    """Login positive and negative scenarios."""

    def test_login_valid_credentials(self, client):
        """Seed admin user can log in."""
        r = client.post("/auth/login", json={"username": "admin", "password": "admin"})
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "admin"

    def test_login_wrong_password(self, client):
        r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401
        assert "Invalid credentials" in r.json()["error"]

    def test_login_nonexistent_user(self, client):
        r = client.post("/auth/login", json={"username": "ghost", "password": "x"})
        assert r.status_code == 401

    def test_login_empty_username(self, client):
        r = client.post("/auth/login", json={"username": "", "password": "x"})
        assert r.status_code == 422  # Pydantic validation

    def test_login_empty_password(self, client):
        r = client.post("/auth/login", json={"username": "admin", "password": ""})
        assert r.status_code == 422

    def test_login_missing_fields(self, client):
        r = client.post("/auth/login", json={})
        assert r.status_code == 422

    def test_login_sql_injection(self, client):
        r = client.post(
            "/auth/login", json={"username": "admin' OR '1'='1", "password": "x"}
        )
        assert r.status_code == 401

    def test_login_xss_in_username(self, client):
        r = client.post(
            "/auth/login",
            json={"username": "<script>alert(1)</script>", "password": "x"},
        )
        assert r.status_code == 401

    def test_login_unicode_username(self, client):
        r = client.post("/auth/login", json={"username": "用户名", "password": "x"})
        assert r.status_code == 401

    def test_login_extra_fields_ignored(self, client):
        # Clear rate limiter before this test (previous failed logins accumulate)
        import main as _main

        _main._login_attempts.clear()
        r = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin", "extra": "ignored"},
        )
        assert r.status_code == 200


class TestAuthRegister:
    """Registration positive and negative scenarios."""

    def test_register_success(self, client):
        r = client.post(
            "/auth/register",
            json={
                "username": "newuser1",
                "password": "Str0ng@Pass!",
                "email": "new@test.com",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "newuser1"
        assert "verification_code" in data

    def test_register_duplicate_username(self, client):
        r = client.post(
            "/auth/register",
            json={
                "username": "admin",
                "password": "Admin@2026!",
                "email": "x@test.com",
            },
        )
        assert r.status_code == 409

    def test_register_duplicate_email(self, client):
        client.post(
            "/auth/register",
            json={
                "username": "first",
                "password": "Str0ng@Pass!",
                "email": "dup@test.com",
            },
        )
        r = client.post(
            "/auth/register",
            json={
                "username": "second",
                "password": "Str0ng@Pass!",
                "email": "dup@test.com",
            },
        )
        assert r.status_code == 409

    def test_register_short_username(self, client):
        r = client.post(
            "/auth/register",
            json={"username": "a", "password": "Str0ng@Pass!", "email": ""},
        )
        assert r.status_code == 422

    def test_register_short_password(self, client):
        r = client.post(
            "/auth/register",
            json={"username": "shortpw", "password": "1234567", "email": ""},
        )
        assert r.status_code == 422

    def test_register_empty_email_allowed(self, client):
        """Email is optional — empty string is accepted."""
        r = client.post(
            "/auth/register",
            json={"username": "noemail", "password": "Str0ng@Pass!", "email": ""},
        )
        assert r.status_code == 200

    def test_register_missing_password(self, client):
        r = client.post("/auth/register", json={"username": "nopw"})
        assert r.status_code == 422


class TestAuthVerifyEmail:
    """Email verification flow."""

    def test_verify_valid_code(self, client):
        reg = client.post(
            "/auth/register",
            json={
                "username": "verifytest",
                "password": "Str0ng@Pass!",
                "email": "v@t.com",
            },
        ).json()
        r = client.post(
            "/auth/verify-email",
            json={"user_id": reg["id"], "code": reg["verification_code"]},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_verify_wrong_code(self, client):
        reg = client.post(
            "/auth/register",
            json={
                "username": "wrongcode",
                "password": "Str0ng@Pass!",
                "email": "w@t.com",
            },
        ).json()
        r = client.post(
            "/auth/verify-email", json={"user_id": reg["id"], "code": "000000"}
        )
        assert r.status_code == 400

    def test_verify_nonexistent_user(self, client):
        r = client.post(
            "/auth/verify-email", json={"user_id": "ghost-id", "code": "123456"}
        )
        assert r.status_code == 404

    def test_verify_short_code(self, client):
        r = client.post("/auth/verify-email", json={"user_id": "x", "code": "123"})
        assert r.status_code == 422  # code min_length=6

    def test_resend_code(self, client):
        reg = client.post(
            "/auth/register",
            json={
                "username": "resendtest",
                "password": "Str0ng@Pass!",
                "email": "r@t.com",
            },
        ).json()
        r = client.post("/auth/resend-code", json={"user_id": reg["id"]})
        assert r.status_code == 200

    def test_resend_code_nonexistent(self, client):
        r = client.post("/auth/resend-code", json={"user_id": "ghost"})
        assert r.status_code == 404


class TestAuthPasswordReset:
    """Forgot/reset password flow."""

    def test_forgot_password_by_username(self, client):
        r = client.post("/auth/forgot-password", json={"identifier": "admin"})
        assert r.status_code == 200
        assert r.json()["username"] == "admin"

    def test_forgot_password_by_email(self, client):
        r = client.post(
            "/auth/forgot-password", json={"identifier": "admin@agentic.local"}
        )
        assert r.status_code == 200

    def test_forgot_password_nonexistent(self, client):
        r = client.post("/auth/forgot-password", json={"identifier": "nobody"})
        assert r.status_code == 404

    def test_reset_password_success(self, client):
        import main as _main

        _main._login_attempts.clear()
        r = client.post(
            "/auth/reset-password",
            json={"user_id": "admin", "new_password": "NewAdmin@2026!"},
        )
        assert r.status_code == 200
        # Verify can login with new password
        login = client.post(
            "/auth/login", json={"username": "admin", "password": "NewAdmin@2026!"}
        )
        assert login.status_code == 200

    def test_reset_password_short(self, client):
        r = client.post(
            "/auth/reset-password", json={"user_id": "admin", "new_password": "short"}
        )
        assert r.status_code == 422

    def test_reset_password_nonexistent_user(self, client):
        r = client.post(
            "/auth/reset-password",
            json={"user_id": "ghost-999", "new_password": "Str0ng@Pass!"},
        )
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 2. USER MANAGEMENT — CRUD, Admin Actions
# ═══════════════════════════════════════════════════════════════════════════════


class TestUserManagement:
    """User CRUD via admin endpoints."""

    def test_list_users(self, client):
        r = client.get("/users")
        assert r.status_code == 200
        assert "users" in r.json()
        assert len(r.json()["users"]) >= 2  # admin + rachit

    def test_get_user(self, client):
        r = client.get("/users/admin")
        assert r.status_code == 200
        assert r.json()["username"] == "admin"

    def test_get_nonexistent_user(self, client):
        r = client.get("/users/nonexistent-999")
        assert r.status_code == 404

    def test_create_user(self, client):
        r = client.post(
            "/users",
            json={
                "username": "testuser",
                "password": "Test@2026!",
                "email": "test@example.com",
                "role": "member",
            },
        )
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    def test_create_duplicate_user(self, client):
        r = client.post(
            "/users",
            json={
                "username": "admin",
                "password": "Admin@2026!",
                "email": "admin2@test.com",
                "role": "member",
            },
        )
        assert r.status_code == 409

    def test_create_user_invalid_role(self, client):
        r = client.post(
            "/users",
            json={
                "username": "badrole",
                "password": "Test@2026!",
                "email": "",
                "role": "superadmin",
            },
        )
        assert r.status_code == 422

    def test_update_user(self, client):
        created = client.post(
            "/users", json={"username": "upd_user", "password": "Test@2026!"}
        ).json()
        r = client.put(f"/users/{created['id']}", json={"display_name": "Updated Name"})
        assert r.status_code == 200
        assert r.json()["display_name"] == "Updated Name"

    def test_update_nonexistent_user(self, client):
        r = client.put("/users/ghost-id", json={"display_name": "Ghost"})
        assert r.status_code == 404

    def test_delete_user(self, client):
        created = client.post(
            "/users", json={"username": "del_user", "password": "Test@2026!"}
        ).json()
        r = client.delete(f"/users/{created['id']}")
        assert r.status_code == 200
        assert r.json()["deleted"] is True

    def test_delete_admin_forbidden(self, client):
        r = client.delete("/users/admin")
        assert r.status_code == 403

    def test_admin_verify_user(self, client):
        created = client.post(
            "/users", json={"username": "verify_target", "password": "Test@2026!"}
        ).json()
        r = client.post(f"/users/{created['id']}/verify")
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_admin_verify_nonexistent(self, client):
        r = client.post("/users/ghost-id/verify")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AGENTS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentsEdgeCases:
    """Agent CRUD positive and negative scenarios."""

    def test_create_agent_minimal(self, client):
        r = client.post("/agents", json={"name": "Minimal Agent"})
        assert r.status_code == 200
        d = r.json()
        assert d["name"] == "Minimal Agent"
        assert d["provider"] == "ollama"
        assert d["temperature"] == 0.7

    def test_create_agent_full(self, client):
        r = client.post(
            "/agents",
            json={
                "name": "Full Agent",
                "description": "Complete config",
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.3,
                "top_p": 0.9,
                "system_prompt": "Be helpful.",
                "skill_ids": ["s1"],
                "tool_ids": ["web_search"],
                "max_iterations": 10,
                "memory_enabled": True,
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["temperature"] == 0.3
        assert d["top_p"] == 0.9

    def test_create_agent_empty_name(self, client):
        r = client.post("/agents", json={"name": ""})
        assert r.status_code == 422

    def test_create_agent_duplicate_name(self, client):
        """Duplicate agent name triggers UNIQUE constraint → unhandled IntegrityError."""
        r1 = client.post("/agents", json={"name": "DupAgent"})
        assert r1.status_code == 200
        import sqlite3

        with pytest.raises((sqlite3.IntegrityError, Exception)):
            client.post("/agents", json={"name": "DupAgent"})

    def test_create_agent_special_chars(self, client):
        r = client.post("/agents", json={"name": "Agent <test> & 'quotes' \"double\""})
        assert r.status_code == 200
        assert "<test>" in r.json()["name"]

    def test_create_agent_unicode(self, client):
        r = client.post(
            "/agents",
            json={"name": "代理人 エージェント", "description": "日本語テスト"},
        )
        assert r.status_code == 200
        assert "代理人" in r.json()["name"]

    def test_get_agent_not_found(self, client):
        r = client.get("/agents/nonexistent-id-999")
        assert r.status_code == 404

    def test_update_agent(self, client):
        created = client.post("/agents", json={"name": "UpdAgent"}).json()
        r = client.put(f"/agents/{created['id']}", json={"description": "updated"})
        assert r.status_code == 200
        assert r.json()["description"] == "updated"

    def test_update_nonexistent_agent(self, client):
        r = client.put("/agents/fake-id", json={"description": "x"})
        assert r.status_code == 404

    def test_delete_agent(self, client):
        created = client.post("/agents", json={"name": "DelAgent"}).json()
        r = client.delete(f"/agents/{created['id']}")
        assert r.status_code == 200
        # Verify gone
        r2 = client.get(f"/agents/{created['id']}")
        assert r2.status_code == 404

    def test_delete_default_agent_blocked(self, client):
        r = client.delete("/agents/default")
        assert r.status_code == 404  # delete_agent returns False for default

    def test_delete_nonexistent_agent(self, client):
        r = client.delete("/agents/fake-id-999")
        assert r.status_code == 404

    def test_list_agents_includes_default(self, client):
        r = client.get("/agents")
        assert r.status_code == 200
        agents = r.json()["agents"]
        names = [a["name"] for a in agents]
        assert "Assistant" in names

    def test_agent_sub_agents(self, client):
        s1 = client.post("/agents", json={"name": "Sub1"}).json()
        s2 = client.post("/agents", json={"name": "Sub2"}).json()
        orch = client.post(
            "/agents",
            json={"name": "Orchestrator", "sub_agent_ids": [s1["id"], s2["id"]]},
        ).json()
        assert len(orch["sub_agent_ids"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SKILLS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkillsEdgeCases:
    """Skill CRUD positive and negative scenarios."""

    def test_create_skill(self, client):
        r = client.post(
            "/skills",
            json={
                "name": "Research",
                "description": "Web research",
                "system_prompt": "Research thoroughly.",
                "tool_ids": ["web_search"],
            },
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Research"

    def test_create_skill_empty_name(self, client):
        r = client.post("/skills", json={"name": ""})
        assert r.status_code == 422

    def test_create_skill_duplicate_name(self, client):
        """Duplicate skill name triggers UNIQUE constraint → unhandled IntegrityError."""
        r1 = client.post("/skills", json={"name": "DupSkill"})
        assert r1.status_code == 200
        import sqlite3

        with pytest.raises((sqlite3.IntegrityError, Exception)):
            client.post("/skills", json={"name": "DupSkill"})

    def test_get_skill_not_found(self, client):
        r = client.get("/skills/nonexistent-id")
        assert r.status_code == 404

    def test_update_skill(self, client):
        created = client.post("/skills", json={"name": "UpdSkill"}).json()
        r = client.put(f"/skills/{created['id']}", json={"description": "updated"})
        assert r.status_code == 200
        assert r.json()["description"] == "updated"

    def test_update_nonexistent_skill(self, client):
        r = client.put("/skills/fake-id", json={"description": "x"})
        assert r.status_code == 404

    def test_delete_skill(self, client):
        created = client.post("/skills", json={"name": "DelSkill"}).json()
        r = client.delete(f"/skills/{created['id']}")
        assert r.status_code == 200

    def test_delete_nonexistent_skill(self, client):
        r = client.delete("/skills/fake-id")
        assert r.status_code == 404

    def test_skill_unicode(self, client):
        r = client.post(
            "/skills", json={"name": "技能テスト", "description": "Résumé 中文"}
        )
        assert r.status_code == 200
        assert "技能" in r.json()["name"]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PROMPTS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestPromptsEdgeCases:
    """Prompt CRUD positive and negative scenarios."""

    def test_create_prompt(self, client):
        r = client.post(
            "/prompts",
            json={
                "name": "Summarizer",
                "content": "Summarize: {text}",
                "category": "summarization",
                "tags": ["summary", "ai"],
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["name"] == "Summarizer"
        assert "summary" in d["tags"]

    def test_create_prompt_empty_name(self, client):
        """PromptCreate has no min_length on name — empty allowed."""
        r = client.post("/prompts", json={"name": "", "content": "x"})
        assert r.status_code == 200

    def test_create_prompt_duplicate(self, client):
        """Duplicate prompt name triggers UNIQUE constraint → unhandled IntegrityError."""
        r1 = client.post("/prompts", json={"name": "DupPrompt", "content": "x"})
        assert r1.status_code == 200
        import sqlite3

        with pytest.raises((sqlite3.IntegrityError, Exception)):
            client.post("/prompts", json={"name": "DupPrompt", "content": "y"})

    def test_update_prompt(self, client):
        created = client.post(
            "/prompts", json={"name": "UpdPrompt", "content": "v1"}
        ).json()
        r = client.put(f"/prompts/{created['id']}", json={"content": "v2"})
        assert r.status_code == 200
        assert r.json()["content"] == "v2"

    def test_update_nonexistent_prompt(self, client):
        r = client.put("/prompts/fake-id", json={"content": "x"})
        assert r.status_code == 404

    def test_delete_prompt(self, client):
        created = client.post(
            "/prompts", json={"name": "DelPrompt", "content": "x"}
        ).json()
        r = client.delete(f"/prompts/{created['id']}")
        assert r.status_code == 200

    def test_get_prompt_not_found(self, client):
        r = client.get("/prompts/fake-id")
        assert r.status_code == 404

    def test_prompt_unicode_content(self, client):
        r = client.post(
            "/prompts",
            json={
                "name": "I18n Prompt",
                "content": "Résumé: Ñoño 中文 日本語 한국어 العربية",
                "category": "i18n",
            },
        )
        assert r.status_code == 200
        loaded = client.get(f"/prompts/{r.json()['id']}").json()
        assert "中文" in loaded["content"]
        assert "العربية" in loaded["content"]


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CUSTOM TOOLS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestCustomToolsEdgeCases:
    """Custom tool CRUD positive and negative scenarios."""

    def test_create_tool(self, client):
        r = client.post(
            "/custom-tools",
            json={
                "name": "Weather API",
                "description": "Get weather",
                "category": "api",
                "endpoint": "https://api.weather.com",
                "method": "GET",
                "headers": {"X-Key": "secret"},
                "parameters": [{"name": "city", "type": "string", "required": True}],
            },
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Weather API"

    def test_create_tool_minimal(self, client):
        r = client.post("/custom-tools", json={"name": "MinTool"})
        assert r.status_code == 200

    def test_create_tool_duplicate(self, client):
        """Duplicate custom tool name triggers UNIQUE constraint → unhandled IntegrityError."""
        r1 = client.post("/custom-tools", json={"name": "DupTool"})
        assert r1.status_code == 200
        import sqlite3

        with pytest.raises((sqlite3.IntegrityError, Exception)):
            client.post("/custom-tools", json={"name": "DupTool"})

    def test_update_tool(self, client):
        created = client.post("/custom-tools", json={"name": "UpdTool"}).json()
        r = client.put(
            f"/custom-tools/{created['id']}", json={"description": "updated"}
        )
        assert r.status_code == 200

    def test_delete_tool(self, client):
        created = client.post("/custom-tools", json={"name": "DelTool"}).json()
        r = client.delete(f"/custom-tools/{created['id']}")
        assert r.status_code == 200

    def test_list_tools(self, client):
        r = client.get("/custom-tools")
        assert r.status_code == 200
        assert "tools" in r.json()


# ═══════════════════════════════════════════════════════════════════════════════
# 7. MCP SERVERS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPServersEdgeCases:
    """MCP server CRUD positive and negative scenarios."""

    def test_create_mcp_server(self, client):
        r = client.post(
            "/mcp/servers",
            json={
                "name": "TestMCP",
                "url": "http://localhost:9000",
                "transport": "sse",
                "description": "Test server",
            },
        )
        assert r.status_code == 200
        assert r.json()["name"] == "TestMCP"

    def test_create_mcp_empty_name(self, client):
        r = client.post("/mcp/servers", json={"name": "", "url": "http://x"})
        assert r.status_code == 422

    def test_update_mcp_server(self, client):
        created = client.post(
            "/mcp/servers", json={"name": "UpdMCP", "url": "http://x"}
        ).json()
        r = client.put(f"/mcp/servers/{created['id']}", json={"description": "updated"})
        assert r.status_code == 200

    def test_delete_mcp_server(self, client):
        created = client.post(
            "/mcp/servers", json={"name": "DelMCP", "url": "http://x"}
        ).json()
        r = client.delete(f"/mcp/servers/{created['id']}")
        assert r.status_code == 200

    def test_get_mcp_not_found(self, client):
        r = client.get("/mcp/servers/fake-id")
        assert r.status_code == 404

    def test_list_mcp_has_defaults(self, client):
        r = client.get("/mcp/servers")
        assert r.status_code == 200
        servers = r.json()
        assert len(servers) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 8. A2A PEERS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestA2APeersEdgeCases:
    """A2A peer CRUD positive and negative scenarios."""

    def test_create_a2a_peer(self, client):
        r = client.post(
            "/a2a/peers",
            json={
                "name": "External Agent",
                "url": "http://remote:8000",
                "description": "Remote agent",
                "capabilities": ["research"],
            },
        )
        assert r.status_code == 200
        assert r.json()["name"] == "External Agent"

    def test_create_a2a_missing_url(self, client):
        r = client.post("/a2a/peers", json={"name": "NoURL"})
        assert r.status_code == 422

    def test_update_a2a_peer(self, client):
        created = client.post(
            "/a2a/peers", json={"name": "UpdPeer", "url": "http://x"}
        ).json()
        r = client.put(f"/a2a/peers/{created['id']}", json={"description": "updated"})
        assert r.status_code == 200

    def test_delete_a2a_peer(self, client):
        created = client.post(
            "/a2a/peers", json={"name": "DelPeer", "url": "http://x"}
        ).json()
        r = client.delete(f"/a2a/peers/{created['id']}")
        assert r.status_code == 200

    def test_a2a_card(self, client):
        r = client.get("/a2a/card")
        assert r.status_code == 200

    def test_a2a_send_invalid(self, client):
        """Sending to nonexistent peer should fail gracefully."""
        r = client.post("/a2a/send", json={"peer_id": "fake-peer", "task": "hello"})
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 9. GUARDRAILS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardrailsEdgeCases:
    """Guardrail management positive and negative scenarios."""

    def test_list_guardrails_has_defaults(self, client):
        r = client.get("/guardrails")
        assert r.status_code == 200
        data = r.json()
        guardrails = data if isinstance(data, list) else data.get("guardrails", data)
        assert len(guardrails) >= 3  # PII, toxicity, prompt injection

    def test_get_guardrail(self, client):
        r = client.get("/guardrails/gr-pii")
        assert r.status_code == 200
        assert r.json()["name"] == "PII Detection"

    def test_get_guardrail_not_found(self, client):
        r = client.get("/guardrails/nonexistent")
        assert r.status_code == 404

    def test_update_guardrail_enable(self, client):
        r = client.put("/guardrails/gr-pii", json={"enabled": False})
        assert r.status_code == 200
        assert r.json()["enabled"] is False

    def test_update_guardrail_severity(self, client):
        r = client.put("/guardrails/gr-pii", json={"severity": "critical"})
        assert r.status_code == 200
        assert r.json()["severity"] == "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. CONNECTORS — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestConnectorsEdgeCases:
    """Data connector CRUD positive and negative scenarios."""

    def test_connector_catalog(self, client):
        r = client.get("/connectors/catalog")
        assert r.status_code == 200
        data = r.json()
        catalog = data.get("connectors", data)
        assert "database" in catalog
        assert "api" in catalog
        assert "cloud_storage" in catalog

    def test_create_connector(self, client):
        r = client.post(
            "/connectors",
            json={
                "name": "Test DB",
                "connector_type": "database",
                "config": {
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "test",
                    "username": "user",
                    "password": "pass",
                    "query": "SELECT * FROM t",
                    "text_columns": "content",
                },
            },
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Test DB"

    def test_update_connector(self, client):
        created = client.post(
            "/connectors",
            json={
                "name": "UpdConn",
                "connector_type": "api",
                "config": {"url": "http://api.example.com"},
            },
        ).json()
        r = client.put(f"/connectors/{created['id']}", json={"name": "Updated Conn"})
        assert r.status_code == 200

    def test_delete_connector(self, client):
        created = client.post(
            "/connectors",
            json={
                "name": "DelConn",
                "connector_type": "api",
                "config": {"url": "http://x"},
            },
        ).json()
        r = client.delete(f"/connectors/{created['id']}")
        assert r.status_code == 200

    def test_get_nonexistent_connector(self, client):
        r = client.get("/connectors/fake-id")
        # FastAPI tuple return serializes as JSON list [{error}, 404]
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, list):
            assert data[0].get("error") == "Connector not found"
        else:
            assert data.get("error") == "Connector not found"

    def test_connector_test_unknown_type(self, client):
        r = client.post(
            "/connectors/test", json={"connector_type": "nonexistent", "config": {}}
        )
        assert r.status_code == 200  # returns {ok: false}
        assert r.json()["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# 11. WORKSPACES — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkspacesEdgeCases:
    """Workspace CRUD positive and negative scenarios."""

    def test_list_workspaces(self, client):
        r = client.get("/workspaces")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert any(w["id"] == "default" for w in r.json())

    def test_create_workspace(self, client):
        r = client.post(
            "/workspaces", json={"name": "Test WS", "description": "For testing"}
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Test WS"

    def test_create_workspace_empty_name(self, client):
        r = client.post("/workspaces", json={"name": ""})
        assert r.status_code == 200
        assert "error" in r.json()

    def test_delete_default_workspace_blocked(self, client):
        r = client.delete("/workspaces/default")
        assert r.status_code in (200, 403)
        # Should not be deletable
        verify = client.get("/workspaces/default")
        assert verify.status_code == 200

    def test_workspace_members(self, client):
        ws = client.post("/workspaces", json={"name": "MemberWS"}).json()
        # Add member
        r = client.post(
            f"/workspaces/{ws['id']}/members",
            json={"user_id": "admin", "role": "admin"},
        )
        assert r.status_code == 200
        # List members
        r = client.get(f"/workspaces/{ws['id']}/members")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 12. SESSIONS & MEMORY — CRUD & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionsEdgeCases:
    """Session and memory positive and negative scenarios."""

    def test_list_sessions(self, client):
        r = client.get("/sessions")
        assert r.status_code == 200
        assert "sessions" in r.json()

    def test_session_history_empty(self, client):
        r = client.get("/sessions/nonexistent/history")
        assert r.status_code == 200
        assert r.json()["messages"] == []

    def test_session_summary_empty(self, client):
        r = client.get("/sessions/nonexistent/summary")
        assert r.status_code == 200

    def test_delete_session(self, client):
        r = client.delete("/sessions/nonexistent")
        assert r.status_code == 200

    def test_memory_stats(self, client):
        r = client.get("/memory/stats")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 13. VERSIONS & AUDIT — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestVersionsAuditEdgeCases:
    """Versioning and audit log positive and negative scenarios."""

    def test_versions_empty(self, client):
        r = client.get("/versions/agent/nonexistent")
        assert r.status_code == 200
        assert r.json()["versions"] == []

    def test_audit_log(self, client):
        r = client.get("/audit-log")
        assert r.status_code == 200
        assert "entries" in r.json()

    def test_version_detail_not_found(self, client):
        r = client.get("/versions/detail/fake-version-id")
        assert r.status_code in (400, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. EXPORT / IMPORT — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportImportEdgeCases:
    """Export and import positive and negative scenarios."""

    def test_export(self, client):
        r = client.get("/export")
        assert r.status_code == 200
        data = r.json()
        export = data["export"]
        assert "agents" in export
        assert "skills" in export
        assert "prompts" in export

    def test_import_empty(self, client):
        r = client.post("/import", json={})
        assert r.status_code == 200

    def test_import_merge(self, client):
        data = client.get("/export").json()
        r = client.post("/import", json={"export": data["export"]})
        assert r.status_code == 200

    def test_export_reimport_idempotent(self, client):
        """Export → Import → Export should yield same structure."""
        data1 = client.get("/export").json()
        client.post("/import", json={"export": data1["export"]})
        data2 = client.get("/export").json()
        assert set(data1["export"].keys()) == set(data2["export"].keys())


# ═══════════════════════════════════════════════════════════════════════════════
# 15. MODELS & LLM ACTIVITY — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestModelsEdgeCases:
    """Model switching and LLM activity."""

    def test_list_models(self, client):
        r = client.get("/models")
        assert r.status_code == 200

    def test_switch_model(self, client):
        r = client.post(
            "/models/switch", json={"provider": "ollama", "model": "llama3"}
        )
        assert r.status_code == 200

    def test_llm_activity(self, client):
        r = client.get("/llm-activity")
        assert r.status_code == 200

    def test_llm_activity_summary(self, client):
        r = client.get("/llm-activity/summary")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 16. PLATFORM SETTINGS — Global Constraints, Best Practices, Security
# ═══════════════════════════════════════════════════════════════════════════════


class TestPlatformSettings:
    """Global constraints, best practices, security considerations."""

    def test_get_global_constraints(self, client):
        r = client.get("/global-constraints")
        assert r.status_code == 200

    def test_set_global_constraints(self, client):
        r = client.put(
            "/global-constraints",
            json={"constraints": ["No PII", "Keep responses concise"]},
        )
        assert r.status_code == 200

    def test_get_best_practices(self, client):
        r = client.get("/best-practices")
        assert r.status_code == 200

    def test_set_best_practices(self, client):
        r = client.put(
            "/best-practices", json={"practices": ["Use RAG for factual answers"]}
        )
        assert r.status_code == 200

    def test_get_security_considerations(self, client):
        r = client.get("/security-considerations")
        assert r.status_code == 200

    def test_set_security_considerations(self, client):
        r = client.put(
            "/security-considerations",
            json={"items": ["Validate all inputs", "Rate limit API calls"]},
        )
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 17. HEALTH & INFRASTRUCTURE — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealthInfra:
    """Health checks and infrastructure endpoints."""

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_db_stats(self, client):
        r = client.get("/db-stats")
        assert r.status_code == 200

    def test_tools_list(self, client):
        r = client.get("/tools")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 18. DATA INTEGRITY & SECURITY — Cross-Cutting Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataIntegritySecurity:
    """Cross-cutting data integrity and security edge cases."""

    def test_sql_injection_in_agent_name(self, client):
        """SQL injection attempt in agent name should be stored safely."""
        r = client.post("/agents", json={"name": "'; DROP TABLE agents; --"})
        assert r.status_code == 200
        # Table should still work
        r2 = client.get("/agents")
        assert r2.status_code == 200

    def test_xss_in_skill_description(self, client):
        """XSS payload stored as-is (escaping is UI responsibility)."""
        r = client.post(
            "/skills",
            json={"name": "XSS Skill", "description": "<img src=x onerror=alert(1)>"},
        )
        assert r.status_code == 200
        assert "<img" in r.json()["description"]

    def test_large_payload(self, client):
        """Description max_length=1000 enforced by Pydantic."""
        large_desc = "A" * 1001
        r = client.post(
            "/agents", json={"name": "LargeAgent", "description": large_desc}
        )
        assert r.status_code == 422  # exceeds max_length=1000

    def test_max_description_accepted(self, client):
        """Description at max_length=1000 is accepted."""
        desc = "A" * 1000
        r = client.post("/agents", json={"name": "MaxDescAgent", "description": desc})
        assert r.status_code == 200
        assert len(r.json()["description"]) == 1000

    def test_json_in_string_fields(self, client):
        """JSON strings in text fields should be stored safely."""
        r = client.post(
            "/agents",
            json={
                "name": "JSONAgent",
                "description": '{"nested": true, "array": [1,2,3]}',
            },
        )
        assert r.status_code == 200

    def test_null_bytes_handled(self, client):
        """Null bytes in input shouldn't crash."""
        r = client.post(
            "/agents", json={"name": "NullAgent", "description": "test\x00null"}
        )
        # Should either accept or reject gracefully
        assert r.status_code in (200, 400, 422)

    def test_concurrent_creates(self, client):
        """Rapid sequential creates don't corrupt data."""
        ids = []
        for i in range(20):
            r = client.post("/agents", json={"name": f"Concurrent_{i}"})
            assert r.status_code == 200
            ids.append(r.json()["id"])
        # All should exist
        agents = client.get("/agents").json()["agents"]
        names = [a["name"] for a in agents]
        for i in range(20):
            assert f"Concurrent_{i}" in names

    def test_empty_json_body(self, client):
        """Empty JSON body where fields are required."""
        r = client.post("/agents", json={})
        assert r.status_code == 422

    def test_invalid_json(self, client):
        """Malformed JSON should return 422."""
        r = client.post(
            "/agents", content=b"not json", headers={"content-type": "application/json"}
        )
        assert r.status_code == 422

    def test_wrong_content_type(self, client):
        """Non-JSON content type."""
        r = client.post(
            "/agents",
            content=b"name=test",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 422

    def test_path_traversal_in_ids(self, client):
        """Path traversal attempts in IDs should not cause issues."""
        r = client.get("/agents/../../etc/passwd")
        assert r.status_code in (404, 422)

    def test_very_long_id(self, client):
        """Very long ID should return 404, not crash."""
        long_id = "x" * 1000
        r = client.get(f"/agents/{long_id}")
        assert r.status_code in (404, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. FILESTORE — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestFileStoreEdgeCases:
    """Filestore positive and negative scenarios."""

    def test_save_and_read(self, filestore_dir):
        from agent.filestore import file_exists, read_file, save_file

        save_file("doc1", "test.txt", "Hello World")
        assert file_exists("doc1", "test.txt")
        assert read_file("doc1", "test.txt") == "Hello World"

    def test_save_overwrite(self, filestore_dir):
        from agent.filestore import read_file, save_file

        save_file("doc2", "test.txt", "v1")
        save_file("doc2", "test.txt", "v2")
        assert read_file("doc2", "test.txt") == "v2"

    def test_read_nonexistent(self, filestore_dir):
        from agent.filestore import read_file

        assert read_file("ghost", "ghost.txt") is None

    def test_delete_file(self, filestore_dir):
        from agent.filestore import delete_file, file_exists, save_file

        save_file("doc3", "del.txt", "delete me")
        assert delete_file("doc3") is True
        assert file_exists("doc3", "del.txt") is False

    def test_delete_nonexistent(self, filestore_dir):
        from agent.filestore import delete_file

        assert delete_file("ghost") is False

    def test_storage_stats(self, filestore_dir):
        from agent.filestore import get_storage_stats, save_file

        save_file("stats1", "a.txt", "content")
        stats = get_storage_stats()
        assert stats["total_files"] >= 1

    def test_binary_file(self, filestore_dir):
        from agent.filestore import read_file_bytes, save_file

        binary = bytes(range(256))
        save_file("bin1", "data.bin", binary)
        result = read_file_bytes("bin1", "data.bin")
        assert result == binary

    def test_special_chars_filename(self, filestore_dir):
        from agent.filestore import read_file, save_file

        save_file("doc4", "test file (1).txt", "special")
        assert read_file("doc4", "test file (1).txt") == "special"


# ═══════════════════════════════════════════════════════════════════════════════
# 20. MEMORY LAYER (Direct DB) — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryLayerEdgeCases:
    """Direct memory.py function edge cases."""

    def test_authenticate_user_valid(self):
        from agent.memory import authenticate_user

        result = authenticate_user("admin", "admin")
        assert result is not None
        assert result["username"] == "admin"

    def test_authenticate_user_wrong_pw(self):
        from agent.memory import authenticate_user

        result = authenticate_user("admin", "wrong")
        assert result is None

    def test_authenticate_nonexistent(self):
        from agent.memory import authenticate_user

        result = authenticate_user("ghost", "x")
        assert result is None

    def test_create_user_duplicate_email(self):
        from agent.memory import create_user

        create_user(username="u1", password="pass1234", email="dup@test.com")
        result = create_user(username="u2", password="pass1234", email="dup@test.com")
        assert isinstance(result, dict) and result.get("error") == "email_already_used"

    def test_get_user_by_email(self):
        from agent.memory import create_user, get_user_by_email

        create_user(username="emailtest", password="pass1234", email="find@me.com")
        user = get_user_by_email("find@me.com")
        assert user is not None
        assert user["username"] == "emailtest"

    def test_get_user_by_email_nonexistent(self):
        from agent.memory import get_user_by_email

        assert get_user_by_email("nobody@nowhere.com") is None

    def test_verify_email_wrong_code(self):
        from agent.memory import create_user, verify_user_email

        user = create_user(username="veruser", password="pass1234", email="v@t.com")
        result = verify_user_email(user["id"], "000000")
        assert isinstance(result, dict) and result.get("error") == "invalid_code"

    def test_save_and_get_history(self):
        from agent.memory import get_history, save_message

        sid = "test-session-1"
        save_message(sid, "user", "Hello")
        save_message(sid, "assistant", "Hi there!")
        history = get_history(sid)
        assert len(history) == 2
        assert history[0]["role"] == "user"

    def test_session_summary(self):
        from agent.memory import (
            get_session_summary,
            save_message,
            update_session_summary,
        )

        sid = "summary-test"
        save_message(sid, "user", "What is AI?")
        save_message(sid, "assistant", "AI is artificial intelligence.")
        update_session_summary(sid, "What is AI?", "AI is artificial intelligence.")
        summary = get_session_summary(sid)
        assert summary is not None

    def test_version_save_and_list(self):
        from agent.memory import get_version, list_versions, save_version

        v = save_version("agent", "agent-1", {"name": "v1"}, "test")
        versions = list_versions("agent", "agent-1")
        assert len(versions) >= 1
        detail = get_version(v["id"])
        assert detail is not None

    def test_audit_log(self):
        from agent.memory import list_audit_log, log_audit

        log_audit("create", "agent", "test-1", "TestAgent", {"key": "value"})
        entries = list_audit_log()
        assert len(entries) >= 1
        assert entries[0]["action"] == "create"

    def test_audit_log_filter(self):
        from agent.memory import list_audit_log, log_audit

        log_audit("create", "agent", "a1", "Agent1", {})
        log_audit("update", "skill", "s1", "Skill1", {})
        creates = list_audit_log(action="create")
        assert all(e["action"] == "create" for e in creates)

    def test_db_stats(self):
        from agent.memory import get_db_stats

        stats = get_db_stats()
        assert "agents" in stats
        assert stats["agents"] >= 1  # default agent

    def test_memory_stats(self):
        from agent.memory import get_memory_stats

        stats = get_memory_stats()
        assert "total_sessions" in stats

    def test_global_constraints_roundtrip(self):
        from agent.memory import get_global_constraints, set_global_constraints

        set_global_constraints(["No PII", "Be concise"])
        result = get_global_constraints()
        assert "No PII" in result
        assert "Be concise" in result

    def test_best_practices_roundtrip(self):
        from agent.memory import get_best_practices, set_best_practices

        set_best_practices(["Use RAG"])
        result = get_best_practices()
        assert "Use RAG" in result

    def test_security_considerations_roundtrip(self):
        from agent.memory import (
            get_security_considerations,
            set_security_considerations,
        )

        set_security_considerations(["Validate inputs"])
        result = get_security_considerations()
        assert "Validate inputs" in result

    def test_estimate_cost(self):
        from agent.memory import estimate_cost

        cost = estimate_cost("gpt-4", 1000, 500)
        assert cost >= 0

    def test_llm_usage_logging(self):
        from agent.memory import get_llm_usage_summary, list_llm_usage, log_llm_usage

        log_llm_usage(
            request_id="req-1",
            session_id="s1",
            model="llama3",
            provider="ollama",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=200,
        )
        usage = list_llm_usage()
        assert len(usage) >= 1
        summary = get_llm_usage_summary()
        assert summary["total_requests"] >= 1
