"""
Integration tests — require a running docker compose stack.
Run with:  pytest tests/integration/ -v --timeout=60
"""

import os

import httpx
import pytest

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8010")
TOOLS_URL = os.getenv("TOOLS_URL", "http://localhost:8011")
CONSOLE_URL = os.getenv("CONSOLE_URL", "http://localhost:3000")
LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://localhost:3002")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3003")


@pytest.fixture
def http():
    return httpx.Client(timeout=30.0)


# ── Service health ─────────────────────────────────────────────────────────


def test_agent_health(http):
    r = http.get(f"{AGENT_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_tools_health(http):
    r = http.get(f"{TOOLS_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_console_health(http):
    r = http.get(f"{CONSOLE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_langfuse_health(http):
    r = http.get(f"{LANGFUSE_URL}/api/public/health")
    assert r.status_code == 200


def test_grafana_health(http):
    r = http.get(f"{GRAFANA_URL}/api/health")
    assert r.status_code == 200


# ── Cross-service flows ───────────────────────────────────────────────────


def test_tools_math(http):
    r = http.post(f"{TOOLS_URL}/tools/math", json={"expression": "7 * 6"})
    assert r.status_code == 200
    assert r.json()["result"] == 42


def test_tools_datetime(http):
    r = http.post(f"{TOOLS_URL}/tools/datetime")
    assert r.status_code == 200
    assert "utc" in r.json()


def test_agent_run(http):
    """Full agent round-trip through Ollama."""
    r = http.post(
        f"{AGENT_URL}/run",
        json={"prompt": "What is 2 + 2?", "sessionId": "integration-test"},
        timeout=120.0,
    )
    assert r.status_code == 200
    body = r.json()
    assert "response" in body
    assert body["sessionId"] == "integration-test"


def test_agent_sessions(http):
    r = http.get(f"{AGENT_URL}/sessions")
    assert r.status_code == 200
    assert "sessions" in r.json()


def test_console_overview(http):
    r = http.get(f"{CONSOLE_URL}/", follow_redirects=False)
    # Auth-protected: unauthenticated requests redirect to login
    assert r.status_code in (200, 302)


def test_console_health_check_api(http):
    r = http.get(f"{CONSOLE_URL}/api/health-check")
    # Auth-protected: unauthenticated requests return 401
    assert r.status_code in (200, 401)


def test_console_marketplace_templates(http):
    r = http.get(f"{CONSOLE_URL}/api/marketplace/templates")
    # Auth-protected: unauthenticated requests return 401
    assert r.status_code in (200, 401)


# ── New endpoints ──────────────────────────────────────────────────────────


def test_agent_tools_list(http):
    r = http.get(f"{AGENT_URL}/tools")
    assert r.status_code == 200
    body = r.json()
    assert "tools" in body
    tool_names = [t["name"] for t in body["tools"]]
    assert "math" in tool_names


def test_agent_models(http):
    r = http.get(f"{AGENT_URL}/models")
    assert r.status_code == 200
    body = r.json()
    assert "active" in body


def test_agent_documents_stats(http):
    r = http.get(f"{AGENT_URL}/documents/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_chunks" in body


def test_agent_documents_list(http):
    r = http.get(f"{AGENT_URL}/documents")
    assert r.status_code == 200
    body = r.json()
    assert "documents" in body


def test_document_ingest_search_delete(http):
    """Full RAG pipeline: ingest → search → delete."""
    # Ingest
    r = http.post(
        f"{AGENT_URL}/documents/ingest",
        json={
            "text": "The quick brown fox jumps over the lazy dog. This is a test document for integration testing.",
            "source": "integration-test.txt",
        },
    )
    assert r.status_code == 200
    assert "chunks" in r.json()

    # Search
    r = http.post(
        f"{AGENT_URL}/documents/search",
        json={
            "query": "quick brown fox",
            "k": 3,
        },
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) > 0

    # Delete
    r = http.delete(f"{AGENT_URL}/documents/integration-test.txt")
    assert r.status_code == 200


def test_tools_web_search(http):
    """DuckDuckGo web search endpoint."""
    r = http.post(
        f"{TOOLS_URL}/tools/web-search",
        json={
            "query": "python programming language",
            "max_results": 2,
        },
    )
    assert r.status_code == 200
    assert "results" in r.json()


def test_tools_code_execute(http):
    r = http.post(f"{TOOLS_URL}/tools/code-execute", json={"code": "print(1+1)"})
    assert r.status_code == 200
    body = r.json()
    assert body["exit_code"] == 0
    assert "2" in body["stdout"]


def test_console_documents_page(http):
    r = http.get(f"{CONSOLE_URL}/documents", follow_redirects=False)
    assert r.status_code in (200, 302)


def test_console_api_models(http):
    r = http.get(f"{CONSOLE_URL}/api/models")
    assert r.status_code in (200, 401)


def test_console_api_tools(http):
    r = http.get(f"{CONSOLE_URL}/api/tools")
    assert r.status_code in (200, 401)


def test_console_api_documents_stats(http):
    r = http.get(f"{CONSOLE_URL}/api/documents/stats")
    assert r.status_code in (200, 401)


def test_console_api_n8n_workflows(http):
    r = http.get(f"{CONSOLE_URL}/api/n8n/workflows")
    assert r.status_code in (200, 401)


def test_agent_metrics(http):
    r = http.get(f"{AGENT_URL}/metrics")
    assert r.status_code == 200
    assert "agent_run" in r.text or "http" in r.text


def test_tools_metrics(http):
    r = http.get(f"{TOOLS_URL}/metrics")
    assert r.status_code == 200
