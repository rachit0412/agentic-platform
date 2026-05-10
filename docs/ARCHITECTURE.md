# Architecture

> **Auto-generated** — do not edit manually. Run `bash scripts/generate-docs.sh` to refresh.

## System Overview

The Agentic Platform is a containerised agent factory built with:

- **Frontend**: Express.js + EJS (ui-console)
- **Agent Runtime**: FastAPI + LangGraph (agent-service)
- **Tool Runtime**: FastAPI (tools-service)
- **LLM Providers**: Ollama (local), Azure OpenAI, OpenAI, Azure AI Foundry
- **Knowledge Base**: ChromaDB (vector store, RAG)
- **Memory**: SQLite (conversations, agents, skills, A2A peers, MCP servers, LLM usage logs)
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

## LLM Activity Tracking

Every agent run logs usage metrics to the `llm_usage_log` table:

- **Per-request**: model, provider, prompt/completion/total tokens, estimated cost, latency, tools used, guardrail status
- **Dashboard**: `/llm-activity` page with timeseries charts (tokens, cost, latency), model breakdown, filters (time range, provider, model, session), sortable request log, CSV export
- **API**: `GET /llm-activity` (list with filters), `GET /llm-activity/summary` (aggregated stats)

## Guardrails

Triple-layer safety classification:

1. **LLM-based** (primary): Single LLM call evaluates ALL enabled guardrails against text using a dynamic classifier system prompt. Returns per-guardrail JSON verdicts (`{guardrail_id: {triggered, detail}}`). Handles temperature-restricted models via retry loop.
2. **Azure Content Filter** (cloud): When Azure content filter rejects text (hate, jailbreak, violence), auto-triggers toxicity/bias guardrails and falls back to regex for remaining checks. Captures Azure's specific violation categories.
3. **Regex-based** (fallback): Pattern matching for PII formats (email, phone, SSN, credit card, password, API key, IBAN), injection signatures (17 patterns), toxicity keywords, data leak indicators. Used when LLM is unavailable.

Guardrails run on **both** execution paths:

- **Non-streaming** (`POST /run` → `run_agent()`): Input guardrails before graph execution, output guardrails after response generation
- **Streaming** (`POST /run/stream` → `run_agent_stream()`): Input guardrails at start, output guardrails after final response

Multiple violations from a single prompt are all captured and reported simultaneously.

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
