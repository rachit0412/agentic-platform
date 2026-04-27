# Platform Architecture

Comprehensive architecture reference for the Agentic Platform — a containerised agent factory built on Docker Compose with 12 services.

---

## System Overview

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                        Docker Network: platform-net                     │
 │                                                                         │
 │  ┌─────────────┐                                                        │
 │  │  Browser     │  http://localhost:3000                                │
 │  └──────┬──────┘                                                        │
 │         │                                                               │
 │  ┌──────▼──────┐    ┌──────────────┐    ┌──────────────┐               │
 │  │ ui-console  │───►│agent-service │───►│tools-service │               │
 │  │ Express.js  │    │ FastAPI +    │    │  FastAPI     │               │
 │  │ :3000       │    │ LangGraph    │    │  :8011       │               │
 │  └─────────────┘    │ :8010        │    └──────────────┘               │
 │                     │              │                                    │
 │                     │  ┌───────┐   │    ┌──────────────┐               │
 │                     │  │SQLite │   │───►│  ChromaDB    │               │
 │                     │  │memory │   │    │  :8200       │               │
 │                     │  └───────┘   │    └──────────────┘               │
 │                     │              │                                    │
 │                     │  ┌───────────┤    ┌──────────────┐               │
 │                     │  │ LLM       │───►│   Ollama     │               │
 │                     │  │ Provider  │    │   :11436     │               │
 │                     │  │           │    │ OR Azure     │               │
 │                     │  │           │    │ OpenAI ☁     │               │
 │                     │  └───────────┤    └──────────────┘               │
 │                     │              │                                    │
 │                     │  ┌─────┐ ┌─────┐                                 │
 │                     │  │ A2A │ │ MCP │  Peer agents & tool servers     │
 │                     │  └─────┘ └─────┘                                 │
 │                     └──────────────┘                                    │
 │                                                                         │
 │  ┌──── Observability ──────────────────────────────────────────────┐   │
 │  │                                                                  │   │
 │  │  agent/tools ──► OTel Collector ──► Prometheus ──► Grafana      │   │
 │  │       │                    │                           │         │   │
 │  │       │                    └──► Loki (logs) ──────────►│         │   │
 │  │       │                                                          │   │
 │  │       └──────► Langfuse SDK ──► Langfuse ◄── langfuse-db (PG)  │   │
 │  │                                                                  │   │
 │  └──────────────────────────────────────────────────────────────────┘   │
 │                                                                         │
 │  ┌──── Automation ─────┐                                               │
 │  │  n8n  :5678         │  Workflow orchestration, webhooks,            │
 │  │  (5 workflow        │  scheduled tasks                              │
 │  │   templates)        │                                               │
 │  └─────────────────────┘                                               │
 └─────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer              | Technology                      | Version        |
| ------------------ | ------------------------------- | -------------- |
| **Frontend**       | Express.js + EJS                | Node 20        |
| **Agent Runtime**  | FastAPI + LangGraph + LangChain | Python 3.11    |
| **Tool Runtime**   | FastAPI                         | Python 3.11    |
| **LLM (local)**    | Ollama                          | latest         |
| **LLM (cloud)**    | Azure OpenAI                    | 2024-06-01 API |
| **Vector Store**   | ChromaDB                        | 0.6.3          |
| **Memory**         | SQLite                          | —              |
| **Workflows**      | n8n                             | latest         |
| **LLM Tracing**    | Langfuse                        | v2             |
| **Metrics**        | Prometheus                      | latest         |
| **Dashboards**     | Grafana                         | 11.0.0         |
| **Logs**           | Loki                            | 3.0.0          |
| **Trace Pipeline** | OpenTelemetry Collector         | 0.100.0        |
| **Langfuse DB**    | PostgreSQL                      | 16 Alpine      |
| **Containers**     | Docker Compose                  | v2             |

---

## Service Details

### Agent Service (`services/agent/`)

The core intelligence layer. A FastAPI application running a LangGraph ReAct agent.

**Internal port:** 8000 → **Host port:** 8010

