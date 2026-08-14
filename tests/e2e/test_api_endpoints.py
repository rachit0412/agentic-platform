"""
HTTP API Test Suite — FastAPI Endpoint Tests.
Tests the full REST API surface via TestClient (no network required).

Run with: pytest tests/e2e/test_api_endpoints.py -v
"""

import json
import os
import sys

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


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    """Set up a fresh database for each test."""
    db_dir = str(tmp_path / "data")
    fs_dir = str(tmp_path / "filestore")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(fs_dir, exist_ok=True)
    monkeypatch.setenv("MEMORY_DIR", db_dir)
    monkeypatch.setenv("FILESTORE_ROOT", fs_dir)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("CHROMADB_HOST", "localhost")
    monkeypatch.setenv("CHROMADB_PORT", "8100")

    import agent.filestore as fs
    import agent.memory as mem

    mem._reset_conn()
    monkeypatch.setattr(mem, "MEMORY_DIR", db_dir)
    monkeypatch.setattr(mem, "DB_PATH", os.path.join(db_dir, "platform.db"))
    monkeypatch.setattr(fs, "FILESTORE_ROOT", fs_dir)
    mem.init_db()
    mem.list_guardrails()  # Init guardrails table
    yield
    mem._reset_conn()


@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH & BASIC
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"

    def test_db_stats(self, client):
        r = client.get("/db-stats")
        assert r.status_code == 200
        data = r.json()
        assert "agents" in data
        assert "skills" in data
        assert "db_size_bytes" in data


