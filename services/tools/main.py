"""
Tools Service — lightweight FastAPI endpoints that the agent can call.

Endpoints:
  GET  /health
  POST /tools/math
  POST /tools/http-fetch
  POST /tools/file-write
  POST /tools/file-read
  POST /tools/datetime
"""
import ast
import operator
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("tools-service")

app = FastAPI(title="Tools Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Observability ───────────────────────────────────────────────────────────

def _setup_otel(app):
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if otel_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            resource = Resource.create({"service.name": "tools-service"})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=f"{otel_endpoint}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            FastAPIInstrumentor.instrument_app(app)
            logger.info("OTel tracing enabled → %s", otel_endpoint)
        except Exception as e:
            logger.warning("OTel setup failed: %s", e)
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
        logger.info("Prometheus /metrics enabled")
    except Exception as e:
        logger.warning("Prometheus instrumentator failed: %s", e)

_setup_otel(app)

NOTES_DIR = Path(os.getenv("NOTES_DIR", "/data/notes"))
NOTES_DIR.mkdir(parents=True, exist_ok=True)

# Allowed domains for http-fetch (prevent SSRF)
ALLOWED_DOMAINS = {"httpbin.org", "jsonplaceholder.typicode.com"}


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "tools-service"}


# ── Math ────────────────────────────────────────────────────────────────────

class MathRequest(BaseModel):
    expression: str = Field(..., max_length=200)


# Safe operators for AST-based math evaluation
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    """Recursively evaluate an AST node using only safe arithmetic ops."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        # Guard against huge exponents
        if op_type is ast.Pow and isinstance(right, (int, float)) and abs(right) > 1000:
            raise ValueError("Exponent too large")
        return _SAFE_OPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _SAFE_OPS[op_type](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


@app.post("/tools/math")
async def tool_math(body: MathRequest):
    logger.info("math expression=%s", body.expression)
    try:
        tree = ast.parse(body.expression, mode="eval")
        result = _safe_eval(tree)
        return {"result": result, "expression": body.expression}
    except (ValueError, TypeError, SyntaxError, ZeroDivisionError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {exc}")


# ── HTTP Fetch ──────────────────────────────────────────────────────────────

class HttpFetchRequest(BaseModel):
    url: str = Field(..., max_length=2048)


def _is_allowed_url(url: str) -> bool:
    """Check URL is in the allowlist to prevent SSRF."""
    # Extract hostname
    match = re.match(r"https?://([^/:]+)", url)
    if not match:
        return False
    hostname = match.group(1).lower()
    return hostname in ALLOWED_DOMAINS


@app.post("/tools/http-fetch")
async def tool_http_fetch(body: HttpFetchRequest):
    logger.info("http-fetch url=%s", body.url)
    if not _is_allowed_url(body.url):
        raise HTTPException(
            status_code=403,
            detail=f"Domain not allowed. Allowed: {', '.join(sorted(ALLOWED_DOMAINS))}",
        )
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(body.url)
            resp.raise_for_status()
            text = resp.text[:5000]  # truncate for safety
            return {"url": body.url, "status": resp.status_code, "content": text}
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {exc}")


# ── File Write ──────────────────────────────────────────────────────────────

class FileWriteRequest(BaseModel):
    filename: str = Field(..., max_length=255)
    content: str = Field(..., max_length=10000)


def _safe_filename(name: str) -> str:
    """Sanitise filename — strip path separators and dangerous chars."""
    name = Path(name).name  # strip any directory components
    name = re.sub(r'[^\w\-. ]', '_', name)  # only allow safe chars
    if not name or name.startswith('.'):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


@app.post("/tools/file-write")
async def tool_file_write(body: FileWriteRequest):
    safe = _safe_filename(body.filename)
    filepath = NOTES_DIR / safe
    logger.info("file-write file=%s bytes=%d", safe, len(body.content))
    filepath.write_text(body.content, encoding="utf-8")
    return {"status": "written", "filename": safe, "bytes": len(body.content)}


# ── File Read ───────────────────────────────────────────────────────────────

class FileReadRequest(BaseModel):
    filename: str = Field(..., max_length=255)


@app.post("/tools/file-read")
async def tool_file_read(body: FileReadRequest):
    safe = _safe_filename(body.filename)
    filepath = NOTES_DIR / safe
    logger.info("file-read file=%s", safe)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {safe}")
    content = filepath.read_text(encoding="utf-8")
    return {"filename": safe, "content": content}


# ── DateTime ────────────────────────────────────────────────────────────────

@app.post("/tools/datetime")
async def tool_datetime():
    now = datetime.now(timezone.utc)
    return {
        "utc": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "timezone": "UTC",
    }


# ── Web Search (DuckDuckGo) ────────────────────────────────────────────────

class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)


@app.post("/tools/web-search")
async def tool_web_search(body: WebSearchRequest):
    logger.info("web-search query=%s max=%d", body.query, body.max_results)
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(body.query, max_results=body.max_results))
        return {
            "query": body.query,
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in results
            ],
            "count": len(results),
        }
    except Exception as e:
        logger.error("web-search failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


# ── Code Execution (sandboxed) ─────────────────────────────────────────────

class CodeExecuteRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10000)
    language: str = Field(default="python", pattern="^python$")
    timeout: int = Field(default=10, ge=1, le=30)


@app.post("/tools/code-execute")
async def tool_code_execute(body: CodeExecuteRequest):
    import subprocess
    import tempfile

    logger.info("code-execute lang=%s bytes=%d", body.language, len(body.code))

    # Security: block dangerous imports/operations
    BLOCKED_PATTERNS = [
        "import os", "import sys", "import subprocess", "import shutil",
        "__import__", "eval(", "exec(", "open(", "compile(",
        "import socket", "import http", "import urllib",
        "os.system", "os.popen", "os.exec",
    ]
    code_lower = body.code.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in code_lower:
            return {
                "stdout": "",
                "stderr": f"Blocked: '{pattern}' is not allowed in sandboxed execution",
                "exit_code": 1,
                "language": body.language,
            }

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir="/tmp"
        ) as f:
            f.write(body.code)
            f.flush()
            tmp_path = f.name

        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=body.timeout,
            cwd="/tmp",
        )

        # Clean up
        import os as _os
        _os.unlink(tmp_path)

        return {
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000],
            "exit_code": result.returncode,
            "language": body.language,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {body.timeout}s",
            "exit_code": 124,
            "language": body.language,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": 1,
            "language": body.language,
        }


# ── Vector Search (proxy to ChromaDB via agent-service) ────────────────────

class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=50)


@app.post("/tools/vector-search")
async def tool_vector_search(body: VectorSearchRequest):
    logger.info("vector-search query=%s k=%d", body.query[:80], body.k)
    agent_url = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8000")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{agent_url}/documents/search",
                json={"query": body.query, "k": body.k},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"query": body.query, "results": [], "error": str(e)}


class VectorStoreRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    source: str = Field(..., min_length=1, max_length=500)
    metadata: dict = Field(default_factory=dict)


@app.post("/tools/vector-store")
async def tool_vector_store(body: VectorStoreRequest):
    logger.info("vector-store source=%s bytes=%d", body.source, len(body.text))
    agent_url = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8000")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{agent_url}/documents/ingest",
                json={"text": body.text, "source": body.source, "metadata": body.metadata},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"source": body.source, "error": str(e)}
