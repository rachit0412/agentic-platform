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

## Services (6 source directories)

| Directory | Description |
| --------- | ----------- |
| `services/agent` | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry, managed MCP provisioning |
| `services/managed-mcp-base` | Generic MCP server runtime — config mode (HTTP proxy) and code mode (Python functions), deployed as isolated containers |
| `services/n8n-proxy` | Nginx reverse proxy for n8n iframe embedding |
| `services/otel` | OpenTelemetry Collector configuration |
| `services/tools` | FastAPI tools-service — math, HTTP, file, datetime tools |
| `services/ui-console` | Express.js platform dashboard — 25 pages, API proxies |

## Docker Compose Services (23 containers)

`agent-service` `chroma-data` `chromadb` `datastore-db` `datastore-db-data` `grafana` `grafana-data` `langfuse` `langfuse-db` `langfuse-db-data` `loki` `loki-data` `n8n` `n8n-data` `n8n-proxy` `ollama` `ollama-data` `otel-collector` `platform-net` `prometheus` `prometheus-data` `tools-service` `ui-console` 

## UI Pages (24 pages)



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
- **MCP (Model Context Protocol)**: External and managed tool servers provide dynamic tool discovery. Agents with bound MCP servers see MCP tools natively in their ReAct loop. Managed MCP servers are provisioned as isolated Docker containers via the Docker SDK, with two creation modes:
  - **Config mode**: No-code HTTP endpoint proxies defined via forms
  - **Code mode**: Custom Python functions written in a code editor
  - Containers run on `platform-net`, auto-discovered via `/tools/list`, and managed (start/stop/restart/logs/destroy) from the UI
