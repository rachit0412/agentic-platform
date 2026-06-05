"""
Agent Service — FastAPI + LangGraph
Accepts prompts, runs an agent loop (tool-calling + Ollama), returns responses.
"""

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager

from agent.connectors import CONNECTOR_CATALOG, generate_connector_id, generate_job_id
from agent.connectors.sync_engine import run_sync, test_connector
from agent.graph import run_agent, run_agent_stream
from agent.llm import (
    get_active_model,
    list_available_embedding_providers,
    list_available_models,
    set_active_model,
)
from agent.memory import _get_conn  # Persona management
from agent.memory import (
    add_workspace_member,
    assign_persona,
    authenticate_user,
    create_a2a_peer,
    create_agent,
    create_connector,
    create_custom_tool,
    create_document_registry,
    create_mcp_server,
    create_persona,
    create_pipeline,
    create_pipeline_run,
    create_prompt,
    create_skill,
    create_sync_job,
    create_user,
    create_workspace,
    delete_a2a_peer,
    delete_agent,
    delete_connector,
    delete_custom_tool,
    delete_document_registry,
    delete_document_registry_by_source,
    delete_documents_by_collection,
    delete_mcp_server,
    delete_persona,
    delete_pipeline,
    delete_prompt,
    delete_session,
    delete_skill,
    delete_user,
    delete_workspace,
    export_all_data,
    get_a2a_peer,
    get_agent,
    get_connector,
    get_custom_tool,
    get_db_stats,
    get_disabled_tools,
    get_document_registry,
    get_guardrail,
    get_history,
    get_llm_usage_summary,
    get_mcp_server,
    get_memory_stats,
    get_persona,
    get_pipeline,
    get_prompt,
    get_session_summary,
    get_skill,
    get_user,
    get_user_by_email,
    get_user_by_username,
    get_user_personas,
    get_version,
    get_workspace,
    import_all_data,
    init_db,
    list_a2a_peers,
    list_agents,
    list_audit_log,
    list_connectors,
    list_custom_tools,
    list_documents_registry,
    list_folders,
    list_guardrails,
    list_llm_usage,
    list_mcp_servers,
    list_personas,
    list_pipeline_runs,
    list_pipelines,
    list_prompts,
    list_sessions,
    list_skills,
    list_sync_jobs,
    list_users,
    list_versions,
    list_workspace_members,
    list_workspaces,
    log_audit,
    remove_workspace_member,
    resend_verification_code,
    reset_user_password,
    save_version,
    set_disabled_tools,
    tag_document_to_agent,
    unassign_persona,
    untag_all_for_agent,
    untag_document_from_agent,
    update_a2a_peer,
    update_agent,
    update_connector,
    update_custom_tool,
    update_document_registry,
    update_guardrail,
    update_mcp_server,
    update_persona,
    update_pipeline,
    update_pipeline_run,
    update_prompt,
    update_skill,
    update_sync_job,
    update_user,
    update_workspace,
    verify_user_email,
)
from agent.observability import setup_otel
from agent.workspace import current_user_id, current_user_role, current_workspace_id
from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("agent-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise resources on startup."""
    init_db()
    stats = get_db_stats()
    logger.info("Memory DB initialised at %s", stats.get("db_path", "unknown"))
    logger.info(
        "DB stats: %s agents, %s skills, %s prompts, %s conversations, %s documents",
        stats.get("agents", 0),
        stats.get("skills", 0),
        stats.get("prompts", 0),
        stats.get("conversations", 0),
        stats.get("documents", 0),
    )
    yield


app = FastAPI(title="Agent Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def workspace_middleware(request: Request, call_next):
    """Extract workspace context from request headers for multi-tenant scoping."""
    ws_id = request.headers.get("x-workspace-id", "default")
    user_id = request.headers.get("x-user-id", "system")
    user_role = request.headers.get("x-user-role", "admin")
    ws_token = current_workspace_id.set(ws_id)
    uid_token = current_user_id.set(user_id)
    role_token = current_user_role.set(user_role)
    try:
        response = await call_next(request)
        return response
    finally:
        current_workspace_id.reset(ws_token)
        current_user_id.reset(uid_token)
        current_user_role.reset(role_token)


# Wire observability
setup_otel(app)


# ── Models ──────────────────────────────────────────────────────────────────
class RunRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    sessionId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str | None = Field(
        default=None, description="Model name to use (e.g. llama3, mistral)"
    )
    provider: str | None = Field(
        default=None, description="Provider: ollama or azure-openai"
    )
    agent_id: str | None = Field(default=None, description="Agent config ID to use")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    system_prompt: str | None = Field(default=None, max_length=8192)
    max_completion_tokens: int | None = Field(
        default=None, ge=1, le=32768, description="Max tokens in response"
    )
    use_kb: bool = Field(
        default=True, description="Whether to search the Knowledge Base for context"
    )
    memory_window: int | None = Field(
        default=None, ge=1, le=50, description="Number of past messages to include"
    )


class RunResponse(BaseModel):
    sessionId: str
    response: str
    tools_used: list[str] = []
    request_id: str
    trace_id: str | None = None
    guardrails: dict | None = None


# ── Endpoints ───────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-service"}


# ── Authentication ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


# ── Login Rate Limiting (in-memory, per-IP) ─────────────────────────────────
import time as _time

_login_attempts: dict[str, list[float]] = {}
_LOGIN_WINDOW = 300  # 5-minute window
_LOGIN_MAX_ATTEMPTS = 5  # max 5 attempts per window


def _check_rate_limit(client_ip: str) -> bool:
    """Return True if the client has exceeded login attempt limits."""
    now = _time.time()
    attempts = _login_attempts.get(client_ip, [])
    # Prune old entries
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW]
    _login_attempts[client_ip] = attempts
    return len(attempts) >= _LOGIN_MAX_ATTEMPTS


def _record_attempt(client_ip: str):
    _login_attempts.setdefault(client_ip, []).append(_time.time())


@app.post("/auth/login")
async def auth_login(body: LoginRequest, request: Request):
    from fastapi.responses import JSONResponse

    client_ip = (
        request.headers.get(
            "x-forwarded-for", request.client.host if request.client else "unknown"
        )
        .split(",")[0]
        .strip()
    )
    if _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many login attempts. Try again in 5 minutes."},
        )
    user = authenticate_user(body.username, body.password)
    if not user:
        _record_attempt(client_ip)
        remaining = _LOGIN_MAX_ATTEMPTS - len(_login_attempts.get(client_ip, []))
        return JSONResponse(
            status_code=401,
            content={
                "error": "Invalid credentials",
                "remaining_attempts": max(remaining, 0),
            },
        )
    # Check if email verification is required
    if isinstance(user, dict) and user.get("error") == "email_not_verified":
        return JSONResponse(
            status_code=403,
            content={
                "error": "Email not verified. Please verify your email to continue.",
                "code": "email_not_verified",
                "user_id": user.get("user_id", ""),
                "email": user.get("email", ""),
            },
        )
    # Clear attempts on successful login
    _login_attempts.pop(client_ip, None)
    return user


@app.get("/auth/me")
async def auth_me(request: Request):
    user_id = request.headers.get("x-user-id", "")
    if not user_id or user_id == "system":
        return {"error": "Not authenticated"}
    user = get_user(user_id)
    if not user:
        user = get_user_by_username(user_id)
    return user if user else {"error": "User not found"}


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = ""
    email: str = ""


@app.post("/auth/register")
async def auth_register(body: RegisterRequest):
    from fastapi.responses import JSONResponse

    existing = get_user_by_username(body.username)
    if existing:
        return JSONResponse(
            status_code=409, content={"error": "Username already exists"}
        )
    if body.email:
        existing_email = get_user_by_email(body.email)
        if existing_email:
            return JSONResponse(
                status_code=409,
                content={"error": "An account with this email already exists"},
            )
    user = create_user(
        username=body.username,
        password=body.password,
        display_name=body.display_name or body.username,
        email=body.email,
        role="member",
        default_workspace="default",
    )
    if isinstance(user, dict) and user.get("error") == "email_already_used":
        return JSONResponse(
            status_code=409,
            content={"error": "An account with this email already exists"},
        )
    # Return user with verification_code so the UI can show the code
    # (In production, you'd send this via email instead)
    return user


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=128)


@app.post("/auth/forgot-password")
async def auth_forgot_password(body: ForgotPasswordRequest):
    from fastapi.responses import JSONResponse

    user = get_user_by_username(body.identifier)
    if not user:
        user = get_user_by_email(body.identifier)
    if not user:
        return JSONResponse(
            status_code=404,
            content={"error": "No account found with that username or email."},
        )
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email", ""),
    }


class ResetPasswordRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=128)


@app.post("/auth/reset-password")
async def auth_reset_password(body: ResetPasswordRequest):
    from fastapi.responses import JSONResponse

    user = reset_user_password(body.user_id, body.new_password)
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    return {"success": True, "username": user["username"]}


class VerifyEmailRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=6, max_length=6)


@app.post("/auth/verify-email")
async def auth_verify_email(body: VerifyEmailRequest):
    from fastapi.responses import JSONResponse

    result = verify_user_email(body.user_id, body.code)
    if not result:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    if isinstance(result, dict) and result.get("error") == "invalid_code":
        return JSONResponse(
            status_code=400, content={"error": "Invalid verification code"}
        )
    return {"success": True, "username": result["username"]}


class ResendCodeRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)


@app.post("/auth/resend-code")
async def auth_resend_code(body: ResendCodeRequest):
    from fastapi.responses import JSONResponse

    result = resend_verification_code(body.user_id)
    if not result:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    # In production, send the code via email. For now, return it in response.
    return {
        "success": True,
        "verification_code": result["verification_code"],
        "email": result["email"],
    }


# ── SSO Login (find-or-create user by provider email) ───────────────────────
class SSOLoginRequest(BaseModel):
    provider: str = Field(..., description="SSO provider: google, github, microsoft")
    provider_id: str = Field(..., description="Unique ID from the provider")
    email: str = Field(..., description="Email from the provider profile")
    display_name: str = Field(default="", description="Display name from provider")


@app.post("/auth/sso-login")
async def auth_sso_login(body: SSOLoginRequest):
    from fastapi.responses import JSONResponse

    if not body.email:
        return JSONResponse(
            status_code=400, content={"error": "Email is required from SSO provider"}
        )

    # Try to find existing user by email
    user = get_user_by_email(body.email)
    if user:
        return user

    # Create new user from SSO (pre-verified, random password since they use SSO)
    import secrets

    random_pw = secrets.token_urlsafe(32)
    username = body.email.split("@")[0]
    # Ensure unique username
    base = username
    suffix = 1
    while get_user_by_username(username):
        username = f"{base}{suffix}"
        suffix += 1

    user = create_user(
        username=username,
        password=random_pw,
        display_name=body.display_name or username,
        email=body.email,
        role="member",
        default_workspace="default",
        pre_verified=True,
    )
    return user


# ── User Management (admin-only enforced by UI) ────────────────────────────
@app.get("/users")
async def list_users_endpoint():
    return {"users": list_users()}


@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: str):
    user = get_user(user_id)
    if not user:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "User not found"})
    return user


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)
    display_name: str = ""
    email: str = ""
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")
    default_workspace: str = "default"


@app.post("/users")
async def create_user_endpoint(body: UserCreate):
    from fastapi.responses import JSONResponse

    existing = get_user_by_username(body.username)
    if existing:
        return JSONResponse(
            status_code=409, content={"error": "Username already exists"}
        )
    if body.email:
        existing_email = get_user_by_email(body.email)
        if existing_email:
            return JSONResponse(
                status_code=409,
                content={"error": "An account with this email already exists"},
            )
    user = create_user(
        username=body.username,
        password=body.password,
        display_name=body.display_name,
        email=body.email,
        role=body.role,
        default_workspace=body.default_workspace,
        pre_verified=True,
    )
    if isinstance(user, dict) and user.get("error") == "email_already_used":
        return JSONResponse(
            status_code=409,
            content={"error": "An account with this email already exists"},
        )
    return user


class UserUpdate(BaseModel):
    display_name: str | None = None
    email: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|member|viewer)$")
    password: str | None = None
    is_active: bool | None = None
    default_workspace: str | None = None


@app.put("/users/{user_id}")
async def update_user_endpoint(user_id: str, body: UserUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    user = update_user(user_id, **updates)
    if not user:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "User not found"})
    if isinstance(user, dict) and user.get("error") == "email_already_used":
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=409,
            content={"error": "An account with this email already exists"},
        )
    return user


@app.delete("/users/{user_id}")
async def delete_user_endpoint(user_id: str):
    if user_id == "admin":
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=403, content={"error": "Cannot delete admin user"}
        )
    ok = delete_user(user_id)
    return {"deleted": ok}


