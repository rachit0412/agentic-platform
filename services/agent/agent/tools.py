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


# ── New proxy tools ─────────────────────────────────────────────────────────


@tool
async def file_list(directory: str = "", pattern: str = "*") -> str:
    """List files in the notes directory with optional glob pattern filter. Returns file names, sizes, and modification dates."""
    result = await _proxy_call(
        "/tools/file-list", {"directory": directory, "pattern": pattern}
    )
    return json.dumps(result)


@tool
async def file_search_content(
    query: str, pattern: str = "*", max_results: int = 10
) -> str:
    """Search for text content across all saved files. Returns matching files and line numbers."""
    result = await _proxy_call(
        "/tools/file-search-content",
        {"query": query, "pattern": pattern, "max_results": max_results},
    )
    return json.dumps(result)


@tool
async def text_summarize(text: str, max_sentences: int = 3) -> str:
    """Extract the most important sentences from text using extractive summarization. Good for quick summaries of long content."""
    result = await _proxy_call(
        "/tools/text-summarize", {"text": text, "max_sentences": max_sentences}
    )
    return json.dumps(result)


@tool
async def text_transform(text: str, operation: str) -> str:
    """Transform text with string operations. Operations: uppercase, lowercase, title, capitalize, reverse, snake_case, camel_case, kebab_case, count_words, count_chars, count_lines, trim, deduplicate_lines, sort_lines, number_lines, remove_blank_lines."""
    result = await _proxy_call(
        "/tools/text-transform", {"text": text, "operation": operation}
    )
    return json.dumps(result)


@tool
async def text_diff(text_a: str, text_b: str, context_lines: int = 3) -> str:
    """Generate a unified diff between two text strings. Shows additions, deletions, and unchanged context."""
    result = await _proxy_call(
        "/tools/text-diff",
        {"text_a": text_a, "text_b": text_b, "context_lines": context_lines},
    )
    return json.dumps(result)


@tool
async def text_extract(text: str, extract_type: str) -> str:
    """Extract structured data from text. Types: emails, urls, phone_numbers, ip_addresses, dates, numbers, hashtags, mentions."""
    result = await _proxy_call(
        "/tools/text-extract", {"text": text, "extract_type": extract_type}
    )
    return json.dumps(result)


@tool
async def json_transform(data: str, operation: str, jq_path: str = "") -> str:
    """Transform JSON data. Operations: prettify, minify, flatten, keys, values, sort_keys, validate, paths, filter_nulls, to_csv."""
    result = await _proxy_call(
        "/tools/json-transform",
        {"data": data, "operation": operation, "jq_path": jq_path},
    )
    return json.dumps(result)


@tool
async def csv_parse(
    csv_text: str,
    operation: str = "to_json",
    filter_column: str = "",
    filter_value: str = "",
    max_rows: int = 100,
) -> str:
    """Parse CSV text: to_json (convert), stats (column statistics), headers (list columns), preview (first 10 rows), filter (by column value)."""
    result = await _proxy_call(
        "/tools/csv-parse",
        {
            "csv_text": csv_text,
            "operation": operation,
            "filter_column": filter_column,
            "filter_value": filter_value,
            "max_rows": max_rows,
        },
    )
    return json.dumps(result)


@tool
async def yaml_convert(content: str, direction: str = "yaml_to_json") -> str:
    """Convert between YAML and JSON formats. Directions: yaml_to_json, json_to_yaml."""
    result = await _proxy_call(
        "/tools/yaml-convert", {"content": content, "direction": direction}
    )
    return json.dumps(result)


@tool
async def base64_codec(text: str, operation: str = "encode") -> str:
    """Encode or decode Base64 text. Operations: encode, decode."""
    result = await _proxy_call(
        "/tools/base64-codec", {"text": text, "operation": operation}
    )
    return json.dumps(result)


@tool
async def hash_generate(text: str, algorithm: str = "sha256") -> str:
    """Generate a cryptographic hash. Algorithms: md5, sha1, sha256, sha512."""
    result = await _proxy_call(
        "/tools/hash-generate", {"text": text, "algorithm": algorithm}
    )
    return json.dumps(result)


@tool
async def uuid_generate(count: int = 1) -> str:
    """Generate one or more UUID v4 values."""
    result = await _proxy_call("/tools/uuid-generate", {"count": count})
    return json.dumps(result)


@tool
async def regex_match(text: str, pattern: str, flags: str = "") -> str:
    """Test a regex pattern against text. Returns all matches with positions and captured groups. Flags: i (ignore case), m (multiline), s (dotall)."""
    result = await _proxy_call(
        "/tools/regex-match", {"text": text, "pattern": pattern, "flags": flags}
    )
    return json.dumps(result)


@tool
async def url_parse(url: str) -> str:
    """Parse a URL into components: scheme, host, port, path, query parameters, fragment."""
    result = await _proxy_call("/tools/url-parse", {"url": url})
    return json.dumps(result)


@tool
async def html_strip(html: str, keep_links: bool = False) -> str:
    """Strip HTML tags and return clean plain text. Optionally preserves link URLs inline."""
    result = await _proxy_call(
        "/tools/html-strip", {"html": html, "keep_links": keep_links}
    )
    return json.dumps(result)


@tool
async def markdown_to_html(markdown: str) -> str:
    """Convert Markdown text to HTML."""
    result = await _proxy_call("/tools/markdown-to-html", {"markdown": markdown})
    return json.dumps(result)


@tool
async def webpage_extract(url: str, max_length: int = 5000) -> str:
    """Fetch a webpage and extract its main text content. Strips HTML tags. Good for reading articles or documentation."""
    result = await _proxy_call(
        "/tools/webpage-extract", {"url": url, "max_length": max_length}
    )
    return json.dumps(result)


