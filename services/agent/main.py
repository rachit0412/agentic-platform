"""
Agent Service — FastAPI + LangGraph
Accepts prompts, runs an agent loop (tool-calling + Ollama), returns responses.
"""
import os
import uuid
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.graph import run_agent, run_agent_stream
from agent.memory import (
    init_db, get_history, list_sessions, delete_session,
    get_session_summary, get_memory_stats,
    list_skills, get_skill, create_skill, update_skill, delete_skill,
    list_agents, get_agent, create_agent, update_agent, delete_agent,
    list_a2a_peers, get_a2a_peer, create_a2a_peer, update_a2a_peer, delete_a2a_peer,
    list_mcp_servers, get_mcp_server, create_mcp_server, update_mcp_server, delete_mcp_server,
    list_prompts, get_prompt, create_prompt, update_prompt, delete_prompt,
)
from agent.llm import list_available_models, get_active_model, set_active_model
from agent.observability import setup_otel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("agent-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise resources on startup."""
    init_db()
    logger.info("Memory DB initialised")
    yield


app = FastAPI(title="Agent Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire observability
setup_otel(app)


# ── Models ──────────────────────────────────────────────────────────────────
class RunRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    sessionId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str | None = Field(default=None, description="Model name to use (e.g. llama3, mistral)")
    provider: str | None = Field(default=None, description="Provider: ollama or azure-openai")
    agent_id: str | None = Field(default=None, description="Agent config ID to use")


class RunResponse(BaseModel):
    sessionId: str
    response: str
    tools_used: list[str] = []
    request_id: str
    trace_id: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-service"}


@app.post("/run", response_model=RunResponse)
async def run(body: RunRequest, request: Request):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
    logger.info(
        "req=%s session=%s prompt=%s provider=%s model=%s",
        request_id,
        body.sessionId,
        body.prompt[:80],
        body.provider or "default",
        body.model or "default",
    )

    # Switch model if requested
    if body.provider or body.model:
        from agent.llm import set_active_model as _switch
        _switch(
            provider=body.provider or "ollama",
            model=body.model or "",
        )

    result = await run_agent(
        prompt=body.prompt,
        session_id=body.sessionId,
        request_id=request_id,
    )

    active = get_active_model()
    logger.info("req=%s done tools=%s model=%s/%s", request_id, result["tools_used"], active["provider"], active["model"])
    return RunResponse(
        sessionId=body.sessionId,
        response=result["response"],
        tools_used=result["tools_used"],
        request_id=request_id,
        trace_id=result.get("trace_id"),
    )


# ── Streaming endpoint (SSE) ───────────────────────────────────────────────

@app.post("/run/stream")
async def run_stream(body: RunRequest):
    request_id = str(uuid.uuid4())[:8]
    logger.info(
        "req=%s session=%s prompt=%s provider=%s model=%s agent=%s (stream)",
        request_id,
        body.sessionId,
        body.prompt[:80],
        body.provider or "default",
        body.model or "default",
        body.agent_id or "default",
    )

    # Switch model if requested explicitly
    if body.provider or body.model:
        from agent.llm import set_active_model as _switch
        _switch(
            provider=body.provider or "ollama",
            model=body.model or "",
        )

    # Load agent config if specified
    agent_config = None
    if body.agent_id:
        agent_config = get_agent(body.agent_id)
        if agent_config and not (body.provider or body.model):
            # Apply agent's model settings
            from agent.llm import set_active_model as _switch
            _switch(
                provider=agent_config.get("provider", "ollama"),
                model=agent_config.get("model", "llama3"),
            )

    async def event_generator():
        async for event in run_agent_stream(
            prompt=body.prompt,
            session_id=body.sessionId,
            request_id=request_id,
            agent_config=agent_config,
        ):
            data = json.dumps(event["data"]) if isinstance(event["data"], dict) else event["data"]
            yield f"event: {event['event']}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Model management ──────────────────────────────────────────────────────

@app.get("/models")
async def models_list():
    """List all available models across providers."""
    models = list_available_models()
    active = get_active_model()
    return {"models": models, "active": active}


class ModelSwitchRequest(BaseModel):
    provider: str = Field(..., description="ollama or azure-openai")
    model: str = Field(..., min_length=1, max_length=200)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


@app.post("/models/switch")
async def models_switch(body: ModelSwitchRequest):
    """Switch the active LLM provider and model."""
    active = set_active_model(body.provider, body.model, body.temperature)
    logger.info("Model switched to %s/%s", active["provider"], active["model"])
    return {"status": "switched", "active": active}


# ── Session management ─────────────────────────────────────────────────────

@app.get("/sessions")
async def sessions_list():
    return {"sessions": list_sessions()}


@app.get("/sessions/{session_id}/history")
async def session_history(session_id: str):
    history = get_history(session_id, limit=100)
    return {"session_id": session_id, "messages": history}


@app.delete("/sessions/{session_id}")
async def session_delete(session_id: str):
    count = delete_session(session_id)
    return {"session_id": session_id, "deleted_messages": count}


@app.get("/sessions/{session_id}/summary")
async def session_summary(session_id: str):
    summary = get_session_summary(session_id)
    return {"session_id": session_id, "summary": summary}


# ── Memory management ──────────────────────────────────────────────────────

@app.get("/memory/stats")
async def memory_stats():
    stats = get_memory_stats()
    from agent.vectorstore import get_collection_stats
    try:
        kb_stats = get_collection_stats()
    except Exception:
        kb_stats = {"total_chunks": 0, "unique_documents": 0}
    return {
        "memory": stats,
        "knowledge_base": kb_stats,
    }


# ── Document / RAG endpoints ───────────────────────────────────────────────

class DocumentIngestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    source: str = Field(..., min_length=1, max_length=500)
    metadata: dict = Field(default_factory=dict)
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    collection: str = Field(default="agentic_docs", max_length=200)


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=50)


@app.post("/documents/ingest")
async def documents_ingest(body: DocumentIngestRequest):
    from agent.vectorstore import ingest_document
    result = ingest_document(
        text=body.text,
        source=body.source,
        metadata=body.metadata,
        chunk_size=body.chunk_size,
        chunk_overlap=body.chunk_overlap,
        collection_name=body.collection,
    )
    return result


@app.post("/documents/search")
async def documents_search(body: DocumentSearchRequest):
    from agent.vectorstore import search_similar
    results = search_similar(body.query, k=body.k)
    return {"query": body.query, "results": results, "count": len(results)}


@app.get("/documents")
async def documents_list():
    from agent.vectorstore import list_documents
    return {"documents": list_documents()}


@app.get("/documents/stats")
async def documents_stats():
    from agent.vectorstore import get_collection_stats
    return get_collection_stats()


@app.delete("/documents/{source}")
async def documents_delete(source: str):
    from agent.vectorstore import delete_document
    return delete_document(source)


class FetchUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


@app.post("/documents/fetch-url")
async def documents_fetch_url(body: FetchUrlRequest):
    """Fetch text content from a URL for ingestion."""
    import httpx
    from urllib.parse import urlparse

    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Only http/https URLs are supported")

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, max_redirects=5) as client:
            resp = await client.get(body.url, headers={"User-Agent": "AgenticPlatform/1.0"})
            resp.raise_for_status()

            content_length = len(resp.content)
            if content_length > 512 * 1024:
                from fastapi import HTTPException
                raise HTTPException(status_code=413, detail="Content exceeds 512 KB limit")

            content_type = resp.headers.get("content-type", "")
            text = resp.text

            # Strip HTML tags for HTML content
            if "text/html" in content_type:
                import re
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()

            source_name = parsed.netloc + parsed.path
            if len(source_name) > 200:
                source_name = source_name[:200]

            return {
                "text": text,
                "source": source_name,
                "content_type": content_type,
                "size": content_length,
            }
    except httpx.HTTPStatusError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=f"URL returned {e.response.status_code}")
    except httpx.RequestError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")


