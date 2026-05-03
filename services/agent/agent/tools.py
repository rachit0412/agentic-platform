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
    result = await _proxy_call(
        "/tools/file-write", {"filename": filename, "content": content}
    )
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
    result = await _proxy_call(
        "/tools/web-search", {"query": query, "max_results": max_results}
    )
    return json.dumps(result)


@tool
async def code_execute(code: str, language: str = "python") -> str:
    """Execute code in a sandboxed environment. Supports Python. Returns stdout, stderr, and exit code."""
    result = await _proxy_call(
        "/tools/code-execute", {"code": code, "language": language}
    )
    return json.dumps(result)


# ── Local tools (vector operations) ─────────────────────────────────────────


@tool
async def delegate_to_agent(agent_id: str, task: str) -> str:
    """Delegate a task to another agent by its ID. Use when a sub-agent is better suited for a specific part of your task. Returns the sub-agent's response."""
    try:
        from agent.memory import get_agent
        from agent.graph import run_agent
        import uuid

        agent_cfg = get_agent(agent_id)
        if not agent_cfg:
            return json.dumps({"error": f"Agent '{agent_id}' not found"})

        # Prevent deep recursion
        result = await run_agent(
            prompt=task,
            session_id=f"delegation-{uuid.uuid4().hex[:8]}",
            request_id=f"del-{uuid.uuid4().hex[:6]}",
            agent_config=agent_cfg,
        )
        return json.dumps(
            {
                "agent_name": agent_cfg.get("name", agent_id),
                "response": result.get("response", ""),
                "tools_used": result.get("tools_used", []),
            }
        )
    except Exception as e:
        return json.dumps({"error": f"Delegation failed: {str(e)}"})


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


# ── LlamaIndex-powered tools ───────────────────────────────────────────────


@tool
async def advanced_search(query: str, mode: str = "hybrid", k: int = 5) -> str:
    """Advanced knowledge base search with multiple retrieval strategies.
    Modes: 'hybrid' (vector+keyword), 'sentence_window' (with context),
    'auto_merging' (merge related chunks), 'reranked' (LLM reranking).
    Use this for more precise or context-rich retrieval than basic vector_search."""
    try:
        from agent.advanced_retrieval import advanced_search as _advanced_search

        results = _advanced_search(query=query, mode=mode, k=k)
        return json.dumps({"results": results, "count": len(results), "mode": mode})
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


@tool
async def query_database(
    question: str, connection_string: str, tables: Optional[str] = None
) -> str:
    """Ask a natural language question about data in a SQL database.
    Translates your question to SQL, runs it, and returns the answer.
    Provide a SQLAlchemy connection string and optionally comma-separated table names.
    """
    try:
        from agent.structured_query import query_sql

        table_list = [t.strip() for t in tables.split(",")] if tables else None
        result = query_sql(
            question=question, connection_string=connection_string, tables=table_list
        )
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def query_csv_data(question: str, csv_path: str) -> str:
    """Ask a natural language question about data in a CSV file.
    Uses Pandas under the hood to analyze the data and answer your question."""
    try:
        from agent.structured_query import query_csv

        result = query_csv(question=question, csv_path=csv_path)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool registry ───────────────────────────────────────────────────────────


def get_all_tools() -> list:
    """Return all available LangChain tools (built-in + custom dynamic)."""
    builtin = [
        math,
        http_fetch,
        file_write,
        file_read,
        datetime_tool,
        web_search,
        code_execute,
        delegate_to_agent,
        vector_search,
        vector_store,
        advanced_search,
        query_database,
        query_csv_data,
    ]
    try:
        from agent.memory import list_custom_tools

        custom = list_custom_tools()
        for ct in custom:
            if not ct.get("enabled", True):
                continue
            t = _make_custom_tool(ct)
            if t:
                builtin.append(t)
    except Exception as e:
        logger.warning("Failed to load custom tools: %s", e)
    return builtin


def _make_custom_tool(ct: dict):
    """Build a LangChain StructuredTool from a custom tool DB record."""
    name = ct["name"]
    description = ct["description"] or f"Custom tool: {name}"
    endpoint = ct.get("endpoint", "")
    method = ct.get("method", "POST").upper()
    headers = ct.get("headers", {})

    async def _invoke(**kwargs) -> str:
        if not endpoint:
            return json.dumps({"error": "No endpoint configured for this tool"})
        url = endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == "GET":
                    resp = await client.get(url, params=kwargs, headers=headers)
                else:
                    resp = await client.request(
                        method, url, json=kwargs, headers=headers
                    )
                resp.raise_for_status()
                try:
                    return json.dumps(resp.json())
                except Exception:
                    return resp.text[:4000]
            except httpx.HTTPStatusError as exc:
                return json.dumps({"error": f"HTTP {exc.response.status_code}"})
            except httpx.RequestError as exc:
                return json.dumps({"error": f"Request failed: {exc}"})

    # Build input schema from parameters
    params = ct.get("parameters", [])
    fields = {}
    for p in params:
        pname = p.get("name", "input")
        ptype = p.get("type", "string")
        pdesc = p.get("desc", p.get("description", ""))
        if ptype == "int":
            fields[pname] = (Optional[int], None)
        elif ptype == "float":
            fields[pname] = (Optional[float], None)
        elif ptype == "bool":
            fields[pname] = (Optional[bool], None)
        else:
            fields[pname] = (Optional[str], None)

    if not fields:
        fields["input"] = (Optional[str], None)

    from pydantic import create_model

    InputModel = create_model(f"{name}_Input", **fields)

    return StructuredTool.from_function(
        coroutine=_invoke,
        name=name,
        description=description,
        args_schema=InputModel,
    )


# ── Legacy compatibility ────────────────────────────────────────────────────
# These keep the old graph.py imports working during migration.


def _get_tool_catalogue() -> list[dict]:
    """Build a fresh tool catalogue including custom tools."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "endpoint": "",
            "method": "POST",
            "parameters": {},
        }
        for t in get_all_tools()
    ]


# Lazy property: rebuilt on access so custom tools are always included.
TOOL_CATALOGUE: list[dict] = []


def _refresh_catalogue():
    global TOOL_CATALOGUE
    TOOL_CATALOGUE[:] = _get_tool_catalogue()


def catalogue_as_text() -> str:
    """Render tool list as plain text for system prompts."""
    _refresh_catalogue()
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
