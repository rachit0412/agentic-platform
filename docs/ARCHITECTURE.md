# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  🖥️  UI Console (Express.js + EJS)                :3000        │
│  24 pages — build, run, evaluate, trace agents                 │
├─────────────────────────────────────────────────────────────────┤
│  🧠 Agent Service (FastAPI + LangGraph)            :8010        │
│  ReAct loop · agent/skill registry · auto-RAG · memory         │
├──────────────────────┬──────────────────────────────────────────┤
│  🔧 Tools Service    │  📚 ChromaDB        │  💾 SQLite         │
│  :8011               │  :8200              │  (embedded)        │
│  35 tool endpoints   │  Vector store / RAG │  Memory & registry │
├──────────────────────┴──────────────────────┴───────────────────┤
│  🤖 LLM Layer                                                  │
│  Ollama (local) · OpenAI · Azure OpenAI · Azure AI Foundry     │
├─────────────────────────────────────────────────────────────────┤
│  📡 Observability                                               │
│  Langfuse · Prometheus · Grafana · Loki · OTel Collector        │
├─────────────────────────────────────────────────────────────────┤
│  ⚡ Orchestration                                               │
│  n8n (workflows, webhooks, scheduled jobs)                      │
└─────────────────────────────────────────────────────────────────┘
```

## Services

| Service | Port | Tech | Role |
|---------|------|------|------|
| ui-console | 3000 | Express.js + EJS | Platform dashboard, API proxy |
| agent-service | 8010 | FastAPI + LangGraph | ReAct agent, registry, RAG, memory |
| tools-service | 8011 | FastAPI | 35 sandboxed tool endpoints |
| ollama | 11436 | Ollama | Local LLM runtime |
| chromadb | 8200 | ChromaDB | Vector store for RAG |
| n8n | 5678 | n8n | Workflow automation |
| langfuse | 3012 | Langfuse | LLM tracing & cost tracking |
| grafana | 3013 | Grafana | Monitoring dashboards |
| prometheus | 9090 | Prometheus | Metrics |
| loki | 3100 | Loki | Log aggregation |
| otel-collector | 4317 | OTel | Telemetry pipeline |

## Agent Execution Flow

```
User Prompt
    │
    ▼
┌─────────────────────────────────┐
│  1. Input guardrails (safety)   │
│  2. Retrieve context (RAG)      │
│  3. Load memory (session)       │
│  4. Inject skills + prompt      │
│  5. LLM reasoning (ReAct)      │
│     ├─ Tool calls → tools-svc   │
│     └─ Delegate → sub-agent     │
│  6. Output guardrails           │
│  7. Generate response           │
│  8. Save memory + emit traces   │
└─────────────────────────────────┘
    │
    ├──→ Langfuse (trace)
    ├──→ Prometheus (metrics)
    └──→ Response to user
```

## Data Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  SQLite         │     │  PostgreSQL  │     │  ChromaDB    │
│  /data/platform │     │  :5433       │     │  :8200       │
│  .db            │     │              │     │              │
├─────────────────┤     ├──────────────┤     ├──────────────┤
│ agents          │     │ documents    │     │ collections  │
│ skills          │     │ (JSONB meta) │     │ (per-agent)  │
│ prompts         │     │              │     │              │
│ guardrails      │     └──────────────┘     └──────────────┘
│ custom_tools    │
│ conversations   │
│ a2a_peers       │
│ mcp_servers     │
│ llm_usage_log   │
│ audit_log       │
│ version_history │
└─────────────────┘
```

## Telemetry Pipeline

```
agent-service ──→ OTel Collector ──→ Prometheus (metrics)
                                 └──→ Loki (logs)
agent-service ──→ Langfuse SDK  ──→ Langfuse (LLM traces)
Grafana ←── Prometheus + Loki
```

## Protocols

| Protocol | Purpose | Implementation |
|----------|---------|----------------|
| **A2A** | Agent-to-Agent delegation | HTTP peer registry, agent cards, task dispatch |
| **MCP** | External tool discovery | Server registry, JSON-RPC tool discovery & invocation |

## Key Design Decisions

- **LangGraph** over AgentExecutor — explicit state graph with guardrail injection points
- **Separate tools-service** — sandboxed execution, crash isolation, independent scaling
- **SQLite + PostgreSQL** — zero-config for config/memory, PostgreSQL for document registry
- **Multi-provider LLM** — runtime switching via API, no redeploy needed
- **ChromaDB** — per-agent collections for KB isolation
- **Three-pipeline observability** — Langfuse (LLM traces) + Prometheus (metrics) + Loki (logs)

→ Full ADRs: [DECISIONS.md](DECISIONS.md)