@app.post("/users/{user_id}/verify")
async def admin_verify_user_endpoint(user_id: str):
    """Admin action: mark a user's email as verified."""
    from fastapi.responses import JSONResponse

    user = get_user(user_id)
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    conn = _get_conn()
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET email_verified = 1, verification_code = '', updated_at = ? WHERE id = ?",
        (now, user_id),
    )
    conn.commit()
    return {"success": True, "username": user["username"]}


# ── Persona Management ────────────────────────────────────────────────────
@app.get("/personas")
async def list_personas_endpoint():
    return {"personas": list_personas()}


@app.get("/personas/{persona_id}")
async def get_persona_endpoint(persona_id: str):
    p = get_persona(persona_id)
    if not p:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Persona not found"})
    return p


@app.post("/personas")
async def create_persona_endpoint(request: Request):
    from fastapi.responses import JSONResponse

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return JSONResponse(status_code=400, content={"error": "name is required"})
    try:
        p = create_persona(
            name=name,
            description=body.get("description", ""),
            permissions=body.get("permissions"),
        )
        return p
    except Exception as e:
        return JSONResponse(status_code=409, content={"error": str(e)})


@app.put("/personas/{persona_id}")
async def update_persona_endpoint(persona_id: str, request: Request):
    from fastapi.responses import JSONResponse

    body = await request.json()
    p = update_persona(
        persona_id,
        name=body.get("name"),
        description=body.get("description"),
        permissions=body.get("permissions"),
    )
    if not p:
        return JSONResponse(status_code=404, content={"error": "Persona not found"})
    return p


@app.delete("/personas/{persona_id}")
async def delete_persona_endpoint(persona_id: str):
    from fastapi.responses import JSONResponse

    ok = delete_persona(persona_id)
    if not ok:
        return JSONResponse(
            status_code=400, content={"error": "Cannot delete system persona"}
        )
    return {"success": True}


@app.get("/users/{user_id}/personas")
async def get_user_personas_endpoint(user_id: str):
    return {"personas": get_user_personas(user_id)}


@app.post("/users/{user_id}/personas")
async def assign_persona_endpoint(user_id: str, request: Request):
    from fastapi.responses import JSONResponse

    body = await request.json()
    persona_id = body.get("persona_id", "").strip()
    if not persona_id:
        return JSONResponse(
            status_code=400, content={"error": "persona_id is required"}
        )
    ok = assign_persona(user_id, persona_id)
    if not ok:
        return JSONResponse(
            status_code=409, content={"error": "Already assigned or invalid"}
        )
    return {"success": True}


@app.delete("/users/{user_id}/personas/{persona_id}")
async def unassign_persona_endpoint(user_id: str, persona_id: str):
    ok = unassign_persona(user_id, persona_id)
    return {"success": ok}


# ── Workspace Management ───────────────────────────────────────────────────
@app.get("/workspaces")
async def list_workspaces_endpoint():
    return list_workspaces()


@app.get("/workspaces/{workspace_id}")
async def get_workspace_endpoint(workspace_id: str):
    ws = get_workspace(workspace_id)
    if not ws:
        return {"error": "Workspace not found"}, 404
    return ws


@app.post("/workspaces")
async def create_workspace_endpoint(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return {"error": "name is required"}
    return create_workspace(name=name, description=body.get("description", ""))


@app.put("/workspaces/{workspace_id}")
async def update_workspace_endpoint(workspace_id: str, request: Request):
    body = await request.json()
    ws = update_workspace(workspace_id, **body)
    if not ws:
        return {"error": "Workspace not found"}
    return ws


@app.delete("/workspaces/{workspace_id}")
async def delete_workspace_endpoint(workspace_id: str):
    if workspace_id == "default":
        return {"error": "Cannot delete default workspace"}
    ok = delete_workspace(workspace_id)
    return {"deleted": ok}


@app.get("/workspaces/{workspace_id}/members")
async def list_members_endpoint(workspace_id: str):
    return list_workspace_members(workspace_id)


@app.post("/workspaces/{workspace_id}/members")
async def add_member_endpoint(workspace_id: str, request: Request):
    body = await request.json()
    user_id = body.get("user_id", "").strip()
    if not user_id:
        return {"error": "user_id is required"}
    role = body.get("role", "member")
    return add_workspace_member(workspace_id, user_id, role)


@app.delete("/workspaces/{workspace_id}/members/{user_id}")
async def remove_member_endpoint(workspace_id: str, user_id: str):
    ok = remove_workspace_member(workspace_id, user_id)
    return {"removed": ok}


@app.get("/db-stats")
async def db_stats_endpoint():
    return get_db_stats()


@app.get("/export")
async def export_endpoint():
    data = export_all_data()
    return {"export": data, "stats": get_db_stats()}


@app.post("/import")
async def import_endpoint(request: Request):
    body = await request.json()
    data = body.get("export", body)
    merge = body.get("merge", True)
    stats = import_all_data(data, merge=merge)
    return {"status": "ok", "import_stats": stats}


@app.post("/run", response_model=RunResponse)
async def run(body: RunRequest, request: Request):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
    logger.info(
        "req=%s session=%s prompt=%s provider=%s model=%s agent=%s",
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
            temperature=body.temperature,
            top_p=body.top_p,
            max_completion_tokens=body.max_completion_tokens,
        )

    # Load agent config if specified
    agent_config = None
    if body.agent_id:
        agent_config = get_agent(body.agent_id)
        if agent_config and not (body.provider or body.model):
            from agent.llm import set_active_model as _switch

            _switch(
                provider=agent_config.get("provider", "ollama"),
                model=agent_config.get("model", "llama3"),
                temperature=(
                    body.temperature
                    if body.temperature is not None
                    else agent_config.get("temperature")
                ),
                top_p=(
                    body.top_p if body.top_p is not None else agent_config.get("top_p")
                ),
                max_completion_tokens=body.max_completion_tokens,
            )

    # Build agent_config for run_agent (same pattern as /run/stream)
    if agent_config is None:
        agent_config = {}
    # If user explicitly chose provider/model, override agent defaults
    if body.provider:
        agent_config["provider"] = body.provider
    if body.model:
        agent_config["model"] = body.model
    agent_config["use_kb"] = body.use_kb if hasattr(body, "use_kb") else True
    if body.temperature is not None:
        agent_config["temperature"] = body.temperature
    if body.top_p is not None:
        agent_config["top_p"] = body.top_p
    if body.system_prompt:
        agent_config["system_prompt"] = body.system_prompt
    if hasattr(body, "memory_window") and body.memory_window is not None:
        agent_config["memory_window"] = body.memory_window

    result = await run_agent(
        prompt=body.prompt,
        session_id=body.sessionId,
        request_id=request_id,
        agent_config=agent_config,
    )

    active = get_active_model()
    logger.info(
        "req=%s done tools=%s model=%s/%s",
        request_id,
        result["tools_used"],
        active["provider"],
        active["model"],
    )
    return RunResponse(
        sessionId=body.sessionId,
        response=result["response"],
        tools_used=result["tools_used"],
        request_id=request_id,
        trace_id=result.get("trace_id"),
        guardrails=result.get("guardrails"),
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
            temperature=body.temperature,
            top_p=body.top_p,
            max_completion_tokens=body.max_completion_tokens,
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
                temperature=(
                    body.temperature
                    if body.temperature is not None
                    else agent_config.get("temperature")
                ),
                top_p=(
                    body.top_p if body.top_p is not None else agent_config.get("top_p")
                ),
                max_completion_tokens=body.max_completion_tokens,
            )

    # Override agent config with request-level params
    if agent_config is None:
        agent_config = {}
    # If user explicitly chose provider/model, override agent defaults
    if body.provider:
        agent_config["provider"] = body.provider
    if body.model:
        agent_config["model"] = body.model
    agent_config["use_kb"] = body.use_kb
    if body.temperature is not None:
        agent_config["temperature"] = body.temperature
    if body.top_p is not None:
        agent_config["top_p"] = body.top_p
    if body.system_prompt:
        agent_config["system_prompt"] = body.system_prompt
    if body.memory_window is not None:
        agent_config["memory_window"] = body.memory_window

    async def event_generator():
        async for event in run_agent_stream(
            prompt=body.prompt,
            session_id=body.sessionId,
            request_id=request_id,
            agent_config=agent_config,
        ):
            # Always JSON-encode to keep SSE frames newline-safe
            data = json.dumps(event["data"])
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
    embed_providers = list_available_embedding_providers()
    return {
        "models": models,
        "active": active,
        "available_embedding_providers": embed_providers,
    }


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


class EmbeddingSwitchRequest(BaseModel):
    provider: str
    model: str


@app.post("/models/embedding")
async def models_embedding_switch(body: EmbeddingSwitchRequest):
    """Switch the embedding provider and model."""
    from agent.llm import set_embedding_model

    active = set_embedding_model(body.provider, body.model)
    logger.info("Embedding switched to %s/%s", body.provider, body.model)
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
    folder: str = Field(default="/", max_length=500)
    agent_id: str | None = Field(default=None, max_length=100)


class DocumentUploadRequest(BaseModel):
    """Upload a file to staging (does NOT index to ChromaDB immediately)."""

    filename: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=500000)
    folder: str = Field(default="/", max_length=500)
    agent_id: str | None = Field(default=None, max_length=100)
    metadata: dict = Field(default_factory=dict)
    collection: str = Field(default="agentic_docs", max_length=200)


class DocumentConnectRequest(BaseModel):
    """Connect an external URL as a document reference (fetches content on demand)."""

    url: str = Field(..., min_length=1, max_length=2048)
    name: str | None = Field(default=None, max_length=500)
    folder: str = Field(default="/", max_length=500)
    agent_id: str | None = Field(default=None, max_length=100)
    collection: str = Field(default="agentic_docs", max_length=200)


class DocumentShortcutRequest(BaseModel):
    """Create a shortcut/reference to an existing document."""

    target_doc_id: str = Field(..., min_length=1, max_length=100)
    folder: str = Field(default="/", max_length=500)
    name: str | None = Field(default=None, max_length=500)


class DocumentIndexRequest(BaseModel):
    """Trigger indexing of a staged document into ChromaDB."""

    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    collection: str | None = Field(default=None, max_length=200)


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=50)


# ── Upload to staging (enterprise pattern) ─────────────────────────────────


@app.post("/documents/upload")
async def documents_upload(body: DocumentUploadRequest):
    """Upload a file to the staging file store. Does NOT index to ChromaDB.
    The file sits in staging until explicitly indexed."""
    from agent.filestore import save_file

    file_ext = body.filename.rsplit(".", 1)[-1].lower() if "." in body.filename else ""
    agent_tags = [body.agent_id] if body.agent_id else []

    # Create registry entry first to get the doc_id
    doc = create_document_registry(
        name=body.filename,
        source=body.filename,
        collection=body.collection,
        folder=body.folder,
        agent_tags=agent_tags,
        file_type=file_ext,
        file_size=len(body.content),
        chunk_count=0,
        metadata=body.metadata,
        status="uploaded",
        source_type="upload",
        storage_path="",
    )

    # Save file to disk
    store_result = save_file(doc["id"], body.filename, body.content)
    update_document_registry(doc["id"], storage_path=store_result["storage_path"])
    doc["storage_path"] = store_result["storage_path"]
    doc["status"] = "uploaded"

    return {
        "id": doc["id"],
        "name": doc["name"],
        "status": "uploaded",
        "storage_path": store_result["storage_path"],
        "size_bytes": store_result["size_bytes"],
        "message": "File staged successfully. Use POST /documents/{id}/index to index into knowledge base.",
    }


@app.post("/documents/connect")
async def documents_connect(body: DocumentConnectRequest):
    """Connect an external URL as a document reference.
    Content is fetched and stored locally but NOT indexed until triggered."""
    from urllib.parse import urlparse

    import httpx
    from agent.filestore import save_file

    parsed = urlparse(body.url)
    if not parsed.scheme or not parsed.netloc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid URL")

    # Fetch the content
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(body.url)
            resp.raise_for_status()
            text = resp.text
    except httpx.HTTPStatusError as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=502, detail=f"URL returned {e.response.status_code}"
        )
    except httpx.RequestError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")

    source_name = body.name or parsed.path.split("/")[-1] or parsed.netloc
    file_ext = source_name.rsplit(".", 1)[-1].lower() if "." in source_name else "html"
    agent_tags = [body.agent_id] if body.agent_id else []

    doc = create_document_registry(
        name=source_name,
        source=body.url,
        collection=body.collection,
        folder=body.folder,
        agent_tags=agent_tags,
        file_type=file_ext,
        file_size=len(text),
        chunk_count=0,
        metadata={
            "url": body.url,
            "content_type": resp.headers.get("content-type", ""),
        },
        status="uploaded",
        source_type="connected",
        storage_path="",
    )

    # Store fetched content locally
    store_result = save_file(doc["id"], source_name, text)
    update_document_registry(doc["id"], storage_path=store_result["storage_path"])

    return {
        "id": doc["id"],
        "name": source_name,
        "status": "uploaded",
        "source_type": "connected",
        "url": body.url,
        "size_bytes": store_result["size_bytes"],
        "message": "URL content fetched and staged. Use POST /documents/{id}/index to index.",
    }


