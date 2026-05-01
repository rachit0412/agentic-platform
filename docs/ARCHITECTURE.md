# Architecture

## System Overview

The Agentic Platform is a containerised agent factory built on 13+ services running via Docker Compose.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (http://localhost:3000)                                     │
│  Express.js + EJS — 22 pages, streaming SSE, API proxy              │
├──────────────────────────────────────────────────────────────────────┤
│  Agent Service (FastAPI + LangGraph)   :8010 (internal :8000)        │
│  ReAct loop, agent/skill/prompt registry, auto-RAG, memory, A2A/MCP │
├──────────────┬───────────────────────┬───────────────────────────────┤
│ Tools :8011  │ ChromaDB :8200        │ SQLite (embedded)             │
│ 9 endpoints  │ Vector store + RAG    │ Memory, agents, skills, etc.  │
├──────────────┴───────────────────────┴───────────────────────────────┤
│  LLM Providers: Ollama :11436 · OpenAI · Azure OpenAI · AI Foundry  │
├──────────────────────────────────────────────────────────────────────┤
│  Observability Stack                                                 │
│  Langfuse :3014 · Prometheus :9090 · Grafana :3003 · Loki :3100     │
│  OpenTelemetry Collector :4317-4318                                  │
├──────────────────────────────────────────────────────────────────────┤
│  Orchestration: n8n :5678 (proxy :5679)                              │
└──────────────────────────────────────────────────────────────────────┘
```

## Service Architecture

### UI Console (`services/ui-console/`)

- **Runtime**: Node.js 20 + Express.js + EJS templates
- **Port**: 3000
- **Role**: Server-rendered dashboard; proxies all API calls to agent-service
- **Key files**:
  - `server.js` — Express routes + API proxy middleware (~870 lines)
  - `views/*.ejs` — 22 page templates (layout.ejs provides global navigation, test chat panel, and shared CSS/JS)
- **Architecture**: Each page is an EJS template that includes `layout.ejs` via `<%- include('layout', { title, page, body }) %>`. The body is a template literal containing all HTML + inline `<script>` blocks.
- **Streaming**: Uses SSE (Server-Sent Events) for real-time agent execution — steps, tokens, guardrails, and completion data stream to the browser.

### Agent Service (`services/agent/`)

- **Runtime**: Python 3.11 + FastAPI + LangGraph
- **Port**: 8000 (mapped to 8010 externally)
- **Role**: Core agent runtime — ReAct execution loop, CRUD for agents/skills/prompts/guardrails/tools, A2A/MCP protocol handlers, auto-RAG
- **Key files**:
  - `main.py` — FastAPI app with 50+ REST endpoints (~1100 lines)
  - `agent/graph.py` — LangGraph state graph (ReAct pipeline)
  - `agent/llm.py` — LLM provider abstraction (Ollama, OpenAI, Azure OpenAI, Azure AI Foundry)
  - `agent/memory.py` — SQLite storage layer (~750 lines, 11 tables)
  - `agent/tools.py` — Tool bindings for LangChain
  - `agent/vectorstore.py` — ChromaDB wrapper for RAG
  - `agent/observability.py` — Langfuse + OpenTelemetry instrumentation

### Tools Service (`services/tools/`)

- **Runtime**: Python 3.11 + FastAPI
- **Port**: 8011
- **9 tool endpoints**: math_calculate, http_fetch, file_read, file_write, get_datetime, web_search, execute_code, vector_search, vector_ingest

## Data Flow: Agent Execution

```
User sends prompt via UI or API
         │
         ▼
┌─── Agent Service ────────────────────────────────────────┐
│  1. Input Guardrails (PII, prompt injection, toxicity)   │
│  2. Retrieve Context (ChromaDB → top-k RAG chunks)      │
│  3. Load Memory (SQLite → last N session messages)       │
│  4. Inject: system prompt + skills + agent config        │
│  5. ReAct Loop (max 5 iterations):                       │
│     a. LLM Reasoning → decide action or respond          │
│     b. If tool needed → call Tools Service → loop        │
│     c. If direct answer → break                          │
│  6. Generate Response (final synthesis)                   │
│  7. Output Guardrails (toxicity, bias, safety)           │
│  8. Save to Memory (conversation + session summary)      │
│  9. Emit traces (Langfuse) + metrics (OTel)              │
└──────────────────────────────────────────────────────────┘
         │
         ▼
    SSE stream → UI (step events, tokens, guardrails, done)
```

### Streaming Events (SSE)

| Event        | Payload                                           | Purpose                         |
| ------------ | ------------------------------------------------- | ------------------------------- |
| `step`       | `{step, status, label, duration_ms, detail}`      | Flowchart step progress         |
| `token`      | Raw text                                          | Real-time response streaming    |
| `guardrails` | `{phase, results: [{guardrail, status, detail}]}` | Input/output guardrail results  |
| `done`       | `{response, tools_used, trace_id, usage, model}`  | Final metadata and token counts |

## Database Schema (SQLite)

The agent-service uses a single SQLite database (`/data/memory.db`) with 11 tables:

```sql
-- Core conversation memory
conversations (id, session_id, role, content, timestamp, metadata)
session_summaries (session_id, summary, message_count, updated_at)

-- Agent registry
agents (id, name, description, model, provider, temperature, system_prompt,
        skills, tools, knowledge_base, is_default, guardrails, created_at, updated_at)

-- Skill registry
skills (id, name, description, category, prompt_template, tools,
        constraints, tags, created_at, updated_at)

-- Prompt library
prompts (id, name, description, category, template, variables,
         tags, created_at, updated_at)

-- Safety
guardrails (id, name, type, description, config, enabled, created_at, updated_at)

-- Custom tools
custom_tools (id, name, description, endpoint, method, headers,
              parameters, created_at, updated_at)

-- Protocols
a2a_peers (id, name, url, description, capabilities, created_at, updated_at)
mcp_servers (id, name, url, description, tools, created_at, updated_at)

-- Knowledge Base metadata
documents (id, filename, content_type, chunk_count, status, created_at, metadata)
```

## API Reference

### Agent Execution

| Method | Path          | Description                   |
| ------ | ------------- | ----------------------------- |
| POST   | `/run`        | Execute agent (synchronous)   |
| POST   | `/run/stream` | Execute agent (streaming SSE) |

### Agent Registry

| Method | Path           | Description     |
| ------ | -------------- | --------------- |
| GET    | `/agents`      | List all agents |
| POST   | `/agents`      | Create agent    |
| PUT    | `/agents/{id}` | Update agent    |
| DELETE | `/agents/{id}` | Delete agent    |

### Skills

| Method | Path           | Description     |
| ------ | -------------- | --------------- |
| GET    | `/skills`      | List all skills |
| POST   | `/skills`      | Create skill    |
| PUT    | `/skills/{id}` | Update skill    |
| DELETE | `/skills/{id}` | Delete skill    |

### Prompts

| Method | Path            | Description      |
| ------ | --------------- | ---------------- |
| GET    | `/prompts`      | List all prompts |
| POST   | `/prompts`      | Create prompt    |
| PUT    | `/prompts/{id}` | Update prompt    |
| DELETE | `/prompts/{id}` | Delete prompt    |

### Custom Tools

| Method | Path                 | Description        |
| ------ | -------------------- | ------------------ |
| GET    | `/custom-tools`      | List custom tools  |
| POST   | `/custom-tools`      | Create custom tool |
| PUT    | `/custom-tools/{id}` | Update custom tool |
| DELETE | `/custom-tools/{id}` | Delete custom tool |

### Guardrails

| Method | Path               | Description             |
| ------ | ------------------ | ----------------------- |
| GET    | `/guardrails`      | List all guardrails     |
| PUT    | `/guardrails/{id}` | Update guardrail config |

### Memory & Sessions

| Method | Path                     | Description              |
| ------ | ------------------------ | ------------------------ |
| GET    | `/sessions`              | List all sessions        |
| GET    | `/sessions/{id}/summary` | Get session summary      |
| GET    | `/memory/stats`          | Memory and KB statistics |
| POST   | `/memory/clear`          | Clear all memory         |

### Knowledge Base / RAG

| Method | Path                | Description                 |
| ------ | ------------------- | --------------------------- |
| GET    | `/documents`        | List uploaded documents     |
| POST   | `/documents/upload` | Upload and chunk a document |
| POST   | `/documents/search` | Semantic search across KB   |
| DELETE | `/documents/{id}`   | Delete a document           |

### Protocols

| Method | Path                | Description                |
| ------ | ------------------- | -------------------------- |
| GET    | `/a2a/peers`        | List A2A peers             |
| POST   | `/a2a/peers`        | Register A2A peer          |
| DELETE | `/a2a/peers/{id}`   | Remove A2A peer            |
| POST   | `/a2a/delegate`     | Delegate task to peer      |
| GET    | `/mcp/servers`      | List MCP servers           |
| POST   | `/mcp/servers`      | Register MCP server        |
| DELETE | `/mcp/servers/{id}` | Remove MCP server          |
| POST   | `/mcp/discover`     | Discover tools from server |

### System

| Method | Path        | Description                  |
| ------ | ----------- | ---------------------------- |
| GET    | `/health`   | Health check                 |
| GET    | `/models`   | List available LLM models    |
| GET    | `/tools`    | List registered tools        |
| GET    | `/db-stats` | Database table statistics    |
| GET    | `/export`   | Export full database as JSON |
| POST   | `/import`   | Import database from JSON    |

## LLM Provider Architecture

The platform supports 4 LLM providers via a unified abstraction in `agent/llm.py`:

| Provider         | Env Var                    | Models                      |
| ---------------- | -------------------------- | --------------------------- |
| Ollama (local)   | `OLLAMA_MODEL`             | llama3, mistral, phi3, etc. |
| OpenAI           | `OPENAI_API_KEY`           | gpt-4o, gpt-4o-mini, etc.   |
| Azure OpenAI     | `AZURE_OPENAI_API_KEY`     | Any deployed model          |
| Azure AI Foundry | `AZURE_AI_FOUNDRY_API_KEY` | Any Foundry-hosted model    |

Provider selection: `LLM_PROVIDER` env var sets the default. Per-request override via `provider` + `model` in the API payload.

## Observability Pipeline

```
Agent Service
  ├── Langfuse SDK ──→ Langfuse (:3014) ──→ PostgreSQL (langfuse-db)
  │                     └── Traces, costs, latencies, sessions
  ├── OTel SDK ──→ OTel Collector (:4317) ──→ Prometheus (:9090) [metrics]
  │                                        ──→ Loki (:3100) [logs]
  └── Grafana (:3003) ← Prometheus + Loki [dashboards]
```

## Security Controls

- **Input Guardrails**: Prompt injection detection, PII scanning, toxicity filtering
- **Output Guardrails**: Bias detection, hallucination flagging, sensitive topic filtering
- **XSS Protection**: All user content escaped via `escapeHtml()` in EJS templates
- **SSRF Protection**: URL validation in HTTP fetch tool with domain restrictions
- **Path Traversal**: File I/O restricted to `/data` directory
- **Input Validation**: Request payload validation on all API endpoints

## Protocols

### A2A (Agent-to-Agent)

Agents can delegate sub-tasks to peer agents registered by URL. The delegating agent sends a prompt to the peer's `/run` endpoint and incorporates the response into its reasoning loop.

### MCP (Model Context Protocol)

External tool servers expose tools via a discovery endpoint. The platform queries the server's tool manifest, registers discovered tools, and makes them available to agents at runtime.
