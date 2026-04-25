"""
Tool definitions using LangChain @tool decorators + HTTP proxy tools.

Two categories:
1. Proxy tools — call endpoints on tools-service (math, http_fetch, file_write, file_read, datetime, web_search, code_execute)
2. Local tools  — run in-process (vector_search, vector_store)
"""
import os
import json
import logging
from typing import Optional

import httpx
from langchain_core.tools import tool, StructuredTool

logger = logging.getLogger("agent-service.tools")

TOOLS_SERVICE_URL = os.getenv("TOOLS_SERVICE_URL", "http://tools-service:8001")


# ── Helper: call tools-service endpoint ─────────────────────────────────────

async def _proxy_call(endpoint: str, payload: dict) -> dict:
    """POST to tools-service and return JSON."""
    url = f"{TOOLS_SERVICE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"error": f"Tools-service returned {exc.response.status_code}"}
        except httpx.RequestError as exc:
            return {"error": f"Tools-service unreachable: {exc}"}


# ── Proxy tools ─────────────────────────────────────────────────────────────

@tool
async def math(expression: str) -> str:
    """Evaluate a simple arithmetic expression like '2+2' or '(10*5)/3'. Returns the numeric result."""
    result = await _proxy_call("/tools/math", {"expression": expression})
    return json.dumps(result)


@tool
async def http_fetch(url: str) -> str:
    """Fetch the text content of a public URL. Only allowed domains: httpbin.org, jsonplaceholder.typicode.com."""
    result = await _proxy_call("/tools/http-fetch", {"url": url})
    return json.dumps(result)


@tool
async def file_write(filename: str, content: str) -> str:
    """Save a text note to persistent storage. Filename must be simple (no path separators)."""
    result = await _proxy_call("/tools/file-write", {"filename": filename, "content": content})
    return json.dumps(result)


@tool
async def file_read(filename: str) -> str:
    """Read a previously saved text note from storage by filename."""
    result = await _proxy_call("/tools/file-read", {"filename": filename})
    return json.dumps(result)


@tool
async def datetime_tool() -> str:
    """Get the current date, time, and timezone information."""
    result = await _proxy_call("/tools/datetime", {})
    return json.dumps(result)


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo. Returns relevant search results for the query."""
    result = await _proxy_call("/tools/web-search", {"query": query, "max_results": max_results})
    return json.dumps(result)


@tool
async def code_execute(code: str, language: str = "python") -> str:
    """Execute code in a sandboxed environment. Supports Python. Returns stdout, stderr, and exit code."""
    result = await _proxy_call("/tools/code-execute", {"code": code, "language": language})
    return json.dumps(result)


# ── Local tools (vector operations) ─────────────────────────────────────────

@tool
async def vector_search(query: str, k: int = 5) -> str:
    """Search the document knowledge base for information relevant to the query. Uses semantic similarity."""
    try:
        from agent.vectorstore import search_similar
        results = search_similar(query, k=k)
        return json.dumps({"results": results, "count": len(results)})
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


@tool
async def vector_store(text: str, source: str) -> str:
    """Store a document in the knowledge base for later retrieval. Provide the text content and a source name."""
    try:
        from agent.vectorstore import ingest_document
        result = ingest_document(text, source)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool registry ───────────────────────────────────────────────────────────

def get_all_tools() -> list:
    """Return all available LangChain tools."""
    return [
        math,
        http_fetch,
        file_write,
        file_read,
        datetime_tool,
        web_search,
        code_execute,
        vector_search,
        vector_store,
    ]


# ── Legacy compatibility ────────────────────────────────────────────────────
# These keep the old graph.py imports working during migration.

TOOL_CATALOGUE: list[dict] = [
    {"name": t.name, "description": t.description, "endpoint": "", "method": "POST", "parameters": {}}
    for t in get_all_tools()
]


def catalogue_as_text() -> str:
    """Render tool list as plain text for system prompts."""
    lines = []
    for t in get_all_tools():
        lines.append(f"- {t.name}: {t.description}")
    return "\n".join(lines)


async def call_tool(tool_name: str, arguments: dict) -> dict:
    """Legacy: call a tool by name with arguments dict."""
    tools_map = {t.name: t for t in get_all_tools()}
    t = tools_map.get(tool_name)
    if t is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        result_str = await t.ainvoke(arguments)
        return json.loads(result_str) if isinstance(result_str, str) else result_str
    except Exception as e:
        return {"error": f"Tool {tool_name} failed: {e}"}
