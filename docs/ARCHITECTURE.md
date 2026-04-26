# Architecture

> **Auto-generated** - do not edit manually. Run `scripts/generate-docs.sh` or the PowerShell equivalent to refresh.

## System Overview

The Agentic Platform is a containerised agent factory built with:
- **Frontend**: Express.js + EJS (ui-console)
- **Agent Runtime**: FastAPI + LangGraph (agent-service)
- **Tool Runtime**: FastAPI (tools-service)
- **LLM Providers**: Ollama (local) + Azure OpenAI (cloud)
- **Knowledge Base**: ChromaDB (vector store, RAG)
- **Memory**: SQLite (conversations, agents, skills, A2A peers, MCP servers)
- **Workflows**: n8n (automation, webhooks)
- **Observability**: Prometheus + Grafana + Loki + OpenTelemetry + Langfuse

## Services (4 source directories)

| Directory | Description |
| --------- | ----------- |
| `services/agent` | FastAPI agent-service - LangGraph ReAct agent, agent/skill/A2A/MCP registry |
| `services/tools` | FastAPI tools-service - math, HTTP, file, datetime tools |
| `services/ui` | Static HTML UI served by nginx |
| `services/ui-console` | Express.js platform dashboard - 13 pages, API proxies |
| `services/otel` | OpenTelemetry Collector configuration |

## UI Pages (14 pages)

- a2a
- admin
- agents
- documents
- evaluation
- llm-activity
- marketplace
- mcp
- observability
- overview
- run-agent
- skills
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
agent-service -> OTel Collector -> Prometheus (metrics)
                                -> Loki (logs)
agent-service -> Langfuse SDK   -> Langfuse (LLM traces)
Grafana <- Prometheus + Loki
```

## Protocols

- **A2A (Agent-to-Agent)**: Peer agents registered by URL; agents delegate sub-tasks via HTTP
- **MCP (Model Context Protocol)**: External tool servers provide dynamic tool discovery