@app.post("/documents/shortcut")
async def documents_shortcut(body: DocumentShortcutRequest):
    """Create a shortcut (reference) to an existing document.
    Shortcuts don't duplicate data — they point to the original."""
    target = get_document_registry(body.target_doc_id)
    if not target:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Target document not found")

    shortcut_name = body.name or f"↗ {target['name']}"
    doc = create_document_registry(
        name=shortcut_name,
        source=target["source"],
        collection=target["collection"],
        folder=body.folder,
        agent_tags=target["agent_tags"],
        file_type=target["file_type"],
        file_size=target["file_size"],
        chunk_count=target["chunk_count"],
        metadata={"shortcut_to": body.target_doc_id, "original_name": target["name"]},
        status=target["status"],
        source_type="shortcut",
        shortcut_ref=body.target_doc_id,
    )

    return {
        "id": doc["id"],
        "name": shortcut_name,
        "source_type": "shortcut",
        "target_id": body.target_doc_id,
        "target_name": target["name"],
        "message": "Shortcut created. References the same indexed content as the original.",
    }


@app.post("/documents/{doc_id}/index")
async def documents_index(doc_id: str, body: DocumentIndexRequest):
    """Process a staged document and index it into ChromaDB.
    This is the explicit step that moves content from file store → vector DB."""
    from agent.filestore import read_file as fs_read_file
    from agent.vectorstore import ingest_document

    doc = get_document_registry(doc_id)
    if not doc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Document not found")

    if doc["source_type"] == "shortcut":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="Cannot index a shortcut. Index the original document.",
        )

    # Update status to processing
    update_document_registry(doc_id, status="processing")

    # Read content from file store
    text = fs_read_file(doc_id, doc["name"])
    if not text:
        update_document_registry(doc_id, status="failed")
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="File content not found in store. Re-upload required.",
        )

    collection = body.collection or doc["collection"]
    try:
        # Use LlamaIndex parser for rich file types (PDF, DOCX, XLSX, etc.)
        file_ext = (
            os.path.splitext(doc["name"])[1].lower() if "." in doc["name"] else ""
        )
        from agent.llamaindex_loader import SUPPORTED_EXTENSIONS, parse_file_bytes

        if file_ext in SUPPORTED_EXTENSIONS and file_ext not in (".txt", ".md", ""):
            parsed_docs = parse_file_bytes(
                content=text.encode("utf-8") if isinstance(text, str) else text,
                filename=doc["name"],
                metadata=doc.get("metadata", {}),
            )
            total_chunks = 0
            for pdoc in parsed_docs:
                if pdoc.get("text"):
                    r = ingest_document(
                        text=pdoc["text"],
                        source=doc["source"],
                        metadata=pdoc.get("metadata", {}),
                        chunk_size=body.chunk_size,
                        chunk_overlap=body.chunk_overlap,
                        collection_name=collection,
                    )
                    total_chunks += r.get("chunks", 0)
            result = {"chunks": total_chunks}
        else:
            result = ingest_document(
                text=text,
                source=doc["source"],
                metadata=doc.get("metadata", {}),
                chunk_size=body.chunk_size,
                chunk_overlap=body.chunk_overlap,
                collection_name=collection,
            )
        update_document_registry(
            doc_id,
            status="indexed",
            chunk_count=result.get("chunks", 0),
        )
        return {
            "id": doc_id,
            "name": doc["name"],
            "status": "indexed",
            "chunks": result.get("chunks", 0),
            "collection": collection,
            "message": "Document indexed successfully into knowledge base.",
        }
    except Exception as e:
        update_document_registry(doc_id, status="failed")
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


# ── Legacy direct ingest (backward compatible) ─────────────────────────────


@app.post("/documents/ingest")
async def documents_ingest(body: DocumentIngestRequest):
    """Direct ingest into ChromaDB (legacy). For enterprise workflow, use
    POST /documents/upload followed by POST /documents/{id}/index."""
    from agent.filestore import save_file
    from agent.vectorstore import ingest_document

    result = ingest_document(
        text=body.text,
        source=body.source,
        metadata=body.metadata,
        chunk_size=body.chunk_size,
        chunk_overlap=body.chunk_overlap,
        collection_name=body.collection,
    )
    # Create registry record
    file_ext = body.source.rsplit(".", 1)[-1].lower() if "." in body.source else ""
    agent_tags = [body.agent_id] if body.agent_id else []
    doc = create_document_registry(
        name=body.source,
        source=body.source,
        collection=body.collection,
        folder=body.folder,
        agent_tags=agent_tags,
        file_type=file_ext,
        file_size=len(body.text),
        chunk_count=result.get("chunks", 0),
        metadata=body.metadata,
        status="indexed",
        source_type="upload",
    )
    # Also save to file store for future reference
    save_file(doc["id"], body.source, body.text)
    update_document_registry(
        doc["id"], storage_path=f"/data/filestore/{doc['id']}/{body.source}"
    )
    return result


@app.post("/documents/search")
async def documents_search(body: DocumentSearchRequest):
    from agent.vectorstore import search_similar

    results = search_similar(body.query, k=body.k)
    return {"query": body.query, "results": results, "count": len(results)}


@app.get("/documents")
async def documents_list(collection: str | None = None):
    from agent.vectorstore import list_documents

    return {"documents": list_documents(collection)}


@app.get("/documents/stats")
async def documents_stats():
    from agent.filestore import get_storage_stats
    from agent.vectorstore import get_collection_stats

    chroma_stats = get_collection_stats()
    store_stats = get_storage_stats()
    # Count by status from registry
    docs = list_documents_registry()
    status_counts = {}
    for d in docs:
        s = d.get("status", "uploaded")
        status_counts[s] = status_counts.get(s, 0) + 1
    return {
        **chroma_stats,
        "file_store": store_stats,
        "status_counts": status_counts,
        "total_registry": len(docs),
    }


@app.delete("/documents/{source}")
async def documents_delete(source: str, collection: str | None = None):
    from agent.vectorstore import delete_document

    coll = collection or "agentic_docs"
    result = delete_document(
        source, collection_name=coll if coll != "agentic_docs" else None
    )
    delete_document_registry_by_source(source, coll)
    return result


class FetchUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


@app.post("/documents/fetch-url")
async def documents_fetch_url(body: FetchUrlRequest):
    """Fetch text content from a URL for ingestion."""
    from urllib.parse import urlparse

    import httpx

    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https"):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400, detail="Only http/https URLs are supported"
        )

    try:
        async with httpx.AsyncClient(
            timeout=10.0, follow_redirects=True, max_redirects=5
        ) as client:
            resp = await client.get(
                body.url, headers={"User-Agent": "AgenticPlatform/1.0"}
            )
            resp.raise_for_status()

            content_length = len(resp.content)
            if content_length > 512 * 1024:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=413, detail="Content exceeds 512 KB limit"
                )

            content_type = resp.headers.get("content-type", "")
            text = resp.text

            # Strip HTML tags for HTML content
            if "text/html" in content_type:
                import re

                text = re.sub(
                    r"<script[^>]*>.*?</script>",
                    "",
                    text,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                text = re.sub(
                    r"<style[^>]*>.*?</style>",
                    "",
                    text,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()

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

        raise HTTPException(
            status_code=502, detail=f"URL returned {e.response.status_code}"
        )
    except httpx.RequestError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")


@app.get("/documents/collections")
async def documents_collections():
    """List all ChromaDB collections with doc counts."""
    from agent.vectorstore import list_collections

    return {"collections": list_collections()}


class CopyDocsRequest(BaseModel):
    sources: list[str] = Field(..., min_length=1)
    from_collection: str = Field(..., min_length=1, max_length=200)
    to_collection: str = Field(..., min_length=1, max_length=200)


@app.post("/documents/copy")
async def documents_copy(body: CopyDocsRequest):
    """Copy documents from one collection to another (for KB reuse)."""
    from agent.vectorstore import copy_documents_to_collection

    result = copy_documents_to_collection(
        body.sources, body.from_collection, body.to_collection
    )
    return result


# ── Document Registry endpoints ────────────────────────────────────────────


@app.get("/documents/registry")
async def documents_registry(
    folder: str | None = None,
    agent_id: str | None = None,
    search: str | None = None,
    collection: str | None = None,
):
    """List all documents in the registry with optional filters."""
    docs = list_documents_registry(
        folder=folder, agent_id=agent_id, search=search, collection=collection
    )
    return {"documents": docs}


@app.get("/documents/folders")
async def documents_folders():
    """List all unique folder paths with document counts."""
    folders = list_folders()
    return {"folders": folders}


class UpdateDocTagsRequest(BaseModel):
    agent_tags: list[str] = Field(default_factory=list)


@app.put("/documents/registry/{doc_id}/tags")
async def documents_update_tags(doc_id: str, body: UpdateDocTagsRequest):
    """Set the agent tags for a document."""
    doc = update_document_registry(doc_id, agent_tags=body.agent_tags)
    if not doc:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Document not found"})
    return doc


class UpdateDocFolderRequest(BaseModel):
    folder: str = Field(..., min_length=1, max_length=500)


@app.put("/documents/registry/{doc_id}/folder")
async def documents_update_folder(doc_id: str, body: UpdateDocFolderRequest):
    """Move a document to a different folder."""
    doc = update_document_registry(doc_id, folder=body.folder)
    if not doc:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Document not found"})
    return doc


@app.delete("/documents/registry/{doc_id}")
async def documents_registry_delete(doc_id: str):
    """Delete a document from registry, file store, and ChromaDB."""
    doc = get_document_registry(doc_id)
    if not doc:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Document not found"})
    # Delete from ChromaDB (only if it was indexed)
    if doc.get("status") == "indexed" and doc.get("source_type") != "shortcut":
        from agent.vectorstore import delete_document

        delete_document(
            doc["source"],
            collection_name=(
                doc["collection"] if doc["collection"] != "agentic_docs" else None
            ),
        )
    # Delete from file store (only if not a shortcut)
    if doc.get("source_type") != "shortcut":
        from agent.filestore import delete_file

        delete_file(doc_id)
    # Delete from registry
    delete_document_registry(doc_id)
    return {"deleted": True, "source": doc["source"]}


# ── Tools endpoint ─────────────────────────────────────────────────────────


@app.get("/tools")
async def tools_list():
    """List all tools (built-in + custom) with status and enabled state."""
    from agent.tools import get_all_tools_unfiltered

    # Tools that require external internet access
    NETWORK_TOOLS = {"http_fetch", "webpage_extract"}

    disabled = set(get_disabled_tools())
    builtin = get_all_tools_unfiltered()
    builtin_list = []
    for t in builtin:
        status = "ready"
        status_detail = ""
        if t.name in NETWORK_TOOLS:
            status = "network"
            status_detail = "Requires external internet access from container"
        builtin_list.append(
            {
                "name": t.name,
                "description": t.description,
                "type": "builtin",
                "enabled": t.name not in disabled,
                "status": status,
                "status_detail": status_detail,
            }
        )
    custom = list_custom_tools()
    custom_list = [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "type": "custom",
            "category": t["category"],
            "endpoint": t["endpoint"],
            "method": t["method"],
            "headers": t["headers"],
            "body_template": t["body_template"],
            "parameters": t["parameters"],
            "labels": t.get("labels", []),
            "enabled": t["enabled"],
            "status": "ready" if t["enabled"] else "disabled",
            "status_detail": "",
            "scope": t.get("scope", "global"),
            "created_by": t.get("created_by", "system"),
            "created_at": t["created_at"],
            "updated_at": t["updated_at"],
        }
        for t in custom
    ]
    return {"tools": builtin_list + custom_list}


# ── Custom Tools CRUD endpoints ───────────────────────────────────────────


class CustomToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="proxy", pattern="^(proxy|local|api|webhook)$")
    endpoint: str = Field(default="", max_length=500)
    method: str = Field(default="POST", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    headers: dict = Field(default_factory=dict)
    body_template: dict = Field(default_factory=dict)
    parameters: list[dict] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    scope: str = Field(default="workspace", pattern="^(global|workspace)$")


class CustomToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    endpoint: str | None = None
    method: str | None = None
    headers: dict | None = None
    body_template: dict | None = None
    parameters: list[dict] | None = None
    labels: list[str] | None = None
    enabled: bool | None = None


@app.get("/custom-tools")
async def custom_tools_list_endpoint(created_by: str | None = None):
    tools = list_custom_tools()
    if created_by:
        tools = [t for t in tools if t.get("created_by") == created_by]
    return {"tools": tools}


@app.post("/custom-tools")
async def custom_tools_create_endpoint(body: CustomToolCreate):
    tool = create_custom_tool(
        name=body.name,
        description=body.description,
        category=body.category,
        endpoint=body.endpoint,
        method=body.method,
        headers=body.headers,
        body_template=body.body_template,
        parameters=body.parameters,
        scope=body.scope,
        labels=body.labels,
    )
    return tool


@app.get("/custom-tools/{tool_id}")
async def custom_tools_get_endpoint(tool_id: str):
    tool = get_custom_tool(tool_id)
    if not tool:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Custom tool not found")
    return tool


@app.put("/custom-tools/{tool_id}")
async def custom_tools_update_endpoint(tool_id: str, body: CustomToolUpdate):
    updates = body.model_dump(exclude_none=True)
    tool = update_custom_tool(tool_id, **updates)
    if not tool:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Custom tool not found")
    return tool


@app.delete("/custom-tools/{tool_id}")
async def custom_tools_delete_endpoint(tool_id: str):
    ok = delete_custom_tool(tool_id)
    return {"deleted": ok}


class ToolToggleRequest(BaseModel):
    enabled: bool


@app.put("/tools/{tool_name}/toggle")
async def tool_toggle(tool_name: str, body: ToolToggleRequest):
    """Enable or disable a tool with permission checks.

    - Built-in / global tools: admin only
    - Private custom tools: admin or creator
    """
    from agent.workspace import get_user_id, get_user_role
    from fastapi import HTTPException

    role = get_user_role()
    user_id = get_user_id()

    # Check if this is a custom tool
    custom_tools = list_custom_tools()
    ct = next((t for t in custom_tools if t["name"] == tool_name), None)

    if ct:
        # Custom tool: admin can always toggle; non-admin can toggle own private tools
        if role != "admin":
            if ct.get("scope") == "global":
                raise HTTPException(403, "Only admins can toggle global tools")
            if ct.get("created_by") != user_id:
                raise HTTPException(403, "You can only toggle tools you created")
        # Toggle via custom tool update
        update_custom_tool(ct["id"], {"enabled": body.enabled})
        return {"name": tool_name, "enabled": body.enabled}
    else:
        # Built-in tool: admin only
        if role != "admin":
            raise HTTPException(403, "Only admins can toggle built-in tools")
        disabled = set(get_disabled_tools())
        if body.enabled:
            disabled.discard(tool_name)
        else:
            disabled.add(tool_name)
        set_disabled_tools(sorted(disabled))
        return {"name": tool_name, "enabled": body.enabled}


# ── Skills CRUD endpoints ─────────────────────────────────────────────────


_SECRET_PATTERNS = [
    "sk-",
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "aws_access",
    "aws_secret",
    "bearer ",
    "ghp_",
    "gho_",
    "-----BEGIN",
    "AKIA",
]
_VALID_PARAM_TYPES = {"string", "number", "boolean", "array", "object"}


def _check_no_secrets(text: str, field_name: str) -> None:
    """Raise ValueError if text contains likely hardcoded secrets."""
    lower = text.lower()
    for pat in _SECRET_PATTERNS:
        if pat.lower() in lower:
            raise ValueError(
                f"{field_name} appears to contain a hardcoded secret or credential "
                f"(matched '{pat}'). Use environment variables or MCP connections instead."
            )


def _validate_input_parameters(params: list[dict]) -> list[dict]:
    """Validate input parameter schema."""
    seen_names: set[str] = set()
    for i, p in enumerate(params):
        name = p.get("name", "").strip()
        if not name:
            raise ValueError(f"Input parameter {i + 1}: name is required")
        if not name.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Input parameter '{name}': name must be alphanumeric "
                f"(underscores and hyphens allowed)"
            )
        if name in seen_names:
            raise ValueError(f"Duplicate input parameter name: '{name}'")
        seen_names.add(name)
        ptype = p.get("type", "string")
        if ptype not in _VALID_PARAM_TYPES:
            raise ValueError(
                f"Input parameter '{name}': type must be one of "
                f"{', '.join(sorted(_VALID_PARAM_TYPES))}, got '{ptype}'"
            )
    return params


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    system_prompt: str = Field(default="", max_length=10000)
    tool_ids: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    input_parameters: list[dict] = Field(default_factory=list)
    scope: str = Field(default="workspace", pattern="^(global|workspace)$")

    @model_validator(mode="after")
    def validate_skill(self):
        # Security: no secrets in prompts or constraints
        _check_no_secrets(self.system_prompt, "System prompt")
        for i, c in enumerate(self.constraints):
            _check_no_secrets(c, f"Constraint {i + 1}")
        # Prompt token estimate (rough: 1 token ~ 4 chars)
        if len(self.system_prompt) > 20000:
            raise ValueError(
                "System prompt exceeds ~5,000 tokens. Move reference docs to external files."
            )
        # Validate input parameters
        _validate_input_parameters(self.input_parameters)
        return self


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    tool_ids: list[str] | None = None
    constraints: list[str] | None = None
    input_parameters: list[dict] | None = None

    @model_validator(mode="after")
    def validate_skill(self):
        if self.system_prompt is not None:
            _check_no_secrets(self.system_prompt, "System prompt")
            if len(self.system_prompt) > 20000:
                raise ValueError(
                    "System prompt exceeds ~5,000 tokens. Move reference docs to external files."
                )
        if self.constraints is not None:
            for i, c in enumerate(self.constraints):
                _check_no_secrets(c, f"Constraint {i + 1}")
        if self.input_parameters is not None:
            _validate_input_parameters(self.input_parameters)
        return self


