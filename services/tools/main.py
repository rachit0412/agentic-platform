"""
Tools Service — lightweight FastAPI endpoints that the agent can call.

Endpoints:
  GET  /health
  POST /tools/math
  POST /tools/http-fetch
  POST /tools/file-write
  POST /tools/file-read
  POST /tools/file-list
  POST /tools/file-search-content
  POST /tools/datetime
  POST /tools/web-search
  POST /tools/code-execute
  POST /tools/vector-search
  POST /tools/vector-store
  POST /tools/text-summarize
  POST /tools/text-transform
  POST /tools/text-diff
  POST /tools/text-extract
  POST /tools/json-transform
  POST /tools/csv-parse
  POST /tools/yaml-convert
  POST /tools/base64-codec
  POST /tools/hash-generate
  POST /tools/uuid-generate
  POST /tools/regex-match
  POST /tools/url-parse
  POST /tools/html-strip
  POST /tools/markdown-to-html
  POST /tools/webpage-extract
  POST /tools/dns-lookup
  POST /tools/json-schema-validate
  POST /tools/cron-parse
  POST /tools/jwt-decode
  POST /tools/environment-info
"""

import ast
import base64
import csv
import difflib
import hashlib
import io
import json
import operator
import os
import re
import logging
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

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
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
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
    name = re.sub(r"[^\w\-. ]", "_", name)  # only allow safe chars
    if not name or name.startswith("."):
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
        from ddgs import DDGS

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
        "import os",
        "import sys",
        "import subprocess",
        "import shutil",
        "__import__",
        "eval(",
        "exec(",
        "open(",
        "compile(",
        "import socket",
        "import http",
        "import urllib",
        "os.system",
        "os.popen",
        "os.exec",
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
                json={
                    "text": body.text,
                    "source": body.source,
                    "metadata": body.metadata,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"source": body.source, "error": str(e)}


# ── File List ───────────────────────────────────────────────────────────────


class FileListRequest(BaseModel):
    directory: str = Field(default="", max_length=500)
    pattern: str = Field(default="*", max_length=100)


