# Architecture

> **Auto-generated** — do not edit manually. Run `bash scripts/generate-docs.sh` to refresh.

## System Overview

The Agentic Platform is a containerised agent factory built with:

- **Frontend**: Express.js + EJS (ui-console)
- **Agent Runtime**: FastAPI + LangGraph (agent-service)
- **Tool Runtime**: FastAPI (tools-service)
- **LLM Providers**: Ollama (local), Azure OpenAI, OpenAI, Azure AI Foundry
- **Knowledge Base**: ChromaDB (vector store, RAG)
- **Memory**: SQLite (conversations, agents, skills, A2A peers, MCP servers)
- **Workflows**: n8n (automation, webhooks)
- **Observability**: Prometheus + Grafana + Loki + OpenTelemetry + Langfuse

## Services (8 source directories)

| Directory                   | Description                                                                 |
| --------------------------- | --------------------------------------------------------------------------- |
| `services/agent`            | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry |
| `services/managed-mcp-base` | Service                                                                     |
| `services/n8n-proxy`        | Service                                                                     |
| `services/open-tools-mcp`   | Service                                                                     |
| `services/otel`             | OpenTelemetry Collector configuration                                       |
| `services/tools`            | FastAPI tools-service — math, HTTP, file, datetime tools                    |
| `services/ui-console`       | Express.js platform dashboard — 26 pages, API proxies                       |
| `services/ui-login`         | Service                                                                     |

## Docker Compose Services (16 services)

`agent-service` `brave-search-mcp` `chromadb` `datastore-db` `grafana` `langfuse` `langfuse-db` `loki` `n8n` `n8n-proxy` `ollama` `open-tools-mcp` `otel-collector` `prometheus` `tools-service` `ui-console`

## UI Pages (26 pages)

## Test Suites

## Telemetry Pipeline

```
agent-service → OTel Collector → Prometheus (metrics)
                               → Loki (logs)
agent-service → Langfuse SDK   → Langfuse (LLM traces)
Grafana ← Prometheus + Loki
```

## Protocols

- **A2A (Agent-to-Agent)**: Peer agents registered by URL; agents delegate sub-tasks via HTTP
- **MCP (Model Context Protocol)**: External tool servers provide dynamic tool discovery

## Authentication & Authorization

The platform implements enterprise-grade IAM:

### Authentication Flow

```
User → Login Page (React + framer-motion gate animation)
  │
  ├─ POST /auth/login → agent-service authenticates (PBKDF2)
  │   ├─ Email verified or exempt? → Create session (express-session)
  │   └─ Not verified? → 403 with verification prompt
  │
  ├─ POST /auth/register → Create user + 6-digit verification code
  │   └─ POST /auth/verify-email → Verify code → Allow login
  │
  └─ Session cookie (agentic.sid) → All subsequent requests
```

### Key Components

| Component               | Implementation                                                              |
| ----------------------- | --------------------------------------------------------------------------- |
| **Password Hashing**    | PBKDF2 with salt (hashlib)                                                  |
| **Session Management**  | express-session with server-side store                                      |
| **Email Verification**  | 6-digit codes, admin-created users pre-verified                             |
| **Role-Based Access**   | admin/member/viewer roles, admin-gated routes via `requireAdmin` middleware |
| **Change Password**     | Requires current password verification via `/auth/login` before update      |
| **Profile Management**  | Editable display name, updates session + DB                                 |
| **User Management**     | Admin CRUD: create, edit, delete, verify, enable/disable users              |
| **Workspace Isolation** | ContextVar-based multi-tenant scoping via `x-workspace-id` header           |
