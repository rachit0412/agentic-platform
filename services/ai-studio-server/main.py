"""
AI Studio Server — Backend for AI-powered UI generation and agent invocation
- Accepts natural language UI descriptions
- Calls Agent Service to generate code
- Manages projects and sessions
- Proxies API calls from generated UIs to agents/n8n
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

AGENT_URL = os.getenv("AGENT_URL", "http://agent-service:8000")
N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")
STUDIO_PORT = int(os.getenv("STUDIO_PORT", "8020"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store projects in memory (in production, use database)
projects_db: dict[str, dict] = {}

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Studio Server",
    description="Generate and run UIs with AI agents",
    version="1.0.0"
)

# CORS for UI communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class UIPrompt(BaseModel):
    """User describes the UI they want"""
    description: str = Field(..., min_length=10, max_length=2048, description="Describe the UI")
    project_id: str | None = Field(None, description="Existing project or None for new")
    agent_id: str | None = Field(None, description="Agent to use for generation")


class AgentInvocation(BaseModel):
    """Generated UI calls an agent"""
    agent_id: str
    prompt: str
    session_id: str | None = None
    model: str | None = None


class WorkflowInvocation(BaseModel):
    """Generated UI invokes n8n workflow"""
    workflow_id: str
    data: dict[str, Any]


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    ui_code: str
    created_at: str
    updated_at: str
    preview_url: str


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-studio-server",
        "timestamp": datetime.now().isoformat(),
        "agent_service": AGENT_URL,
        "n8n_service": N8N_URL
    }


# ─────────────────────────────────────────────────────────────────────────────
# UI Generation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/studio/generate", response_model=ProjectResponse)
async def generate_ui(body: UIPrompt):
    """
    Generate a custom UI from a natural language description.

    Calls the Agent Service with a system prompt to generate HTML/React code.
    """
    project_id = body.project_id or str(uuid.uuid4())

    logger.info(f"Generating UI for project {project_id}: {body.description[:100]}")

    # System prompt to guide the agent in generating UI code
    system_prompt = """You are an expert web UI developer. The user will describe a web application.
Generate clean, modern, responsive HTML/CSS/JavaScript code that matches their description.

Requirements:
1. Generate ONLY the HTML/CSS/JavaScript code - no explanations
2. Use modern CSS with flexbox/grid
3. Include a data attribute on buttons/forms with data-action="agentCall" for agent invocation
4. For forms, include data-agent-id and data-prompt attributes
5. Use inline styles or <style> tag (no external imports except Tailwind CDN)
6. Include error handling and loading states
7. Make it dark-mode ready with CSS variables
8. The generated UI will run in an iframe - avoid localStorage/dangerous APIs

Output format: wrap everything in <html>, <head>, <body> tags."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AGENT_URL}/run/stream",
                json={
                    "prompt": f"Generate a web UI for: {body.description}",
                    "system_prompt": system_prompt,
                    "agent_id": body.agent_id or "default",
                    "session_id": project_id,
                },
                headers={"x-user-id": "ai-studio"}
            )
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Agent call failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent service error: {str(e)}")

    # For streaming, we'll collect the response
    ui_code = ""
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{AGENT_URL}/run/stream",
            json={
                "prompt": f"Generate a web UI for: {body.description}",
                "system_prompt": system_prompt,
                "agent_id": body.agent_id or "default",
                "session_id": project_id,
            },
            headers={"x-user-id": "ai-studio"}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "content" in data:
                            ui_code += data["content"]
                    except json.JSONDecodeError:
                        continue

    # Store project
    now = datetime.now().isoformat()
    projects_db[project_id] = {
        "id": project_id,
        "name": body.description[:50],
        "description": body.description,
        "ui_code": ui_code,
        "created_at": now,
        "updated_at": now,
    }

    return ProjectResponse(
        id=project_id,
        name=body.description[:50],
        description=body.description,
        ui_code=ui_code,
        created_at=now,
        updated_at=now,
        preview_url=f"/studio/preview/{project_id}"
    )


@app.post("/studio/generate/stream")
async def generate_ui_stream(body: UIPrompt):
    """
    Stream UI generation in real-time using Server-Sent Events.
    """
    project_id = body.project_id or str(uuid.uuid4())

    system_prompt = """You are an expert web UI developer. The user will describe a web application.
Generate clean, modern, responsive HTML/CSS/JavaScript code that matches their description.

Requirements:
1. Generate ONLY the HTML/CSS/JavaScript code - no explanations
2. Use modern CSS with flexbox/grid
3. Include a data attribute on buttons/forms with data-action="agentCall"
4. Use inline styles or <style> tag
5. Make it dark-mode ready with CSS variables
6. The generated UI will run in an iframe

Output format: wrap everything in <html>, <head>, <body> tags."""

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{AGENT_URL}/run/stream",
                    json={
                        "prompt": f"Generate a web UI for: {body.description}",
                        "system_prompt": system_prompt,
                        "agent_id": body.agent_id or "default",
                        "session_id": project_id,
                    },
                    headers={"x-user-id": "ai-studio"}
                ) as response:
                    ui_code = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if "content" in data:
                                    ui_code += data["content"]
                                    yield f"data: {json.dumps({'content': data['content'], 'project_id': project_id})}\n\n"
                            except json.JSONDecodeError:
                                continue

                    # Store final project
                    now = datetime.now().isoformat()
                    projects_db[project_id] = {
                        "id": project_id,
                        "name": body.description[:50],
                        "description": body.description,
                        "ui_code": ui_code,
                        "created_at": now,
                        "updated_at": now,
                    }
                    yield f"data: {json.dumps({'done': True, 'project_id': project_id})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/studio/preview/{project_id}")