@app.get("/skills")
async def skills_list_endpoint(created_by: str | None = None):
    skills = list_skills()
    if created_by:
        skills = [s for s in skills if s.get("created_by") == created_by]
    return {"skills": skills}


@app.post("/skills")
async def skills_create_endpoint(body: SkillCreate):
    skill = create_skill(
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt,
        tool_ids=body.tool_ids,
        constraints=body.constraints,
        input_parameters=body.input_parameters,
        scope=body.scope,
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


# ── Global Constraints endpoints ───────────────────────────────────────────


@app.get("/global-constraints")
async def global_constraints_get():
    from agent.memory import get_global_constraints

    return {"constraints": get_global_constraints()}


@app.put("/global-constraints")
async def global_constraints_update(request: Request):
    data = await request.json()
    constraints = data.get("constraints", [])
    if not isinstance(constraints, list):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400, content={"error": "constraints must be a list of strings"}
        )
    for i, c in enumerate(constraints):
        if not isinstance(c, str) or not c.strip():
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={"error": f"Constraint {i + 1} must be a non-empty string"},
            )
        _check_no_secrets(c, f"Global constraint {i + 1}")

    from agent.memory import set_global_constraints

    updated = set_global_constraints([c.strip() for c in constraints if c.strip()])
    return {"constraints": updated}


# ── Security Considerations endpoints ─────────────────────────────────────


@app.get("/security-considerations")
async def security_considerations_get():
    from agent.memory import get_security_considerations

    return {"items": get_security_considerations()}


@app.put("/security-considerations")
async def security_considerations_update(request: Request):
    data = await request.json()
    items = data.get("items", [])
    if not isinstance(items, list):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400, content={"error": "items must be a list of strings"}
        )
    for i, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={"error": f"Item {i + 1} must be a non-empty string"},
            )
        _check_no_secrets(item, f"Security consideration {i + 1}")

    from agent.memory import set_security_considerations

    updated = set_security_considerations([s.strip() for s in items if s.strip()])
    return {"items": updated}


# ── Best Practices endpoints ──────────────────────────────────────────────


@app.get("/best-practices")
async def best_practices_get():
    from agent.memory import get_best_practices

    return {"practices": get_best_practices()}


@app.put("/best-practices")
async def best_practices_update(request: Request):
    data = await request.json()
    practices = data.get("practices", [])
    if not isinstance(practices, list):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400, content={"error": "practices must be a list of strings"}
        )
    for i, p in enumerate(practices):
        if not isinstance(p, str) or not p.strip():
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={"error": f"Practice {i + 1} must be a non-empty string"},
            )
        _check_no_secrets(p, f"Best practice {i + 1}")

    from agent.memory import set_best_practices

    updated = set_best_practices([p.strip() for p in practices if p.strip()])
    return {"practices": updated}


# ── Skill File Endpoints ───────────────────────────────────────────────────


@app.post("/skills/{skill_id}/files")
async def skill_upload_file(
    skill_id: str, category: str = Form(...), file: UploadFile = File(...)
):
    """Upload a file (script, reference, or asset) to a skill."""
    from agent.memory import add_skill_file

    try:
        content = await file.read()
        meta = add_skill_file(skill_id, category, file.filename, content)
        return {"file": meta}
    except ValueError as e:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/skills/{skill_id}/files")
async def skill_list_files(skill_id: str):
    """List all files attached to a skill."""
    skill = get_skill(skill_id)
    if not skill:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Skill not found"})
    return {"files": skill.get("files", [])}


@app.get("/skills/{skill_id}/files/{category}/{filename}")
async def skill_download_file(skill_id: str, category: str, filename: str):
    """Download a skill file."""
    from agent.memory import get_skill_file_path
    from fastapi.responses import FileResponse, JSONResponse

    path = get_skill_file_path(skill_id, category, filename)
    if not path:
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=filename)


@app.delete("/skills/{skill_id}/files/{category}/{filename}")
async def skill_delete_file(skill_id: str, category: str, filename: str):
    """Delete a file from a skill."""
    from agent.memory import remove_skill_file
    from fastapi.responses import JSONResponse

    ok = remove_skill_file(skill_id, category, filename)
    if not ok:
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return {"deleted": True}


@app.post("/skills/enrich")
async def skills_enrich_endpoint(request: Request):
    """Use LLM to enrich a partially-filled skill with AI-generated suggestions."""
    data = await request.json()
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    system_prompt = data.get("system_prompt", "").strip()
    constraints = data.get("constraints", [])
    input_parameters = data.get("input_parameters", [])
    available_tools = data.get("available_tools", [])
    best_practices = data.get("best_practices", "")
    directions = data.get("directions", "").strip()

    if not name and not description:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content={"error": "Provide at least a name or description to enrich"},
        )

    import json as _json

    from agent.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    system = """\
You are an expert skill architect for an AI agent platform. Given partial information about a skill, enrich and improve it.

A skill is a packaged capability: code + prompt(s) + tools + contracts, exposed as a callable function.
Skills are like reusable functions that take input parameters, use tools, follow a prompt, and operate within constraints.

Return ONLY a JSON object (no other text):
{
  "name": "improved skill name (concise, max 8 words)",
  "description": "clear description of what the skill does and WHEN to use it (max 200 chars). Include keywords that help agents identify relevant tasks.",
  "system_prompt": "production-ready prompt text (max 500 words). Include: persona, step-by-step instructions, expected input/output format, edge cases.",
  "constraints": ["constraint 1", "constraint 2", "..."],
  "input_parameters": [
    {"name": "param_name", "type": "string|number|boolean|array|object", "required": true/false, "default_value": "optional default or description"}
  ],
  "suggested_tools": ["tool1", "tool2"],
  "score": <integer 1-10 quality score>,
  "improvements": ["what was improved 1", "what was improved 2"]
}

Rules:
- Preserve any user-provided values that are already good; improve what is weak or missing.
- If user provided a prompt, enhance it — don't replace it wholesale.
- If no input_parameters are defined, infer logical ones from the skill's purpose.
- suggested_tools should come from the available tools list when possible.
- Constraints should include security and quality guardrails.
"""

    if best_practices:
        system += "\n\nOrganizational Best Practices to align with:\n" + best_practices

    if directions:
        system += (
            "\n\nIMPORTANT — Additional Directions from the user (follow these strictly):\n"
            + directions
        )

    user_parts = []
    if name:
        user_parts.append(f"Name: {name}")
    if description:
        user_parts.append(f"Description: {description}")
    if system_prompt:
        user_parts.append(f"Current Prompt:\n{system_prompt}")
    if constraints:
        user_parts.append(f"Constraints: {', '.join(constraints)}")
    if input_parameters:
        user_parts.append(f"Input Parameters: {_json.dumps(input_parameters)}")
    if available_tools:
        user_parts.append(f"Available Tools: {', '.join(available_tools)}")

    user_msg = "Enrich this skill:\n\n" + "\n".join(user_parts)

    try:
        import time as _time

        _start = _time.time()
        from agent.llm import get_active_model as _gam

        req_provider = data.get("provider")
        req_model = data.get("model")
        if req_provider and req_model:
            provider = req_provider
            model = req_model
        else:
            active = _gam()
            provider = active.get("provider", "ollama")
            model = active.get("model", "llama3")
        msgs = [SystemMessage(content=system), HumanMessage(content=user_msg)]
        for temp in (0.7, 1, None):
            try:
                kwargs = {
                    "provider": provider,
                    "model": model,
                    "max_completion_tokens": 4096,
                }
                if temp is not None:
                    kwargs["temperature"] = temp
                llm = get_llm(**kwargs)
                result = await llm.ainvoke(msgs)
                usage_meta = _log_ai_usage(
                    provider, model, result, _start, "skills-enrich"
                )
                parsed = _extract_json(result.content or "")
                if parsed is not None:
                    parsed["_llm_usage"] = usage_meta
                    return parsed
                return {
                    "error": "LLM returned invalid JSON",
                    "name": name,
                    "description": description,
                    "_llm_usage": usage_meta,
                }
            except Exception as e2:
                if "temperature" in str(e2).lower():
                    continue
                raise
        return {
            "error": "Model rejects all temperature values",
            "name": name,
            "description": description,
        }
    except Exception as e:
        return {"error": str(e), "name": name, "description": description}


