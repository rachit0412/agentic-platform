#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# generate-docs.sh — Auto-update project documentation
# Regenerates ARCHITECTURE.md from the live codebase
# so docs never drift from reality.
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
    pages+=("$name")
  done
fi

# ── Discover docker-compose services ─────────────────────
compose_services=()
if [ -f "$ROOT/docker-compose.yml" ]; then
  # Parse YAML via Python to avoid capturing volumes/networks as services.
  compose_services=($(python - <<'PY'
import yaml
from pathlib import Path

doc = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8")) or {}
for name in sorted((doc.get("services") or {}).keys()):
    print(name)
PY
))
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
- **LLM Providers**: Ollama (local), Azure OpenAI, OpenAI, Azure AI Foundry
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
    ui-console)   desc="Express.js platform dashboard — ${#pages[@]} pages, API proxies" ;;
    otel)         desc="OpenTelemetry Collector configuration" ;;
    *)            desc="Service" ;;
  esac
  echo "| \`services/$svc\` | $desc |" >> "$ROOT/docs/ARCHITECTURE.md"
done

cat >> "$ROOT/docs/ARCHITECTURE.md" << EOF

## Docker Compose Services (${#compose_services[@]} services)

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
