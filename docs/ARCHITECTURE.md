# Architecture

## Visual Architecture

Open **[architecture-diagram.html](architecture-diagram.html)** in a browser for an interactive visual overview of the full system.

---

## System Overview

The Agentic Platform is a containerised **agent factory** — build, register, and run autonomous AI agents, each with its own model, tools, memory, knowledge base, and control logic.

| Layer                | Technology                                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Frontend**         | Express.js + EJS (ui-console) — 24 pages, thin API proxy                                                                 |
| **Agent Runtime**    | FastAPI + LangGraph ReAct loop (agent-service) — 69+ REST endpoints                                                      |
| **Tool Runtime**     | FastAPI (tools-service) — 10 sandboxed tool endpoints                                                                    |
| **LLM Providers**    | Ollama (local), Azure OpenAI, OpenAI, Azure AI Foundry — runtime-switchable via `POST /models/switch`                    |
| **RAG Pipeline**     | ChromaDB vector store + LlamaIndex advanced retrieval (hybrid, reranked, sentence_window, auto_merging)                  |
| **Document Parsing** | LlamaIndex readers — PDF, DOCX, XLSX, CSV, PPTX, EPUB, HTML, Markdown (20+ formats)                                      |
| **Data Connectors**  | Database (PostgreSQL/MySQL/MSSQL), REST API, Cloud Storage (S3/Azure Blob/GCS), Google Drive, SharePoint, Airbyte (300+) |
| **Memory**           | SQLite (conversations, agents, skills, A2A peers, MCP servers) + PostgreSQL (document registry)                          |
| **Workflows**        | n8n (automation, webhooks, multi-agent DAG orchestration)                                                                |
| **Observability**    | Prometheus + Grafana + Loki + OpenTelemetry + Langfuse                                                                   |
| **Protocols**        | A2A (Agent-to-Agent) + MCP (Model Context Protocol)                                                                      |

---

## Services (5 source directories)

| Directory             | Description                                                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `services/agent`      | FastAPI agent-service — LangGraph ReAct agent, RAG pipeline, LlamaIndex integration, connectors, agent/skill/A2A/MCP registry |
| `services/n8n-proxy`  | Nginx reverse proxy for embedding n8n inside the platform dashboard                                                           |
| `services/otel`       | OpenTelemetry Collector configuration (traces → Prometheus metrics + Loki logs)                                               |
| `services/tools`      | FastAPI tools-service — math, HTTP fetch, file I/O, datetime, web search, code execution sandbox                              |
| `services/ui-console` | Express.js platform dashboard — 24 EJS views, 70+ API proxy routes                                                            |

---

## Docker Compose Services (14 containers + 7 volumes/networks)

| Container        | Port    | Purpose                                         |
| ---------------- | ------- | ----------------------------------------------- |
| `ui-console`     | 3000    | Platform dashboard (Express.js)                 |
| `agent-service`  | 8010    | Agent runtime (FastAPI + LangGraph)             |
| `tools-service`  | 8011    | Tool execution sandbox (FastAPI)                |
| `ollama`         | 11436   | Local LLM inference (Llama 3, Mistral, etc.)    |
| `chromadb`       | 8200    | Vector store (embeddings, semantic search)      |
| `datastore-db`   | 5433    | PostgreSQL (document registry, JSONB)           |
| `n8n`            | 5678    | Workflow automation                             |
| `n8n-proxy`      | 5679    | Nginx proxy for n8n iframe embedding            |
| `langfuse`       | 3014    | LLM trace viewer and cost tracking              |
| `langfuse-db`    | —       | PostgreSQL for Langfuse                         |
| `otel-collector` | 4317-18 | OpenTelemetry Collector (traces, metrics, logs) |
| `prometheus`     | 9090    | Metrics database                                |
| `grafana`        | 3003    | Dashboards and alerting                         |
| `loki`           | 3100    | Log aggregation                                 |

**Named volumes**: `ollama-data`, `chroma-data`, `n8n-data`, `langfuse-db-data`, `loki-data`, `prometheus-data`, `grafana-data`, `datastore-db-data`

**Network**: `platform-net` (bridge)

---

## Agent Runtime Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  LangGraph ReAct Loop (graph.py)                            │
│                                                             │
│  ┌──────────────┐    ┌────────┐    ┌───────────────┐        │
│  │ Input        │───▸│Retrieve│───▸│ Reason (LLM)  │──┐     │
│  │ Guardrails   │    │Context │    │               │  │     │
│  └──────────────┘    └────────┘    └───────────────┘  │     │
│                                          ▲             │     │
│                                          │             ▼     │
│  ┌──────────────┐    ┌────────┐    ┌───────────────┐        │
│  │ Output       │◂───│Generate│◂───│ Execute Tools  │        │
│  │ Guardrails   │    │Response│    │               │        │
│  └──────────────┘    └────────┘    └───────────────┘        │
│                                                             │
│  Iterate until: response ready OR max_iterations reached    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
  Response (with token usage, trace ID, session ID)
