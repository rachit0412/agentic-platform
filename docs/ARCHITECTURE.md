# Architecture

> Last updated: June 2026. This document reflects the current state of the platform — what is **built & operational**, what is **planned on the roadmap**, and key design decisions.

## System Overview

The Agentic Platform is a containerised **agent factory** — a production-ready, self-hosted system for building, running, governing, and optimising autonomous AI agents.

### Core Stack

| Layer             | Technology                                     | Role                                   |
| ----------------- | ---------------------------------------------- | -------------------------------------- |
| **Dashboard**     | Express.js + EJS                               | 26-page platform UI, API proxy, SSO    |
| **Agent Runtime** | FastAPI + LangGraph                            | ReAct loop, 145+ endpoints, registry   |
| **Tool Runtime**  | FastAPI                                        | 32 sandboxed tool endpoints            |
| **LLM Providers** | Ollama, Azure OpenAI, OpenAI, Azure AI Foundry | Multi-provider, runtime switchable     |
| **Vector Store**  | ChromaDB                                       | RAG embeddings, per-agent isolation    |
| **Platform DB**   | SQLite (embedded)                              | Agents, skills, prompts, memory, audit |
| **Datastore DB**  | PostgreSQL 16                                  | Connectors, structured data registry   |
| **LLM Tracing**   | Langfuse 2.x                                   | Full LLM call traces, cost, latency    |
| **Metrics**       | Prometheus + Grafana                           | Service health, request rates          |
| **Logs**          | Loki + OTel Collector                          | Structured log aggregation             |
| **Workflows**     | n8n                                            | Visual automation, webhooks, cron      |
| **Local LLM**     | Ollama                                         | llama3, mistral, deepseek-r1, etc.     |

---

## Services (16 containers)

| Service            | Port      | Description                                              |
| ------------------ | --------- | -------------------------------------------------------- |
| `ui-console`       | 3005      | Express.js + EJS platform dashboard — 26 pages           |
| `agent-service`    | 8010      | FastAPI + LangGraph — core agent runtime, 145+ endpoints |
| `tools-service`    | 8011      | FastAPI — 32 sandboxed tool endpoints                    |
| `ollama`           | 11436     | Local LLM inference server                               |
| `chromadb`         | 8200      | Vector store for embeddings and RAG                      |
| `datastore-db`     | 5433      | PostgreSQL for connectors and structured data            |
| `n8n`              | 5678      | Workflow automation engine                               |
| `n8n-proxy`        | 5679      | Nginx reverse proxy for n8n embedding                    |
| `brave-search-mcp` | —         | Managed MCP server — Brave web search                    |
| `open-tools-mcp`   | —         | MCP server — Wikipedia, weather, dictionary              |
| `langfuse`         | 3014      | LLM tracing, cost tracking, evaluation                   |
| `langfuse-db`      | —         | PostgreSQL backend for Langfuse                          |
| `grafana`          | 3003      | Monitoring dashboards                                    |
| `prometheus`       | 9090      | Metrics collection                                       |
| `loki`             | 3100      | Log aggregation                                          |
| `otel-collector`   | 4317/4318 | OpenTelemetry pipeline                                   |

---

## Source Directories

| Directory                   | Description                                                                                                       |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `services/agent`            | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry, RAG pipeline, guardrails, connectors |
| `services/managed-mcp-base` | Generic MCP server runtime — config mode (HTTP proxy) or code mode (Python functions)                             |
| `services/n8n-proxy`        | Nginx config for n8n reverse proxy (iframe embedding)                                                             |
| `services/open-tools-mcp`   | Community MCP server — Wikipedia, weather, dictionary, 60+ tools                                                  |
| `services/otel`             | OpenTelemetry Collector configuration                                                                             |
| `services/tools`            | FastAPI tools-service — math, HTTP fetch, file I/O, datetime, code execution, text transforms                     |
| `services/ui-console`       | Express.js platform dashboard — 26 EJS pages, 115+ API proxy routes                                               |
| `services/ui-login`         | Standalone Vite + Tailwind login page (pre-auth entry point)                                                      |

---

## UI Pages (26 pages)

