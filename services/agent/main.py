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
from agent.memory import init_db, get_history, list_sessions, delete_session
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
        "req=%s session=%s prompt=%s",
        request_id,
        body.sessionId,
        body.prompt[:80],
    )

    result = await run_agent(
        prompt=body.prompt,
        session_id=body.sessionId,
        request_id=request_id,
    )

    logger.info("req=%s done tools=%s", request_id, result["tools_used"])
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
        "req=%s session=%s prompt=%s (stream)",
        request_id,
        body.sessionId,
        body.prompt[:80],
    )

    async def event_generator():
        async for event in run_agent_stream(
            prompt=body.prompt,
            session_id=body.sessionId,
            request_id=request_id,
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


# ── Document / RAG endpoints ───────────────────────────────────────────────

class DocumentIngestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    source: str = Field(..., min_length=1, max_length=500)
    metadata: dict = Field(default_factory=dict)
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)


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
