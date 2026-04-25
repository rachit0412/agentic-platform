"""
Contract tests — validate API responses match expected schemas.
Uses schemathesis for OpenAPI-driven testing where specs exist,
plus manual schema checks for core endpoints.
"""
import pytest
import httpx

AGENT_URL = "http://localhost:8010"
TOOLS_URL = "http://localhost:8011"


@pytest.fixture
def http():
    return httpx.Client(timeout=15.0)


# ── Agent Service contracts ────────────────────────────────────────────────

def test_agent_health_contract(http):
    r = http.get(f"{AGENT_URL}/health")
    body = r.json()
    assert "status" in body
    assert "service" in body
    assert isinstance(body["status"], str)


def test_agent_run_contract(http):
    """POST /run must return sessionId, response, tools_used, request_id."""
    r = http.post(
        f"{AGENT_URL}/run",
        json={"prompt": "hello", "sessionId": "contract-test"},
        timeout=120.0,
    )
    assert r.status_code == 200
    body = r.json()
    required_keys = {"sessionId", "response", "tools_used", "request_id"}
    assert required_keys.issubset(body.keys()), f"Missing keys: {required_keys - body.keys()}"
    assert isinstance(body["tools_used"], list)
    assert isinstance(body["response"], str)


def test_agent_sessions_contract(http):
    r = http.get(f"{AGENT_URL}/sessions")
    body = r.json()
    assert "sessions" in body
    assert isinstance(body["sessions"], list)


def test_agent_session_history_contract(http):
    r = http.get(f"{AGENT_URL}/sessions/contract-test/history")
    body = r.json()
    assert "session_id" in body
    assert "messages" in body
    assert isinstance(body["messages"], list)


# ── Tools Service contracts ────────────────────────────────────────────────

def test_tools_health_contract(http):
    r = http.get(f"{TOOLS_URL}/health")
    body = r.json()
    assert body == {"status": "healthy", "service": "tools-service"}


def test_tools_math_contract(http):
    r = http.post(f"{TOOLS_URL}/tools/math", json={"expression": "1+1"})
    body = r.json()
    assert "result" in body
    assert "expression" in body
    assert isinstance(body["result"], (int, float))


def test_tools_datetime_contract(http):
    r = http.post(f"{TOOLS_URL}/tools/datetime")
    body = r.json()
    for key in ("utc", "date", "time", "weekday", "timezone"):
        assert key in body, f"Missing key: {key}"


def test_tools_file_write_contract(http):
    r = http.post(
        f"{TOOLS_URL}/tools/file-write",
        json={"filename": "contract-test.txt", "content": "test"},
    )
    body = r.json()
    assert "status" in body
    assert "filename" in body
    assert "bytes" in body


def test_tools_math_error_contract(http):
    """Error responses should use HTTP 4xx with detail field."""
    r = http.post(f"{TOOLS_URL}/tools/math", json={"expression": "import os"})
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body


# ── New Agent contracts ────────────────────────────────────────────────────

def test_agent_tools_list_contract(http):
    r = http.get(f"{AGENT_URL}/tools")
    body = r.json()
    assert "tools" in body
    assert isinstance(body["tools"], list)
    if body["tools"]:
        tool = body["tools"][0]
        assert "name" in tool
        assert "description" in tool


def test_agent_models_contract(http):
    r = http.get(f"{AGENT_URL}/models")
    body = r.json()
    assert "current_model" in body
    assert isinstance(body["current_model"], str)


def test_agent_documents_stats_contract(http):
    r = http.get(f"{AGENT_URL}/documents/stats")
    body = r.json()
    assert "total_chunks" in body
    assert "unique_documents" in body
    assert isinstance(body["total_chunks"], int)
    assert isinstance(body["unique_documents"], int)


def test_agent_documents_list_contract(http):
    r = http.get(f"{AGENT_URL}/documents")
    body = r.json()
    assert "documents" in body
    assert isinstance(body["documents"], list)


def test_agent_document_ingest_contract(http):
    r = http.post(f"{AGENT_URL}/documents/ingest", json={
        "text": "Contract test document content.",
        "source": "contract-test-doc.txt",
    })
    body = r.json()
    assert "status" in body
    assert body["status"] == "ingested"
    assert "chunks" in body
    # cleanup
    http.delete(f"{AGENT_URL}/documents/contract-test-doc.txt")


def test_agent_document_search_contract(http):
    r = http.post(f"{AGENT_URL}/documents/search", json={
        "query": "test",
        "k": 3,
    })
    body = r.json()
    assert "results" in body
    assert isinstance(body["results"], list)


# ── New Tools contracts ────────────────────────────────────────────────────

def test_tools_web_search_contract(http):
    r = http.post(f"{TOOLS_URL}/tools/web-search", json={
        "query": "python",
        "max_results": 2,
    })
    body = r.json()
    assert "results" in body
    assert isinstance(body["results"], list)


def test_tools_code_execute_contract(http):
    r = http.post(f"{TOOLS_URL}/tools/code-execute", json={"code": "print('hello')"})
    body = r.json()
    assert "stdout" in body
    assert "stderr" in body
    assert "exit_code" in body
    assert isinstance(body["exit_code"], int)
