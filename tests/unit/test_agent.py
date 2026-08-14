"""Unit tests for Agent Service — graph logic, parsing, endpoints."""

import os
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

# Patch out observability before importing anything
import agent.observability as _obs_mod

_mock_trace = MagicMock()
_mock_trace.trace_id = "test-trace-id"
_obs_mod.LangfuseTrace = MagicMock(return_value=_mock_trace)
_obs_mod.track_llm_call = MagicMock(
    return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
)

from agent.graph import _parse_tool_calls, should_continue, build_graph
from agent.tools import TOOL_CATALOGUE, _refresh_catalogue
from main import app


@pytest.fixture(autouse=True)
def _setup_env(tmp_path, monkeypatch):
    """Use temp dirs so SQLite and filestore work on any OS."""
    db_dir = str(tmp_path / "data")
    fs_dir = str(tmp_path / "filestore")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(fs_dir, exist_ok=True)
    monkeypatch.setenv("MEMORY_DIR", db_dir)
    monkeypatch.setenv("FILESTORE_DIR", fs_dir)
    # Re-initialise DB for this test
    import agent.memory as _mem

    _mem._local = __import__("threading").local()  # reset thread-local conn
    _mem.MEMORY_DIR = db_dir
    _mem.DB_PATH = os.path.join(db_dir, "platform.db")
    _mem.init_db()


@pytest.fixture(autouse=True)
def _populate_catalogue():
    """Ensure TOOL_CATALOGUE is populated so _parse_tool_calls works."""
    _refresh_catalogue()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Health ─────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "agent-service"


# ── Tool-call parsing ─────────────────────────────────────────────────────


def test_parse_single_tool_call():
    text = '{"tool": "math", "arguments": {"expression": "2+2"}}'
    calls = _parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "math"
    assert calls[0]["arguments"]["expression"] == "2+2"


def test_parse_tool_call_with_markdown():
    text = '```json\n{"tool": "math", "arguments": {"expression": "5*3"}}\n```'
    calls = _parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "math"


def test_parse_no_tool_call():
    text = "I'll help you with that. The answer is 42."
    calls = _parse_tool_calls(text)
    assert len(calls) == 0


def test_parse_unknown_tool_ignored():
    text = '{"tool": "nope_fake", "arguments": {}}'
    calls = _parse_tool_calls(text)
    assert len(calls) == 0


def test_parse_datetime_tool():
    text = '{"tool": "datetime_tool", "arguments": {}}'
    calls = _parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "datetime_tool"


def test_parse_tool_call_embedded_in_text():
    text = 'I need to calculate that. {"tool": "math", "arguments": {"expression": "100/4"}} Let me check.'
    calls = _parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "math"


def test_parse_web_search_tool():
    text = '{"tool": "web_search", "arguments": {"query": "python tutorials"}}'
    calls = _parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "web_search"


def test_parse_vector_search_tool():
    text = '{"tool": "vector_search", "arguments": {"query": "company policy"}}'
    calls = _parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "vector_search"


# ── Graph routing ──────────────────────────────────────────────────────────


def test_should_continue_with_pending_tools():
    state = {
        "tool_calls": [{"name": "math", "arguments": {}, "result": None}],
        "iteration": 0,
    }
    assert should_continue(state) == "execute_tools"


def test_should_continue_no_pending():
    state = {"tool_calls": [], "iteration": 0}
    assert should_continue(state) == "generate_response"


def test_should_continue_max_iterations():
    state = {"tool_calls": [], "iteration": 5}
    assert should_continue(state) == "generate_response"


def test_should_continue_empty():
    state = {}
    assert should_continue(state) == "generate_response"


# ── Graph structure ────────────────────────────────────────────────────────


def test_graph_builds():
    g = build_graph()
    assert g is not None


# ── Session endpoints ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_sessions_list(client):
    r = await client.get("/sessions")
    assert r.status_code == 200
    assert "sessions" in r.json()


@pytest.mark.anyio
async def test_session_history_empty(client):
    r = await client.get("/sessions/nonexistent-session/history")
    assert r.status_code == 200
    assert r.json()["messages"] == []


@pytest.mark.anyio
async def test_session_delete(client):
    r = await client.delete("/sessions/nonexistent-session")
    assert r.status_code == 200
    assert r.json()["deleted_messages"] == 0


# ── /run endpoint (mocked Ollama) ──────────────────────────────────────────


@pytest.mark.anyio
async def test_run_no_tools(client):
    """Ollama returns plain text → no tools, plain response."""
    with patch("agent.graph._ollama_chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "The answer is 42."
        r = await client.post("/run", json={"prompt": "What is 42?"})
        assert r.status_code == 200
        body = r.json()
        assert "42" in body["response"]
        assert body["tools_used"] == []


@pytest.mark.anyio
async def test_run_empty_prompt_rejected(client):
    r = await client.post("/run", json={"prompt": ""})
    assert r.status_code == 422  # validation error


@pytest.mark.anyio
async def test_run_prompt_too_long(client):
    r = await client.post("/run", json={"prompt": "x" * 5000})
    assert r.status_code == 422


# ── New endpoints ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_tools_list(client):
    r = await client.get("/tools")
    assert r.status_code == 200
    body = r.json()
    assert "tools" in body
    tool_names = [t["name"] for t in body["tools"]]
    assert "math" in tool_names
    assert "web_search" in tool_names
    assert "vector_search" in tool_names
    assert "code_execute" in tool_names


@pytest.mark.anyio
async def test_models_list(client):
    """Models endpoint should return gracefully even if Ollama is down."""
    r = await client.get("/models")
    assert r.status_code == 200
    body = r.json()
    assert "active" in body or "current_model" in body