@app.post("/tools/file-list")
async def tool_file_list(body: FileListRequest):
    """List files in the notes directory, optionally filtered by glob pattern."""
    logger.info("file-list dir=%s pattern=%s", body.directory, body.pattern)
    # Only allow listing within NOTES_DIR
    base = NOTES_DIR
    if body.directory:
        safe_dir = Path(body.directory).name  # strip path traversal
        base = NOTES_DIR / safe_dir
        if not base.exists() or not str(base.resolve()).startswith(
            str(NOTES_DIR.resolve())
        ):
            return {"files": [], "error": "Directory not found or not allowed"}
    try:
        files = []
        for p in sorted(base.glob(body.pattern)):
            if p.is_file():
                stat = p.stat()
                files.append(
                    {
                        "name": p.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                    }
                )
            elif p.is_dir():
                files.append({"name": p.name + "/", "type": "directory"})
        return {
            "directory": str(base.relative_to(NOTES_DIR)) if base != NOTES_DIR else ".",
            "files": files,
            "count": len(files),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── File Search Content ────────────────────────────────────────────────────


class FileSearchContentRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    pattern: str = Field(default="*", max_length=100)
    max_results: int = Field(default=10, ge=1, le=50)


@app.post("/tools/file-search-content")
async def tool_file_search_content(body: FileSearchContentRequest):
    """Search for text content across all files in notes directory."""
    logger.info("file-search-content query=%s", body.query[:80])
    results = []
    query_lower = body.query.lower()
    for p in sorted(NOTES_DIR.glob(body.pattern)):
        if not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if query_lower in content.lower():
                # Find matching lines
                lines = content.splitlines()
                matches = []
                for i, line in enumerate(lines, 1):
                    if query_lower in line.lower():
                        matches.append({"line": i, "text": line.strip()[:200]})
                        if len(matches) >= 3:
                            break
                results.append({"file": p.name, "matches": matches})
                if len(results) >= body.max_results:
                    break
        except Exception:
            continue
    return {"query": body.query, "results": results, "count": len(results)}


# ── Text Summarize ──────────────────────────────────────────────────────────


class TextSummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    max_sentences: int = Field(default=3, ge=1, le=10)


@app.post("/tools/text-summarize")
async def tool_text_summarize(body: TextSummarizeRequest):
    """Extract the most important sentences from text (extractive summarization)."""
    logger.info(
        "text-summarize chars=%d sentences=%d", len(body.text), body.max_sentences
    )
    sentences = re.split(r"(?<=[.!?])\s+", body.text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    if not sentences:
        return {"summary": body.text[:500], "sentence_count": 0}

    # Score sentences by: position weight + word count + keyword frequency
    word_freq: dict[str, int] = {}
    for s in sentences:
        for w in re.findall(r"\b[a-zA-Z]{3,}\b", s.lower()):
            word_freq[w] = word_freq.get(w, 0) + 1

    # Remove very common words
    stopwords = {
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "are",
        "was",
        "were",
        "been",
        "have",
        "has",
        "had",
        "not",
        "but",
        "from",
        "they",
        "will",
        "can",
        "all",
        "would",
        "there",
        "their",
        "what",
        "about",
        "which",
        "when",
        "one",
        "your",
    }
    for sw in stopwords:
        word_freq.pop(sw, None)

    scored = []
    for i, s in enumerate(sentences):
        words = re.findall(r"\b[a-zA-Z]{3,}\b", s.lower())
        score = sum(word_freq.get(w, 0) for w in words) / (len(words) + 1)
        # Boost first/last sentences
        if i == 0:
            score *= 1.5
        elif i == len(sentences) - 1:
            score *= 1.2
        scored.append((score, i, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = sorted(scored[: body.max_sentences], key=lambda x: x[1])  # preserve order
    summary = " ".join(t[2] for t in top)
    return {
        "summary": summary,
        "sentence_count": len(top),
        "original_sentences": len(sentences),
    }


# ── Text Transform ──────────────────────────────────────────────────────────


class TextTransformRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    operation: str = Field(
        ...,
        pattern=r"^(uppercase|lowercase|title|capitalize|reverse|snake_case|camel_case|kebab_case|count_words|count_chars|count_lines|trim|deduplicate_lines|sort_lines|number_lines|remove_blank_lines)$",
    )


@app.post("/tools/text-transform")
async def tool_text_transform(body: TextTransformRequest):
    """Transform text with various string operations."""
    logger.info("text-transform op=%s chars=%d", body.operation, len(body.text))
    t = body.text
    op = body.operation
    if op == "uppercase":
        result = t.upper()
    elif op == "lowercase":
        result = t.lower()
    elif op == "title":
        result = t.title()
    elif op == "capitalize":
        result = t.capitalize()
    elif op == "reverse":
        result = t[::-1]
    elif op == "snake_case":
        result = (
            re.sub(r"[\s\-]+", "_", re.sub(r"([A-Z])", r"_\1", t)).strip("_").lower()
        )
    elif op == "camel_case":
        parts = re.split(r"[\s_\-]+", t)
        result = parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
    elif op == "kebab_case":
        result = (
            re.sub(r"[\s_]+", "-", re.sub(r"([A-Z])", r"-\1", t)).strip("-").lower()
        )
    elif op == "count_words":
        result = str(len(t.split()))
    elif op == "count_chars":
        result = str(len(t))
    elif op == "count_lines":
        result = str(len(t.splitlines()))
    elif op == "trim":
        result = "\n".join(line.strip() for line in t.splitlines())
    elif op == "deduplicate_lines":
        seen: set[str] = set()
        lines = []
        for line in t.splitlines():
            if line not in seen:
                seen.add(line)
                lines.append(line)
        result = "\n".join(lines)
    elif op == "sort_lines":
        result = "\n".join(sorted(t.splitlines()))
    elif op == "number_lines":
        result = "\n".join(f"{i+1}: {line}" for i, line in enumerate(t.splitlines()))
    elif op == "remove_blank_lines":
        result = "\n".join(line for line in t.splitlines() if line.strip())
    else:
        result = t
    return {"result": result, "operation": op}


# ── Text Diff ───────────────────────────────────────────────────────────────


class TextDiffRequest(BaseModel):
    text_a: str = Field(..., min_length=0, max_length=50000)
    text_b: str = Field(..., min_length=0, max_length=50000)
    context_lines: int = Field(default=3, ge=0, le=10)


@app.post("/tools/text-diff")
async def tool_text_diff(body: TextDiffRequest):
    """Generate a unified diff between two text strings."""
    logger.info("text-diff a=%d b=%d", len(body.text_a), len(body.text_b))
    lines_a = body.text_a.splitlines(keepends=True)
    lines_b = body.text_b.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            lines_a, lines_b, fromfile="text_a", tofile="text_b", n=body.context_lines
        )
    )
    additions = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    return {
        "diff": "".join(diff),
        "additions": additions,
        "deletions": deletions,
        "changed": len(diff) > 0,
    }


# ── Text Extract ────────────────────────────────────────────────────────────


class TextExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    extract_type: str = Field(
        ...,
        pattern=r"^(emails|urls|phone_numbers|ip_addresses|dates|numbers|hashtags|mentions)$",
    )


@app.post("/tools/text-extract")
async def tool_text_extract(body: TextExtractRequest):
    """Extract structured data (emails, URLs, dates, etc.) from text."""
    logger.info("text-extract type=%s chars=%d", body.extract_type, len(body.text))
    patterns = {
        "emails": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "urls": r'https?://[^\s<>"{}|\\^`\[\]]+',
        "phone_numbers": r"[\+]?[(]?[0-9]{1,4}[)]?[\s.\-]?[0-9]{1,4}[\s.\-]?[0-9]{1,9}",
        "ip_addresses": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "dates": r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        "numbers": r"-?\b\d+\.?\d*\b",
        "hashtags": r"#\w+",
        "mentions": r"@\w+",
    }
    pattern = patterns[body.extract_type]
    matches = list(set(re.findall(pattern, body.text)))
    return {"type": body.extract_type, "matches": matches[:100], "count": len(matches)}


# ── JSON Transform ─────────────────────────────────────────────────────────


class JsonTransformRequest(BaseModel):
    data: str = Field(..., min_length=1, max_length=100000)
    operation: str = Field(
        ...,
        pattern=r"^(prettify|minify|flatten|keys|values|sort_keys|validate|paths|filter_nulls|to_csv)$",
    )
    jq_path: str = Field(default="", max_length=500)


def _flatten_json(obj: Any, prefix: str = "") -> dict:
    items: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}.{k}" if prefix else k
            items.update(_flatten_json(v, new_key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            items.update(_flatten_json(v, f"{prefix}[{i}]"))
    else:
        items[prefix] = obj
    return items


def _get_json_paths(obj: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.append(p)
            paths.extend(_get_json_paths(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            paths.append(p)
            paths.extend(_get_json_paths(v, p))
    return paths


def _filter_nulls(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _filter_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_filter_nulls(v) for v in obj if v is not None]
    return obj


@app.post("/tools/json-transform")
async def tool_json_transform(body: JsonTransformRequest):
    """Transform JSON data: prettify, minify, flatten, extract keys, sort, validate, etc."""
    logger.info("json-transform op=%s", body.operation)
    try:
        data = json.loads(body.data)
    except json.JSONDecodeError as e:
        if body.operation == "validate":
            return {"valid": False, "error": str(e)}
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    op = body.operation
    if op == "validate":
        return {"valid": True, "type": type(data).__name__}
    elif op == "prettify":
        return {"result": json.dumps(data, indent=2, ensure_ascii=False)}
    elif op == "minify":
        return {"result": json.dumps(data, separators=(",", ":"), ensure_ascii=False)}
    elif op == "flatten":
        return {"result": _flatten_json(data)}
    elif op == "keys":
        if isinstance(data, dict):
            return {"keys": list(data.keys())}
        return {"keys": [], "note": "Input is not an object"}
    elif op == "values":
        if isinstance(data, dict):
            return {"values": [str(v)[:200] for v in data.values()]}
        return {"values": [], "note": "Input is not an object"}
    elif op == "sort_keys":
        return {
            "result": json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
        }
    elif op == "paths":
        return {"paths": _get_json_paths(data)}
    elif op == "filter_nulls":
        return {"result": _filter_nulls(data)}
    elif op == "to_csv":
        if isinstance(data, list) and data and isinstance(data[0], dict):
            headers = list(data[0].keys())
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, "") for k in headers})
            return {
                "csv": output.getvalue(),
                "rows": len(data),
                "columns": len(headers),
            }
        return {"error": "to_csv requires an array of objects"}
    return {"error": f"Unknown operation: {op}"}


# ── CSV Parse ───────────────────────────────────────────────────────────────


class CsvParseRequest(BaseModel):
    csv_text: str = Field(..., min_length=1, max_length=500000)
    operation: str = Field(
        default="to_json", pattern=r"^(to_json|stats|headers|preview|filter)$"
    )
    filter_column: str = Field(default="", max_length=200)
    filter_value: str = Field(default="", max_length=500)
    max_rows: int = Field(default=100, ge=1, le=1000)


@app.post("/tools/csv-parse")
async def tool_csv_parse(body: CsvParseRequest):
    """Parse CSV text and convert, analyze, or filter it."""
    logger.info("csv-parse op=%s chars=%d", body.operation, len(body.csv_text))
    try:
        reader = csv.DictReader(io.StringIO(body.csv_text))
        rows = []
        headers = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= body.max_rows:
                break
            rows.append(dict(row))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")

    if body.operation == "headers":
        return {"headers": list(headers), "count": len(headers)}
    elif body.operation == "preview":
        return {"headers": list(headers), "rows": rows[:10], "total_rows": len(rows)}
    elif body.operation == "stats":
        stats: dict[str, Any] = {
            "row_count": len(rows),
            "column_count": len(headers),
            "columns": {},
        }
        for h in headers:
            vals = [r.get(h, "") for r in rows if r.get(h)]
            stats["columns"][h] = {
                "non_empty": len(vals),
                "unique": len(set(vals)),
                "sample": vals[:3],
            }
            # Try numeric stats
            nums = []
            for v in vals:
                try:
                    nums.append(float(v))
                except (ValueError, TypeError):
                    pass
            if nums:
                stats["columns"][h]["min"] = min(nums)
                stats["columns"][h]["max"] = max(nums)
                stats["columns"][h]["avg"] = round(sum(nums) / len(nums), 2)
        return stats
    elif body.operation == "filter":
        if not body.filter_column:
            return {"error": "filter_column required for filter operation"}
        filtered = [
            r
            for r in rows
            if body.filter_value.lower() in r.get(body.filter_column, "").lower()
        ]
        return {
            "rows": filtered,
            "count": len(filtered),
            "filter": f"{body.filter_column} contains '{body.filter_value}'",
        }
    else:  # to_json
        return {"data": rows, "headers": list(headers), "row_count": len(rows)}


# ── YAML Convert ────────────────────────────────────────────────────────────


class YamlConvertRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)
    direction: str = Field(
        default="yaml_to_json", pattern=r"^(yaml_to_json|json_to_yaml)$"
    )


@app.post("/tools/yaml-convert")
async def tool_yaml_convert(body: YamlConvertRequest):
    """Convert between YAML and JSON formats."""
    logger.info("yaml-convert direction=%s", body.direction)
    try:
        import yaml
    except ImportError:
        raise HTTPException(status_code=500, detail="PyYAML not installed")

    try:
        if body.direction == "yaml_to_json":
            data = yaml.safe_load(body.content)
            return {
                "result": json.dumps(data, indent=2, ensure_ascii=False, default=str),
                "format": "json",
            }
        else:
            data = json.loads(body.content)
            return {
                "result": yaml.dump(data, default_flow_style=False, allow_unicode=True),
                "format": "yaml",
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Conversion failed: {e}")


# ── Base64 Encode/Decode ───────────────────────────────────────────────────


class Base64CodecRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500000)
    operation: str = Field(default="encode", pattern=r"^(encode|decode)$")


@app.post("/tools/base64-codec")
async def tool_base64_codec(body: Base64CodecRequest):
    """Encode or decode Base64 text."""
    logger.info("base64-codec op=%s chars=%d", body.operation, len(body.text))
    try:
        if body.operation == "encode":
            result = base64.b64encode(body.text.encode("utf-8")).decode("ascii")
        else:
            result = base64.b64decode(body.text.encode("ascii")).decode("utf-8")
        return {"result": result, "operation": body.operation}
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Base64 {body.operation} failed: {e}"
        )


# ── Hash Generate ──────────────────────────────────────────────────────────


class HashGenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500000)
    algorithm: str = Field(default="sha256", pattern=r"^(md5|sha1|sha256|sha512)$")