@app.post("/skills/decompose")
async def skills_decompose_endpoint(request: Request):
    """Decompose a concept/prompt into a family of related skills."""
    data = await request.json()
    concept = data.get("concept", "").strip()
    base_prompt = data.get("base_prompt", "").strip()
    raw_count = data.get("count")
    count = min(int(raw_count), 10) if raw_count is not None else None
    available_tools = data.get("available_tools", [])
    best_practices = data.get("best_practices", "")
    directions = data.get("directions", "").strip()

    if not concept and not base_prompt:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content={
                "error": "Provide a concept or base prompt to decompose into skills"
            },
        )

    import json as _json

    from agent.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    system = f"""\
You are an expert skill architect for an AI agent platform.

A skill is a packaged capability: code + prompt(s) + tools + contracts, exposed as a callable function.
Skills follow the Agent Skills open standard (agentskills.io).

Your task: given a concept or base prompt, decompose it into a FAMILY of {(str(count) + ' ') if count else ''}complementary skills.
Each skill should be a distinct, focused capability that together cover the full lifecycle.
{'Choose the right number of skills to fully cover the domain.' if not count else ''}

Think about it this way:
- A prompt defines HOW to do something
- A skill defines HOW that capability WORKS in the organization
- A skill family covers the complete workflow: create, update, validate, convert, compare, extract

Return ONLY a JSON object (no other text):
{{
  "family_name": "short family name (e.g. Documentation, Code Review, Data Analysis)",
  "family_description": "what this skill family covers as a whole",
  "skills": [
    {{
      "name": "ConcisePascalCaseName",
      "description": "clear description (max 200 chars) — when should an agent activate this skill?",
      "system_prompt": "production-ready prompt (max 400 words). Include: persona, step-by-step instructions, expected I/O format, edge cases.",
      "constraints": ["constraint 1", "constraint 2"],
      "input_parameters": [
        {{"name": "param_name", "type": "string|number|boolean|array|object", "required": true, "default_value": ""}}
      ],
      "suggested_tools": ["tool1"],
      "role_in_family": "What role this skill plays (e.g. Creator, Validator, Converter)"
    }}
  ]
}}

Rules:
- Each skill must be DISTINCT — no overlapping responsibilities
- Skills should compose well together (output of one can feed into another)
- Include at least one validation/quality-check skill
- Include input_parameters that make each skill reusable and composable
- Constraints should include security and quality guardrails
- If a base prompt is provided, the first skill should wrap that prompt; others complement it
"""

    if best_practices:
        system += "\n\nOrganizational Best Practices to align with:\n" + best_practices

    if directions:
        system += (
            "\n\nIMPORTANT — Additional Directions from the user (follow these strictly):\n"
            + directions
        )

    user_parts = []
    if concept:
        user_parts.append(f"Concept/Domain: {concept}")
    if base_prompt:
        user_parts.append(f"Base Prompt:\n{base_prompt}")
    if available_tools:
        user_parts.append(f"Available Tools: {', '.join(available_tools)}")

    user_msg = (
        f"Decompose this into a family of {(str(count) + ' ') if count else ''}skills:\n\n"
        + "\n".join(user_parts)
    )

    try:
        import time as _time

        _start = _time.time()
        from agent.llm import get_active_model as _gam

        req_provider = data.get("provider")
        req_model = data.get("model")
        if req_provider and req_model:
            provider = req_provider
            model = req_model
        else:
            active = _gam()
            provider = active.get("provider", "ollama")
            model = active.get("model", "llama3")
        msgs = [SystemMessage(content=system), HumanMessage(content=user_msg)]
        for temp in (0.7, 1, None):
            try:
                kwargs = {
                    "provider": provider,
                    "model": model,
                    "max_completion_tokens": 8192,
                }
                if temp is not None:
                    kwargs["temperature"] = temp
                llm = get_llm(**kwargs)
                result = await llm.ainvoke(msgs)
                usage_meta = _log_ai_usage(
                    provider, model, result, _start, "skills-decompose"
                )
                parsed = _extract_json(result.content or "")
                if parsed is not None and "skills" in parsed:
                    parsed["_llm_usage"] = usage_meta
                    return parsed
                return {
                    "error": "LLM returned invalid JSON",
                    "concept": concept,
                    "_llm_usage": usage_meta,
                }
            except Exception as e2:
                if "temperature" in str(e2).lower():
                    continue
                raise
        return {"error": "Model rejects all temperature values", "concept": concept}
    except Exception as e:
        return {"error": str(e), "concept": concept}


# ── Prompts CRUD endpoints ────────────────────────────────────────────────


class PromptCreate(BaseModel):
    name: str
    content: str
    category: str = "general"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    model: str = ""
    scope: str = Field(default="workspace", pattern="^(global|workspace)$")


class PromptUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    category: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    model: str | None = None


@app.get("/prompts")
async def prompts_list_endpoint(created_by: str | None = None):
    prompts = list_prompts()
    if created_by:
        prompts = [p for p in prompts if p.get("created_by") == created_by]
    return {"prompts": prompts}


@app.post("/prompts")
async def prompts_create_endpoint(body: PromptCreate):
    prompt = create_prompt(
        name=body.name,
        content=body.content,
        category=body.category,
        description=body.description,
        tags=body.tags,
        model=body.model,
        scope=body.scope,
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


def _extract_json(raw: str):
    """Extract a JSON object from LLM output that may contain extra text."""
    import json as _json
    import re as _re

    s = raw.strip()
    if s.startswith("```"):
        s = _re.sub(r"^```\w*\n?", "", s)
        s = _re.sub(r"\n?```$", "", s)
    try:
        return _json.loads(s)
    except _json.JSONDecodeError:
        pass
    m = _re.search(r"\{[\s\S]*\}", s)
    if m:
        try:
            return _json.loads(m.group())
        except _json.JSONDecodeError:
            pass
    return None


def _log_ai_usage(
    provider: str,
    model: str,
    result,
    start_time: float,
    feature: str = "ai-feature",
) -> dict:
    """Log LLM usage from an AI feature endpoint and return usage metadata."""
    import time as _time

    usage_meta = {
        "provider": provider,
        "model": model,
        "feature": feature,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "latency_ms": int((_time.time() - start_time) * 1000),
        "estimated_cost": 0.0,
    }
    try:
        from agent.memory import log_llm_usage

        # Extract token counts from LangChain response metadata
        usage = getattr(result, "usage_metadata", None) or {}
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        # Fallback: try response_metadata (OpenAI/Azure style)
        if not prompt_tokens and hasattr(result, "response_metadata"):
            rm = result.response_metadata or {}
            tu = rm.get("token_usage") or rm.get("usage") or {}
            prompt_tokens = tu.get("prompt_tokens", 0)
            completion_tokens = tu.get("completion_tokens", 0)
            total_tokens = tu.get("total_tokens", prompt_tokens + completion_tokens)

        latency_ms = int((_time.time() - start_time) * 1000)
        entry = log_llm_usage(
            request_id=f"{feature}-{str(__import__('uuid').uuid4())[:8]}",
            session_id=feature,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            tools_used=[],
            guardrail_status="passed",
            agent_id="",
        )
        usage_meta.update(
            {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "latency_ms": latency_ms,
                "estimated_cost": entry.get("estimated_cost", 0.0),
            }
        )
    except Exception as e:
        logger.warning("Failed to log AI feature usage (%s): %s", feature, e)
    return usage_meta


async def _fetch_references(references: list) -> dict:
    """Fetch URL references concurrently. Returns {ref_text, references_used} with status per ref."""
    import asyncio
    import re as _re

    import httpx

    url_pattern = _re.compile(r"^https?://", _re.IGNORECASE)
    urls = [
        (i, r)
        for i, r in enumerate(references)
        if r.strip() and url_pattern.match(r.strip())
    ]
    plain = [
        (i, r)
        for i, r in enumerate(references)
        if r.strip() and not url_pattern.match(r.strip())
    ]

    results = [None] * len(references)

    # Fetch URLs concurrently
    async def fetch_one(idx, url):
        url = url.strip()
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    url, headers={"User-Agent": "AgenticPlatform/1.0"}
                )
                if resp.status_code >= 400:
                    results[idx] = {
                        "ref": url,
                        "status": "error",
                        "reason": f"HTTP {resp.status_code}",
                    }
                else:
                    # Extract text content (strip HTML tags for a rough plain-text extraction)
                    content_type = resp.headers.get("content-type", "")
                    body = resp.text[:8000]  # cap content to avoid huge payloads
                    if "html" in content_type:
                        body = _re.sub(
                            r"<script[^>]*>.*?</script>",
                            "",
                            body,
                            flags=_re.DOTALL | _re.IGNORECASE,
                        )
                        body = _re.sub(
                            r"<style[^>]*>.*?</style>",
                            "",
                            body,
                            flags=_re.DOTALL | _re.IGNORECASE,
                        )
                        body = _re.sub(r"<[^>]+>", " ", body)
                        body = _re.sub(r"\s+", " ", body).strip()[:4000]
                    results[idx] = {"ref": url, "status": "ok", "content": body}
        except httpx.TimeoutException:
            results[idx] = {
                "ref": url,
                "status": "error",
                "reason": "Timeout (unreachable after 10s)",
            }
        except httpx.ConnectError:
            results[idx] = {
                "ref": url,
                "status": "error",
                "reason": "Connection refused or DNS failure",
            }
        except Exception as e:
            results[idx] = {"ref": url, "status": "error", "reason": str(e)[:100]}

    if urls:
        await asyncio.gather(*(fetch_one(i, u) for i, u in urls))

    # Plain-text references
    for idx, text in plain:
        results[idx] = {"ref": text, "status": "ok", "content": text}

    # Build the text to inject into the system prompt
    ref_parts = []
    for r in results:
        if r is None:
            continue
        if r["status"] == "ok":
            ref_parts.append(f"[REFERENCE: {r['ref']}]\n{r['content']}")
        else:
            ref_parts.append(f"[REFERENCE: {r['ref']}] — UNREACHABLE: {r['reason']}")
    ref_text = "\n\n".join(ref_parts)

    # Build references_used metadata for the response
    references_used = []
    for r in results:
        if r is None:
            continue
        entry = {"ref": r["ref"], "status": r["status"]}
        if r["status"] == "error":
            entry["reason"] = r["reason"]
        references_used.append(entry)

    return {"ref_text": ref_text, "references_used": references_used}


@app.post("/prompts/validate")
async def prompts_validate_endpoint(request: Request):
    """Validate a prompt using LLM — returns quality score, issues, suggestions."""
    import json as _json
    import re as _re

    data = await request.json()
    content = data.get("content", "").strip()
    category = data.get("category", "general")
    if not content:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"error": "content is required"})

    import json as _json
    import re as _re

    from agent.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    system = (
        """\
You are a prompt engineering expert. Evaluate the prompt below and return a JSON object:
{
  "score": <integer 1-10>,
  "clarity": <integer 1-10>,
  "specificity": <integer 1-10>,
  "completeness": <integer 1-10>,
  "effectiveness": <integer 1-10>,
  "issues": ["list of problems found"],
  "suggestions": ["list of actionable improvements"],
  "summary": "one-sentence overall assessment"
}

Scoring guide:
- clarity: Is the instruction unambiguous? Does it tell the model exactly what to do?
- specificity: Does it include format, constraints, examples, or persona?
- completeness: Does it cover edge cases, output format, and context?
- effectiveness: Would this prompt reliably produce high-quality output?
- score: overall weighted average

Category context: """
        + category
        + """
Respond ONLY with valid JSON."""
    )

    references = data.get("references", [])
    refs_meta = None
    if references:
        refs_meta = await _fetch_references(references)
        system += (
            "\n\nOrganizational Best Practices & References (evaluate the prompt against these standards and flag deviations as issues):\n"
            + refs_meta["ref_text"]
        )

    try:
        import time as _time

        _start = _time.time()
        from agent.llm import get_active_model as _gam

        req_provider = data.get("provider")
        req_model = data.get("model")
        if req_provider and req_model:
            provider = req_provider
            model = req_model
        else:
            active = _gam()
            provider = active.get("provider", "ollama")
            model = active.get("model", "llama3")
        msgs = [SystemMessage(content=system), HumanMessage(content=content)]
        for temp in (0, 1, None):
            try:
                kwargs = {
                    "provider": provider,
                    "model": model,
                    "max_completion_tokens": 4096,
                }
                if temp is not None:
                    kwargs["temperature"] = temp
                llm = get_llm(**kwargs)
                result = await llm.ainvoke(msgs)
                usage_meta = _log_ai_usage(
                    provider, model, result, _start, "prompts-validate"
                )
                parsed = _extract_json(result.content)
                if parsed is not None:
                    if refs_meta:
                        parsed["references_used"] = refs_meta["references_used"]
                    parsed["_llm_usage"] = usage_meta
                    # ── persist validation score if prompt_id provided ──
                    prompt_id = data.get("prompt_id")
                    if prompt_id and parsed.get("score"):
                        from datetime import datetime
                        from datetime import timezone as _tz

                        details = {
                            k: parsed.get(k)
                            for k in (
                                "clarity",
                                "specificity",
                                "completeness",
                                "effectiveness",
                                "summary",
                                "issues",
                                "suggestions",
                            )
                            if parsed.get(k) is not None
                        }
                        update_prompt(
                            prompt_id,
                            validation_score=parsed["score"],
                            validation_details=details,
                            validated_at=datetime.now(_tz.utc).isoformat(),
                        )
                    return parsed
                return {
                    "score": 0,
                    "error": "LLM returned invalid JSON",
                    "summary": "Validation failed",
                    "_llm_usage": usage_meta,
                }
            except Exception as e2:
                if "temperature" in str(e2).lower():
                    continue
                raise
        return {
            "score": 0,
            "error": "Model rejects all temperature values",
            "summary": "Validation failed",
        }
    except Exception as e:
        return {
            "score": 0,
            "error": str(e),
            "summary": "Validation failed — LLM unavailable",
        }


