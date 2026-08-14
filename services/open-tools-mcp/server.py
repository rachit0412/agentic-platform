"""
Open Tools MCP Server — zero-config, no API keys needed.

Provides tools that call free public APIs:
  - wikipedia_search: Look up any topic on Wikipedia
  - get_weather: Current weather for any city (wttr.in)
  - dictionary_lookup: English word definitions (Free Dictionary API)
"""

import json
import logging
import traceback
import urllib.parse
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("open-tools-mcp")

app = FastAPI(title="Open Tools MCP Server")

HEADERS = {"User-Agent": "AgenticPlatform/1.0 (MCP)"}

TOOLS_META = [
    {
        "name": "wikipedia_search",
        "description": "Search Wikipedia and get a concise summary of any topic. Returns title, extract, and URL. No API key required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic to search for on Wikipedia",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather conditions for any city worldwide. Returns temperature, humidity, wind, and description. No API key required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name (e.g. London, New York, Tokyo, Mumbai)",
                },
            },
            "required": ["location"],
        },
    },
    {
        "name": "dictionary_lookup",
        "description": "Look up the definition, phonetics, and usage examples of an English word. No API key required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "word": {
                    "type": "string",
                    "description": "English word to look up",
                },
            },
            "required": ["word"],
        },
    },
]


# ── Tool handlers ─────────────────────────────────────────────────────────


async def _wikipedia_search(query: str) -> str:
    encoded = urllib.parse.quote(query.strip(), safe="")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=HEADERS, follow_redirects=True)
        if resp.status_code == 404:
            # Try search API as fallback
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={encoded}&limit=5&format=json"
            resp2 = await client.get(search_url, headers=HEADERS)
            data = resp2.json()
            if len(data) >= 4 and data[1]:
                results = [
                    {"title": t, "description": d, "url": u}
                    for t, d, u in zip(data[1], data[2], data[3])
                ]
                return json.dumps(
                    {"type": "search_results", "query": query, "results": results}
                )
            return json.dumps({"error": f"No Wikipedia article found for '{query}'"})
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(
            {
                "title": data.get("title", ""),
                "extract": data.get("extract", ""),
                "description": data.get("description", ""),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
        )


async def _get_weather(location: str) -> str:
    encoded = urllib.parse.quote(location.strip(), safe="")
    url = f"https://wttr.in/{encoded}?format=j1"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=HEADERS, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]
        city = area.get("areaName", [{}])[0].get("value", location)
        country = area.get("country", [{}])[0].get("value", "")
        return json.dumps(
            {
                "location": f"{city}, {country}",
                "temperature_c": current.get("temp_C", ""),
                "temperature_f": current.get("temp_F", ""),
                "feels_like_c": current.get("FeelsLikeC", ""),
                "condition": current.get("weatherDesc", [{}])[0].get("value", ""),
                "humidity": current.get("humidity", "") + "%",
                "wind_speed_kmph": current.get("windspeedKmph", ""),
                "wind_direction": current.get("winddir16Point", ""),
                "visibility_km": current.get("visibility", ""),
                "uv_index": current.get("uvIndex", ""),
            }
        )


async def _dictionary_lookup(word: str) -> str:
    encoded = urllib.parse.quote(word.strip().lower(), safe="")
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{encoded}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 404:
            return json.dumps({"error": f"No definition found for '{word}'"})
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return json.dumps({"error": f"No definition found for '{word}'"})
        entry = data[0]
        meanings = []
        for m in entry.get("meanings", []):
            defs = []
            for d in m.get("definitions", [])[:3]:
                item = {"definition": d.get("definition", "")}
                if d.get("example"):
                    item["example"] = d["example"]
                defs.append(item)
            meanings.append(
                {
                    "part_of_speech": m.get("partOfSpeech", ""),
                    "definitions": defs,
                }
            )
        return json.dumps(
            {
                "word": entry.get("word", word),
                "phonetic": entry.get("phonetic", ""),
                "meanings": meanings,
            }
        )


TOOL_HANDLERS = {
    "wikipedia_search": lambda **kw: _wikipedia_search(kw.get("query", "")),
    "get_weather": lambda **kw: _get_weather(kw.get("location", "")),
    "dictionary_lookup": lambda **kw: _dictionary_lookup(kw.get("word", "")),
}


# ── MCP JSON-RPC endpoints ───────────────────────────────────────────────


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str = ""
    params: dict = {}
    id: Any = 1


@app.get("/health")
async def health():
    return {"status": "healthy", "tools": len(TOOLS_META), "server": "open-tools-mcp"}


@app.post("/tools/list")
async def tools_list(req: JsonRpcRequest = JsonRpcRequest()):
    return {"jsonrpc": "2.0", "result": {"tools": TOOLS_META}, "id": req.id}


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
        return {
            "jsonrpc": "2.0",
            "result": {"content": [{"type": "text", "text": result}]},
            "id": req.id,
        }
    except Exception as e:
        logger.error("Tool %s failed: %s\n%s", tool_name, e, traceback.format_exc())
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": req.id,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