@app.post("/tools/hash-generate")
async def tool_hash_generate(body: HashGenerateRequest):
    """Generate a cryptographic hash of text."""
    logger.info("hash-generate algo=%s chars=%d", body.algorithm, len(body.text))
    h = hashlib.new(body.algorithm)
    h.update(body.text.encode("utf-8"))
    return {
        "hash": h.hexdigest(),
        "algorithm": body.algorithm,
        "length": len(h.hexdigest()),
    }


# ── UUID Generate ──────────────────────────────────────────────────────────


class UuidGenerateRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=20)
    version: int = Field(default=4, ge=4, le=4)


@app.post("/tools/uuid-generate")
async def tool_uuid_generate(body: UuidGenerateRequest):
    """Generate one or more UUID v4 values."""
    logger.info("uuid-generate count=%d", body.count)
    uuids = [str(_uuid.uuid4()) for _ in range(body.count)]
    return {"uuids": uuids, "count": len(uuids), "version": body.version}


# ── Regex Match ─────────────────────────────────────────────────────────────


class RegexMatchRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    pattern: str = Field(..., min_length=1, max_length=1000)
    flags: str = Field(default="", max_length=10)


@app.post("/tools/regex-match")
async def tool_regex_match(body: RegexMatchRequest):
    """Test a regex pattern against text and return all matches with groups."""
    logger.info("regex-match pattern=%s chars=%d", body.pattern[:60], len(body.text))
    flag_map = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}
    flags = 0
    for f in body.flags:
        flags |= flag_map.get(f, 0)

    try:
        compiled = re.compile(body.pattern, flags)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {e}")

    matches = []
    for m in compiled.finditer(body.text):
        match_info: dict[str, Any] = {
            "match": m.group(),
            "start": m.start(),
            "end": m.end(),
        }
        if m.groups():
            match_info["groups"] = list(m.groups())
        if m.groupdict():
            match_info["named_groups"] = m.groupdict()
        matches.append(match_info)
        if len(matches) >= 100:
            break
    return {"pattern": body.pattern, "matches": matches, "count": len(matches)}


