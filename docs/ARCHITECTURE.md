# Architecture

> **Auto-generated** — do not edit manually. Run `bash scripts/generate-docs.sh` to refresh.

## System Overview

The Agentic Platform is a containerised agent factory built with:

- **Frontend**: Express.js + EJS (ui-console)
- **Agent Runtime**: FastAPI + LangGraph (agent-service)
- **Tool Runtime**: FastAPI (tools-service)
- **LLM Providers**: Ollama (local), Azure OpenAI, OpenAI, Azure AI Foundry
- **Knowledge Base**: ChromaDB (vector store, RAG, per-agent isolated collections)
- **Memory**: SQLite (conversations, agents, skills, A2A peers, MCP servers)
- **Orchestration**: Multi-agent delegation (runtime LLM-driven) + n8n (pre-planned workflows)
- **Observability**: Prometheus + Grafana + Loki + OpenTelemetry + Langfuse

## Services (5 source directories)

| Directory             | Description                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `services/agent`      | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry |
| `services/n8n-proxy`  | Service                                                                     |
| `services/otel`       | OpenTelemetry Collector configuration                                       |
| `services/tools`      | FastAPI tools-service — math, HTTP, file, datetime tools                    |
| `services/ui-console` | Express.js platform dashboard — 22 pages, API proxies                       |

## Docker Compose Services (21 containers)

`agent-service` `chroma-data` `chromadb` `grafana` `grafana-data` `langfuse` `langfuse-db` `langfuse-db-data` `loki` `loki-data` `n8n` `n8n-data` `n8n-proxy` `ollama` `ollama-data` `otel-collector` `platform-net` `prometheus` `prometheus-data` `tools-service` `ui-console`

## UI Pages (22 pages)

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

## Multi-Agent Orchestration

The platform supports two complementary orchestration patterns:

### 1. Runtime LLM-Driven Delegation (Agent Service)

```
Orchestrator Agent
  │ (has sub_agent_ids: [worker_1, worker_2])
  │
  ├── LLM decides to delegate → delegate_to_agent(worker_1, "research X")
  │     └── Worker 1 runs full ReAct loop → returns result
  │
  └── LLM decides to delegate → delegate_to_agent(worker_2, "analyze Y")
        └── Worker 2 runs full ReAct loop → returns result
```

- **When**: The orchestrator agent's LLM autonomously decides which sub-agent to call based on the task
- **How**: `delegate_to_agent` tool in `tools.py` loads sub-agent config, calls `run_agent()` in-process
- **Config**: `sub_agent_ids` field on agent record; `reason` node injects sub-agent descriptions into system prompt
- **Guard**: Max delegation depth prevents infinite recursion

### 2. Pre-Planned Workflow Pipelines (n8n)

```
Webhook → Strategy Router
  ├── Sequential: Agent A → Agent B → Respond
  └── Parallel:   Agent A + Agent B → Merge → Respond
```

- **When**: The orchestration pattern is deterministic (always run A then B, or A and B in parallel)
- **How**: n8n workflow calls `/run` endpoint with different `agent_id` per branch
- **Template**: `n8n/workflows/multi-agent-orchestration.json`

### Separation of Concerns

| Concern                               | Owner                       | Pattern                        |
| ------------------------------------- | --------------------------- | ------------------------------ |
| "Which sub-agent should handle this?" | Agent Service (LLM decides) | `delegate_to_agent` tool       |
| "Run A then B, merge results"         | n8n (pre-planned DAG)       | Sequential/parallel workflow   |
| "Run A and B simultaneously"          | n8n (pre-planned DAG)       | Parallel branches + merge node |