@app.post("/prompts/generate")
async def prompts_generate_endpoint(request: Request):
    """Use LLM to generate a prompt from a natural-language description."""
    data = await request.json()
    description = data.get("description", "").strip()
    category = data.get("category", "general")
    if not description:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400, content={"error": "description is required"}
        )

    import json as _json
    import re as _re

    from agent.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    system = (
        """\
You are a prompt engineering expert. Given a user's description, generate a production-ready prompt.

Return ONLY a JSON object (no other text):
{
  "name": "short name (max 8 words)",
  "content": "the prompt text (max 300 words) — include persona, constraints, output format",
  "description": "one-sentence summary",
  "tags": ["max", "5", "tags"],
  "score": <integer 1-10>
}

Category: """
        + category
        + """

Keep the content field concise but complete. Do NOT include examples or lengthy templates.
Respond ONLY with the JSON object."""
    )

    directions = data.get("directions", "").strip()
    references = data.get("references", [])
    refs_meta = None
    if references:
        refs_meta = await _fetch_references(references)
        system += (
            "\n\nOrganizational Best Practices & References (align the generated prompt with these):\n"
            + refs_meta["ref_text"]
        )

    if directions:
        system += (
            "\n\nIMPORTANT — Additional Directions from the user (follow these strictly):\n"
            + directions
        )

    try:
        import time as _time

        _start = _time.time()
        from agent.llm import get_active_model as _gam

        req_provider = data.get("provider")
        req_model = data.get("model")
        if req_provider and req_model:
            provider = req_provider
            model = req_model
        else:
            active = _gam()
            provider = active.get("provider", "ollama")
            model = active.get("model", "llama3")
        msgs = [SystemMessage(content=system), HumanMessage(content=description)]
        for temp in (0.7, 1, None):
            try:
                kwargs = {
                    "provider": provider,
                    "model": model,
                    "max_completion_tokens": 4096,
                }
                if temp is not None:
                    kwargs["temperature"] = temp
                llm = get_llm(**kwargs)
                result = await llm.ainvoke(msgs)
                usage_meta = _log_ai_usage(
                    provider, model, result, _start, "prompts-generate"
                )
                parsed = _extract_json(result.content or "")
                if parsed is not None:
                    if refs_meta:
                        parsed["references_used"] = refs_meta["references_used"]
                    parsed["_llm_usage"] = usage_meta
                    return parsed
                return {
                    "error": "LLM returned invalid JSON",
                    "content": "",
                    "name": "",
                    "_llm_usage": usage_meta,
                }
            except Exception as e2:
                if "temperature" in str(e2).lower():
                    continue
                raise
        return {
            "error": "Model rejects all temperature values",
            "content": "",
            "name": "",
        }
    except Exception as e:
        return {"error": str(e), "content": "", "name": ""}


# ── Agents CRUD endpoints ─────────────────────────────────────────────────


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    provider: str = Field(default="ollama")
    model: str = Field(default="llama3")
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    system_prompt: str = Field(default="", max_length=20000)
    skill_ids: list[str] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)
    sub_agent_ids: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    mcp_server_ids: list[str] = Field(default_factory=list)
    kb_collection: str = Field(default="agentic_docs")
    retrieval_mode: str = Field(default="basic")
    max_iterations: int = Field(default=5, ge=1, le=20)
    memory_enabled: bool = Field(default=True)
    scope: str = Field(default="workspace", pattern="^(global|workspace)$")


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    system_prompt: str | None = None
    skill_ids: list[str] | None = None
    tool_ids: list[str] | None = None
    sub_agent_ids: list[str] | None = None
    constraints: list[str] | None = None
    mcp_server_ids: list[str] | None = None
    kb_collection: str | None = None
    retrieval_mode: str | None = None
    max_iterations: int | None = None
    memory_enabled: bool | None = None


@app.get("/agents")
async def agents_list_endpoint(created_by: str | None = None):
    agents = list_agents()
    if created_by:
        agents = [a for a in agents if a.get("created_by") == created_by]
    return {"agents": agents}


@app.post("/agents")
async def agents_create_endpoint(body: AgentCreate):
    agent = create_agent(
        name=body.name,
        description=body.description,
        provider=body.provider,
        model=body.model,
        temperature=body.temperature,
        top_p=body.top_p,
        system_prompt=body.system_prompt,
        skill_ids=body.skill_ids,
        tool_ids=body.tool_ids,
        sub_agent_ids=body.sub_agent_ids,
        constraints=body.constraints,
        mcp_server_ids=body.mcp_server_ids,
        kb_collection=body.kb_collection,
        retrieval_mode=body.retrieval_mode,
        max_iterations=body.max_iterations,
        memory_enabled=body.memory_enabled,
        scope=body.scope,
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
    agent = get_agent(agent_id)
    if not agent:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Agent not found"})
    ok = delete_agent(agent_id)
    if not ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"error": "Agent not found or is default"}
        )
    # Remove agent tags from global documents (keeps the docs, just removes the tag)
    try:
        untag_all_for_agent(agent_id)
    except Exception:
        pass  # datastore may be unavailable
    # Clean up the agent's isolated KB collection and its registry records
    kb = agent.get("kb_collection", "")
    if kb and kb != "agentic_docs" and kb.startswith("agent_"):
        from agent.vectorstore import delete_collection

        try:
            delete_collection(kb)
            delete_documents_by_collection(kb)
        except Exception:
            pass
    return {"deleted": True}


# ── A2A (Agent-to-Agent) endpoints ─────────────────────────────────────────


class A2APeerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=1000)
    capabilities: list[str] = Field(default_factory=list)
    scope: str = Field(default="workspace", pattern="^(global|workspace)$")


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
        name=body.name,
        url=body.url,
        description=body.description,
        capabilities=body.capabilities,
        scope=body.scope,
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
                update_a2a_peer(
                    peer_id, status="online", agent_card=agent_card, last_seen=now
                )
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
            return {
                "status": "completed",
                "peer": peer["name"],
                "response": resp.json(),
            }
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "peer": peer["name"],
            "code": exc.response.status_code,
            "error": str(exc),
        }
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
        "agents": [
            {"id": a["id"], "name": a["name"], "description": a["description"]}
            for a in agents
        ],
        "tools": [{"name": t.name, "description": t.description} for t in tools],
    }


# ── MCP (Model Context Protocol) endpoints ────────────────────────────────


class MCPServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    transport: str = Field(default="stdio", pattern="^(stdio|sse|http)$")
    description: str = Field(default="", max_length=1000)
    scope: str = Field(default="workspace", pattern="^(global|workspace)$")


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
        name=body.name,
        url=body.url,
        transport=body.transport,
        description=body.description,
        scope=body.scope,
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
    server = get_mcp_server(server_id)
    if not server:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "MCP server not found"})
    if server.get("managed") and server.get("container_id"):
        try:
            from agent.docker_manager import remove_container

            remove_container(server["container_id"])
        except Exception as e:
            logger.warning("Failed to remove managed container: %s", e)
    ok = delete_mcp_server(server_id)
    if not ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "MCP server not found"})


# ── LlamaIndex: Advanced Retrieval ─────────────────────────────────────────


class AdvancedSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    mode: str = Field(
        default="hybrid",
        description="Retrieval mode: hybrid, sentence_window, auto_merging, reranked",
    )
    k: int = Field(default=5, ge=1, le=50)
    collection: str | None = Field(default=None)
    alpha: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Hybrid alpha (1.0=vector, 0.0=keyword)",
    )


@app.post("/documents/advanced-search")
async def documents_advanced_search(body: AdvancedSearchRequest):
    """Advanced retrieval with multiple strategies (LlamaIndex-powered)."""
    from agent.advanced_retrieval import advanced_search

    kwargs = {}
    if body.alpha is not None:
        kwargs["alpha"] = body.alpha

    results = advanced_search(
        query=body.query,
        mode=body.mode,
        k=body.k,
        collection_name=body.collection,
        **kwargs,
    )
    return {
        "query": body.query,
        "mode": body.mode,
        "results": results,
        "count": len(results),
    }


@app.get("/documents/retrieval-modes")
async def documents_retrieval_modes():
    """List available advanced retrieval modes."""
    from agent.advanced_retrieval import list_retrieval_modes

    return {"modes": list_retrieval_modes()}


# ── LlamaIndex: Document Parsing ───────────────────────────────────────────


@app.get("/documents/supported-types")
async def documents_supported_types():
    """List file types supported by LlamaIndex document parser."""
    from agent.llamaindex_loader import get_supported_types

    return {"supported_types": get_supported_types()}


class ParseURLRequest(BaseModel):
    url: str = Field(..., min_length=1)
    metadata: dict | None = None
    collection: str | None = None
    ingest: bool = Field(
        default=True, description="Immediately ingest parsed content into KB"
    )


@app.post("/documents/parse-url")
async def documents_parse_url(body: ParseURLRequest):
    """Parse a web URL using LlamaIndex and optionally ingest into knowledge base."""
    from agent.llamaindex_loader import parse_url
    from agent.vectorstore import ingest_document

    docs = parse_url(body.url, metadata=body.metadata)
    if not docs or not docs[0].get("text"):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"error": "Failed to parse URL"})

    result = {"url": body.url, "sections_parsed": len(docs)}

    if body.ingest:
        total_chunks = 0
        for doc in docs:
            if doc.get("text"):
                r = ingest_document(
                    text=doc["text"],
                    source=body.url,
                    metadata=doc.get("metadata"),
                    collection_name=body.collection,
                )
                total_chunks += r.get("chunks", 0)
        result["ingested"] = True
        result["total_chunks"] = total_chunks
    else:
        result["ingested"] = False
        result["documents"] = docs

    return result


# ── LlamaIndex: Structured Data Querying ───────────────────────────────────


class SQLQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4096)
    connection_string: str = Field(..., min_length=1)
    tables: list[str] | None = None


@app.post("/query/sql")
async def query_sql_endpoint(body: SQLQueryRequest):
    """Natural language → SQL query. Translates question to SQL and executes it."""
    from agent.structured_query import query_sql

    result = query_sql(
        question=body.question,
        connection_string=body.connection_string,
        tables=body.tables,
    )
    return result


class CSVQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4096)
    csv_path: str = Field(..., min_length=1)


@app.post("/query/csv")
async def query_csv_endpoint(body: CSVQueryRequest):
    """Natural language query over a CSV file."""
    from agent.structured_query import query_csv

    result = query_csv(question=body.question, csv_path=body.csv_path)
    return result


class SchemaRequest(BaseModel):
    connection_string: str = Field(..., min_length=1)
    tables: list[str] | None = None


@app.post("/query/schema")
async def query_schema_endpoint(body: SchemaRequest):
    """Inspect database schema — returns tables, columns, and types."""
    from agent.structured_query import get_table_schema

    result = get_table_schema(
        connection_string=body.connection_string, tables=body.tables
    )
    return result


# ── LlamaIndex: RAG Evaluation ─────────────────────────────────────────────


class RAGEvalRequest(BaseModel):
    query: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    contexts: list[str] = Field(default_factory=list)
    reference: str | None = None
    guidelines: list[str] | None = None