# ── URL Parse ───────────────────────────────────────────────────────────────


class UrlParseRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=4096)


@app.post("/tools/url-parse")
async def tool_url_parse(body: UrlParseRequest):
    """Parse a URL into its components (scheme, host, path, query params, etc.)."""
    logger.info("url-parse url=%s", body.url[:80])
    parsed = urlparse(body.url)
    query_params = parse_qs(parsed.query)
    # Flatten single-value params
    flat_params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname or "",
        "port": parsed.port,
        "path": parsed.path,
        "query": parsed.query,
        "query_params": flat_params,
        "fragment": parsed.fragment,
        "username": parsed.username,
        "netloc": parsed.netloc,
    }


# ── HTML Strip ──────────────────────────────────────────────────────────────


class HtmlStripRequest(BaseModel):
    html: str = Field(..., min_length=1, max_length=500000)
    keep_links: bool = Field(default=False)


@app.post("/tools/html-strip")
async def tool_html_strip(body: HtmlStripRequest):
    """Strip HTML tags and return plain text. Optionally preserve link URLs."""
    logger.info("html-strip chars=%d keep_links=%s", len(body.html), body.keep_links)
    text = body.html
    if body.keep_links:
        text = re.sub(
            r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            r"\2 [\1]",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
    # Remove script/style content
    text = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
    # Remove all tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common entities
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    # Collapse whitespace
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    text = text.strip()
    return {"text": text, "original_length": len(body.html), "text_length": len(text)}


# ── Markdown to HTML ────────────────────────────────────────────────────────


class MarkdownToHtmlRequest(BaseModel):
    markdown: str = Field(..., min_length=1, max_length=200000)


@app.post("/tools/markdown-to-html")
async def tool_markdown_to_html(body: MarkdownToHtmlRequest):
    """Convert Markdown text to HTML."""
    logger.info("markdown-to-html chars=%d", len(body.markdown))
    # Simple markdown → HTML without external deps
    html = body.markdown
    # Code blocks (``` ... ```)
    html = re.sub(
        r"```(\w*)\n(.*?)```",
        lambda m: f'<pre><code class="language-{m.group(1)}">{m.group(2)}</code></pre>',
        html,
        flags=re.DOTALL,
    )
    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    # Headers
    html = re.sub(r"^######\s+(.+)$", r"<h6>\1</h6>", html, flags=re.MULTILINE)
    html = re.sub(r"^#####\s+(.+)$", r"<h5>\1</h5>", html, flags=re.MULTILINE)
    html = re.sub(r"^####\s+(.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
    html = re.sub(r"^###\s+(.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^##\s+(.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^#\s+(.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    # Bold and italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)
    # Images
    html = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', html)
    # Unordered lists
    html = re.sub(r"^[\-\*]\s+(.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    # Horizontal rule
    html = re.sub(r"^---+$", "<hr>", html, flags=re.MULTILINE)
    # Paragraphs (simple: wrap non-tag lines)
    lines = html.split("\n")
    result_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("<"):
            result_lines.append(f"<p>{stripped}</p>")
        else:
            result_lines.append(line)
    html = "\n".join(result_lines)
    return {"html": html, "original_length": len(body.markdown)}


# ── Webpage Extract ─────────────────────────────────────────────────────────


class WebpageExtractRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=4096)
    max_length: int = Field(default=5000, ge=100, le=50000)


@app.post("/tools/webpage-extract")
async def tool_webpage_extract(body: WebpageExtractRequest):
    """Fetch a webpage and extract its main text content (strip HTML)."""
    logger.info("webpage-extract url=%s", body.url[:80])
    # Validate URL scheme
    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs allowed")
    # Block private/internal IPs (SSRF protection)
    hostname = parsed.hostname or ""
    if (
        hostname in ("localhost", "127.0.0.1", "0.0.0.0")
        or hostname.startswith("10.")
        or hostname.startswith("192.168.")
        or hostname.startswith("172.")
    ):
        raise HTTPException(status_code=403, detail="Internal/private URLs not allowed")
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "AgenticPlatform/1.0"},
        ) as client:
            resp = await client.get(body.url)
            resp.raise_for_status()
            html = resp.text
        # Strip tags
        text = re.sub(
            r"<(script|style|noscript)[^>]*>.*?</\1>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        # Extract title
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else ""
        return {
            "url": body.url,
            "title": title,
            "text": text[: body.max_length],
            "length": len(text),
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502, detail=f"HTTP {e.response.status_code}: {e}"
        )


# ── DNS Lookup ──────────────────────────────────────────────────────────────


class DnsLookupRequest(BaseModel):
    hostname: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9.\-]+$"
    )