# ── Model management endpoints ─────────────────────────────────────────────

@app.get("/models")
async def models_list():
    """List available Ollama models."""
    import httpx
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return {
                "models": [
                    {
                        "name": m.get("name", ""),
                        "size": m.get("size", 0),
                        "modified_at": m.get("modified_at", ""),
                        "digest": m.get("digest", "")[:12],
                    }
                    for m in models
                ],
                "current_model": os.getenv("OLLAMA_MODEL", "llama3"),
            }
    except Exception as e:
        return {"models": [], "error": str(e), "current_model": os.getenv("OLLAMA_MODEL", "llama3")}


@app.get("/tools")
async def tools_list():
    """List available tools."""
    from agent.tools import get_all_tools
    tools = get_all_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in tools
        ]
    }


# ── Skills CRUD endpoints ─────────────────────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    system_prompt: str = Field(default="", max_length=10000)
    tool_ids: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    tool_ids: list[str] | None = None
    constraints: list[str] | None = None


@app.get("/skills")
async def skills_list_endpoint():
    return {"skills": list_skills()}


@app.post("/skills")
async def skills_create_endpoint(body: SkillCreate):
    skill = create_skill(
        name=body.name, description=body.description,
        system_prompt=body.system_prompt, tool_ids=body.tool_ids,
        constraints=body.constraints,
    )
    return skill


