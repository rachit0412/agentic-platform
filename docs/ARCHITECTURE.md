# Architecture

> **Auto-generated** — do not edit manually. Run `bash scripts/generate-docs.sh` to refresh.

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

## Services (5 source directories)

| Directory             | Description                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `services/agent`      | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry |
| `services/n8n-proxy`  | Service                                                                     |
| `services/otel`       | OpenTelemetry Collector configuration                                       |
| `services/tools`      | FastAPI tools-service — math, HTTP, file, datetime tools                    |
| `services/ui-console` | Express.js platform dashboard — 13 pages, API proxies                       |

## Docker Compose Services (21 containers)

`agent-service` `chroma-data` `chromadb` `grafana` `grafana-data` `langfuse` `langfuse-db` `langfuse-db-data` `loki` `loki-data` `n8n` `n8n-data` `n8n-proxy` `ollama` `ollama-data` `otel-collector` `platform-net` `prometheus` `prometheus-data` `tools-service` `ui-console`

## UI Pages (19 pages)

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