| Module            | File                     | Purpose                                                                             |
| ----------------- | ------------------------ | ----------------------------------------------------------------------------------- |
| API layer         | `main.py`                | 47 REST endpoints — CRUD for agents, skills, prompts, A2A, MCP, sessions, documents |
| Agent graph       | `agent/graph.py`         | LangGraph state graph: retrieve → reason → act → respond                            |
| LLM provider      | `agent/llm.py`           | Multi-provider abstraction (Ollama + Azure OpenAI)                                  |
| Memory & registry | `agent/memory.py`        | SQLite storage for conversations, agents, skills, prompts, A2A peers, MCP servers   |
| Tool client       | `agent/tools.py`         | HTTP client to tools-service; tool catalogue                                        |
| Vector store      | `agent/vectorstore.py`   | ChromaDB wrapper for document ingestion & search                                    |
| Observability     | `agent/observability.py` | OpenTelemetry spans + Langfuse callback handler                                     |

**Key API groups (47 endpoints):**

- `POST /run`, `POST /run/stream` — Execute agent (blocking / SSE streaming)
- `GET|POST /agents`, `GET|PUT|DELETE /agents/{id}` — Agent CRUD
- `GET|POST /skills`, `GET|PUT|DELETE /skills/{id}` — Skill CRUD
- `GET|POST /prompts`, `GET|PUT|DELETE /prompts/{id}` — Prompt CRUD
- `GET|POST /a2a/peers`, `GET|PUT|DELETE /a2a/peers/{id}`, `POST /a2a/send`, `GET /a2a/card` — A2A protocol
- `GET|POST /mcp/servers`, `GET|PUT|DELETE /mcp/servers/{id}`, `POST /mcp/servers/{id}/discover|invoke` — MCP protocol
- `GET|DELETE /sessions/{id}`, `GET /sessions/{id}/history|summary` — Session management
- `POST /documents/ingest|search|fetch-url`, `GET /documents`, `DELETE /documents/{source}` — RAG
- `GET /models`, `POST /models/switch` — Model management
- `GET /tools`, `GET /memory/stats`, `GET /health` — Utilities

### Tools Service (`services/tools/`)

Stateless utility functions exposed as REST endpoints. Called by the agent at runtime.

**Internal port:** 8001 → **Host port:** 8011

| Endpoint                    | Purpose                                                                  |
| --------------------------- | ------------------------------------------------------------------------ |
| `POST /tools/math`          | AST-based safe arithmetic (max 200 chars, blocked dangerous builtins)    |
| `POST /tools/http-fetch`    | URL fetch with domain allowlist (SSRF protection)                        |
| `POST /tools/file-write`    | Write notes to `/data/notes/` (path traversal protection, dotfile block) |
| `POST /tools/file-read`     | Read notes from `/data/notes/` (same protections)                        |
| `POST /tools/datetime`      | Current UTC date, time, weekday                                          |
| `POST /tools/web-search`    | DuckDuckGo search                                                        |
| `POST /tools/code-execute`  | Python code sandbox (blocked patterns: import os, exec, eval, etc.)      |
| `POST /tools/vector-search` | Proxy to agent-service document search                                   |
| `POST /tools/vector-store`  | Proxy to agent-service document ingest                                   |

### UI Console (`services/ui-console/`)

Express.js dashboard serving 15 EJS pages and proxying all `/api/*` requests to backend services.

**Internal port:** 3001 → **Host port:** 3000

**Page routes (15):** `/` (overview), `/run-agent`, `/agents`, `/skills`, `/prompts`, `/documents`, `/a2a`, `/mcp`, `/workflows`, `/llm-activity`, `/traceability`, `/evaluation`, `/observability`, `/marketplace`, `/admin`

**API proxy routes (~80):** Forward all `/api/*` requests to agent-service, tools-service, n8n, Langfuse, Prometheus, Grafana, and ChromaDB.

---

## Data Flow

### Agent Execution Flow

```
 User prompt (UI or curl)
        │
        ▼
 ┌─ agent-service ──────────────────────────────────────────┐
 │                                                           │
 │  1. Load agent config (SQLite) — model, skills, KB       │
 │  2. Retrieve context from ChromaDB (auto-RAG)            │
 │  3. Build system prompt (agent prompt + skill prompts)   │
 │  4. Enter LangGraph ReAct loop:                          │
 │     a. LLM reasons about the task                        │
 │     b. LLM decides to call a tool (or respond)           │
 │     c. Tool call → tools-service HTTP request            │
 │     d. Tool result → back to LLM for next iteration      │
 │     e. Repeat until task complete or max_iterations       │
 │  5. Store conversation in SQLite memory                  │
 │  6. Emit traces to Langfuse + OTel spans                 │
 │  7. Return response (or stream via SSE)                  │
 │                                                           │
 └───────────────────────────────────────────────────────────┘
```