@app.post("/tools/dns-lookup")
async def tool_dns_lookup(body: DnsLookupRequest):
    """Resolve a hostname to its IP addresses."""
    import socket

    logger.info("dns-lookup hostname=%s", body.hostname)
    try:
        results = socket.getaddrinfo(body.hostname, None)
        ips = list(set(r[4][0] for r in results))
        ipv4 = [ip for ip in ips if ":" not in ip]
        ipv6 = [ip for ip in ips if ":" in ip]
        return {"hostname": body.hostname, "ipv4": ipv4, "ipv6": ipv6, "all": ips}
    except socket.gaierror as e:
        raise HTTPException(status_code=404, detail=f"DNS lookup failed: {e}")


# ── JSON Schema Validate ───────────────────────────────────────────────────


class JsonSchemaValidateRequest(BaseModel):
    data: str = Field(..., min_length=1, max_length=100000)
    schema_def: str = Field(..., min_length=1, max_length=50000)


@app.post("/tools/json-schema-validate")
async def tool_json_schema_validate(body: JsonSchemaValidateRequest):
    """Validate JSON data against a JSON Schema definition."""
    logger.info("json-schema-validate")
    try:
        data = json.loads(body.data)
        schema = json.loads(body.schema_def)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # Simple schema validation without jsonschema dependency
    errors: list[str] = []
    _validate_schema(data, schema, "", errors)
    return {"valid": len(errors) == 0, "errors": errors[:20]}


