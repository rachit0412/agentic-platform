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