### Document Ingestion Flow

```
 Text / URL input
      │
      ▼
 agent-service /documents/ingest
      │
      ├─ Chunk text (configurable size + overlap)
      ├─ Generate embeddings (Ollama or OpenAI)
      └─ Store vectors in ChromaDB
```

### A2A Delegation Flow

```
 Agent A (this platform)
      │
      ├─ POST /a2a/send { peer_id, task, context }
      │
      ▼
 Peer Agent B (remote URL)
      │
      └─ Returns result → Agent A continues reasoning
```

---

## Docker Compose Services

12 application containers on the `platform-net` bridge network:

| Container        | Image                                          | Ports (host:container) |
| ---------------- | ---------------------------------------------- | ---------------------- |
| `ui-console`     | Built from `services/ui-console/`              | 3000:3001              |
| `agent-service`  | Built from `services/agent/`                   | 8010:8000              |
| `tools-service`  | Built from `services/tools/`                   | 8011:8001              |
| `ollama`         | `ollama/ollama:latest`                         | 11436:11434            |
| `chromadb`       | `chromadb/chroma:0.6.3`                        | 8200:8000              |
| `n8n`            | `n8nio/n8n:latest`                             | 5678:5678              |
| `langfuse`       | `langfuse/langfuse:2`                          | 3012:3000              |
| `langfuse-db`    | `postgres:16-alpine`                           | — (internal)           |
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.100.0` | 4317, 4318, 8889       |
| `prometheus`     | `prom/prometheus:latest`                       | 9090:9090              |
| `grafana`        | `grafana/grafana:11.0.0`                       | 3013:3000              |
| `loki`           | `grafana/loki:3.0.0`                           | 3100:3100              |

### Dependency Chain

```
ollama ─────────────┐
chromadb ───────────┤
tools-service ──────┼──► agent-service ──► ui-console
langfuse-db ──► langfuse
prometheus ──► grafana
```

### Persistent Volumes

| Volume             | Purpose                    |
| ------------------ | -------------------------- |
| `ollama-data`      | Downloaded LLM model files |
| `chroma-data`      | Vector store embeddings    |
| `n8n-data`         | n8n workflow definitions   |
| `langfuse-db-data` | Langfuse PostgreSQL data   |
| `prometheus-data`  | Metrics time-series data   |
| `grafana-data`     | Dashboard configs & state  |
| `loki-data`        | Log index & chunks         |

### Bind Mounts

| Host Path                               | Container Path                 | Purpose                  |
| --------------------------------------- | ------------------------------ | ------------------------ |
| `./services/agent/`                     | `/app` (agent-service)         | Live-reload for dev      |
| `./services/tools/`                     | `/app` (tools-service)         | Live-reload for dev      |
| `./data/`                               | `/data` (both services)        | SQLite DB + notes files  |
| `./observability/prometheus/`           | `/etc/prometheus/`             | Prometheus scrape config |
| `./observability/grafana/provisioning/` | `/etc/grafana/provisioning/`   | Grafana data sources     |
| `./observability/grafana/dashboards/`   | `/var/lib/grafana/dashboards/` | Grafana dashboards       |
| `./observability/loki/`                 | `/etc/loki/`                   | Loki configuration       |
| `./services/otel/`                      | `/etc/` (otel-collector)       | OTel collector config    |

---

## Telemetry Pipeline

```
 agent-service ──┬── OpenTelemetry SDK ──► otel-collector ──┬──► Prometheus (metrics)
                 │                                           └──► (stdout / Loki)
                 │
                 └── Langfuse CallbackHandler ──► Langfuse (LLM traces, costs, latency)

 Grafana ──► Prometheus (metrics datasource)
         └──► Loki (logs datasource)