@app.get("/skills/{skill_id}")
async def skills_get_endpoint(skill_id: str):
    skill = get_skill(skill_id)
    if not skill:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Skill not found"})
    return skill


@app.put("/skills/{skill_id}")
async def skills_update_endpoint(skill_id: str, body: SkillUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    skill = update_skill(skill_id, **updates)
    if not skill:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Skill not found"})
    return skill


@app.delete("/skills/{skill_id}")
async def skills_delete_endpoint(skill_id: str):
    ok = delete_skill(skill_id)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Skill not found"})
    return {"deleted": True}


# ── Prompts CRUD endpoints ────────────────────────────────────────────────

class PromptCreate(BaseModel):
    name: str
    content: str
    category: str = "general"
    description: str = ""
    tags: list[str] = Field(default_factory=list)

class PromptUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    category: str | None = None
    description: str | None = None
    tags: list[str] | None = None


@app.get("/prompts")
async def prompts_list_endpoint():
    return {"prompts": list_prompts()}


@app.post("/prompts")
async def prompts_create_endpoint(body: PromptCreate):
    prompt = create_prompt(
        name=body.name, content=body.content,
        category=body.category, description=body.description,
        tags=body.tags,
    )
    return prompt


@app.get("/prompts/{prompt_id}")
async def prompts_get_endpoint(prompt_id: str):
    prompt = get_prompt(prompt_id)
    if not prompt:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})
    return prompt


@app.put("/prompts/{prompt_id}")
async def prompts_update_endpoint(prompt_id: str, body: PromptUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    prompt = update_prompt(prompt_id, **updates)
    if not prompt:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})
    return prompt


@app.delete("/prompts/{prompt_id}")
async def prompts_delete_endpoint(prompt_id: str):
    ok = delete_prompt(prompt_id)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})
    return {"deleted": True}


# ── Agents CRUD endpoints ─────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    provider: str = Field(default="ollama")
    model: str = Field(default="llama3")
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: str = Field(default="", max_length=20000)
    skill_ids: list[str] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)
    kb_collection: str = Field(default="agentic_docs")
    max_iterations: int = Field(default=5, ge=1, le=20)
    memory_enabled: bool = Field(default=True)

class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    system_prompt: str | None = None
    skill_ids: list[str] | None = None
    tool_ids: list[str] | None = None
    kb_collection: str | None = None
    max_iterations: int | None = None
    memory_enabled: bool | None = None


@app.get("/agents")
async def agents_list_endpoint():
    return {"agents": list_agents()}


