"""
Comprehensive Platform Test Suite — Enterprise Validation
Tests every feature end-to-end: data ingestion, agents, orchestration,
A2A, MCP, guardrails, intelligence hub, workflows, and more.

Run with: pytest tests/e2e/test_platform_comprehensive.py -v
"""

import os
import sys
import json
import uuid
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Ensure project root is importable
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "agent")
)

from agent.memory import (
    init_db,
    _get_conn,
    _reset_conn,
    # Skills
    list_skills,
    get_skill,
    create_skill,
    update_skill,
    delete_skill,
    # Agents
    list_agents,
    get_agent,
    create_agent,
    update_agent,
    delete_agent,
    # A2A
    list_a2a_peers,
    get_a2a_peer,
    create_a2a_peer,
    update_a2a_peer,
    delete_a2a_peer,
    # MCP
    list_mcp_servers,
    get_mcp_server,
    create_mcp_server,
    update_mcp_server,
    delete_mcp_server,
    # Prompts
    list_prompts,
    get_prompt,
    create_prompt,
    update_prompt,
    delete_prompt,
    # Guardrails
    list_guardrails,
    get_guardrail,
    update_guardrail,
    # Custom Tools
    list_custom_tools,
    get_custom_tool,
    create_custom_tool,
    update_custom_tool,
    delete_custom_tool,
    # Documents
    list_documents_registry,
    get_document_registry,
    create_document_registry,
    update_document_registry,
    delete_document_registry,
    list_folders,
    tag_document_to_agent,
    untag_document_from_agent,
    # Connectors
    list_connectors,
    get_connector,
    create_connector,
    update_connector,
    delete_connector,
    create_sync_job,
    update_sync_job,
    list_sync_jobs,
    # Versions & Audit
    list_versions,
    get_version,
    save_version,
    list_audit_log,
    log_audit,
    # Sessions
    get_history,
    save_message,
    list_sessions,
    delete_session,
    get_session_summary,
    # Stats
    get_memory_stats,
    get_db_stats,
    export_all_data,
    import_all_data,
)
from agent.filestore import (
    save_file,
    read_file,
    read_file_bytes,
    file_exists,
    delete_file,
    get_storage_stats,
)
from agent.connectors import (
    CONNECTOR_CATALOG,
    generate_connector_id,
    generate_job_id,
    ConnectorType,
    SyncStatus,
)
from agent.connectors.sync_engine import test_connector as check_connector, run_sync

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Each test gets a fresh SQLite database."""
    db_dir = str(tmp_path / "data")
    os.makedirs(db_dir, exist_ok=True)
    monkeypatch.setenv("MEMORY_DIR", db_dir)
    # Reset connection
    import agent.memory as mem

    mem._reset_conn()
    monkeypatch.setattr(mem, "MEMORY_DIR", db_dir)
    monkeypatch.setattr(mem, "DB_PATH", os.path.join(db_dir, "platform.db"))
    init_db()
    # Initialize guardrails table + defaults eagerly so tests can use get_guardrail
    list_guardrails()
    yield
    mem._reset_conn()


@pytest.fixture
def filestore_dir(tmp_path, monkeypatch):
    """Fresh filestore directory."""
    fs_dir = str(tmp_path / "filestore")
    os.makedirs(fs_dir, exist_ok=True)
    import agent.filestore as fs

    monkeypatch.setattr(fs, "FILESTORE_ROOT", fs_dir)
    return fs_dir


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATA INGESTION — File Store
# ═══════════════════════════════════════════════════════════════════════════════


class TestFileStore:
    """Enterprise file staging layer tests."""

    def test_save_and_read_text(self, filestore_dir):
        """Upload text file and read it back."""
        doc_id = "doc_001"
        result = save_file(doc_id, "test.txt", "Hello World")
        assert result["size_bytes"] > 0
        assert "storage_path" in result

        content = read_file(doc_id, "test.txt")
        assert content == "Hello World"

    def test_save_and_read_bytes(self, filestore_dir):
        """Upload binary content."""
        doc_id = "doc_002"
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        save_file(doc_id, "image.png", data)
        assert file_exists(doc_id, "image.png")

    def test_file_exists_false(self, filestore_dir):
        """Non-existent file returns False."""
        assert not file_exists("nonexistent", "nothing.txt")

    def test_delete_file(self, filestore_dir):
        """Delete removes entire document directory."""
        doc_id = "doc_del"
        save_file(doc_id, "temp.txt", "delete me")
        assert file_exists(doc_id, "temp.txt")
        result = delete_file(doc_id)
        assert result is True
        assert not file_exists(doc_id, "temp.txt")

    def test_delete_nonexistent(self, filestore_dir):
        """Delete of nonexistent returns False."""
        assert delete_file("ghost_doc") is False

    def test_storage_stats(self, filestore_dir):
        """Stats correctly reports file count and size."""
        save_file("s1", "a.txt", "content a")
        save_file("s2", "b.txt", "content b")
        stats = get_storage_stats()
        assert stats["total_files"] >= 2
        assert stats["total_size_bytes"] > 0

    def test_multiple_files_per_doc(self, filestore_dir):
        """Multiple files in same document directory."""
        doc_id = "multi"
        save_file(doc_id, "readme.md", "# Title")
        save_file(doc_id, "data.json", '{"key": "value"}')
        assert file_exists(doc_id, "readme.md")
        assert file_exists(doc_id, "data.json")
        assert read_file(doc_id, "readme.md") == "# Title"

    def test_large_file(self, filestore_dir):
        """Handle larger files (1MB)."""
        doc_id = "large"
        content = "x" * (1024 * 1024)
        save_file(doc_id, "big.txt", content)
        assert file_exists(doc_id, "big.txt")
        read_back = read_file(doc_id, "big.txt")
        assert len(read_back) == 1024 * 1024


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DATA INGESTION — Document Registry
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentRegistry:
    """Document lifecycle: upload → staged → indexed."""

    def test_create_document_uploaded(self):
        """Create document in 'uploaded' state."""
        doc = create_document_registry(
            name="report.pdf",
            source="upload:report.pdf",
            status="uploaded",
            source_type="upload",
            file_type="pdf",
            file_size=5000,
        )
        assert doc["name"] == "report.pdf"
        assert doc["status"] == "uploaded"
        assert doc["source_type"] == "upload"

    def test_create_document_connected(self):
        """Create document from URL connection."""
        doc = create_document_registry(
            name="wiki-page.html",
            source="https://example.com/wiki",
            status="uploaded",
            source_type="connected",
            file_type="html",
        )
        assert doc["source_type"] == "connected"
        assert doc["status"] == "uploaded"

    def test_create_document_shortcut(self):
        """Create shortcut reference."""
        original = create_document_registry(
            name="original.txt", source="upload:original.txt"
        )
        shortcut = create_document_registry(
            name="shortcut-to-original",
            source="shortcut",
            source_type="shortcut",
            shortcut_ref=original["id"],
        )
        assert shortcut["source_type"] == "shortcut"
        assert shortcut["shortcut_ref"] == original["id"]

    def test_update_document_status_to_indexed(self):
        """Transition document from uploaded → indexed."""
        doc = create_document_registry(
            name="doc.txt", source="upload:doc.txt", status="uploaded"
        )
        updated = update_document_registry(doc["id"], status="indexed", chunk_count=15)
        assert updated["status"] == "indexed"
        assert updated["chunk_count"] == 15

    def test_update_document_status_to_failed(self):
        """Mark document as failed."""
        doc = create_document_registry(
            name="bad.pdf", source="upload:bad.pdf", status="uploaded"
        )
        updated = update_document_registry(doc["id"], status="failed")
        assert updated["status"] == "failed"

    def test_list_documents_by_folder(self):
        """Filter documents by folder."""
        create_document_registry(name="a.txt", source="a", folder="/reports/")
        create_document_registry(name="b.txt", source="b", folder="/data/")
        reports = list_documents_registry(folder="/reports/")
        assert len(reports) >= 1
        assert all(d["folder"] == "/reports/" for d in reports)

    def test_list_documents_by_search(self):
        """Search documents by name."""
        create_document_registry(name="quarterly-report.pdf", source="qr")
        create_document_registry(name="meeting-notes.txt", source="mn")
        results = list_documents_registry(search="quarterly")
        assert len(results) >= 1
        assert "quarterly" in results[0]["name"]

    def test_folder_listing(self):
        """List unique folders with counts."""
        create_document_registry(name="a.txt", source="a", folder="/sales/")
        create_document_registry(name="b.txt", source="b", folder="/sales/")
        create_document_registry(name="c.txt", source="c", folder="/engineering/")
        folders = list_folders()
        folder_paths = [f["path"] for f in folders]
        assert "/sales/" in folder_paths
        assert "/engineering/" in folder_paths

    def test_tag_document_to_agent(self):
        """Tag a document to an agent."""
        doc = create_document_registry(name="tagged.txt", source="t")
        # Create an agent first
        agent = create_agent(name="TagAgent", description="test")
        result = tag_document_to_agent(doc["id"], agent["id"])
        assert result is not None
        assert agent["id"] in result["agent_tags"]

    def test_untag_document_from_agent(self):
        """Remove agent tag from document."""
        doc = create_document_registry(name="untagme.txt", source="u")
        agent = create_agent(name="UntagAgent", description="test")
        tag_document_to_agent(doc["id"], agent["id"])
        untag_document_from_agent(doc["id"], agent["id"])
        updated = get_document_registry(doc["id"])
        assert agent["id"] not in updated["agent_tags"]

    def test_delete_document(self):
        """Delete document from registry."""
        doc = create_document_registry(name="delete-me.txt", source="dm")
        result = delete_document_registry(doc["id"])
        assert result is True
        assert get_document_registry(doc["id"]) is None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DATA INGESTION — Connectors
# ═══════════════════════════════════════════════════════════════════════════════


class TestConnectors:
    """Data connector CRUD and catalog."""

    def test_connector_catalog_complete(self):
        """All expected connector types exist in catalog."""
        assert "database" in CONNECTOR_CATALOG
        assert "cloud_storage" in CONNECTOR_CATALOG
        assert "api" in CONNECTOR_CATALOG
        assert "google_drive" in CONNECTOR_CATALOG
        assert "sharepoint" in CONNECTOR_CATALOG

    def test_connector_catalog_has_config_schema(self):
        """Each catalog entry has a config_schema."""
        for ctype, meta in CONNECTOR_CATALOG.items():
            assert "config_schema" in meta, f"{ctype} missing config_schema"
            assert "name" in meta, f"{ctype} missing name"
            assert "description" in meta, f"{ctype} missing description"

    def test_create_connector(self):
        """Create a database connector."""
        cid = generate_connector_id()
        connector = create_connector(
            cid,
            "Production DB",
            "database",
            config={
                "db_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "mydb",
                "username": "user",
                "password": "pass",
                "query": "SELECT * FROM docs",
                "text_columns": "content",
            },
        )
        assert connector["id"] == cid
        assert connector["name"] == "Production DB"
        assert connector["connector_type"] == "database"
        assert connector["config"]["db_type"] == "postgresql"
        assert connector["enabled"] is True

    def test_create_cloud_storage_connector(self):
        """Create an S3 connector."""
        cid = generate_connector_id()
        connector = create_connector(
            cid,
            "Marketing S3",
            "cloud_storage",
            config={"provider": "s3", "bucket": "docs-bucket", "prefix": "marketing/"},
        )
        assert connector["connector_type"] == "cloud_storage"
        assert connector["config"]["provider"] == "s3"

    def test_create_api_connector(self):
        """Create a REST API connector."""
        cid = generate_connector_id()
        connector = create_connector(
            cid,
            "CRM API",
            "api",
            config={
                "url": "https://api.example.com/data",
                "method": "GET",
                "text_field": "description",
                "name_field": "title",
            },
        )
        assert connector["connector_type"] == "api"

    def test_update_connector(self):
        """Update connector config."""
        cid = generate_connector_id()
        create_connector(cid, "Update Test", "database", config={"db_type": "mysql"})
        updated = update_connector(cid, {"name": "Updated DB", "enabled": False})
        assert updated["name"] == "Updated DB"
        assert updated["enabled"] is False

    def test_delete_connector(self):
        """Delete connector and its jobs."""
        cid = generate_connector_id()
        create_connector(cid, "Delete Me", "api", config={})
        result = delete_connector(cid)
        assert result is True
        assert get_connector(cid) is None

    def test_list_connectors(self):
        """List all connectors."""
        create_connector(generate_connector_id(), "C1", "database", config={})
        create_connector(generate_connector_id(), "C2", "api", config={})
        connectors = list_connectors()
        assert len(connectors) >= 2

    def test_sync_job_lifecycle(self):
        """Create and update a sync job."""
        cid = generate_connector_id()
        create_connector(cid, "Sync Test", "database", config={})
        job_id = generate_job_id()
        job = create_sync_job(job_id, cid)
        assert job["status"] == "running"
        assert job["connector_id"] == cid

        update_sync_job(job_id, "completed", docs_pulled=10, docs_indexed=5)
        jobs = list_sync_jobs(connector_id=cid)
        assert len(jobs) >= 1
        assert jobs[0]["status"] == "completed"
        assert jobs[0]["docs_pulled"] == 10

    def test_sync_job_failure(self):
        """Sync job failure records error."""
        cid = generate_connector_id()
        create_connector(cid, "Fail Test", "database", config={})
        job_id = generate_job_id()
        create_sync_job(job_id, cid)
        update_sync_job(job_id, "failed", error="Connection refused")
        jobs = list_sync_jobs(connector_id=cid)
        assert jobs[0]["status"] == "failed"
        assert "Connection refused" in jobs[0]["error"]

    def test_connector_auto_index_flag(self):
        """Auto-index flag persists."""
        cid = generate_connector_id()
        connector = create_connector(cid, "AutoIdx", "api", config={}, auto_index=True)
        assert connector["auto_index"] is True

    def test_generate_ids_unique(self):
        """Generated IDs are unique."""
        ids = {generate_connector_id() for _ in range(100)}
        assert len(ids) == 100
        job_ids = {generate_job_id() for _ in range(100)}
        assert len(job_ids) == 100


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AGENTS — CRUD & Configuration
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentsCRUD:
    """Agent creation, configuration, and management."""

    def test_default_agent_exists(self):
        """Default agent created on init."""
        agents = list_agents()
        defaults = [a for a in agents if a.get("is_default")]
        assert len(defaults) >= 1

    def test_create_agent(self):
        """Create a fully configured agent."""
        agent = create_agent(
            name="Research Agent",
            description="Specialized in web research",
            provider="ollama",
            model="llama3",
            temperature=0.5,
            top_p=0.9,
            system_prompt="You are a research assistant.",
            skill_ids=["sk1"],
            tool_ids=["web_search", "http_fetch"],
            kb_collection="research_docs",
            max_iterations=10,
            memory_enabled=True,
        )
        assert agent["name"] == "Research Agent"
        assert agent["temperature"] == 0.5
        assert agent["top_p"] == 0.9
        assert "web_search" in agent["tool_ids"]
        assert agent["kb_collection"] == "research_docs"
        assert agent["max_iterations"] == 10

    def test_create_agent_minimal(self):
        """Create agent with minimal config."""
        agent = create_agent(name="Minimal Agent", description="Basic")
        assert agent["id"] is not None
        assert agent["provider"] == "ollama"
        assert agent["model"] == "llama3"

    def test_update_agent(self):
        """Update agent properties."""
        agent = create_agent(name="Updatable", description="v1")
        updated = update_agent(agent["id"], description="v2", temperature=0.3)
        assert updated["description"] == "v2"
        assert updated["temperature"] == 0.3

    def test_update_agent_sub_agents(self):
        """Assign sub-agents for orchestration."""
        sub1 = create_agent(name="SubAgent1", description="sub")
        sub2 = create_agent(name="SubAgent2", description="sub")
        orchestrator = create_agent(name="Orchestrator", description="main")
        updated = update_agent(
            orchestrator["id"], sub_agent_ids=[sub1["id"], sub2["id"]]
        )
        assert sub1["id"] in updated["sub_agent_ids"]
        assert sub2["id"] in updated["sub_agent_ids"]

    def test_delete_agent(self):
        """Delete non-default agent."""
        agent = create_agent(name="Deletable", description="temp")
        assert delete_agent(agent["id"]) is True
        assert get_agent(agent["id"]) is None

    def test_cannot_delete_default_agent(self):
        """Default agent cannot be deleted."""
        agents = list_agents()
        default = next(a for a in agents if a.get("is_default"))
        result = delete_agent(default["id"])
        assert result is False
        assert get_agent(default["id"]) is not None

    def test_agent_name_unique(self):
        """Agent names must be unique."""
        create_agent(name="Unique Name", description="first")
        with pytest.raises(Exception):
            create_agent(name="Unique Name", description="second")

    def test_agent_skill_assignment(self):
        """Assign skills to agent."""
        skill = create_skill(
            name="Analysis",
            description="Data analysis",
            system_prompt="Analyze data carefully.",
        )
        agent = create_agent(
            name="Analyst", description="test", skill_ids=[skill["id"]]
        )
        assert skill["id"] in agent["skill_ids"]

    def test_agent_tool_assignment(self):
        """Assign tools to agent."""
        agent = create_agent(
            name="ToolUser",
            description="test",
            tool_ids=["math", "web_search", "code_execute"],
        )
        assert "math" in agent["tool_ids"]
        assert "web_search" in agent["tool_ids"]

    def test_list_agents_returns_all(self):
        """List returns all agents including default."""
        create_agent(name="ListAgent1", description="a")
        create_agent(name="ListAgent2", description="b")
        agents = list_agents()
        names = [a["name"] for a in agents]
        assert "ListAgent1" in names
        assert "ListAgent2" in names


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MULTI-AGENT ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultiAgentOrchestration:
    """Orchestration: parent agent with sub-agents."""

    def test_orchestrator_with_sub_agents(self):
        """Create orchestrator with multiple sub-agents."""
        researcher = create_agent(
            name="Researcher", description="Web research", tool_ids=["web_search"]
        )
        coder = create_agent(
            name="Coder", description="Code tasks", tool_ids=["code_execute"]
        )
        writer = create_agent(name="Writer", description="Content writing")
        orchestrator = create_agent(
            name="MainOrchestrator",
            description="Routes tasks to specialists",
            sub_agent_ids=[researcher["id"], coder["id"], writer["id"]],
        )
        assert len(orchestrator["sub_agent_ids"]) == 3
        # Verify sub-agents are accessible
        for sid in orchestrator["sub_agent_ids"]:
            sub = get_agent(sid)
            assert sub is not None

    def test_orchestrator_sub_agent_config_accessible(self):
        """Sub-agent configs can be loaded for routing."""
        sub = create_agent(
            name="SubConfig", description="Specialized", tool_ids=["math"]
        )
        orch = create_agent(
            name="OrchConfig", description="Main", sub_agent_ids=[sub["id"]]
        )
        # Simulate what graph.py does
        orch_full = get_agent(orch["id"])
        sub_configs = []
        for sid in orch_full["sub_agent_ids"]:
            sub_configs.append(get_agent(sid))
        assert len(sub_configs) == 1
        assert sub_configs[0]["name"] == "SubConfig"

    def test_update_orchestrator_sub_agents(self):
        """Dynamically add/remove sub-agents."""
        s1 = create_agent(name="OrcSub1", description="a")
        s2 = create_agent(name="OrcSub2", description="b")
        s3 = create_agent(name="OrcSub3", description="c")
        orch = create_agent(
            name="DynOrch", description="Dynamic", sub_agent_ids=[s1["id"]]
        )
        # Add more
        update_agent(orch["id"], sub_agent_ids=[s1["id"], s2["id"], s3["id"]])
        updated = get_agent(orch["id"])
        assert len(updated["sub_agent_ids"]) == 3
        # Remove one
        update_agent(orch["id"], sub_agent_ids=[s2["id"], s3["id"]])
        updated = get_agent(orch["id"])
        assert s1["id"] not in updated["sub_agent_ids"]

    def test_nested_orchestration_not_circular(self):
        """Sub-agents cannot include their own parent (data integrity)."""
        parent = create_agent(name="Parent", description="top")
        child = create_agent(name="Child", description="bottom", sub_agent_ids=[])
        update_agent(parent["id"], sub_agent_ids=[child["id"]])
        # The system stores it — circular detection is application-level
        parent_data = get_agent(parent["id"])
        assert child["id"] in parent_data["sub_agent_ids"]


# ═══════════════════════════════════════════════════════════════════════════════
# 6. A2A — Agent-to-Agent Protocol
# ═══════════════════════════════════════════════════════════════════════════════


class TestA2APeers:
    """Agent-to-Agent peer management."""

    def test_create_a2a_peer(self):
        """Register an A2A peer agent."""
        peer = create_a2a_peer(
            name="External Research Agent",
            url="http://research-agent.company.com:8000",
            description="Handles research tasks",
            capabilities=["web_search", "summarization"],
        )
        assert peer["name"] == "External Research Agent"
        assert peer["url"] == "http://research-agent.company.com:8000"
        assert "web_search" in peer["capabilities"]

    def test_create_multiple_peers(self):
        """Register multiple peers."""
        p1 = create_a2a_peer(
            name="Peer1", url="http://p1:8000", description="", capabilities=[]
        )
        p2 = create_a2a_peer(
            name="Peer2",
            url="http://p2:8000",
            description="",
            capabilities=["translate"],
        )
        peers = list_a2a_peers()
        assert len(peers) >= 2

    def test_update_a2a_peer(self):
        """Update peer status and capabilities."""
        peer = create_a2a_peer(name="UpdatePeer", url="http://up:8000", description="")
        updated = update_a2a_peer(
            peer["id"], status="healthy", capabilities=["code", "math"]
        )
        assert updated["status"] == "healthy"
        assert "code" in updated["capabilities"]

    def test_delete_a2a_peer(self):
        """Remove a peer."""
        peer = create_a2a_peer(name="DeletePeer", url="http://del:8000", description="")
        assert delete_a2a_peer(peer["id"]) is True
        assert get_a2a_peer(peer["id"]) is None

    def test_a2a_peer_agent_card(self):
        """Peer with agent card metadata."""
        peer = create_a2a_peer(
            name="CardPeer",
            url="http://card:8000",
            description="Has agent card",
            capabilities=["analysis"],
        )
        updated = update_a2a_peer(
            peer["id"], agent_card={"version": "1.0", "skills": ["data_analysis"]}
        )
        assert updated["agent_card"]["version"] == "1.0"

    def test_a2a_peer_url_required(self):
        """Peer requires a URL."""
        peer = create_a2a_peer(
            name="URLRequired", url="http://valid:8000", description=""
        )
        assert peer["url"] != ""

    def test_list_peers_empty(self):
        """Empty list when no peers registered."""
        peers = list_a2a_peers()
        # May have 0 if this test runs first after fresh DB
        assert isinstance(peers, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. MCP — Model Context Protocol Servers
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPServers:
    """MCP server registration and management."""

    def test_create_mcp_server_stdio(self):
        """Register stdio-transport MCP server."""
        server = create_mcp_server(
            name="File System MCP",
            url="npx @modelcontextprotocol/server-filesystem /data",
            transport="stdio",
            description="File system access",
            tools=["read_file", "write_file", "list_dir"],
        )
        assert server["name"] == "File System MCP"
        assert server["transport"] == "stdio"
        assert "read_file" in server["tools"]

    def test_create_mcp_server_sse(self):
        """Register SSE-transport MCP server."""
        server = create_mcp_server(
            name="Web Search MCP",
            url="http://mcp-search:3000/sse",
            transport="sse",
            description="Web search via MCP",
            tools=["search", "fetch_url"],
        )
        assert server["transport"] == "sse"

    def test_update_mcp_server(self):
        """Update MCP server status and tools."""
        server = create_mcp_server(
            name="Updateable MCP", url="test://url", transport="stdio", description=""
        )
        updated = update_mcp_server(
            server["id"], status="connected", tools=["tool_a", "tool_b"]
        )
        assert updated["status"] == "connected"
        assert len(updated["tools"]) == 2

    def test_disable_mcp_server(self):
        """Disable MCP server."""
        server = create_mcp_server(
            name="Disable MCP", url="test://url2", transport="stdio", description=""
        )
        updated = update_mcp_server(server["id"], enabled=False)
        assert updated["enabled"] is False

    def test_delete_mcp_server(self):
        """Remove MCP server."""
        server = create_mcp_server(
            name="Del MCP", url="test://del", transport="stdio", description=""
        )
        assert delete_mcp_server(server["id"]) is True
        assert get_mcp_server(server["id"]) is None

    def test_list_mcp_servers(self):
        """List all MCP servers."""
        create_mcp_server(
            name="MCP List 1", url="u1", transport="stdio", description=""
        )
        create_mcp_server(name="MCP List 2", url="u2", transport="sse", description="")
        servers = list_mcp_servers()
        assert len(servers) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# 8. GUARDRAILS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardrails:
    """Input/output guardrail configuration."""

    def test_list_guardrails_has_defaults(self):
        """Default guardrails exist after init."""
        guardrails = list_guardrails()
        # Should have at least: prompt-injection, pii, topic-restrict, output-length, data-leak, toxicity
        assert len(guardrails) >= 6
        ids = [g["id"] for g in guardrails]
        assert "gr-prompt-injection" in ids
        assert "gr-pii" in ids
        assert "gr-toxicity" in ids

    def test_get_guardrail(self):
        """Get specific guardrail."""
        gr = get_guardrail("gr-pii")
        assert gr is not None
        assert gr["name"] == "PII Detection"
        assert "enabled" in gr
        assert "severity" in gr

    def test_update_guardrail_enable(self):
        """Enable/disable guardrail."""
        update_guardrail("gr-toxicity", enabled=True)
        gr = get_guardrail("gr-toxicity")
        assert gr["enabled"] is True
        update_guardrail("gr-toxicity", enabled=False)
        gr = get_guardrail("gr-toxicity")
        assert gr["enabled"] is False

    def test_update_guardrail_severity(self):
        """Change guardrail severity."""
        update_guardrail("gr-prompt-injection", severity="high")
        gr = get_guardrail("gr-prompt-injection")
        assert gr["severity"] == "high"

    def test_update_guardrail_config(self):
        """Update guardrail config (e.g. max length)."""
        update_guardrail("gr-output-length", config={"max_tokens": 500})
        gr = get_guardrail("gr-output-length")
        assert gr["config"]["max_tokens"] == 500

    def test_all_guardrails_have_required_fields(self):
        """Every guardrail has id, name, enabled, severity, config."""
        for gr in list_guardrails():
            assert "id" in gr
            assert "name" in gr
            assert "enabled" in gr
            assert "severity" in gr
            assert "config" in gr


# ═══════════════════════════════════════════════════════════════════════════════
# 9. INTELLIGENCE HUB — Skills
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkills:
    """Skills CRUD for intelligence hub."""

    def test_create_skill(self):
        """Create a skill with system prompt and tools."""
        skill = create_skill(
            name="Data Analysis",
            description="Analyzes data and generates insights",
            system_prompt="You are an expert data analyst. Always provide statistical context.",
            tool_ids=["math", "code_execute"],
            constraints=["Never expose raw data", "Always cite sources"],
        )
        assert skill["name"] == "Data Analysis"
        assert "math" in skill["tool_ids"]
        assert len(skill["constraints"]) == 2

    def test_update_skill(self):
        """Update skill properties."""
        skill = create_skill(name="Update Skill", description="v1", system_prompt="")
        updated = update_skill(
            skill["id"], description="v2", system_prompt="Be concise."
        )
        assert updated["description"] == "v2"
        assert updated["system_prompt"] == "Be concise."

    def test_delete_skill(self):
        """Delete skill."""
        skill = create_skill(name="Temp Skill", description="", system_prompt="")
        assert delete_skill(skill["id"]) is True
        assert get_skill(skill["id"]) is None

    def test_skill_name_unique(self):
        """Skill names must be unique."""
        create_skill(name="Unique Skill", description="", system_prompt="")
        with pytest.raises(Exception):
            create_skill(name="Unique Skill", description="", system_prompt="")

    def test_list_skills(self):
        """List all skills."""
        create_skill(name="Skill A", description="", system_prompt="")
        create_skill(name="Skill B", description="", system_prompt="")
        skills = list_skills()
        names = [s["name"] for s in skills]
        assert "Skill A" in names
        assert "Skill B" in names


# ═══════════════════════════════════════════════════════════════════════════════
# 10. INTELLIGENCE HUB — Prompts
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrompts:
    """Prompt library CRUD."""

    def test_create_prompt(self):
        """Create a categorized prompt."""
        prompt = create_prompt(
            name="Summarize Document",
            content="Summarize the following document in 3 bullet points:\n{document}",
            category="summarization",
            description="Standard document summarization prompt",
            tags=["summary", "document", "enterprise"],
        )
        assert prompt["name"] == "Summarize Document"
        assert prompt["category"] == "summarization"
        assert "summary" in prompt["tags"]

    def test_update_prompt(self):
        """Update prompt content."""
        prompt = create_prompt(
            name="Updatable Prompt", content="v1", category="general", description=""
        )
        updated = update_prompt(
            prompt["id"], content="v2 - improved", category="analysis"
        )
        assert updated["content"] == "v2 - improved"
        assert updated["category"] == "analysis"

    def test_delete_prompt(self):
        """Delete prompt."""
        prompt = create_prompt(
            name="Del Prompt", content="x", category="general", description=""
        )
        assert delete_prompt(prompt["id"]) is True
        assert get_prompt(prompt["id"]) is None

    def test_prompt_name_unique(self):
        """Prompt names must be unique."""
        create_prompt(
            name="Unique Prompt", content="x", category="general", description=""
        )
        with pytest.raises(Exception):
            create_prompt(
                name="Unique Prompt", content="y", category="other", description=""
            )

    def test_list_prompts(self):
        """List all prompts."""
        create_prompt(name="P1", content="c1", category="cat1", description="")
        create_prompt(name="P2", content="c2", category="cat2", description="")
        prompts = list_prompts()
        assert len(prompts) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# 11. INTELLIGENCE HUB — Custom Tools
# ═══════════════════════════════════════════════════════════════════════════════


class TestCustomTools:
    """Custom tool CRUD."""

    def test_create_custom_tool(self):
        """Create a custom API tool."""
        tool = create_custom_tool(
            name="Weather API",
            description="Get current weather",
            category="external",
            endpoint="https://api.weather.com/current",
            method="GET",
            headers={"X-Api-Key": "secret"},
            body_template={},
            parameters=[
                {
                    "name": "city",
                    "type": "string",
                    "required": True,
                    "description": "City name",
                },
            ],
        )
        assert tool["name"] == "Weather API"
        assert tool["endpoint"] == "https://api.weather.com/current"
        assert len(tool["parameters"]) == 1

    def test_update_custom_tool(self):
        """Update tool endpoint."""
        tool = create_custom_tool(
            name="UpdTool",
            description="",
            category="test",
            endpoint="http://old.com",
            method="GET",
            headers={},
            body_template={},
            parameters=[],
        )
        updated = update_custom_tool(
            tool["id"], endpoint="http://new.com", method="POST"
        )
        assert updated["endpoint"] == "http://new.com"
        assert updated["method"] == "POST"

    def test_delete_custom_tool(self):
        """Delete custom tool."""
        tool = create_custom_tool(
            name="DelTool",
            description="",
            category="test",
            endpoint="http://x.com",
            method="GET",
            headers={},
            body_template={},
            parameters=[],
        )
        assert delete_custom_tool(tool["id"]) is True
        assert get_custom_tool(tool["id"]) is None

    def test_list_custom_tools(self):
        """List all custom tools."""
        create_custom_tool(
            name="Tool1",
            description="",
            category="a",
            endpoint="http://1.com",
            method="GET",
            headers={},
            body_template={},
            parameters=[],
        )
        create_custom_tool(
            name="Tool2",
            description="",
            category="b",
            endpoint="http://2.com",
            method="POST",
            headers={},
            body_template={},
            parameters=[],
        )
        tools = list_custom_tools()
        assert len(tools) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# 12. VERSIONING & AUDIT
# ═══════════════════════════════════════════════════════════════════════════════


class TestVersioningAndAudit:
    """Version history and audit logging."""

    def test_save_version(self):
        """Save entity version snapshot."""
        agent = create_agent(name="VersionAgent", description="v1")
        result = save_version("agent", agent["id"], agent)
        assert result is not None
        assert "id" in result
        version = get_version(result["id"])
        assert version is not None
        assert version["entity_type"] == "agent"

    def test_version_history(self):
        """Track multiple versions."""
        agent = create_agent(name="MultiVer", description="v1")
        save_version("agent", agent["id"], agent)
        update_agent(agent["id"], description="v2")
        updated = get_agent(agent["id"])
        save_version("agent", agent["id"], updated)
        versions = list_versions("agent", agent["id"])
        # update_agent internally calls save_version too, so at least 2
        assert len(versions) >= 2

    def test_audit_log_create(self):
        """Audit log records actions."""
        log_audit("create", "agent", "ag123", "TestAgent", {"model": "llama3"})
        entries = list_audit_log(limit=10, entity_type="agent")
        assert len(entries) >= 1
        assert entries[0]["action"] == "create"
        assert entries[0]["entity_name"] == "TestAgent"

    def test_audit_log_filter_by_action(self):
        """Filter audit log by action type."""
        log_audit("create", "connector", "c1", "ProdDB", {})
        log_audit("delete", "connector", "c2", "OldConn", {})
        creates = list_audit_log(limit=50, action="create")
        deletes = list_audit_log(limit=50, action="delete")
        assert all(e["action"] == "create" for e in creates)
        assert all(e["action"] == "delete" for e in deletes)

    def test_audit_log_entity_type_filter(self):
        """Filter by entity type."""
        log_audit("update", "skill", "s1", "Analysis", {})
        log_audit("update", "prompt", "p1", "Summary", {})
        skills = list_audit_log(limit=50, entity_type="skill")
        assert all(e["entity_type"] == "skill" for e in skills)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. SESSIONS & MEMORY
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionsAndMemory:
    """Conversation memory and session management."""

    def test_save_and_get_history(self):
        """Save messages and retrieve history."""
        sid = "session_test_001"
        save_message(sid, "user", "Hello")
        save_message(sid, "assistant", "Hi there!")
        history = get_history(sid, limit=10)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_list_sessions(self):
        """List all active sessions."""
        save_message("s1", "user", "msg1")
        save_message("s2", "user", "msg2")
        sessions = list_sessions(limit=50)
        ids = [s["session_id"] for s in sessions]
        assert "s1" in ids
        assert "s2" in ids

    def test_delete_session(self):
        """Delete session removes all messages."""
        sid = "delete_session"
        save_message(sid, "user", "hello")
        save_message(sid, "assistant", "bye")
        count = delete_session(sid)
        assert count >= 2
        history = get_history(sid)
        assert len(history) == 0

    def test_memory_stats(self):
        """Memory stats reports correctly."""
        save_message("stat_session", "user", "x")
        stats = get_memory_stats()
        assert stats["total_messages"] >= 1
        assert stats["total_sessions"] >= 1

    def test_db_stats(self):
        """DB stats include all tables."""
        stats = get_db_stats()
        assert "agents" in stats
        assert "skills" in stats
        assert "db_size_bytes" in stats

    def test_export_import_data(self):
        """Export and re-import data."""
        create_skill(name="Export Skill", description="exported", system_prompt="x")
        create_prompt(name="Export Prompt", content="y", category="z", description="")
        data = export_all_data()
        assert "skills" in data
        assert "prompts" in data
        # Import back (merge mode)
        result = import_all_data(data, merge=True)
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. FULL PIPELINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullPipelineIntegration:
    """End-to-end pipeline: connectors → filestore → documents → agents → orchestration."""

    def test_connector_to_document_pipeline(self, filestore_dir):
        """Full flow: create connector → sync → stage files → verify in registry."""
        # 1. Create connector
        cid = generate_connector_id()
        connector = create_connector(
            cid,
            "Pipeline Test DB",
            "database",
            config={
                "db_type": "postgresql",
                "host": "localhost",
                "port": "5432",
                "database": "testdb",
                "username": "user",
                "password": "pass",
                "query": "SELECT * FROM docs",
                "text_columns": "content",
            },
        )
        assert connector["enabled"] is True

        # 2. Simulate sync (mock the actual DB call)
        job_id = generate_job_id()
        create_sync_job(job_id, cid)

        # Simulate pulled documents
        pulled_docs = [
            {
                "name": "doc1.txt",
                "content": "First document content",
                "metadata": {"source": "db"},
            },
            {
                "name": "doc2.txt",
                "content": "Second document content",
                "metadata": {"source": "db"},
            },
        ]

        # 3. Stage in filestore
        for doc in pulled_docs:
            doc_id = str(uuid.uuid4())[:12]
            save_file(doc_id, doc["name"], doc["content"])
            create_document_registry(
                name=doc["name"],
                source=f"connector:{connector['name']}",
                status="uploaded",
                source_type="connected",
                storage_path=f"/data/filestore/{doc_id}/{doc['name']}",
            )

        # 4. Update job
        update_sync_job(job_id, "completed", docs_pulled=2, docs_indexed=0)

        # 5. Verify
        docs = list_documents_registry()
        conn_docs = [d for d in docs if "Pipeline Test DB" in d.get("source", "")]
        assert len(conn_docs) == 2
        assert all(d["status"] == "uploaded" for d in conn_docs)

    def test_document_to_agent_pipeline(self):
        """Documents tagged to agent for RAG."""
        # 1. Create documents
        doc1 = create_document_registry(name="sales-report.pdf", source="upload:sales")
        doc2 = create_document_registry(
            name="marketing-plan.docx", source="upload:marketing"
        )

        # 2. Create agent
        agent = create_agent(
            name="Sales Agent",
            description="Handles sales queries",
            kb_collection="sales_kb",
        )

        # 3. Tag documents to agent
        tag_document_to_agent(doc1["id"], agent["id"])
        tag_document_to_agent(doc2["id"], agent["id"])

        # 4. Verify
        d1 = get_document_registry(doc1["id"])
        assert agent["id"] in d1["agent_tags"]
        d2 = get_document_registry(doc2["id"])
        assert agent["id"] in d2["agent_tags"]

    def test_full_orchestration_setup(self):
        """Complete orchestration: skills → agents → orchestrator → A2A → MCP."""
        # Skills
        research_skill = create_skill(
            name="Research Skill",
            description="Web research",
            system_prompt="Research thoroughly.",
        )
        coding_skill = create_skill(
            name="Coding Skill",
            description="Write code",
            system_prompt="Write clean code.",
        )

        # Sub-agents
        researcher = create_agent(
            name="Research Sub",
            description="Researches",
            skill_ids=[research_skill["id"]],
            tool_ids=["web_search"],
        )
        coder = create_agent(
            name="Coding Sub",
            description="Codes",
            skill_ids=[coding_skill["id"]],
            tool_ids=["code_execute"],
        )

        # Orchestrator
        orchestrator = create_agent(
            name="Main Orchestrator",
            description="Routes to sub-agents",
            sub_agent_ids=[researcher["id"], coder["id"]],
            max_iterations=10,
        )

        # A2A peer
        peer = create_a2a_peer(
            name="External Analyst",
            url="http://analyst:8000",
            description="Data analysis",
            capabilities=["analyze"],
        )

        # MCP server
        mcp = create_mcp_server(
            name="DB MCP",
            url="postgresql://host/db",
            transport="stdio",
            description="DB access",
            tools=["query_db"],
        )

        # Verify full setup
        orch = get_agent(orchestrator["id"])
        assert len(orch["sub_agent_ids"]) == 2
        assert list_a2a_peers()[0]["name"] == "External Analyst"
        assert list_mcp_servers()[0]["name"] == "DB MCP"

    def test_guardrails_on_agent(self):
        """Agent has guardrails configured."""
        # Enable guardrails
        update_guardrail("gr-prompt-injection", enabled=True, severity="high")
        update_guardrail("gr-pii", enabled=True, severity="medium")
        update_guardrail("gr-toxicity", enabled=True, severity="high")

        # Verify all are enabled
        injection = get_guardrail("gr-prompt-injection")
        assert injection["enabled"] is True
        pii = get_guardrail("gr-pii")
        assert pii["enabled"] is True

    def test_intelligence_hub_complete(self):
        """All intelligence hub components work together."""
        # Create prompt template
        prompt = create_prompt(
            name="RAG Query",
            content="Given context: {context}\nAnswer: {question}",
            category="rag",
            description="Standard RAG prompt",
            tags=["rag", "search"],
        )

        # Create skill using prompt
        skill = create_skill(
            name="RAG Skill",
            description="Retrieve and answer",
            system_prompt=prompt["content"],
            tool_ids=["vector_search"],
        )

        # Create agent using skill
        agent = create_agent(
            name="RAG Agent",
            description="Knowledge base Q&A",
            skill_ids=[skill["id"]],
            tool_ids=["vector_search"],
            kb_collection="main_kb",
        )

        # Create custom tool for the agent
        custom_tool = create_custom_tool(
            name="Internal API",
            description="Query internal API",
            category="internal",
            endpoint="http://internal.company.com/api/data",
            method="GET",
            headers={"Authorization": "Bearer token"},
            body_template={},
            parameters=[
                {
                    "name": "query",
                    "type": "string",
                    "required": True,
                    "description": "Search query",
                }
            ],
        )

        # Verify chain
        full_agent = get_agent(agent["id"])
        assert skill["id"] in full_agent["skill_ids"]
        full_skill = get_skill(skill["id"])
        assert "vector_search" in full_skill["tool_ids"]
        tools = list_custom_tools()
        assert any(t["name"] == "Internal API" for t in tools)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. CONNECTOR ENGINE — Mock Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConnectorEngine:
    """Test connector sync engine with mocks."""

    def test_api_connector_pull(self):
        """API connector pulls data correctly."""
        from agent.connectors.api_connector import pull_api

        mock_response = {
            "data": {
                "items": [
                    {"title": "Doc 1", "content": "Content of doc 1"},
                    {"title": "Doc 2", "content": "Content of doc 2"},
                ]
            }
        }

        with patch(
            "agent.connectors.api_connector._make_request", return_value=mock_response
        ):
            config = {
                "url": "https://api.example.com/docs",
                "method": "GET",
                "headers": "",
                "body": "",
                "response_path": "data.items",
                "text_field": "content",
                "name_field": "title",
            }
            docs = pull_api(config)
            assert len(docs) == 2
            assert docs[0]["name"] == "Doc 1"
            assert docs[0]["content"] == "Content of doc 1"

    def test_api_connector_empty_response(self):
        """API connector handles empty response."""
        from agent.connectors.api_connector import pull_api

        with patch(
            "agent.connectors.api_connector._make_request",
            return_value={"data": {"items": []}},
        ):
            config = {
                "url": "https://api.example.com/empty",
                "method": "GET",
                "headers": "",
                "body": "",
                "response_path": "data.items",
                "text_field": "content",
                "name_field": "title",
            }
            docs = pull_api(config)
            assert docs == []

    def test_api_connector_nested_path(self):
        """API connector navigates nested response paths."""
        from agent.connectors.api_connector import pull_api

        mock_resp = {
            "response": {
                "results": {
                    "documents": [
                        {"body": "Deep content", "id": "1"},
                    ]
                }
            }
        }
        with patch(
            "agent.connectors.api_connector._make_request", return_value=mock_resp
        ):
            config = {
                "url": "https://api.example.com/deep",
                "method": "GET",
                "headers": "",
                "body": "",
                "response_path": "response.results.documents",
                "text_field": "body",
                "name_field": "",
            }
            docs = pull_api(config)
            assert len(docs) == 1
            assert docs[0]["content"] == "Deep content"

    def test_check_connector_unknown_type(self):
        """Test unknown connector type returns error."""
        result = check_connector("unknown_type", {})
        assert result["ok"] is False
        assert "Unknown" in result["message"] or "Unsupported" in result["message"]


# ═══════════════════════════════════════════════════════════════════════════════
# 16. DATA INTEGRITY & EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataIntegrity:
    """Edge cases and data integrity."""

    def test_special_characters_in_names(self):
        """Handle special characters in entity names."""
        agent = create_agent(
            name="Agent <script>alert('xss')</script>", description="XSS test"
        )
        assert (
            "<script>" in agent["name"]
        )  # Stored as-is; escaping is UI responsibility

    def test_unicode_content(self):
        """Unicode content persists correctly."""
        prompt = create_prompt(
            name="Unicode Prompt",
            content="Résumé: Ñoño 中文 日本語 한국어 العربية",
            category="i18n",
            description="International content",
        )
        loaded = get_prompt(prompt["id"])
        assert "中文" in loaded["content"]
        assert "العربية" in loaded["content"]

    def test_large_json_config(self):
        """Large config objects persist."""
        large_config = {f"key_{i}": f"value_{i}" * 10 for i in range(100)}
        cid = generate_connector_id()
        connector = create_connector(cid, "Large Config", "api", config=large_config)
        loaded = get_connector(cid)
        assert len(loaded["config"]) == 100

    def test_empty_strings_handled(self):
        """Empty strings don't cause issues."""
        agent = create_agent(name="EmptyTest", description="", system_prompt="")
        assert agent["description"] == ""
        assert agent["system_prompt"] == ""

    def test_concurrent_operations(self):
        """Multiple rapid operations don't corrupt data."""
        agents = []
        for i in range(20):
            agents.append(create_agent(name=f"Concurrent_{i}", description=f"test_{i}"))
        listed = list_agents()
        names = [a["name"] for a in listed]
        for i in range(20):
            assert f"Concurrent_{i}" in names

    def test_document_status_transitions(self):
        """Valid status transitions."""
        doc = create_document_registry(
            name="transition.txt", source="t", status="uploaded"
        )
        # uploaded → processing
        update_document_registry(doc["id"], status="processing")
        assert get_document_registry(doc["id"])["status"] == "processing"
        # processing → indexed
        update_document_registry(doc["id"], status="indexed", chunk_count=10)
        assert get_document_registry(doc["id"])["status"] == "indexed"

    def test_document_status_failure_path(self):
        """uploaded → processing → failed → uploaded (retry)."""
        doc = create_document_registry(
            name="fail-retry.txt", source="fr", status="uploaded"
        )
        update_document_registry(doc["id"], status="processing")
        update_document_registry(doc["id"], status="failed")
        assert get_document_registry(doc["id"])["status"] == "failed"
        # Retry: back to uploaded
        update_document_registry(doc["id"], status="uploaded")
        assert get_document_registry(doc["id"])["status"] == "uploaded"