```

### Metrics Collected

- **Prometheus**: HTTP request count/duration, active connections, scrape targets health
- **Langfuse**: LLM token usage, cost per call, latency breakdown, model comparison
- **Grafana Dashboards**: Platform health dashboard (`observability/grafana/dashboards/platform-health.json`)

---

## Security

| Protection           | Implementation                                                             |
| -------------------- | -------------------------------------------------------------------------- |
| **XSS Prevention**   | Global `escapeHtml()` function sanitises all user content in EJS           |
| **Input Validation** | Pydantic models enforce types, min/max lengths (e.g., prompt ≤ 4096 chars) |
| **SSRF Protection**  | `http-fetch` tool uses domain allowlist                                    |
| **Path Traversal**   | File tools block `..`, absolute paths, and dotfiles                        |
| **Math Injection**   | AST-based expression parser blocks dangerous builtins                      |
| **Code Execution**   | Blocked patterns (import os, exec, eval, subprocess, etc.)                 |

---

## UI Pages (15)

| #   | Page          | Route            | Key Features                                               |
| --- | ------------- | ---------------- | ---------------------------------------------------------- |
| 1   | Overview      | `/`              | Service health grid, KPI stat cards, platform stats        |
| 2   | Run Agent     | `/run-agent`     | Agent picker, SSE streaming, session history, tool display |
| 3   | Agents        | `/agents`        | CRUD agent configs — model, skills, tools, KB, prompt      |
| 4   | Skills        | `/skills`        | CRUD skill packages — prompt + tools + constraints         |
| 5   | Prompts       | `/prompts`       | Prompt library — name, category, tags, content             |
| 6   | Documents     | `/documents`     | Ingest text/URLs, search RAG, delete documents             |
| 7   | A2A           | `/a2a`           | Register peers, ping health, send tasks, view agent card   |
| 8   | MCP           | `/mcp`           | Register servers, discover tools, invoke tools             |
| 9   | Workflows     | `/workflows`     | n8n workflow list — ID, name, active status, updated date  |
| 10  | LLM Activity  | `/llm-activity`  | LLM usage monitoring and call logs                         |
| 11  | Traceability  | `/traceability`  | Langfuse trace timeline, detail view, observation steps    |
| 12  | Evaluation    | `/evaluation`    | Agent comparison — scoring across models and skills        |
| 13  | Observability | `/observability` | Prometheus targets, Grafana embed, Loki, OTel status       |
| 14  | Marketplace   | `/marketplace`   | Browse & install agent/skill/workflow templates            |
| 15  | Admin         | `/admin`         | Ollama model list, system info, active model management    |

---

## Test Suites

| Suite         | Path                                    | Framework | Scope                                     |
| ------------- | --------------------------------------- | --------- | ----------------------------------------- |
| Unit (Python) | `tests/unit/test_agent.py`              | pytest    | Agent graph, LLM provider, memory         |
| Unit (Python) | `tests/unit/test_llm.py`                | pytest    | LLM provider switching, model listing     |
| Unit (Python) | `tests/unit/test_tools.py`              | pytest    | Tool endpoints, math, file, fetch         |
| Unit (Python) | `tests/unit/test_vectorstore.py`        | pytest    | ChromaDB ingestion, search, deletion      |
| Unit (JS)     | `tests/unit/test_console.test.js`       | jest      | UI console routes, API proxies            |
| Integration   | `tests/integration/test_integration.py` | pytest    | Cross-service API flows                   |
| Contract      | `tests/contract/test_contracts.py`      | pytest    | API schema contracts                      |
| E2E           | `tests/e2e/test_e2e.py`                 | pytest    | Full user journey (create → run → verify) |
| Load          | `tests/load/load-test.js`               | k6        | Concurrent requests, throughput, latency  |
| Smoke         | `tests/smoke/smoke-test.sh`             | bash      | Service health & connectivity checks      |

---

## n8n Workflow Templates

| Workflow          | File                                   | Purpose                         |
| ----------------- | -------------------------------------- | ------------------------------- |
| Agent Workflow    | `n8n/workflows/agent-workflow.json`    | Trigger agent runs via webhook  |
| Create Workflow   | `n8n/workflows/create-workflow.json`   | Create agents/skills via API    |
| RAG Ingest        | `n8n/workflows/rag-ingest.json`        | Automated document ingestion    |
| Scheduled Summary | `n8n/workflows/scheduled-summary.json` | Periodic session summaries      |
| Web Research      | `n8n/workflows/web-research.json`      | Automated web research & ingest |

---

## Protocols

### A2A (Agent-to-Agent)

Peer agents are registered by URL. Each agent exposes a discovery card at `GET /a2a/card` with its name, description, and capabilities. Agents can delegate sub-tasks to peers via `POST /a2a/send` and incorporate results into their reasoning.

### MCP (Model Context Protocol)

External tool servers are registered with a URL and transport type (HTTP/SSE). The platform discovers available tools via `POST /mcp/servers/{id}/discover` and invokes them via `POST /mcp/servers/{id}/invoke?tool_name=...`. Tools become available to the agent alongside built-in tools.