@app.post("/agents")
async def agents_create_endpoint(body: AgentCreate):
    agent = create_agent(
        name=body.name, description=body.description,
        provider=body.provider, model=body.model,
        temperature=body.temperature, system_prompt=body.system_prompt,
        skill_ids=body.skill_ids, tool_ids=body.tool_ids,
        kb_collection=body.kb_collection, max_iterations=body.max_iterations,
        memory_enabled=body.memory_enabled,
    )
    return agent


@app.get("/agents/{agent_id}")
async def agents_get_endpoint(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Agent not found"})
    return agent


@app.put("/agents/{agent_id}")
async def agents_update_endpoint(agent_id: str, body: AgentUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    agent = update_agent(agent_id, **updates)
    if not agent:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Agent not found"})
    return agent


@app.delete("/agents/{agent_id}")
async def agents_delete_endpoint(agent_id: str):
    ok = delete_agent(agent_id)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Agent not found or is default"})
    return {"deleted": True}


# ── A2A (Agent-to-Agent) endpoints ─────────────────────────────────────────

class A2APeerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=1000)
    capabilities: list[str] = Field(default_factory=list)

class A2APeerUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    description: str | None = None
    capabilities: list[str] | None = None

class A2ATaskRequest(BaseModel):
    peer_id: str = Field(..., description="Target peer ID")
    task: str = Field(..., min_length=1, max_length=4096)
    context: dict = Field(default_factory=dict)


@app.get("/a2a/peers")
async def a2a_list_peers():
    return {"peers": list_a2a_peers()}


@app.post("/a2a/peers")
async def a2a_create_peer(body: A2APeerCreate):
    peer = create_a2a_peer(
        name=body.name, url=body.url,
        description=body.description, capabilities=body.capabilities,
    )
    return peer


@app.get("/a2a/peers/{peer_id}")
async def a2a_get_peer(peer_id: str):
    peer = get_a2a_peer(peer_id)
    if not peer:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Peer not found"})
    return peer


@app.put("/a2a/peers/{peer_id}")
async def a2a_update_peer(peer_id: str, body: A2APeerUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    peer = update_a2a_peer(peer_id, **updates)
    if not peer:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Peer not found"})
    return peer


@app.delete("/a2a/peers/{peer_id}")
async def a2a_delete_peer(peer_id: str):
    ok = delete_a2a_peer(peer_id)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Peer not found"})
    return {"deleted": True}


@app.post("/a2a/peers/{peer_id}/ping")
async def a2a_ping_peer(peer_id: str):
    """Ping a peer agent to check connectivity and fetch its agent card."""
    import httpx
    peer = get_a2a_peer(peer_id)
    if not peer:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Peer not found"})
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try well-known agent card endpoint
            card_url = peer["url"].rstrip("/") + "/.well-known/agent.json"
            resp = await client.get(card_url)
            if resp.status_code == 200:
                agent_card = resp.json()
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                update_a2a_peer(peer_id, status="online", agent_card=agent_card, last_seen=now)
                return {"status": "online", "agent_card": agent_card}
            # Fallback: try /health
            health_url = peer["url"].rstrip("/") + "/health"
            resp = await client.get(health_url)
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            if resp.status_code == 200:
                update_a2a_peer(peer_id, status="online", last_seen=now)
                return {"status": "online", "health": resp.json()}
            update_a2a_peer(peer_id, status="unhealthy")
            return {"status": "unhealthy", "code": resp.status_code}
    except Exception as e:
        update_a2a_peer(peer_id, status="unreachable")
        return {"status": "unreachable", "error": str(e)}


@app.post("/a2a/send")
async def a2a_send_task(body: A2ATaskRequest):
    """Send a task to a peer agent via A2A protocol."""
    import httpx
    peer = get_a2a_peer(body.peer_id)
    if not peer:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Peer not found"})
    try:
        task_url = peer["url"].rstrip("/") + "/run"
        payload = {"prompt": body.task, **body.context}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(task_url, json=payload)
            resp.raise_for_status()
            return {"status": "completed", "peer": peer["name"], "response": resp.json()}
    except httpx.HTTPStatusError as exc:
        return {"status": "error", "peer": peer["name"], "code": exc.response.status_code, "error": str(exc)}
    except Exception as e:
        return {"status": "error", "peer": peer["name"], "error": str(e)}


@app.get("/a2a/card")
async def a2a_self_card():
    """Return this agent's own A2A agent card for discovery."""
    from agent.tools import get_all_tools
    tools = get_all_tools()
    agents = list_agents()
    return {
        "name": "Agentic Platform",
        "description": "Multi-agent AI platform with LangGraph ReAct engine",
        "version": "1.0.0",
        "url": os.getenv("AGENT_EXTERNAL_URL", "http://localhost:8010"),
        "protocols": ["a2a/1.0", "mcp/1.0"],
        "capabilities": {
            "streaming": True,
            "multi_turn": True,
            "tool_use": True,
            "rag": True,
        },
        "agents": [{"id": a["id"], "name": a["name"], "description": a["description"]} for a in agents],
        "tools": [{"name": t.name, "description": t.description} for t in tools],
    }


# ── MCP (Model Context Protocol) endpoints ────────────────────────────────

class MCPServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    transport: str = Field(default="stdio", pattern="^(stdio|sse|http)$")
    description: str = Field(default="", max_length=1000)

class MCPServerUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    transport: str | None = None
    description: str | None = None
    enabled: bool | None = None


@app.get("/mcp/servers")
async def mcp_list_servers():
    return {"servers": list_mcp_servers()}


@app.post("/mcp/servers")
async def mcp_create_server(body: MCPServerCreate):
    server = create_mcp_server(
        name=body.name, url=body.url,
        transport=body.transport, description=body.description,
    )
    return server


@app.get("/mcp/servers/{server_id}")
async def mcp_get_server(server_id: str):
    server = get_mcp_server(server_id)
    if not server:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "MCP server not found"})
    return server


