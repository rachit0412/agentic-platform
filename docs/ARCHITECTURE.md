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

## Services (4 source directories)

| Directory             | Description                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `services/agent`      | FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry |
| `services/otel`       | OpenTelemetry Collector configuration                                       |
| `services/tools`      | FastAPI tools-service — math, HTTP, file, datetime tools                    |
| `services/ui-console` | Express.js platform dashboard — 13 pages, API proxies                       |

## Docker Compose Services (20 containers)

`agent-service` `chroma-data` `chromadb` `grafana` `grafana-data` `langfuse` `langfuse-db` `langfuse-db-data` `loki` `loki-data` `n8n` `n8n-data` `ollama` `ollama-data` `otel-collector` `platform-net` `prometheus` `prometheus-data` `tools-service` `ui-console`

## UI Pages (27 pages)

## Test Suites

## Telemetry Pipeline

```
agent-service → OTel Collector → Prometheus (metrics)
                               → Loki (logs)
agent-service → Langfuse SDK   → Langfuse (LLM traces)
Grafana ← Prometheus + Loki
```

### Observability Stack Details

All observability components are pre-wired in `docker-compose.yml` and start automatically — **no separate setup or imports required**.

#### OpenTelemetry Collector (`services/otel/otel-collector.yaml`)

- Receives telemetry via **OTLP** (gRPC `:4317`, HTTP `:4318`)
- Routes **metrics** → Prometheus exporter on `:8889` (scraped by Prometheus)
- Routes **logs** → Loki via OTLP HTTP (`http://loki:3100/otlp`)
- Routes **traces** → console logging (no Jaeger/Tempo backend configured)

#### Agent Service Instrumentation (`services/agent/agent/observability.py`)

Three instrumentation layers are initialized in `setup_otel(app)` at startup:

1. **OTel SDK** — auto-instruments FastAPI and HTTPX; exports spans to OTel Collector
2. **Prometheus metrics** — `prometheus-fastapi-instrumentator` exposes `/metrics` (http_requests_total, latency histograms) + custom counters (`llm_call_duration_seconds`, `tool_calls_total`, `agent_runs_total`)
3. **Langfuse SDK** — per-request trace/span/generation tracking for LLM calls

#### Prometheus (`observability/prometheus/prometheus.yml`)

Scrapes 3 targets every 15 seconds:
| Job | Target | What it collects |
|-----|--------|------------------|
| `otel-collector` | `otel-collector:8889` | Metrics forwarded through OTel |
| `agent-service` | `agent-service:8000/metrics` | FastAPI auto-metrics + custom LLM/agent counters |
| `tools-service` | `tools-service:8001/metrics` | Tools service request metrics |

#### Loki (`observability/loki/loki-config.yaml`)

- Receives logs from OTel Collector via OTLP HTTP
- TSDB store, schema v13, supports structured OTel metadata
- Queryable from Grafana via LogQL

#### Grafana (`observability/grafana/`)

- Auto-provisioned datasources: Prometheus + Loki
- Pre-loaded dashboard: `platform-health.json` (13 panels)
- Anonymous access enabled for embedding into the UI console

#### Python Dependencies (installed in agent-service Dockerfile)

```
opentelemetry-api / opentelemetry-sdk / opentelemetry-exporter-otlp-proto-http
opentelemetry-instrumentation-fastapi / opentelemetry-instrumentation-httpx
prometheus-client / prometheus-fastapi-instrumentator
langfuse
```

## Protocols

- **A2A (Agent-to-Agent)**: Peer agents registered by URL; agents delegate sub-tasks via HTTP
- **MCP (Model Context Protocol)**: External tool servers provide dynamic tool discovery
