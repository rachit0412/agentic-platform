# Architecture

> **Auto-generated** — do not edit manually. Run `bash scripts/generate-docs.sh` to refresh.

## System Overview

The Agentic Platform is a containerised agent factory built with:

- **Frontend**: Express.js + EJS (ui-console)
- **Agent Runtime**: FastAPI + LangGraph (agent-service)
- **Tool Runtime**: FastAPI (tools-service)
- **LLM Providers**: Ollama (local) + Azure OpenAI (cloud) + OpenAI (cloud) + Azure AI Foundry (cloud)
- **Knowledge Base**: ChromaDB (vector store, RAG)
- **Memory**: SQLite (conversations, agents, skills, A2A peers, MCP servers)
- **Workflows**: n8n (automation, webhooks)
- **Observability**: Prometheus + Grafana + Loki + OpenTelemetry + Langfuse

## Services (4 source directories)

| Directory             | Description                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `services/agent`      | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry |
| `services/otel`       | OpenTelemetry Collector configuration                                       |
| `services/tools`      | FastAPI tools-service — math, HTTP, file, datetime tools                    |
| `services/ui-console` | Express.js platform dashboard — 13 pages, API proxies                       |

## Docker Compose Services (20 containers)

`agent-service` `chroma-data` `chromadb` `grafana` `grafana-data` `langfuse` `langfuse-db` `langfuse-db-data` `loki` `loki-data` `n8n` `n8n-data` `ollama` `ollama-data` `otel-collector` `platform-net` `prometheus` `prometheus-data` `tools-service` `ui-console`

## UI Pages (15 pages)

## Test Suites

## Telemetry Pipeline

```
agent-service → OTel Collector → Prometheus (metrics)
                               → Loki (logs)
agent-service → Langfuse SDK   → Langfuse (LLM traces)
Grafana ← Prometheus + Loki
```

## Embedding & RAG Pipeline

```
Documents (file / URL / text)
  → Chunking (RecursiveCharacterTextSplitter)
    → Embedding (Ollama nomic-embed-text)
      → ChromaDB (vector store, persist)

User Prompt
  → Query Embedding (nomic-embed-text)
    → ChromaDB similarity_search (top-k)
      → Context injection → LLM (ReAct loop)
```

## LLM Providers (4)

| Provider         | Class             | Config Env Vars                                                           |
| ---------------- | ----------------- | ------------------------------------------------------------------------- |
| Ollama           | `ChatOllama`      | `OLLAMA_BASE_URL`, `OLLAMA_MODEL`                                         |
| Azure OpenAI     | `AzureChatOpenAI` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`                           |
| OpenAI           | `ChatOpenAI`      | `OPENAI_API_KEY`, `OPENAI_MODEL`                                          |
| Azure AI Foundry | `AzureChatOpenAI` | `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, `AZURE_FOUNDRY_MODELS` |

## Protocols

- **A2A (Agent-to-Agent)**: Peer agents registered by URL; agents delegate sub-tasks via HTTP
- **MCP (Model Context Protocol)**: External tool servers provide dynamic tool discovery