@app.post("/evaluation/rag")
async def evaluation_rag(body: RAGEvalRequest):
    """Evaluate a RAG response for faithfulness, relevancy, and correctness."""
    from agent.rag_evaluation import evaluate_rag_pipeline

    result = evaluate_rag_pipeline(
        query=body.query,
        response=body.response,
        contexts=body.contexts,
        reference=body.reference,
        guidelines=body.guidelines,
    )
    return result


class BatchEvalRequest(BaseModel):
    test_cases: list[RAGEvalRequest]


@app.post("/evaluation/rag/batch")
async def evaluation_rag_batch(body: BatchEvalRequest):
    """Batch-evaluate multiple RAG responses."""
    from agent.rag_evaluation import batch_evaluate

    cases = [tc.model_dump() for tc in body.test_cases]
    result = batch_evaluate(test_cases=cases)
    return result
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
            resp = await client.post(
                tools_url, json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            )
            if resp.status_code == 200:
                data = resp.json()
                tools = data.get("result", {}).get("tools", data.get("tools", []))
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()
                update_mcp_server(
                    server_id, tools=tools, status="connected", last_seen=now
                )
                return {"status": "connected", "tools": tools}
            # Fallback: try /tools
            tools_url = server["url"].rstrip("/") + "/tools"
            resp = await client.get(tools_url)
            if resp.status_code == 200:
                data = resp.json()
                tools = data.get("tools", data if isinstance(data, list) else [])
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()
                update_mcp_server(
                    server_id, tools=tools, status="connected", last_seen=now
                )
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


# ── Managed MCP Server endpoints ──────────────────────────────────────────


class ManagedMCPToolParam(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="string", pattern="^(string|integer|number|boolean)$")
    required: bool = Field(default=False)
    description: str = Field(default="", max_length=500)


class ManagedMCPToolDef(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    endpoint_url: str = Field(..., min_length=1, max_length=2000)
    http_method: str = Field(default="POST", pattern="^(GET|POST|PUT|DELETE|PATCH)$")
    headers: dict[str, str] = Field(default_factory=dict)
    parameters: list[ManagedMCPToolParam] = Field(default_factory=list)


class ManagedMCPCreateConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    tools: list[ManagedMCPToolDef]


class ManagedMCPCreateCode(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    code: str = Field(..., min_length=1, max_length=100000)


async def _provision_managed_server(server_id: str, config: dict):
    """Background task: provision container, wait for health, auto-discover."""
    from agent.docker_manager import create_managed_container, wait_for_health

    server = get_mcp_server(server_id)
    if not server:
        return
    try:
        result = create_managed_container(
            server_id=server_id,
            server_name=server["name"],
            config=config,
        )
        update_mcp_server(
            server_id,
            container_id=result["container_id"],
            container_name=result["container_name"],
            url=result["url"],
            container_status="starting",
        )
        healthy = await wait_for_health(result["url"], timeout=45)
        if healthy:
            update_mcp_server(server_id, container_status="running", status="connected")
            # Auto-discover tools
            try:
                import httpx as _httpx

                async with _httpx.AsyncClient(timeout=10.0) as client:
                    tools_url = result["url"].rstrip("/") + "/tools/list"
                    resp = await client.post(
                        tools_url,
                        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        tools = data.get("result", {}).get("tools", [])
                        from datetime import datetime, timezone

                        now = datetime.now(timezone.utc).isoformat()
                        update_mcp_server(server_id, tools=tools, last_seen=now)
            except Exception as e:
                logger.warning("Auto-discover failed for %s: %s", server_id, e)
        else:
            update_mcp_server(
                server_id,
                container_status="error",
                error_message="Health check timeout after 45s",
            )
    except Exception as e:
        logger.error("Provisioning failed for %s: %s", server_id, e)
        update_mcp_server(
            server_id,
            container_status="error",
            error_message=str(e),
        )


@app.post("/mcp/servers/managed/config")
async def mcp_create_managed_config(
    body: ManagedMCPCreateConfig, background_tasks: BackgroundTasks
):
    config = {
        "mode": "config",
        "server_name": body.name,
        "tools": [t.model_dump() for t in body.tools],
    }
    server = create_mcp_server(
        name=body.name,
        url="pending://provisioning",
        transport="http",
        description=body.description,
    )
    server_id = server["id"]
    update_mcp_server(
        server_id,
        managed=True,
        server_type="config",
        config=config,
        container_status="creating",
    )
    background_tasks.add_task(_provision_managed_server, server_id, config)
    return {"server": get_mcp_server(server_id), "provisioning": True}


@app.post("/mcp/servers/managed/code")
async def mcp_create_managed_code(
    body: ManagedMCPCreateCode, background_tasks: BackgroundTasks
):
    config = {
        "mode": "code",
        "server_name": body.name,
        "code": body.code,
    }
    server = create_mcp_server(
        name=body.name,
        url="pending://provisioning",
        transport="http",
        description=body.description,
    )
    server_id = server["id"]
    update_mcp_server(
        server_id,
        managed=True,
        server_type="code",
        config=config,
        container_status="creating",
    )
    background_tasks.add_task(_provision_managed_server, server_id, config)
    return {"server": get_mcp_server(server_id), "provisioning": True}


@app.post("/mcp/servers/{server_id}/provision")
async def mcp_provision_server(server_id: str, background_tasks: BackgroundTasks):
    server = get_mcp_server(server_id)
    if not server:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "MCP server not found"})
    if not server.get("managed"):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"error": "Not a managed server"})
    config = server.get("config", {})
    if server.get("container_id"):
        from agent.docker_manager import remove_container

        try:
            remove_container(server["container_id"])
        except Exception:
            pass
    update_mcp_server(server_id, container_status="creating", error_message="")
    background_tasks.add_task(_provision_managed_server, server_id, config)
    return {"status": "provisioning"}


@app.post("/mcp/servers/{server_id}/container/stop")
async def mcp_stop_container(server_id: str):
    server = get_mcp_server(server_id)
    if not server or not server.get("managed"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"error": "Managed server not found"}
        )
    from agent.docker_manager import stop_container

    ok = stop_container(server["container_id"])
    if ok:
        update_mcp_server(server_id, container_status="stopped")
    return {"stopped": ok}


@app.post("/mcp/servers/{server_id}/container/start")
async def mcp_start_container(server_id: str):
    server = get_mcp_server(server_id)
    if not server or not server.get("managed"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"error": "Managed server not found"}
        )
    from agent.docker_manager import start_container

    ok = start_container(server["container_id"])
    if ok:
        update_mcp_server(server_id, container_status="running")
    return {"started": ok}


@app.post("/mcp/servers/{server_id}/container/restart")
async def mcp_restart_container(server_id: str):
    server = get_mcp_server(server_id)
    if not server or not server.get("managed"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"error": "Managed server not found"}
        )
    from agent.docker_manager import restart_container

    ok = restart_container(server["container_id"])
    if ok:
        update_mcp_server(server_id, container_status="running")
    return {"restarted": ok}


@app.delete("/mcp/servers/{server_id}/container")
async def mcp_destroy_container(server_id: str):
    server = get_mcp_server(server_id)
    if not server or not server.get("managed"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"error": "Managed server not found"}
        )
    from agent.docker_manager import remove_container

    ok = remove_container(server["container_id"])
    update_mcp_server(
        server_id,
        container_id="",
        container_name="",
        container_status="",
        url="pending://provisioning",
        status="disconnected",
        tools=[],
    )
    return {"destroyed": ok}


@app.get("/mcp/servers/{server_id}/container/logs")
async def mcp_container_logs(server_id: str, tail: int = 100):
    server = get_mcp_server(server_id)
    if not server or not server.get("managed"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"error": "Managed server not found"}
        )
    from agent.docker_manager import get_container_logs

    logs = get_container_logs(server["container_id"], tail=tail)
    return {"logs": logs}


@app.get("/mcp/servers/{server_id}/container/status")
async def mcp_container_status(server_id: str):
    server = get_mcp_server(server_id)
    if not server or not server.get("managed"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"error": "Managed server not found"}
        )
    from agent.docker_manager import get_container_status

    status = get_container_status(server["container_id"])
    return {"status": status}


# ── Guardrails ──────────────────────────────────────────────────────────────


@app.get("/guardrails")
async def api_list_guardrails():
    return {"guardrails": list_guardrails()}


@app.get("/guardrails/{guardrail_id}")
async def api_get_guardrail(guardrail_id: str):
    g = get_guardrail(guardrail_id)
    if not g:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Guardrail not found"})
    return g


@app.put("/guardrails/{guardrail_id}")
async def api_update_guardrail(guardrail_id: str, request: Request):
    data = await request.json()
    g = update_guardrail(guardrail_id, **data)
    if not g:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Guardrail not found"})
    return g


# ── Version History endpoints ──────────────────────────────────────────────


@app.get("/versions/{entity_type}/{entity_id}")
async def versions_list(entity_type: str, entity_id: str):
    """List all versions for an entity (agent, skill, prompt)."""
    if entity_type not in ("agent", "skill", "prompt"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content={"error": "entity_type must be agent, skill, or prompt"},
        )
    versions = list_versions(entity_type, entity_id)
    return {"versions": versions, "count": len(versions)}


@app.get("/versions/detail/{version_id}")
async def versions_detail(version_id: str):
    """Get a specific version snapshot."""
    v = get_version(version_id)
    if not v:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Version not found"})
    return v


@app.post("/versions/{entity_type}/{entity_id}/rollback/{version_id}")
async def versions_rollback(entity_type: str, entity_id: str, version_id: str):
    """Rollback an entity to a previous version."""
    if entity_type not in ("agent", "skill", "prompt"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content={"error": "entity_type must be agent, skill, or prompt"},
        )
    v = get_version(version_id)
    if not v or v["entity_type"] != entity_type or v["entity_id"] != entity_id:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404,
            content={"error": "Version not found or does not match entity"},
        )
    snapshot = v["snapshot"]
    # Apply rollback based on entity type
    if entity_type == "agent":
        result = update_agent(
            entity_id,
            **{
                k: v
                for k, v in snapshot.items()
                if k not in ("id", "created_at", "updated_at", "is_default")
            },
        )
    elif entity_type == "skill":
        result = update_skill(
            entity_id,
            **{
                k: v
                for k, v in snapshot.items()
                if k not in ("id", "created_at", "updated_at")
            },
        )
    elif entity_type == "prompt":
        result = update_prompt(
            entity_id,
            **{
                k: v
                for k, v in snapshot.items()
                if k not in ("id", "created_at", "updated_at")
            },
        )
    else:
        result = None
    if not result:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": "Rollback failed"})
    log_audit(
        "rollback",
        entity_type,
        entity_id,
        snapshot.get("name", ""),
        {"to_version": v["version"]},
    )
    return {"status": "rolled_back", "version": v["version"], "entity": result}


# ── Audit Log endpoints ───────────────────────────────────────────────────


@app.get("/audit-log")
async def audit_log_endpoint(
    limit: int = 100, entity_type: str | None = None, action: str | None = None
):
    """List recent audit log entries."""
    entries = list_audit_log(
        limit=min(limit, 500), entity_type=entity_type, action=action
    )
    return {"entries": entries, "count": len(entries)}


# ── LLM Usage / Activity endpoints ────────────────────────────────────────


@app.get("/llm-activity")
async def llm_activity_list(
    limit: int = 200,
    session_id: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    since: str | None = None,
):
    """List LLM usage logs with optional filters."""
    entries = list_llm_usage(
        limit=min(limit, 1000),
        session_id=session_id,
        model=model,
        provider=provider,
        since=since,
    )
    return {"entries": entries, "count": len(entries)}


@app.get("/llm-activity/summary")
async def llm_activity_summary():
    """Return aggregated LLM usage statistics."""
    return get_llm_usage_summary()


# ── Data Connectors endpoints ──────────────────────────────────────────────


class ConnectorCreateRequest(BaseModel):
    name: str
    connector_type: str
    config: dict = {}
    auto_index: bool = False
    schedule: str = ""


class ConnectorUpdateRequest(BaseModel):
    name: str | None = None
    config: dict | None = None
    enabled: bool | None = None
    auto_index: bool | None = None
    schedule: str | None = None


class ConnectorTestRequest(BaseModel):
    connector_type: str
    config: dict


class ConnectorSyncRequest(BaseModel):
    auto_index: bool = False
    chunk_size: int = 1000
    chunk_overlap: int = 200


@app.get("/connectors/catalog")
async def connectors_catalog():
    """List available connector types and their config schemas."""
    return {"connectors": CONNECTOR_CATALOG}


@app.get("/connectors")
async def connectors_list():
    """List all configured connectors."""
    connectors = list_connectors()
    return {"connectors": connectors}


@app.get("/connectors/{connector_id}")
async def connectors_get(connector_id: str):
    """Get a single connector."""
    c = get_connector(connector_id)
    if not c:
        return {"error": "Connector not found"}, 404
    return c