def _validate_schema(data: Any, schema: dict, path: str, errors: list[str]) -> None:
    """Minimal JSON Schema validator (type, required, properties, items)."""
    if "type" in schema:
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        expected = type_map.get(schema["type"])
        if expected and not isinstance(data, expected):
            errors.append(
                f"{path or '/'}: expected {schema['type']}, got {type(data).__name__}"
            )
            return

    if isinstance(data, dict) and "properties" in schema:
        for prop, prop_schema in schema["properties"].items():
            if prop in data:
                _validate_schema(data[prop], prop_schema, f"{path}/{prop}", errors)
        if "required" in schema:
            for req in schema["required"]:
                if req not in data:
                    errors.append(f"{path or '/'}: missing required property '{req}'")

    if isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data[:50]):  # limit
            _validate_schema(item, schema["items"], f"{path}[{i}]", errors)


# ── Cron Parse ──────────────────────────────────────────────────────────────


class CronParseRequest(BaseModel):
    expression: str = Field(..., min_length=1, max_length=100)


@app.post("/tools/cron-parse")
async def tool_cron_parse(body: CronParseRequest):
    """Parse a cron expression and return a human-readable description."""
    logger.info("cron-parse expr=%s", body.expression)
    parts = body.expression.strip().split()
    if len(parts) not in (5, 6):
        raise HTTPException(
            status_code=400, detail="Cron expression must have 5 or 6 fields"
        )

    field_names = ["minute", "hour", "day_of_month", "month", "day_of_week"]
    if len(parts) == 6:
        field_names = ["second"] + field_names

    parsed = dict(zip(field_names, parts))

    # Build human-readable description
    desc_parts = []
    minute = parsed.get("minute", "*")
    hour = parsed.get("hour", "*")
    dom = parsed.get("day_of_month", "*")
    month = parsed.get("month", "*")
    dow = parsed.get("day_of_week", "*")

    if minute.startswith("*/"):
        desc_parts.append(f"Every {minute[2:]} minutes")
    elif hour.startswith("*/"):
        desc_parts.append(f"Every {hour[2:]} hours at minute {minute}")
    elif minute == "*" and hour == "*":
        desc_parts.append("Every minute")
    elif minute == "0" and hour == "*":
        desc_parts.append("Every hour at :00")
    elif minute == "0" and hour == "0":
        desc_parts.append("At midnight")
    elif hour == "*":
        desc_parts.append(f"At minute {minute} of every hour")
    else:
        desc_parts.append(f"At {hour.zfill(2)}:{minute.zfill(2)}")

    day_names = {
        "0": "Sun",
        "1": "Mon",
        "2": "Tue",
        "3": "Wed",
        "4": "Thu",
        "5": "Fri",
        "6": "Sat",
        "7": "Sun",
    }
    month_names = {
        "1": "Jan",
        "2": "Feb",
        "3": "Mar",
        "4": "Apr",
        "5": "May",
        "6": "Jun",
        "7": "Jul",
        "8": "Aug",
        "9": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec",
    }

    if dow != "*":
        days = [day_names.get(d.strip(), d.strip()) for d in dow.split(",")]
        desc_parts.append(f"on {', '.join(days)}")
    if dom != "*":
        desc_parts.append(f"on day {dom} of the month")
    if month != "*":
        months = [month_names.get(m.strip(), m.strip()) for m in month.split(",")]
        desc_parts.append(f"in {', '.join(months)}")

    return {
        "expression": body.expression,
        "fields": parsed,
        "description": " ".join(desc_parts),
    }


