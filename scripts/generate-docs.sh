#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# generate-docs.sh — Auto-update project documentation
# Regenerates ARCHITECTURE.md and GET_STARTED.md from the
# live codebase so docs never drift from reality.
# Usage:  bash scripts/generate-docs.sh
# ──────────────────────────────────────────────────────────
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ── Discover services ─────────────────────────────────────
services=()
for dir in "$ROOT"/services/*/; do
  [ -d "$dir" ] && services+=("$(basename "$dir")")
done

# ── Discover EJS pages ────────────────────────────────────
pages=()
if [ -d "$ROOT/services/ui-console/views" ]; then
  for f in "$ROOT"/services/ui-console/views/*.ejs; do
    name="$(basename "$f" .ejs)"
    [ "$name" = "layout" ] && continue
    pages+=("$name")
  done
fi

# ── Discover docker-compose services ─────────────────────
compose_services=()
if [ -f "$ROOT/docker-compose.yml" ]; then
  compose_services=($(grep -E '^\s{2}[a-z]' "$ROOT/docker-compose.yml" | sed 's/://g' | awk '{print $1}' | sort))
fi

# ── Discover tests ────────────────────────────────────────
test_types=()
for dir in "$ROOT"/tests/*/; do
  [ -d "$dir" ] && test_types+=("$(basename "$dir")")
done

# ── Generate ARCHITECTURE.md ──────────────────────────────
cat > "$ROOT/docs/ARCHITECTURE.md" << 'HEADER'
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

HEADER

cat >> "$ROOT/docs/ARCHITECTURE.md" << EOF
## Services (${#services[@]} source directories)

| Directory | Description |
| --------- | ----------- |
EOF

for svc in "${services[@]}"; do
  desc=""
  case "$svc" in
    agent)        desc="FastAPI agent-service — LangGraph ReAct agent, agent/skill/A2A/MCP registry" ;;
    tools)        desc="FastAPI tools-service — math, HTTP, file, datetime tools" ;;
    ui)           desc="Static HTML UI served by nginx" ;;
    ui-console)   desc="Express.js platform dashboard — 13 pages, API proxies" ;;
    otel)         desc="OpenTelemetry Collector configuration" ;;
    *)            desc="Service" ;;
  esac
  echo "| \`services/$svc\` | $desc |" >> "$ROOT/docs/ARCHITECTURE.md"
done

cat >> "$ROOT/docs/ARCHITECTURE.md" << EOF

## Docker Compose Services (${#compose_services[@]} containers)

$(printf '`%s` ' "${compose_services[@]}")

## UI Pages (${#pages[@]} pages)

$(printf '- %s\n' "${pages[@]}")

## Test Suites

$(printf '- `tests/%s/`\n' "${test_types[@]}")

## Telemetry Pipeline

\`\`\`
agent-service → OTel Collector → Prometheus (metrics)
                               → Loki (logs)
agent-service → Langfuse SDK   → Langfuse (LLM traces)
Grafana ← Prometheus + Loki
\`\`\`

## Protocols

- **A2A (Agent-to-Agent)**: Peer agents registered by URL; agents delegate sub-tasks via HTTP
- **MCP (Model Context Protocol)**: External tool servers provide dynamic tool discovery
EOF

echo "✅ docs/ARCHITECTURE.md updated"

# ── Generate GET_STARTED.md ───────────────────────────────
cat > "$ROOT/docs/GET_STARTED.md" << 'EOF'
# Get Started

> **Auto-generated** — do not edit manually. Run `bash scripts/generate-docs.sh` to refresh.

## Prerequisites

- **Docker Desktop** with Compose v2
- **8 GB RAM** minimum (16 GB recommended)
- **~6 GB disk** for images + models

## Quick Start

```bash
# 1. Clone
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Start everything
docker compose up -d --build

# 3. Pull a model
docker exec ollama ollama pull llama3
```

## Access Points

| Service        | URL                          |
| -------------- | ---------------------------- |
| UI Console     | http://localhost:3001         |
| Agent API      | http://localhost:8010/docs    |
| Tools API      | http://localhost:8011/docs    |
| n8n Workflows  | http://localhost:5678         |
| Langfuse       | http://localhost:3012         |
| Grafana        | http://localhost:3013         |

## First Steps

1. **Run an agent** — Go to *Run Agent*, pick a model, type a prompt, press Run
2. **Create a skill** — Go to *Skills*, define a reusable capability with tools + constraints
3. **Register an agent** — Go to *Agents*, compose an agent with model + skills + knowledge base
4. **Upload documents** — Go to *Documents*, upload files for RAG-powered answers
5. **Set up A2A** — Go to *A2A Protocol*, register a peer agent URL for delegation
6. **Connect MCP** — Go to *MCP Protocol*, register an external tool server
7. **View traces** — Go to *Traceability* to see LLM call traces via Langfuse
8. **Check health** — Go to *Observability* to see live stack status and Grafana dashboards

## Troubleshooting

| Problem                            | Fix                                                     |
| ---------------------------------- | ------------------------------------------------------- |
| Agent-service unhealthy            | Check Ollama: `curl http://localhost:11436/api/tags`     |
| Grafana not loading                | Verify port 3013 is free: `docker compose logs grafana`  |
| Model not in dropdown              | `docker exec ollama ollama pull <model>`                 |
| Langfuse not loading               | Verify port 3012 is free: `docker compose logs langfuse` |
EOF

echo "✅ docs/GET_STARTED.md updated"
