"""Unit tests for Tools Service endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_math_addition(client):
    r = await client.post("/tools/math", json={"expression": "2 + 3"})
    assert r.status_code == 200
    assert r.json()["result"] == 5


@pytest.mark.anyio
async def test_math_complex(client):
    r = await client.post("/tools/math", json={"expression": "10 * (3 + 2)"})
    assert r.status_code == 200
    assert r.json()["result"] == 50


@pytest.mark.anyio
async def test_math_division(client):
    r = await client.post("/tools/math", json={"expression": "100 / 4"})
    assert r.status_code == 200
    assert r.json()["result"] == 25.0


@pytest.mark.anyio
async def test_math_invalid_expression(client):
    r = await client.post("/tools/math", json={"expression": "import os"})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_math_division_by_zero(client):
    r = await client.post("/tools/math", json={"expression": "1 / 0"})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_math_large_exponent(client):
    r = await client.post("/tools/math", json={"expression": "2 ** 10000"})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_http_fetch_blocked_domain(client):
    r = await client.post("/tools/http-fetch", json={"url": "http://evil.com/steal"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_http_fetch_no_scheme(client):
    r = await client.post("/tools/http-fetch", json={"url": "not-a-url"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_file_write_read(client, tmp_path, monkeypatch):
    monkeypatch.setattr("main.NOTES_DIR", tmp_path)
    w = await client.post(
        "/tools/file-write",
        json={"filename": "hello.txt", "content": "Hello World"},
    )
    assert w.status_code == 200
    assert w.json()["status"] == "written"

    r = await client.post("/tools/file-read", json={"filename": "hello.txt"})
    assert r.status_code == 200
    assert r.json()["content"] == "Hello World"


@pytest.mark.anyio
async def test_file_read_not_found(client, tmp_path, monkeypatch):
    monkeypatch.setattr("main.NOTES_DIR", tmp_path)
    r = await client.post("/tools/file-read", json={"filename": "nope.txt"})
    assert r.status_code == 404


@pytest.mark.anyio
async def test_file_write_path_traversal(client, tmp_path, monkeypatch):
    monkeypatch.setattr("main.NOTES_DIR", tmp_path)
    r = await client.post(
        "/tools/file-write",
        json={"filename": "../../../etc/passwd", "content": "bad"},
    )
    assert r.status_code == 200
    # filename should be sanitized to just 'passwd'
    assert r.json()["filename"] == "passwd"


@pytest.mark.anyio
async def test_file_write_dot_file_rejected(client, tmp_path, monkeypatch):
    monkeypatch.setattr("main.NOTES_DIR", tmp_path)
    r = await client.post(
        "/tools/file-write",
        json={"filename": ".hidden", "content": "secret"},
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_datetime(client):
    r = await client.post("/tools/datetime")
    assert r.status_code == 200
    body = r.json()
    assert "utc" in body
    assert "date" in body
    assert body["timezone"] == "UTC"


# ── Web Search ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_web_search_missing_query(client):
    r = await client.post("/tools/web-search", json={})
    assert r.status_code == 422  # pydantic validation


@pytest.mark.anyio
async def test_web_search_with_mock(client):
    """Mock DuckDuckGo to avoid real network calls."""
    mock_results = [
        {"title": "Python.org", "href": "https://python.org", "body": "Welcome to Python"},
        {"title": "Docs", "href": "https://docs.python.org", "body": "Python docs"},
    ]
    with patch("main.DDGS") as MockDDGS:
        instance = MagicMock()
        instance.text.return_value = mock_results
        MockDDGS.return_value.__enter__ = MagicMock(return_value=instance)
        MockDDGS.return_value.__exit__ = MagicMock(return_value=False)
        r = await client.post("/tools/web-search", json={"query": "python", "max_results": 2})
        assert r.status_code == 200
        body = r.json()
        assert "results" in body
        assert len(body["results"]) == 2


# ── Code Execute ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_code_execute_simple(client):
    r = await client.post("/tools/code-execute", json={"code": "print(2+2)"})
    assert r.status_code == 200
    body = r.json()
    assert "4" in body["stdout"]
    assert body["exit_code"] == 0


@pytest.mark.anyio
async def test_code_execute_blocked_import(client):
    r = await client.post("/tools/code-execute", json={"code": "import os; os.system('ls')"})
    assert r.status_code == 400
    assert "blocked" in r.json()["detail"].lower() or "security" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_code_execute_blocked_subprocess(client):
    r = await client.post("/tools/code-execute", json={"code": "import subprocess"})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_code_execute_syntax_error(client):
    r = await client.post("/tools/code-execute", json={"code": "def foo(:"})
    assert r.status_code == 200
    body = r.json()
    assert body["exit_code"] != 0