# ── JWT Decode ──────────────────────────────────────────────────────────────


class JwtDecodeRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=10000)


@app.post("/tools/jwt-decode")
async def tool_jwt_decode(body: JwtDecodeRequest):
    """Decode a JWT token (without verification) to inspect its header and payload."""
    logger.info("jwt-decode token=%s...", body.token[:20])
    parts = body.token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=400,
            detail="Invalid JWT format (expected 3 dot-separated parts)",
        )
    try:
        # Add padding
        def _b64_decode(s: str) -> dict:
            padding = 4 - len(s) % 4
            if padding != 4:
                s += "=" * padding
            decoded = base64.urlsafe_b64decode(s)
            return json.loads(decoded)

        header = _b64_decode(parts[0])
        payload = _b64_decode(parts[1])

        # Check expiration
        exp = payload.get("exp")
        expired = None
        if exp:
            from datetime import datetime, timezone

            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            expired = exp_dt < datetime.now(timezone.utc)
            payload["_exp_readable"] = exp_dt.isoformat()

        return {
            "header": header,
            "payload": payload,
            "expired": expired,
            "signature_present": bool(parts[2]),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JWT decode failed: {e}")


# ── Environment Info ────────────────────────────────────────────────────────


@app.post("/tools/environment-info")
async def tool_environment_info():
    """Get information about the tools-service runtime environment."""
    import platform
    import sys

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "utc_now": datetime.now(timezone.utc).isoformat(),
        "notes_directory": str(NOTES_DIR),
        "notes_file_count": len(list(NOTES_DIR.glob("*"))) if NOTES_DIR.exists() else 0,
    }
