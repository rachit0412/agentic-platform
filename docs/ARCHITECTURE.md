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

## Services (5 source directories)

| Directory             | Description                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `services/agent`      | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry |
| `services/n8n-proxy`  | Service                                                                     |
| `services/otel`       | OpenTelemetry Collector configuration                                       |
| `services/tools`      | FastAPI tools-service — math, HTTP, file, datetime tools                    |
| `services/ui-console` | Express.js platform dashboard — 24 pages, API proxies                       |

## Docker Compose Services (23 containers)

`agent-service` `chroma-data` `chromadb` `datastore-db` `datastore-db-data` `grafana` `grafana-data` `langfuse` `langfuse-db` `langfuse-db-data` `loki` `loki-data` `n8n` `n8n-data` `n8n-proxy` `ollama` `ollama-data` `otel-collector` `platform-net` `prometheus` `prometheus-data` `tools-service` `ui-console`

## UI Pages (24 pages)

| Page             | Route               | Key Features                                                  |
| ---------------- | ------------------- | ------------------------------------------------------------- |
| Overview         | `/`                 | Platform stats, architecture, quick-start                     |
| Run Agent        | `/run-agent`        | SSE streaming, session history, inline skill inputs           |
| Agent Builder    | `/agent-builder`    | 6-step wizard, skill workflow (sequential/router), sub-agents |
| AI Studio        | `/ai-studio`        | IDE-style editor with chat, preview, projects                 |
| Agent Hub        | `/agent-hub`        | Agent factory overview dashboard                              |
| Agents           | `/agents`           | Agent CRUD registry                                           |
| Skills           | `/skills`           | Skill packages with file attachments, global constraints      |
| Prompts          | `/prompts`          | Prompt template library                                       |
| Tools            | `/tools`            | Tool management and capabilities                              |
| Knowledge Base   | `/documents`        | Upload, search, manage RAG documents                          |
| Data Ingestion   | `/data-ingestion`   | Batch ingestion with connectors                               |
| Workflows        | `/workflows`        | n8n workflow monitoring                                       |
| A2A Protocol     | `/a2a`              | Peer agent registration, inter-agent delegation               |
| MCP Registry     | `/mcp`              | External tool server connection                               |
| REST Console     | `/rest`             | Interactive API console — all endpoints                       |
| Intelligence Hub | `/intelligence-hub` | Operational intelligence overview                             |
| Traceability     | `/traceability`     | Langfuse trace timeline, deep-dive                            |
| LLM Activity     | `/llm-activity`     | LLM call logs and metrics                                     |
| Evaluation       | `/evaluation`       | Agent quality scoring, model comparison                       |
| Observability    | `/observability`    | Stack health — Prometheus, Grafana, Loki                      |
| Guardrails       | `/guardrails`       | Runtime safety controls, policy enforcement                   |
| Marketplace      | `/marketplace`      | Browse and install templates                                  |
| Admin            | `/admin`            | 6-tab admin plane: service health, platform overview, LLM management, database & data, configuration, audit log |
| Docs             | `/docs`             | Built-in documentation portal with search                     |

## Admin Plane (6 tabs)

The Admin page (`/admin`) is a comprehensive control plane behind a client-side auth wall.

| Tab               | Key Features                                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------------------------------- |
| Service Health    | Live health checks for 10 services with latency, HTTP status, environment/endpoints table, service version matrix |
| Platform Overview | Entity count cards (agents, skills, prompts, tools, etc.), 18 capability indicators, memory & storage stats       |
| LLM & Models      | Active LLM config display, provider/model switcher, available models table, usage summary with per-model breakdown |
| Database & Data   | SQLite table stats with percentage bars, export/import, ChromaDB collections, knowledge base document stats       |
| Configuration     | Global constraints JSON editor, guardrails registry, n8n workflows, quick links to external services              |
| Audit Log         | Filterable audit trail (9 entity types × 4 action types), 100-entry table with timestamps and change details      |

### Admin API Endpoints (server.js)

| Endpoint                         | Method | Purpose                                      |
| -------------------------------- | ------ | -------------------------------------------- |
| `/api/admin/services/health`     | GET    | Health-check 10 services with latency timing |
| `/api/admin/overview`            | GET    | Aggregate counts for 10 entity types         |
| `/api/admin/metrics`             | GET    | Prometheus CPU, memory, HTTP rate, errors     |
| `/api/admin/llm-summary`         | GET    | LLM usage stats (tokens, cost, latency)      |
| `/api/admin/memory-stats`        | GET    | Memory and knowledge base statistics         |
| `/api/admin/global-constraints`  | GET/PUT| Read/write global agent constraints          |
| `/api/admin/chromadb/collections`| GET    | ChromaDB collection listing                  |
| `/api/admin/documents/stats`     | GET    | Document registry and file store stats       |
| `/api/admin/n8n/workflows`       | GET    | n8n workflow listing                         |

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