| Page             | Path                | Purpose                                                           |
| ---------------- | ------------------- | ----------------------------------------------------------------- |
| Overview         | `/`                 | Platform stats, architecture diagram, service health, quick start |
| Run Agent        | `/run-agent`        | Stream agent responses, activity panel, session management        |
| Agent Builder    | `/agent-builder`    | Visual composition with skill workflow, live test                 |
| AI Studio        | `/ai-studio`        | IDE-style code editor with chat and preview                       |
| Agent Hub        | `/agent-hub`        | Agent factory overview dashboard                                  |
| Agent Registry   | `/agents`           | Create and manage agent definitions                               |
| Skills           | `/skills`           | Build reusable skill packages with file attachments               |
| Prompts          | `/prompts`          | Prompt template library with versioning                           |
| Tools            | `/tools`            | Agent tool catalog management                                     |
| Knowledge Base   | `/documents`        | Upload, search, manage RAG documents                              |
| Workflows        | `/workflows`        | n8n workflow monitoring                                           |
| A2A Protocol     | `/a2a`              | Register peer agents for inter-agent delegation                   |
| MCP Registry     | `/mcp`              | Create, host, and manage MCP tool servers                         |
| REST Console     | `/rest`             | Interactive API console                                           |
| Intelligence Hub | `/intelligence-hub` | Operational intelligence — traces, eval, LLM cost, health         |
| Traceability     | `/traceability`     | Langfuse trace timeline and deep-dive                             |
| Evaluation       | `/evaluation`       | Agent quality scoring and model comparison                        |
| Observability    | `/observability`    | Stack health — Prometheus, Grafana, Loki status                   |
| Guardrails       | `/guardrails`       | Runtime safety controls and policy enforcement                    |
| Data Ingestion   | `/data-ingestion`   | ETL pipeline — connectors, chunking, embedding                    |
| LLM Activity     | `/llm-activity`     | Token usage tracking, cost analysis, per-model breakdown          |
| Pipelines        | `/pipelines`        | Pipeline management and monitoring                                |
| Marketplace      | `/marketplace`      | Browse and install templates                                      |
| Admin            | `/admin`            | 8-tab admin plane — users, personas, health, config               |
| Docs             | `/docs`             | Auto-generated API and architecture documentation                 |

---

## Agent Runtime — How the Agent Thinks

```
User Prompt
  │
  ├── 1. Input Guardrails (PII, injection, toxicity)
  ├── 2. Retrieve Context (ChromaDB → semantic similarity → top-k chunks)
  ├── 3. Load Memory (SQLite → session history → rolling summary)
  ├── 4. Inject Skills + Files + System Prompt
  ├── 4b. Bind MCP Tools (per-agent server registry)
  │
  └── 5. LangGraph ReAct Loop ──────────────────────────────┐
        │                                                   │
        ├── reason(LLM)                                     │
        │     ↓ needs tools?                                │
        ├── tool_call (built-in or MCP)                     │
        │     ↓ or delegate?                                │
        ├── delegate_to_agent (A2A HTTP)                    │
        │     ↓ done?                                       │
        └── generate_response ──────────────────────────────┘
  │
  ├── 6. Output Guardrails (toxicity, length, data leak)
  ├── 7. Save Memory + Emit LLM usage
  ├── 8. OpenTelemetry trace (→ Prometheus + Loki)
  └── 9. Langfuse trace (full prompt/response/cost/latency)
```

### LangGraph State Graph (graph.py)

```python
StateGraph([
  "guardrails_input",     # Safety checks on user input
  "retrieve_context",     # ChromaDB vector search
  "load_memory",          # SQLite session recall
  "reason",               # LLM decision node (ReAct)
  "tool_call",            # Tool execution (may loop)
  "generate_response",    # Final LLM response generation
  "guardrails_output",    # Safety checks on output
])
```

---

## LLM Provider Architecture

```
Agent Service
  ├── get_llm(provider, model, temperature, top_p, max_tokens)
  │     ├── ollama     → ChatOllama (langchain_ollama)
  │     ├── openai     → ChatOpenAI (langchain_openai)
  │     ├── azure-openai → AzureChatOpenAI (langchain_openai)
  │     └── azure-foundry → AzureChatOpenAI (different endpoint/auth)
  │
  └── get_embeddings(provider)
        ├── ollama     → OllamaEmbeddings (nomic-embed-text)
        ├── openai     → OpenAIEmbeddings (text-embedding-3-small)
        ├── azure-openai → AzureOpenAIEmbeddings (ada-002)
        └── azure-foundry → AzureOpenAIEmbeddings
```

**Active model** is persisted to `/data/llm-config.json` — survives container restarts. UI model selector writes to this file via `POST /set-model`.

**Provider detection** (`list_available_models()`):

1. Always returns Ollama models (queried from `/api/tags`)
2. Adds OpenAI models if `OPENAI_API_KEY` is set
3. Adds Azure OpenAI if `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` are set
4. Adds Azure Foundry deployments from `AZURE_FOUNDRY_MODELS` env var

---

