"""
Managed MCP Server — Generic runtime for config-defined and code-defined tools.

Reads MCP_CONFIG env var (JSON) on startup. Supports two modes:
  - "config": proxies HTTP calls to external endpoints
  - "code": executes user-defined Python functions
"""

import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
import traceback
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("managed-mcp")

app = FastAPI(title="Managed MCP Server")

# ── Config parsing ────────────────────────────────────────────────────────

CONFIG: dict = {}
TOOLS_META: list[dict] = []
TOOL_HANDLERS: dict = {}

TYPE_MAP = {"string": str, "integer": int, "number": float, "boolean": bool}
REVERSE_TYPE_MAP = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _python_type_to_json(t) -> str:
    if t in REVERSE_TYPE_MAP:
        return REVERSE_TYPE_MAP[t]
    return "string"


# ── Config mode setup ─────────────────────────────────────────────────────

def _setup_config_mode(config: dict):
    tools_defs = config.get("tools", [])
    for td in tools_defs:
        name = td["name"]
        desc = td.get("description", f"Tool: {name}")
        params = td.get("parameters", [])

        properties = {}
        required = []
        for p in params:
            pname = p["name"]
            ptype = p.get("type", "string")
            properties[pname] = {
                "type": ptype,
                "description": p.get("description", ""),
            }
            if p.get("required", False):
                required.append(pname)

        TOOLS_META.append({
            "name": name,
            "description": desc,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })

        endpoint_url = td.get("endpoint_url", "")
        http_method = td.get("http_method", "POST").upper()
        headers = td.get("headers", {})

        async def _handler(
            _url=endpoint_url, _method=http_method, _headers=headers, **kwargs
        ) -> str:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if _method == "GET":
                    resp = await client.get(_url, params=kwargs, headers=_headers)
                else:
                    resp = await client.request(
                        _method, _url, json=kwargs, headers=_headers
                    )
                resp.raise_for_status()
                try:
                    return json.dumps(resp.json())
                except Exception:
                    return resp.text[:8000]

        TOOL_HANDLERS[name] = _handler
    logger.info("Config mode: loaded %d tools", len(TOOLS_META))


# ── Code mode setup ───────────────────────────────────────────────────────

def _setup_code_mode(config: dict):
    code = config.get("code", "")
    if not code:
        logger.warning("Code mode but no code provided")
        return

    code_path = "/app/user_tools.py"
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)

    spec = importlib.util.spec_from_file_location("user_tools", code_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["user_tools"] = mod
    spec.loader.exec_module(mod)

    for name, func in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("_"):
            continue

        sig = inspect.signature(func)
        docstring = inspect.getdoc(func) or f"User tool: {name}"
        properties = {}
        required = []

        for pname, param in sig.parameters.items():
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                ptype = "string"
            else:
                ptype = _python_type_to_json(annotation)

            properties[pname] = {"type": ptype, "description": ""}
            if param.default is inspect.Parameter.empty:
                required.append(pname)

        TOOLS_META.append({
            "name": name,
            "description": docstring,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })

        if asyncio.iscoroutinefunction(func):
            TOOL_HANDLERS[name] = func
        else:
            async def _async_wrap(_fn=func, **kwargs) -> str:
                result = _fn(**kwargs)
                return str(result)
            TOOL_HANDLERS[name] = _async_wrap

    logger.info("Code mode: loaded %d tools from user code", len(TOOLS_META))


# ── Startup ───────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global CONFIG
    raw = os.environ.get("MCP_CONFIG", "")
    if not raw:
        config_path = "/app/config.json"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                raw = f.read()
    if not raw:
        logger.error("No MCP_CONFIG env var or /app/config.json found")
        return

    try:
        CONFIG = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Invalid MCP_CONFIG JSON: %s", e)
        return

    mode = CONFIG.get("mode", "config")
    logger.info("Starting managed MCP server in %s mode", mode)

    if mode == "config":
        _setup_config_mode(CONFIG)
    elif mode == "code":
        _setup_code_mode(CONFIG)
    else:
        logger.error("Unknown mode: %s", mode)


# ── JSON-RPC models ──────────────────────────────────────────────────────

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str = ""
    params: dict = {}
    id: Any = 1


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "tools": len(TOOLS_META), "mode": CONFIG.get("mode", "unknown")}


@app.post("/tools/list")
async def tools_list(req: JsonRpcRequest = JsonRpcRequest()):
    return {
        "jsonrpc": "2.0",
        "result": {"tools": TOOLS_META},
        "id": req.id,
    }


@app.get("/tools")
async def tools_list_get():
    return {"tools": TOOLS_META}


@app.post("/tools/call")
async def tools_call(req: JsonRpcRequest):
    tool_name = req.params.get("name", "")
    arguments = req.params.get("arguments", {})

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
            "id": req.id,
        }

    try:
        result = await handler(**arguments)
        if not isinstance(result, str):
            result = json.dumps(result) if result is not None else ""
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [{"type": "text", "text": result}],
            },
            "id": req.id,
        }
    except Exception as e:
        logger.error("Tool %s failed: %s\n%s", tool_name, e, traceback.format_exc())
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": req.id,
        }