@tool
async def dns_lookup(hostname: str) -> str:
    """Resolve a hostname to its IP addresses (IPv4 and IPv6)."""
    result = await _proxy_call("/tools/dns-lookup", {"hostname": hostname})
    return json.dumps(result)


@tool
async def json_schema_validate(data: str, schema_def: str) -> str:
    """Validate JSON data against a JSON Schema definition. Returns whether data is valid and any validation errors."""
    result = await _proxy_call(
        "/tools/json-schema-validate", {"data": data, "schema_def": schema_def}
    )
    return json.dumps(result)


@tool
async def cron_parse(expression: str) -> str:
    """Parse a cron expression and return a human-readable description of the schedule."""
    result = await _proxy_call("/tools/cron-parse", {"expression": expression})
    return json.dumps(result)


@tool
async def jwt_decode(token: str) -> str:
    """Decode a JWT token (without verification) to inspect its header and payload. Shows expiration status."""
    result = await _proxy_call("/tools/jwt-decode", {"token": token})
    return json.dumps(result)


@tool
async def environment_info() -> str:
    """Get information about the tools-service runtime: Python version, platform, file counts."""
    result = await _proxy_call("/tools/environment-info", {})
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
        file_list,
        file_search_content,
        datetime_tool,
        web_search,
        code_execute,
        delegate_to_agent,
        vector_search,
        vector_store,
        advanced_search,
        query_database,
        query_csv_data,
        text_summarize,
        text_transform,
        text_diff,
        text_extract,
        json_transform,
        csv_parse,
        yaml_convert,
        base64_codec,
        hash_generate,
        uuid_generate,
        regex_match,
        url_parse,
        html_strip,
        markdown_to_html,
        webpage_extract,
        dns_lookup,
        json_schema_validate,
        cron_parse,
        jwt_decode,
        environment_info,
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


def _make_mcp_tool(server_config: dict, tool_def: dict):
    """Build a LangChain StructuredTool that calls an MCP server's tool via JSON-RPC."""
    server_name = server_config["name"].replace("-", "_").replace(" ", "_").lower()
    tool_name_raw = tool_def.get("name", "unknown")
    name = f"mcp_{server_name}_{tool_name_raw}"
    description = tool_def.get("description", f"MCP tool: {tool_name_raw}")
    server_url = server_config["url"].rstrip("/")

    async def _invoke(**kwargs) -> str:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name_raw, "arguments": kwargs},
            "id": 1,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(server_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if "result" in data:
                    content = data["result"].get("content", [])
                    texts = [c.get("text", str(c)) for c in content if isinstance(c, dict)]
                    return "\n".join(texts) if texts else json.dumps(data["result"])
                if "error" in data:
                    return json.dumps({"error": data["error"]})
                return json.dumps(data)
            except httpx.HTTPStatusError as exc:
                return json.dumps({"error": f"HTTP {exc.response.status_code}"})
            except httpx.RequestError as exc:
                return json.dumps({"error": f"MCP request failed: {exc}"})

    input_schema = tool_def.get("inputSchema", {})
    properties = input_schema.get("properties", {})
    required_fields = set(input_schema.get("required", []))

    from pydantic import create_model

    fields = {}
    type_map = {"string": str, "integer": int, "number": float, "boolean": bool}
    for pname, pschema in properties.items():
        ptype = type_map.get(pschema.get("type", "string"), str)
        if pname in required_fields:
            fields[pname] = (ptype, ...)
        else:
            fields[pname] = (Optional[ptype], None)

    if not fields:
        fields["input"] = (Optional[str], None)

    InputModel = create_model(f"{name}_Input", **fields)

    return StructuredTool.from_function(
        coroutine=_invoke,
        name=name,
        description=description,
        args_schema=InputModel,
    )


def get_mcp_tools(mcp_server_ids: list[str] | None = None) -> list:
    """Build StructuredTool wrappers for MCP server tools.

    If *mcp_server_ids* is provided, only those servers are loaded.
    If empty/None, **all enabled** MCP servers are auto-discovered —
    the agent decides which tools to call at runtime (agentic behaviour).
    """
    from agent.memory import get_mcp_server, list_mcp_servers

    if mcp_server_ids:
        servers = []
        for sid in mcp_server_ids:
            s = get_mcp_server(sid)
            if s:
                servers.append(s)
    else:
        servers = list_mcp_servers()

    tools = []
    for server in servers:
        if not server.get("enabled", True):
            continue
        for tool_def in server.get("tools", []):
            t = _make_mcp_tool(server, tool_def)
            if t:
                tools.append(t)
    return tools


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


def catalogue_as_text_filtered(tool_ids: list[str] | None = None, extra_tools: list | None = None) -> str:
    """Render tool list filtered by tool_ids. If tool_ids is None or empty, return all."""
    _refresh_catalogue()
    all_tools = get_all_tools()
    if extra_tools:
        all_tools = all_tools + extra_tools
    if tool_ids:
        id_set = set(tool_ids)
        all_tools = [t for t in all_tools if t.name in id_set]
    lines = []
    for t in all_tools:
        lines.append(f"- {t.name}: {t.description}")
    return "\n".join(lines)


async def call_tool(tool_name: str, arguments: dict, extra_tools: list | None = None) -> dict:
    """Legacy: call a tool by name with arguments dict."""
    all_tools = get_all_tools()
    if extra_tools:
        all_tools = all_tools + extra_tools
    tools_map = {t.name: t for t in all_tools}
    t = tools_map.get(tool_name)
    if t is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        result_str = await t.ainvoke(arguments)
        return json.loads(result_str) if isinstance(result_str, str) else result_str
    except Exception as e:
        return {"error": f"Tool {tool_name} failed: {e}"}