## RAG (Retrieval-Augmented Generation) Pipeline

```
Document Upload
  │
  ├── 1. Text extraction (plain text, PDF, code, markdown)
  ├── 2. Chunking (RecursiveCharacterTextSplitter, 512 tokens, 50 overlap)
  ├── 3. Embedding (OllamaEmbeddings / OpenAIEmbeddings)
  └── 4. ChromaDB upsert (per-agent isolated collection)

Agent Run
  │
  ├── 1. Query embedding (same model as ingest)
  ├── 2. ChromaDB similarity search (top-k=4, cosine distance)
  ├── 3. Context injection into system prompt
  └── 4. LLM reasoning with grounded context
```

**Per-agent isolation**: each agent has a ChromaDB collection named `agent_{agent_id}`. Documents are tagged to agents via the `document_agent_tags` SQLite table.

**Advanced retrieval** (`advanced_retrieval.py`):

- Self-query retrieval (LlamaIndex-backed structured queries)
- Hybrid retrieval (dense + sparse via LlamaIndex)
- RAG evaluation scoring (faithfulness, relevance, coherence)

---

## Protocols

### A2A (Agent-to-Agent)

Agents can delegate sub-tasks to other registered agents over HTTP:

```
Orchestrator Agent
  └── reason() → "delegate: research_agent"
       └── POST /run → research-agent-service:8000
            └── returns result → orchestrator continues
```

Peers are registered in SQLite (`a2a_peers` table) and exposed via `GET /a2a-peers`. The `delegate_to_agent` built-in tool handles the HTTP call and response parsing.

### MCP (Model Context Protocol)

Two modes:

1. **External**: Register a URL to any MCP-compatible tool server (`GET /tools/list` endpoint)
2. **Managed**: The platform spawns an isolated Docker container running `managed-mcp-base`:
   - **Config mode**: HTTP endpoint proxy (no-code, JSON configuration)
   - **Code mode**: Custom Python functions deployed as MCP tools

MCP tools are bound per-agent. At runtime, the agent's system prompt is extended with tool descriptions and the ReAct loop calls them via `POST /tools/call`.

**Note**: MCP 1.x introduced the Streamable HTTP transport (replacing the older SSE-based transport). The platform currently uses the SSE transport. Upgrade to Streamable HTTP is on the roadmap.

---

## Telemetry Pipeline

```
agent-service ──OTLP──→ otel-collector ──→ Prometheus (metrics scrape)
                                       └──→ Loki (log pipeline)

agent-service ──Langfuse SDK──→ langfuse → langfuse-db (PostgreSQL)

Grafana ←── Prometheus (datasource)
        ←── Loki (datasource)

Dashboard ←── /api/observability/* (proxy to Prometheus HTTP API)
          ←── /api/traces (proxy to Langfuse API)
```

**Instrumentation** (`observability.py`):

- `setup_otel()` configures OpenTelemetry with OTLP HTTP exporter
- `LangfuseCallbackHandler` attached to every LLM call (captures prompt, response, tokens, cost)
- Custom spans for tool calls, guardrail checks, and RAG retrieval

---

## Database Schema (SQLite — 16 tables)

| Table                 | Purpose                                                     |
| --------------------- | ----------------------------------------------------------- |
| `users`               | Auth — email, hashed password, role, verification status    |
| `personas`            | RBAC persona definitions with nav + action permissions      |
| `user_personas`       | Many-to-many user-to-persona assignments                    |
| `workspaces`          | Multi-tenant workspace definitions                          |
| `workspace_members`   | Workspace membership                                        |
| `agents`              | Agent definitions — model, provider, skills, tools          |
| `skills`              | Reusable skill packages — prompt, tools, constraints, files |
| `prompts`             | Prompt templates with versioning                            |
| `custom_tools`        | User-defined agent tools                                    |
| `mcp_servers`         | MCP server registry                                         |
| `a2a_peers`           | A2A peer agent registry                                     |
| `conversations`       | Session-scoped conversation messages                        |
| `document_registry`   | Document metadata (source, size, chunk count)               |
| `document_agent_tags` | Which documents are attached to which agents                |
| `guardrails`          | Guardrail definitions and configurations                    |
| `llm_usage_log`       | Per-call LLM usage: tokens, cost, latency, provider         |
| `audit_log`           | All write operations for compliance and debugging           |
| `pipelines`           | Pipeline definitions (n8n-style DAGs)                       |
| `pipeline_runs`       | Pipeline execution history                                  |
| `versions`            | Version history for agents, skills, prompts                 |
| `connectors`          | Data connector configurations                               |
| `sync_jobs`           | Connector sync job history                                  |