@app.post("/connectors")
async def connectors_create(req: ConnectorCreateRequest):
    """Create a new connector configuration."""
    if req.connector_type not in CONNECTOR_CATALOG:
        return {"error": f"Unknown connector type: {req.connector_type}"}, 400
    cid = generate_connector_id()
    connector = create_connector(
        cid, req.name, req.connector_type, req.config, req.auto_index, req.schedule
    )
    log_audit("create", "connector", cid, req.name, {"type": req.connector_type})
    return connector


@app.put("/connectors/{connector_id}")
async def connectors_update(connector_id: str, req: ConnectorUpdateRequest):
    """Update a connector configuration."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    result = update_connector(connector_id, updates)
    if not result:
        return {"error": "Connector not found"}, 404
    return result


@app.delete("/connectors/{connector_id}")
async def connectors_delete(connector_id: str):
    """Delete a connector and its sync history."""
    c = get_connector(connector_id)
    if not c:
        return {"error": "Connector not found"}, 404
    delete_connector(connector_id)
    log_audit("delete", "connector", connector_id, c["name"], {})
    return {"status": "deleted"}


@app.post("/connectors/test")
async def connectors_test(req: ConnectorTestRequest):
    """Test a connector's connectivity without saving."""
    result = test_connector(req.connector_type, req.config)
    return result


@app.post("/connectors/{connector_id}/sync")
async def connectors_sync(connector_id: str, req: ConnectorSyncRequest):
    """Run a sync: pull data from source into filestore, optionally index."""
    from agent.filestore import save_file

    c = get_connector(connector_id)
    if not c:
        return {"error": "Connector not found"}, 404

    job_id = generate_job_id()
    create_sync_job(job_id, connector_id)

    try:
        documents = run_sync(c["connector_type"], c["config"])
        docs_indexed = 0

        for doc in documents:
            doc_id = str(uuid.uuid4())
            filename = doc["name"]
            content = doc["content"]

            # Stage in filestore
            save_file(doc_id, filename, content)

            # Create registry entry
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "txt"
            create_document_registry(
                doc_id=doc_id,
                name=filename,
                source=f"connector:{c['name']}",
                file_type=ext,
                status="uploaded",
                source_type="connected",
                storage_path=f"/data/filestore/{doc_id}/{filename}",
            )

            # Auto-index if requested
            if req.auto_index or c.get("auto_index"):
                from agent.vectorstore import ingest_text

                chunks = ingest_text(
                    content,
                    filename,
                    chunk_size=req.chunk_size,
                    chunk_overlap=req.chunk_overlap,
                )
                update_document_registry(
                    doc_id,
                    {
                        "status": "indexed",
                        "chunk_count": chunks,
                    },
                )
                docs_indexed += 1

        # Update job and connector
        update_sync_job(
            job_id, "completed", docs_pulled=len(documents), docs_indexed=docs_indexed
        )
        update_connector(
            connector_id,
            {
                "last_sync": __import__("datetime")
                .datetime.now(__import__("datetime").timezone.utc)
                .isoformat(),
                "last_status": "completed",
                "doc_count": c["doc_count"] + len(documents),
            },
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "docs_pulled": len(documents),
            "docs_indexed": docs_indexed,
        }

    except Exception as e:
        update_sync_job(job_id, "failed", error=str(e))
        update_connector(connector_id, {"last_status": "failed"})
        logger.error(f"Connector sync failed: {e}")
        return {"error": str(e), "job_id": job_id, "status": "failed"}


@app.get("/connectors/{connector_id}/jobs")
async def connectors_jobs(connector_id: str, limit: int = 20):
    """List sync job history for a connector."""
    jobs = list_sync_jobs(connector_id=connector_id, limit=limit)
    return {"jobs": jobs}


# ── Pipeline CRUD + Execution ──────────────────────────────────────────────


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    strategy: str = Field(
        default="sequential", pattern="^(sequential|parallel|conditional)$"
    )
    steps: list[dict] = Field(default_factory=list)


class PipelineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    strategy: str | None = None
    steps: list[dict] | None = None
    status: str | None = None


class PipelineRunRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8192)
    session_id: str = Field(default="")
    variables: dict = Field(default_factory=dict)


@app.get("/pipelines")
async def pipelines_list():
    return {"pipelines": list_pipelines()}


@app.post("/pipelines")
async def pipelines_create(body: PipelineCreate):
    p = create_pipeline(
        name=body.name,
        description=body.description,
        strategy=body.strategy,
        steps=body.steps,
    )
    return p


@app.get("/pipelines/{pipeline_id}")
async def pipelines_get(pipeline_id: str):
    p = get_pipeline(pipeline_id)
    if not p:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Pipeline not found"})
    return p


@app.put("/pipelines/{pipeline_id}")
async def pipelines_update(pipeline_id: str, body: PipelineUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    p = update_pipeline(pipeline_id, **updates)
    if not p:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Pipeline not found"})
    return p


@app.delete("/pipelines/{pipeline_id}")
async def pipelines_delete(pipeline_id: str):
    ok = delete_pipeline(pipeline_id)
    if not ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Pipeline not found"})
    return {"deleted": True}


@app.get("/pipelines/{pipeline_id}/runs")
async def pipelines_runs_list(pipeline_id: str, limit: int = 50):
    runs = list_pipeline_runs(pipeline_id=pipeline_id, limit=limit)
    return {"runs": runs}


@app.get("/pipeline-runs")
async def all_pipeline_runs(limit: int = 50):
    runs = list_pipeline_runs(limit=limit)
    return {"runs": runs}


@app.post("/pipelines/{pipeline_id}/run")
async def pipelines_execute(pipeline_id: str, body: PipelineRunRequest):
    """Execute a multi-agent pipeline — sequential, parallel, or conditional."""
    from datetime import datetime, timezone

    pipeline = get_pipeline(pipeline_id)
    if not pipeline:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"error": "Pipeline not found"})

    steps = pipeline["steps"]
    if not steps:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"error": "Pipeline has no steps"})

    strategy = pipeline["strategy"]
    session_id = body.session_id or f"pipeline-{pipeline_id}-{str(uuid.uuid4())[:6]}"

    # Create a run record
    run = create_pipeline_run(pipeline_id, strategy, steps)
    run_id = run["id"]

    step_results = []
    prompt = body.prompt
    overall_status = "completed"

    try:
        if strategy == "sequential":
            # Each agent runs in order, output feeds into next
            for i, step in enumerate(steps):
                agent_id = step.get("agent_id", "")
                step_name = step.get("name", f"Step {i+1}")
                agent = get_agent(agent_id) if agent_id else None

                step_prompt = prompt
                if i > 0 and step_results:
                    prev = step_results[-1]
                    step_prompt = f"Previous step output:\\n{prev.get('response', '')}\\n\\nNow: {prompt}"
                    if step.get("prompt_template"):
                        step_prompt = (
                            step["prompt_template"]
                            .replace("{{input}}", prompt)
                            .replace("{{previous}}", prev.get("response", ""))
                        )

                try:
                    result = await run_agent(
                        prompt=step_prompt,
                        session_id=f"{session_id}-step-{i}",
                        request_id=f"pipe-{run_id}-{i}",
                        agent_config=agent or {},
                    )
                    step_results.append(
                        {
                            "step": i,
                            "name": step_name,
                            "agent_id": agent_id,
                            "agent_name": agent["name"] if agent else "Default",
                            "status": "completed",
                            "response": result["response"],
                            "tools_used": result.get("tools_used", []),
                        }
                    )
                except Exception as e:
                    step_results.append(
                        {
                            "step": i,
                            "name": step_name,
                            "agent_id": agent_id,
                            "agent_name": agent["name"] if agent else "Default",
                            "status": "failed",
                            "error": str(e),
                        }
                    )
                    if not step.get("continue_on_error"):
                        overall_status = "failed"
                        break

        elif strategy == "parallel":
            import asyncio

            # All agents run simultaneously
            async def run_step(i, step):
                agent_id = step.get("agent_id", "")
                step_name = step.get("name", f"Step {i+1}")
                agent = get_agent(agent_id) if agent_id else None
                step_prompt = (
                    step.get("prompt_template", prompt).replace("{{input}}", prompt)
                    if step.get("prompt_template")
                    else prompt
                )
                try:
                    result = await run_agent(
                        prompt=step_prompt,
                        session_id=f"{session_id}-step-{i}",
                        request_id=f"pipe-{run_id}-{i}",
                        agent_config=agent or {},
                    )
                    return {
                        "step": i,
                        "name": step_name,
                        "agent_id": agent_id,
                        "agent_name": agent["name"] if agent else "Default",
                        "status": "completed",
                        "response": result["response"],
                        "tools_used": result.get("tools_used", []),
                    }
                except Exception as e:
                    return {
                        "step": i,
                        "name": step_name,
                        "agent_id": agent_id,
                        "agent_name": agent["name"] if agent else "Default",
                        "status": "failed",
                        "error": str(e),
                    }

            tasks = [run_step(i, step) for i, step in enumerate(steps)]
            step_results = await asyncio.gather(*tasks)
            step_results = list(step_results)
            if any(r["status"] == "failed" for r in step_results):
                overall_status = "partial"

        elif strategy == "conditional":
            # First step runs, then condition determines which branch to take
            for i, step in enumerate(steps):
                agent_id = step.get("agent_id", "")
                step_name = step.get("name", f"Step {i+1}")
                agent = get_agent(agent_id) if agent_id else None
                condition = step.get("condition", "")

                # Check condition against previous result
                if condition and step_results:
                    prev_response = step_results[-1].get("response", "").lower()
                    if condition.startswith("contains:"):
                        keyword = condition.split(":", 1)[1].strip().lower()
                        if keyword not in prev_response:
                            step_results.append(
                                {
                                    "step": i,
                                    "name": step_name,
                                    "agent_id": agent_id,
                                    "agent_name": agent["name"] if agent else "Default",
                                    "status": "skipped",
                                    "reason": f"Condition not met: {condition}",
                                }
                            )
                            continue
                    elif condition == "on_error":
                        if step_results[-1].get("status") != "failed":
                            step_results.append(
                                {
                                    "step": i,
                                    "name": step_name,
                                    "agent_id": agent_id,
                                    "agent_name": agent["name"] if agent else "Default",
                                    "status": "skipped",
                                    "reason": "Previous step did not fail",
                                }
                            )
                            continue

                step_prompt = prompt
                if i > 0 and step_results:
                    last_completed = [
                        r for r in step_results if r["status"] == "completed"
                    ]
                    if last_completed:
                        step_prompt = f"Previous output:\\n{last_completed[-1].get('response', '')}\\n\\nNow: {prompt}"

                try:
                    result = await run_agent(
                        prompt=step_prompt,
                        session_id=f"{session_id}-step-{i}",
                        request_id=f"pipe-{run_id}-{i}",
                        agent_config=agent or {},
                    )
                    step_results.append(
                        {
                            "step": i,
                            "name": step_name,
                            "agent_id": agent_id,
                            "agent_name": agent["name"] if agent else "Default",
                            "status": "completed",
                            "response": result["response"],
                            "tools_used": result.get("tools_used", []),
                        }
                    )
                except Exception as e:
                    step_results.append(
                        {
                            "step": i,
                            "name": step_name,
                            "agent_id": agent_id,
                            "agent_name": agent["name"] if agent else "Default",
                            "status": "failed",
                            "error": str(e),
                        }
                    )

    except Exception as e:
        overall_status = "failed"
        logger.error(f"Pipeline execution error: {e}")

    # Finalize run record
    now = datetime.now(timezone.utc).isoformat()
    update_pipeline_run(
        run_id, status=overall_status, step_results=step_results, completed_at=now
    )

    return {
        "run_id": run_id,
        "pipeline_id": pipeline_id,
        "status": overall_status,
        "strategy": strategy,
        "step_results": step_results,
    }


# ── n8n Agent Discovery ───────────────────────────────────────────────────


@app.get("/n8n/agents")
async def n8n_agent_discovery():
    """Agent discovery endpoint for n8n — returns agents in a format
    suitable for dynamic HTTP node usage."""
    agents = list_agents()
    return {
        "agents": [
            {
                "id": a["id"],
                "name": a["name"],
                "description": a.get("description", ""),
                "provider": a.get("provider", "ollama"),
                "model": a.get("model", "llama3"),
                "run_url": f"http://agent-service:8000/run",
                "payload_template": {
                    "prompt": "{{your_prompt}}",
                    "agent_id": a["id"],
                    "sessionId": "{{session_id}}",
                },
            }
            for a in agents
        ],
        "pipelines": [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description", ""),
                "strategy": p["strategy"],
                "step_count": len(p.get("steps", [])),
                "run_url": f"http://agent-service:8000/pipelines/{p['id']}/run",
                "payload_template": {
                    "prompt": "{{your_prompt}}",
                    "session_id": "{{session_id}}",
                },
            }
            for p in list_pipelines()
        ],
    }