@app.put("/mcp/servers/{server_id}")
async def mcp_update_server(server_id: str, body: MCPServerUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    server = update_mcp_server(server_id, **updates)
    if not server:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "MCP server not found"})
    return server


@app.delete("/mcp/servers/{server_id}")
async def mcp_delete_server(server_id: str):
    ok = delete_mcp_server(server_id)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "MCP server not found"})
    return {"deleted": True}


@app.post("/mcp/servers/{server_id}/discover")
async def mcp_discover_tools(server_id: str):
    """Discover available tools from an MCP server."""
    import httpx
    server = get_mcp_server(server_id)
    if not server:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "MCP server not found"})
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Try MCP tools/list endpoint
            tools_url = server["url"].rstrip("/") + "/tools/list"
            resp = await client.post(tools_url, json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
            if resp.status_code == 200:
                data = resp.json()
                tools = data.get("result", {}).get("tools", data.get("tools", []))
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                update_mcp_server(server_id, tools=tools, status="connected", last_seen=now)
                return {"status": "connected", "tools": tools}
            # Fallback: try /tools
            tools_url = server["url"].rstrip("/") + "/tools"
            resp = await client.get(tools_url)
            if resp.status_code == 200:
                data = resp.json()
                tools = data.get("tools", data if isinstance(data, list) else [])
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                update_mcp_server(server_id, tools=tools, status="connected", last_seen=now)
                return {"status": "connected", "tools": tools}
            return {"status": "error", "code": resp.status_code}
    except Exception as e:
        update_mcp_server(server_id, status="disconnected")
        return {"status": "disconnected", "error": str(e)}


@app.post("/mcp/servers/{server_id}/invoke")
async def mcp_invoke_tool(server_id: str, tool_name: str, arguments: dict = {}):
    """Invoke a tool on an MCP server."""
    import httpx
    server = get_mcp_server(server_id)
    if not server:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "MCP server not found"})
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            invoke_url = server["url"].rstrip("/") + "/tools/call"
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
                "id": 1,
            }
            resp = await client.post(invoke_url, json=payload)
            resp.raise_for_status()
            return {"status": "success", "result": resp.json()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