---

## Security Architecture

- **Authentication**: Session-based (express-session), bcrypt password hashing
- **Rate limiting**: 5 login attempts per 5-minute window per IP
- **Email verification**: 6-digit codes, resendable
- **RBAC**: Admin / Member / Viewer roles, persona-based nav gating
- **SSRF protection**: Tool HTTP calls blocked against private IP ranges
- **Path traversal prevention**: File I/O tools restricted to `/data` directory
- **Input sanitisation**: All user inputs validated and escaped
- **XSS protection**: EJS auto-escaping + CSP headers
- **Prompt injection guard**: Guardrail check on all incoming prompts

---

## Platform Architecture Layers

### Build — Agent Factory & Model Hub

What's **operational**:

- 4 LLM providers (Ollama, Azure OpenAI, OpenAI, Azure AI Foundry)
- Agent Builder, Skills Designer, Prompt Library, Agent Registry
- LangChain, LangGraph ReAct, LlamaIndex RAG, Langfuse Tracing
- A2A Protocol, MCP Servers (managed + external), RAG Pipeline
- Web Search, Code Execution, 30+ built-in tools
- ChromaDB vector store, per-agent KB isolation
- n8n Automation, Scheduled Runs, Webhook Triggers

On the **roadmap**:

- Anthropic Claude, Google Gemini, Groq, Mistral AI providers
- LangGraph HITL (interrupt nodes for human-in-the-loop)
- LangGraph Checkpointing (state persistence across runs)
- Structured Output mode (JSON enforcement via Pydantic)
- Google A2A (open interoperability standard)
- MCP 1.x Streamable HTTP transport
- Hybrid Search (BM25 + vector), Re-ranking

### Scale — Agent Runtime & Memory

What's **operational**:

- FastAPI agent runtime, Agent Sessions, SSE Streaming
- Short-Term Memory (session history), Long-Term Summaries
- Agent Registry (SQLite), MCP tool binding per-agent

On the **roadmap**:

- Agent Sandbox (isolated execution environments)
- Semantic Memory Bank (vector-backed long-term memory)
- Multi-Tenant isolation (per-workspace agent scoping)
- LangGraph Interrupt/HITL, Checkpoints

### Govern — Guardrails, Observability & Tracing

What's **operational**:

- 10 runtime guardrails (PII, injection, toxicity, topic, length, data leak)
- OpenTelemetry tracing pipeline → Prometheus + Loki
- LLM Tracing via Langfuse (every call: prompt, response, tokens, cost)
- Prometheus Metrics, Grafana Dashboards, Loki Log Aggregation
- Intelligence Hub, Control Matrix, Agent Performance Table
- LLM Activity Tracking, Cost per Run tracking

On the **roadmap**:

- Azure AI Content Safety integration
- Jailbreak Detection patterns
- Agent Simulation for offline testing
- A/B Testing framework
- LLM-as-Judge scoring
- Agent Identity (RBAC per-agent), Agent Gateway
- Anomaly Detection, Compliance Audit
- Policy-as-Code (OPA/Rego), AI Governance Framework (ISO 42001)

### Optimize — Continuous Improvement

What's **operational**:

- Prompt Versioning, Skill Iteration
- Model Comparison, Cost Tracking, Latency Profiling
- Token Usage Analytics

On the **roadmap**:

- Response Feedback UI (thumbs up/down)
- Prompt Auto-Optimizer
- Agent Simulation, A/B Testing

---

## Key Design Decisions

See [docs/DECISIONS.md](DECISIONS.md) for full ADRs. Summary:

| Decision        | Choice                      | Rationale                                                 |
| --------------- | --------------------------- | --------------------------------------------------------- |
| Agent framework | LangGraph                   | Full control over ReAct loop — not a black box            |
| Vector store    | ChromaDB                    | Embedded, no infra, persists across restarts              |
| Memory          | SQLite                      | Zero-dependency, 16 tables, fast for single-node          |
| LLM tracing     | Langfuse                    | Best-in-class LLM observability — prompt + cost + latency |
| Dashboard       | Express + EJS               | Server-rendered, no build step, full SSE support          |
| Auth            | bcrypt + express-session    | Enterprise IAM without overcomplicating                   |
| Workflows       | n8n                         | Visual automation; LangGraph owns the agent brain         |
| Observability   | Prometheus + Grafana + Loki | Industry-standard SRE tooling                             |
| Tool execution  | Sandboxed FastAPI           | Isolated from agent runtime for security                  |
| Protocols       | A2A + MCP                   | Agent interoperability + tool extensibility standards     |