# ═══════════════════════════════════════════════════════════════════════════════
# SKILLS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkillsAPI:
    def test_list_skills(self, client):
        r = client.get("/skills")
        assert r.status_code == 200
        data = r.json()
        assert "skills" in data
        assert isinstance(data["skills"], list)

    def test_create_skill(self, client):
        r = client.post(
            "/skills",
            json={
                "name": "Test Skill",
                "description": "A test skill",
                "system_prompt": "Be helpful.",
                "tool_ids": ["math"],
                "constraints": ["Be concise"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Test Skill"
        assert "id" in data

    def test_get_skill(self, client):
        created = client.post(
            "/skills", json={"name": "GetMe", "description": "", "system_prompt": ""}
        ).json()
        r = client.get(f"/skills/{created['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "GetMe"

    def test_update_skill(self, client):
        created = client.post(
            "/skills", json={"name": "UpdSkill", "description": "", "system_prompt": ""}
        ).json()
        r = client.put(f"/skills/{created['id']}", json={"description": "Updated"})
        assert r.status_code == 200
        assert r.json()["description"] == "Updated"

    def test_delete_skill(self, client):
        created = client.post(
            "/skills", json={"name": "DelSkill", "description": "", "system_prompt": ""}
        ).json()
        r = client.delete(f"/skills/{created['id']}")
        assert r.status_code == 200
        # Verify gone
        r2 = client.get(f"/skills/{created['id']}")
        assert r2.status_code == 404

    def test_skill_not_found(self, client):
        r = client.get("/skills/nonexistent")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# AGENTS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentsAPI:
    def test_list_agents(self, client):
        r = client.get("/agents")
        assert r.status_code == 200
        agents = r.json()
        assert len(agents) >= 1  # Default agent

    def test_create_agent(self, client):
        r = client.post(
            "/agents",
            json={
                "name": "API Agent",
                "description": "Created via API",
                "provider": "ollama",
                "model": "llama3",
                "temperature": 0.5,
                "tool_ids": ["math", "web_search"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "API Agent"
        assert data["temperature"] == 0.5

    def test_get_agent(self, client):
        created = client.post(
            "/agents", json={"name": "GetAgent", "description": "test"}
        ).json()
        r = client.get(f"/agents/{created['id']}")
        assert r.status_code == 200

    def test_update_agent(self, client):
        created = client.post(
            "/agents", json={"name": "UpdAgent", "description": "v1"}
        ).json()
        r = client.put(f"/agents/{created['id']}", json={"description": "v2"})
        assert r.status_code == 200
        assert r.json()["description"] == "v2"

    def test_delete_agent(self, client):
        created = client.post(
            "/agents", json={"name": "DelAgent", "description": "temp"}
        ).json()
        r = client.delete(f"/agents/{created['id']}")
        assert r.status_code == 200

    def test_agent_not_found(self, client):
        r = client.get("/agents/nonexistent")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# A2A PEERS API  (route: /a2a/peers)
# ═══════════════════════════════════════════════════════════════════════════════


class TestA2AAPI:
    def test_list_a2a_peers(self, client):
        r = client.get("/a2a/peers")
        assert r.status_code == 200
        data = r.json()
        assert "peers" in data
        assert isinstance(data["peers"], list)

    def test_create_a2a_peer(self, client):
        r = client.post(
            "/a2a/peers",
            json={
                "name": "Remote Agent",
                "url": "http://remote:8000",
                "description": "Remote research agent",
                "capabilities": ["search", "summarize"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Remote Agent"
        assert "search" in data["capabilities"]

    def test_update_a2a_peer(self, client):
        created = client.post(
            "/a2a/peers",
            json={"name": "UpdPeer", "url": "http://x:8000", "description": ""},
        ).json()
        r = client.put(f"/a2a/peers/{created['id']}", json={"status": "healthy"})
        assert r.status_code == 200

    def test_delete_a2a_peer(self, client):
        created = client.post(
            "/a2a/peers",
            json={"name": "DelPeer", "url": "http://d:8000", "description": ""},
        ).json()
        r = client.delete(f"/a2a/peers/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# MCP SERVERS API  (route: /mcp/servers)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPAPI:
    def test_list_mcp_servers(self, client):
        r = client.get("/mcp/servers")
        assert r.status_code == 200
        data = r.json()
        assert "servers" in data
        assert isinstance(data["servers"], list)

    def test_create_mcp_server(self, client):
        r = client.post(
            "/mcp/servers",
            json={
                "name": "FS Server",
                "url": "npx @mcp/fs /data",
                "transport": "stdio",
                "description": "File access",
                "tools": ["read", "write"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "FS Server"
        assert data["transport"] == "stdio"

    def test_update_mcp_server(self, client):
        created = client.post(
            "/mcp/servers",
            json={
                "name": "UpdMCP",
                "url": "x",
                "transport": "stdio",
                "description": "",
            },
        ).json()
        r = client.put(f"/mcp/servers/{created['id']}", json={"status": "connected"})
        assert r.status_code == 200

    def test_delete_mcp_server(self, client):
        created = client.post(
            "/mcp/servers",
            json={
                "name": "DelMCP",
                "url": "x",
                "transport": "stdio",
                "description": "",
            },
        ).json()
        r = client.delete(f"/mcp/servers/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestPromptsAPI:
    def test_list_prompts(self, client):
        r = client.get("/prompts")
        assert r.status_code == 200
        data = r.json()
        assert "prompts" in data
        assert isinstance(data["prompts"], list)

    def test_create_prompt(self, client):
        r = client.post(
            "/prompts",
            json={
                "name": "Summary Prompt",
                "content": "Summarize: {text}",
                "category": "summarization",
                "description": "Standard summary",
                "tags": ["summary"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Summary Prompt"

    def test_update_prompt(self, client):
        created = client.post(
            "/prompts",
            json={
                "name": "UpdPrompt",
                "content": "v1",
                "category": "g",
                "description": "",
            },
        ).json()
        r = client.put(f"/prompts/{created['id']}", json={"content": "v2"})
        assert r.status_code == 200
        assert r.json()["content"] == "v2"

    def test_delete_prompt(self, client):
        created = client.post(
            "/prompts",
            json={
                "name": "DelPrompt",
                "content": "x",
                "category": "g",
                "description": "",
            },
        ).json()
        r = client.delete(f"/prompts/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAILS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardrailsAPI:
    def test_list_guardrails(self, client):
        r = client.get("/guardrails")
        assert r.status_code == 200
        data = r.json()
        assert "guardrails" in data
        guardrails = data["guardrails"]
        assert len(guardrails) >= 6
        assert any(g["id"] == "gr-pii" for g in guardrails)

    def test_get_guardrail(self, client):
        r = client.get("/guardrails/gr-prompt-injection")
        assert r.status_code == 200
        assert r.json()["name"] == "Prompt Injection Guard"

    def test_update_guardrail(self, client):
        r = client.put("/guardrails/gr-pii", json={"enabled": False, "severity": "low"})
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is False
        assert data["severity"] == "low"


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM TOOLS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestCustomToolsAPI:
    def test_list_custom_tools(self, client):
        r = client.get("/custom-tools")
        assert r.status_code == 200
        data = r.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)

    def test_create_custom_tool(self, client):
        r = client.post(
            "/custom-tools",
            json={
                "name": "API Tool",
                "description": "Calls external API",
                "category": "api",
                "endpoint": "https://api.example.com/data",
                "method": "GET",
                "headers": {},
                "body_template": {},
                "parameters": [
                    {
                        "name": "q",
                        "type": "string",
                        "required": True,
                        "description": "Query",
                    }
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "API Tool"

    def test_delete_custom_tool(self, client):
        created = client.post(
            "/custom-tools",
            json={
                "name": "Temp Tool",
                "description": "",
                "category": "api",
                "endpoint": "http://x",
                "method": "GET",
                "headers": {},
                "body_template": {},
                "parameters": [],
            },
        ).json()
        r = client.delete(f"/custom-tools/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTORS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestConnectorsAPI:
    def test_connector_catalog(self, client):
        r = client.get("/connectors/catalog")
        assert r.status_code == 200
        data = r.json()
        # Catalog is wrapped: {"connectors": {"database": ..., "api": ...}}
        assert "connectors" in data
        catalog = data["connectors"]
        assert "database" in catalog
        assert "api" in catalog

    def test_list_connectors(self, client):
        r = client.get("/connectors")
        assert r.status_code == 200
        data = r.json()
        assert "connectors" in data
        assert isinstance(data["connectors"], list)

    def test_create_connector(self, client):
        r = client.post(
            "/connectors",
            json={
                "name": "Test DB Connector",
                "connector_type": "database",
                "config": {
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "test",
                    "username": "u",
                    "password": "p",
                    "query": "SELECT 1",
                    "text_columns": "col",
                },
                "auto_index": False,
                "schedule": "",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Test DB Connector"
        assert "id" in data

    def test_get_connector(self, client):
        created = client.post(
            "/connectors",
            json={
                "name": "Get Conn",
                "connector_type": "api",
                "config": {
                    "url": "http://x",
                    "method": "GET",
                    "text_field": "t",
                    "name_field": "n",
                },
            },
        ).json()
        r = client.get(f"/connectors/{created['id']}")
        assert r.status_code == 200

    def test_update_connector(self, client):
        created = client.post(
            "/connectors",
            json={
                "name": "Upd Conn",
                "connector_type": "api",
                "config": {
                    "url": "http://x",
                    "method": "GET",
                    "text_field": "t",
                    "name_field": "n",
                },
            },
        ).json()
        r = client.put(f"/connectors/{created['id']}", json={"name": "Updated Conn"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Conn"

    def test_delete_connector(self, client):
        created = client.post(
            "/connectors",
            json={
                "name": "Del Conn",
                "connector_type": "api",
                "config": {
                    "url": "http://x",
                    "method": "GET",
                    "text_field": "t",
                    "name_field": "n",
                },
            },
        ).json()
        r = client.delete(f"/connectors/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS API
# ═══════════════════════════════════════════════════════════════════════════════


@needs_postgres
class TestDocumentsAPI:
    def test_list_documents(self, client):
        r = client.get("/documents/registry")
        assert r.status_code == 200
        data = r.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    def test_document_connect_failure(self, client):
        """Connect fails for unreachable URL (expected 502)."""
        r = client.post(
            "/documents/connect",
            json={
                "url": "https://example.invalid/doc.pdf",
                "collection": "test_docs",
            },
        )
        # Unreachable URL should return an error status
        assert r.status_code in (400, 502, 500)

    def test_document_folders(self, client):
        r = client.get("/documents/folders")
        assert r.status_code == 200
        data = r.json()
        assert "folders" in data
        assert isinstance(data["folders"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSIONS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionsAPI:
    def test_list_sessions(self, client):
        r = client.get("/sessions")
        assert r.status_code == 200
        data = r.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_session_history(self, client):
        import agent.memory as mem

        mem.save_message("api-session-1", "user", "hello")
        mem.save_message("api-session-1", "assistant", "hi")
        r = client.get("/sessions/api-session-1/history")
        assert r.status_code == 200
        data = r.json()
        assert "messages" in data
        assert len(data["messages"]) >= 2

    def test_delete_session(self, client):
        import agent.memory as mem

        mem.save_message("del-session", "user", "msg")
        r = client.delete("/sessions/del-session")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS API
# ═══════════════════════════════════════════════════════════════════════════════


class TestModelsAPI:
    def test_list_models(self, client):
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert "active" in data
        assert "models" in data

    def test_switch_model(self, client):
        r = client.post(
            "/models/switch", json={"provider": "ollama", "model": "llama3"}
        )
        # May fail with connection error to Ollama, but endpoint validates + accepts
        assert r.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# VERSION HISTORY & AUDIT
# ═══════════════════════════════════════════════════════════════════════════════


class TestVersionsAuditAPI:
    def test_versions_endpoint(self, client):
        created = client.post(
            "/agents", json={"name": "VerAgent", "description": "v1"}
        ).json()
        client.put(f"/agents/{created['id']}", json={"description": "v2"})
        r = client.get(f"/versions/agent/{created['id']}")
        assert r.status_code == 200
        versions = r.json()
        assert len(versions) >= 1

    def test_audit_log_endpoint(self, client):
        client.post(
            "/skills",
            json={"name": "AuditSkill", "description": "", "system_prompt": ""},
        )
        r = client.get("/audit-log")
        assert r.status_code == 200
        data = r.json()
        assert "entries" in data
        entries = data["entries"]
        assert len(entries) >= 1
        assert any(e["entity_name"] == "AuditSkill" for e in entries)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT / IMPORT
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportImportAPI:
    def test_export(self, client):
        r = client.get("/export")
        assert r.status_code == 200
        data = r.json()
        # export wraps in {"export": {...}}
        assert "export" in data
        export_data = data["export"]
        assert "agents" in export_data
        assert "skills" in export_data

    def test_import(self, client):
        # Export, then re-import using the "export" key format
        export_resp = client.get("/export").json()
        export_data = export_resp["export"]
        r = client.post("/import", json={"export": export_data, "merge": True})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
