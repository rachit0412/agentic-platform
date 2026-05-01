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

| Directory             | Description                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| `services/agent`      | FastAPI agent-service — LangGraph ReAct agent, 69 REST endpoints, agent/skill/A2A/MCP registry |
| `services/n8n-proxy`  | Express.js n8n reverse proxy for cross-origin workflow access                                  |
| `services/otel`       | OpenTelemetry Collector configuration                                                          |
| `services/tools`      | FastAPI tools-service — math, HTTP, file, datetime, web search, code execute, vector tools     |
| `services/ui-console` | Express.js platform dashboard — 22 pages, API proxies, REST Console                            |

## Docker Compose Services (13 containers)

`agent-service` `chromadb` `grafana` `langfuse` `langfuse-db` `loki` `n8n` `n8n-proxy` `ollama` `otel-collector` `prometheus` `tools-service` `ui-console`

## UI Pages (22 pages)

- a2a
- admin
- agent-builder
- agent-hub
- agents
- ai-studio
- docs
- documents
- evaluation
- guardrails
- intelligence-hub
- marketplace
- mcp
- observability
- overview
- prompts
- rest
- run-agent
- skills
- tools
- traceability
- workflows

## Test Suites

- `tests/contract/`
- `tests/e2e/`
- `tests/integration/`
- `tests/load/`
- `tests/smoke/`
- `tests/unit/`

## Telemetry Pipeline

```
agent-service → OTel Collector → Prometheus (metrics)
                               → Loki (logs)
agent-service → Langfuse SDK   → Langfuse (LLM traces)
Grafana ← Prometheus + Loki
```

## Protocols

- **A2A (Agent-to-Agent)**: Peer agents registered by URL; agents delegate sub-tasks via HTTP
- **MCP (Model Context Protocol)**: External tool servers provide dynamic tool discovery via MCP Registry
- **REST Console**: Interactive API console for testing all 69 agent-service + 10 tools-service endpoints