```

### Retrieval Modes (per-agent `retrieval_mode`)

| Mode       | Strategy                                                      | Implementation                         |
| ---------- | ------------------------------------------------------------- | -------------------------------------- |
| `basic`    | Direct ChromaDB cosine similarity (k=3)                       | `vectorstore.search_similar()`         |
| `advanced` | LlamaIndex hybrid / reranked / sentence_window / auto_merging | `advanced_retrieval.advanced_search()` |
| `none`     | Skip knowledge base entirely                                  | No retrieval step                      |

### Multi-Agent Orchestration

Two modes operate complementarily:

1. **LLM-driven delegation** — Orchestrator agents have `sub_agent_ids`. The `reason` node injects sub-agent descriptions so the LLM can autonomously decide to call `delegate_to_agent(agent_name, task)`. Recursion guard prevents infinite loops.
2. **DAG-driven pipelines** — n8n workflows call `POST /run` with different `agent_id` per branch for deterministic sequential/parallel execution.

---

## Knowledge & Data Pipeline

```
                   ┌──────────────────────────────────┐
                   │         Data Sources              │
                   │  Files · URLs · Databases · APIs  │
                   │  Cloud Storage · Google Drive      │
                   │  SharePoint · Airbyte (300+)       │
                   └──────────────┬───────────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────────┐
                   │     LlamaIndex Document Parser     │
                   │  PDF · DOCX · XLSX · CSV · PPTX    │
                   │  EPUB · HTML · Markdown · JSON      │
                   └──────────────┬───────────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────────┐
                   │   Chunking & Embedding             │
                   │   RecursiveCharacterTextSplitter    │
                   │   Ollama nomic-embed-text           │
                   └──────────────┬───────────────────┘
                                  │
                          ┌───────┴───────┐
                          ▼               ▼
                   ┌──────────┐    ┌──────────────┐
                   │ ChromaDB │    │  PostgreSQL   │
                   │ Vectors  │    │  Doc Registry │
                   └──────────┘    └──────────────┘
```

---

## Telemetry Pipeline

```
agent-service ──▸ OTel Collector ──▸ Prometheus (metrics)
                                 └──▸ Loki (logs)
agent-service ──▸ Langfuse SDK  ──▸ Langfuse (LLM traces + cost)
                  Grafana ◂── Prometheus + Loki
```

**Prometheus metrics**: `llm_call_duration_seconds`, `tool_calls_total`, `agent_runs_total`

---

## Protocols

| Protocol | Purpose                               | Endpoints                                                                               |
| -------- | ------------------------------------- | --------------------------------------------------------------------------------------- |
| **A2A**  | Agent-to-Agent task delegation        | `GET /a2a/card`, `POST /a2a/send`, CRUD `/a2a/peers`, `POST /a2a/peers/{id}/ping`       |
| **MCP**  | External tool server discovery/invoke | CRUD `/mcp/servers`, `POST /mcp/servers/{id}/discover`, `POST /mcp/servers/{id}/invoke` |

---

## UI Pages (24 views)

| Page             | Route               | Purpose                                  |
| ---------------- | ------------------- | ---------------------------------------- |
| Overview         | `/`                 | Platform health, stats, architecture     |
| Run Agent        | `/run-agent`        | Agent execution with streaming           |
| Agent Builder    | `/agent-builder`    | Create/edit agents with full config      |
| AI Studio        | `/ai-studio`        | Model switching and testing              |
| Agent Hub        | `/agent-hub`        | Agent discovery and marketplace          |
| Intelligence Hub | `/intelligence-hub` | Aggregated insights dashboard            |
| Documents        | `/documents`        | Knowledge base management                |
| Data Ingestion   | `/data-ingestion`   | Data connector management                |
| Workflows        | `/workflows`        | n8n workflow management                  |
| Skills           | `/skills`           | Skill creation and management            |
| Prompts          | `/prompts`          | Prompt library management                |
| Agents           | `/agents`           | Agent list and configuration             |
| Tools            | `/tools`            | Custom tool management                   |
| Guardrails       | `/guardrails`       | Guardrail configuration                  |
| A2A              | `/a2a`              | A2A peer management                      |
| MCP              | `/mcp`              | MCP server registration                  |
| REST Console     | `/rest`             | Interactive API explorer (69+ endpoints) |
| Evaluation       | `/evaluation`       | RAG evaluation dashboard                 |
| Observability    | `/observability`    | Grafana/Prometheus/Loki dashboards       |
| Traceability     | `/traceability`     | LLM trace viewing (Langfuse)             |
| Marketplace      | `/marketplace`      | Agent/skill/tool marketplace             |
| Admin            | `/admin`            | System administration                    |
| Docs             | `/docs`             | Documentation viewer                     |

---

## Test Suites

| Suite       | Files | Coverage                                                |
| ----------- | ----- | ------------------------------------------------------- |
| Unit        | 5     | Agent graph, LLM providers, tools, vectorstore, console |
| Integration | 1     | Agent + tools end-to-end, memory persistence            |
| E2E         | 4     | API endpoints, orchestration, platform health           |
| Contract    | 1     | A2A and MCP protocol validation                         |
| Load        | 1     | k6 load testing script                                  |
| Smoke       | 1     | Service health verification                             |

---

## Guardrails (10 default)

| Guard                | Phase  | Detection                                       |
| -------------------- | ------ | ----------------------------------------------- |
| PII Detection        | Input  | Email, phone, SSN, credit card regex            |
| Prompt Injection     | Input  | System prompt override patterns                 |
| Topic Restriction    | Input  | Off-topic content blocking                      |
| PII Flagging         | Output | PII in agent responses                          |
| Data Leak Prevention | Output | Sensitive data exposure detection               |
| Toxicity Filter      | Output | Harmful content detection                       |
| Output Length        | Output | Response length enforcement                     |
| Rate Limit           | Input  | Calls per minute/session (config, not enforced) |
| Custom Regex         | Both   | User-defined patterns                           |
| Content Safety       | Both   | General content policy                          |