async def preview_ui(project_id: str):
    """
    Serve the generated UI in an HTML wrapper with agent invocation support.
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]

    # Wrap generated UI with agent invocation layer
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project['name']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        [data-loading] {{ opacity: 0.6; pointer-events: none; }}
    </style>
</head>
<body>
    <div id="studio-root">
        {project['ui_code']}
    </div>

    <script>
        // Agent invocation proxy
        async function invokeAgent(agentId, prompt, sessionId = null) {{
            try {{
                const response = await fetch('/studio/invoke-agent', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        agent_id: agentId,
                        prompt: prompt,
                        session_id: sessionId
                    }})
                }});
                const data = await response.json();
                return data;
            }} catch (error) {{
                console.error('Agent call failed:', error);
                throw error;
            }}
        }}

        // Auto-wire agent buttons
        document.querySelectorAll('[data-action="agentCall"]').forEach(btn => {{
            btn.addEventListener('click', async (e) => {{
                e.preventDefault();
                const agentId = btn.dataset.agentId || 'default';
                const prompt = btn.dataset.prompt || btn.textContent;
                const sessionId = btn.dataset.sessionId || null;

                btn.setAttribute('data-loading', '');
                try {{
                    const result = await invokeAgent(agentId, prompt, sessionId);
                    // Dispatch event so UI can handle response
                    window.dispatchEvent(new CustomEvent('agentResponse', {{ detail: result }}));
                }} finally {{
                    btn.removeAttribute('data-loading');
                }}
            }});
        }});
    </script>
</body>
</html>"""

    return FileResponse(
        path=None,
        media_type="text/html",
        content=html.encode('utf-8')
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent/Workflow Invocation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/studio/invoke-agent")
async def invoke_agent(body: AgentInvocation):
    """
    Proxy agent invocations from generated UIs.
    """
    logger.info(f"Invoking agent {body.agent_id}: {body.prompt[:100]}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AGENT_URL}/run",
                json={
                    "prompt": body.prompt,
                    "agent_id": body.agent_id,
                    "session_id": body.session_id or str(uuid.uuid4()),
                    "model": body.model,
                },
                headers={"x-user-id": "ai-studio"}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")


@app.post("/studio/invoke-agent/stream")
async def invoke_agent_stream(body: AgentInvocation):
    """
    Stream agent response in real-time.
    """
    logger.info(f"Streaming agent {body.agent_id}: {body.prompt[:100]}")

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{AGENT_URL}/run/stream",
                    json={
                        "prompt": body.prompt,
                        "agent_id": body.agent_id,
                        "session_id": body.session_id or str(uuid.uuid4()),
                        "model": body.model,
                    },
                    headers={"x-user-id": "ai-studio"}
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/studio/invoke-workflow")
async def invoke_workflow(body: WorkflowInvocation):
    """
    Invoke an n8n workflow from a generated UI.
    """
    logger.info(f"Invoking n8n workflow {body.workflow_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # n8n webhook format: /webhook/{workflow_id}
            response = await client.post(
                f"{N8N_URL}/webhook/{body.workflow_id}",
                json=body.data
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Workflow invocation failed: {e}")
        raise HTTPException(status_code=502, detail=f"Workflow error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Project Management
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/studio/projects")
async def list_projects():
    """List all projects"""
    return {
        "projects": list(projects_db.values()),
        "total": len(projects_db)
    }


@app.get("/studio/projects/{project_id}")
async def get_project(project_id: str):
    """Get a single project"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects_db[project_id]


@app.delete("/studio/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    del projects_db[project_id]
    return {"deleted": project_id}


@app.post("/studio/projects/{project_id}/update")
async def update_project_code(project_id: str, body: dict):
    """
    Manually update project UI code (for UI editor).
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    if "ui_code" in body:
        projects_db[project_id]["ui_code"] = body["ui_code"]
        projects_db[project_id]["updated_at"] = datetime.now().isoformat()

    return projects_db[project_id]


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket for Real-time UI Updates (optional, for future use)
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/studio/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket for real-time collaboration and updates.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "update_code":
                if project_id in projects_db:
                    projects_db[project_id]["ui_code"] = message["code"]
                    projects_db[project_id]["updated_at"] = datetime.now().isoformat()
                    await websocket.send_json({"status": "saved"})

            elif message["type"] == "invoke_agent":
                # Can handle real-time agent calls via WebSocket too
                await websocket.send_json({"status": "processing"})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {project_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=STUDIO_PORT)
