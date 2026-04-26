# Agentic Platform

Production-ready, containerised **agent factory** — build, register, and run hundreds of autonomous AI agents, each with its own model, tools, memory, knowledge base, and control logic. Supports **A2A** (Agent-to-Agent) protocol for inter-agent delegation and **MCP** (Model Context Protocol) for dynamic tool discovery.

```
UI Console → Agent Registry → Agent Service (LangGraph + LangChain) → Skills / Tools / Knowledge Base / Memory
                                    ↕ A2A Protocol (peer agents)
                                    ↕ MCP Protocol (tool servers)
```

Start everything with one command, define **skills** (packaged capabilities with a prompt + tools + constraints), compose **agents** by attaching skills + a model + a knowledge base, and run them interactively or via n8n workflows.

### Core Concepts

| Concept            | Definition                                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent**          | `LLM + Tools + Memory + Control Logic + Context` — an autonomous loop that observes, reasons, acts, and repeats until the task is done.            |
| **Skill**          | A packaged capability that performs a specific task — reusable logic + tools + optional data access. Think: _reusable function with intelligence_. |
| **Prompt**         | The instructional context given to a model or skill — defines what the model should do, how it should behave, and what output is expected.         |
| **Knowledge Base** | ChromaDB vector store — upload documents that the agent auto-retrieves via RAG on every prompt.                                                    |
| **A2A Protocol**   | Agent-to-Agent — register peer agents by URL so they can delegate sub-tasks to each other over HTTP.                                               |
| **MCP Protocol**   | Model Context Protocol — connect to external tool servers that dynamically expose tools the agent can use.                                         |

---

## Architecture

```
 Browser (http://localhost:3001)
      │
      ▼
 ┌──────────────────┐
 │   ui-console     │  Express.js dashboard (13 pages)
 │   :3001          │  Agent runner, Registry, Skills, A2A, MCP,
 │                  │  Documents, Workflows, Traceability,
 │                  │  Evaluation, Observability, Marketplace, Admin
 └────────┬─────────┘
          │ /api/*
          ▼
 ┌──────────────────┐     ┌────────────────┐
 │  agent-service   │────►│ tools-service  │
 │  :8010           │     │ :8011          │
 │  FastAPI +       │     └────────────────┘
 │  LangGraph       │
 │       │          │     ┌────────────────┐
 │       ├─────────►│────►│   ChromaDB     │  Vector store (RAG)
 │       │          │     │   :8200        │
 │       ├──► SQLite│     └────────────────┘
 │       │  (memory)│
 │       ▼          │     ┌────────────────┐
 │   LLM Provider   │────►│ Ollama :11436  │  Local LLMs
 │  (multi-model)   │     │   OR           │
 │                   │     │ Azure OpenAI ☁ │  Cloud LLMs
 └───────┬──────────┘     └────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 ┌──────┐  ┌──────┐
 │ A2A  │  │ MCP  │  Agent-to-Agent delegation &
 │Peers │  │Srvrs │  Model Context Protocol tools
 └──────┘  └──────┘

 ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐
 │   n8n    │  │  Langfuse    │  │ Grafana  │  │Prometheus │  │   Loki   │
 │  :5678   │  │  :3012       │  │ :3013    │  │  :9090    │  │  :3100   │
 │ Workflows│  │ LLM Tracing  │  │Dashboards│  │  Metrics  │  │   Logs   │
 └──────────┘  └──────────────┘  └──────────┘  └───────────┘  └──────────┘
```

## Services

| Service            | Port    | Stack               | Purpose                                             |
| ------------------ | ------- | ------------------- | --------------------------------------------------- |
| **ui-console**     | `3001`  | Express.js + EJS    | Platform dashboard (13 pages), agent runner, admin  |
| **agent-service**  | `8010`  | FastAPI + LangGraph | ReAct agent, auto-RAG, memory, A2A, MCP, skills API |
| **tools-service**  | `8011`  | FastAPI             | Math, HTTP fetch, file I/O, datetime tools          |
| **ollama**         | `11436` | Ollama              | Local LLM runtime (llama3, mistral, phi3, etc.)     |
| **chromadb**       | `8200`  | ChromaDB            | Vector store for knowledge base / RAG               |
| **n8n**            | `5678`  | n8n                 | Workflow orchestration & webhooks                   |
| **langfuse**       | `3012`  | Langfuse v2         | LLM tracing, evaluation & prompt analytics          |
| **grafana**        | `3013`  | Grafana             | Monitoring dashboards                               |
| **prometheus**     | `9090`  | Prometheus          | Metrics collection                                  |
| **loki**           | `3100`  | Loki                | Log aggregation                                     |
| **otel-collector** | `4317`  | OpenTelemetry       | Trace & metric pipeline (gRPC + HTTP 4318)          |
| **postgres**       | `5432`  | PostgreSQL          | Langfuse backend database                           |
| **redis**          | `6379`  | Redis               | n8n queue backend                                   |

## Key Features

- **Agent Registry** — Create, configure, and manage multiple agents, each with its own model, skills, tools, knowledge base, and behavior
- **Skills System** — Define reusable skill packages (prompt + tools + constraints) and attach them to any agent
- **A2A Protocol** — Register peer agents for inter-agent delegation over HTTP; monitor trust status and capabilities
- **MCP Protocol** — Connect to external tool servers; dynamically discover and invoke tools via Model Context Protocol
- **Multi-Model LLM Support** — Switch between Ollama local models (llama3, mistral, phi3, codellama) and Azure OpenAI (gpt-4o, gpt-4o-mini) from the UI
- **Auto-RAG Knowledge Base** — Upload documents into ChromaDB directly from the agent form; automatically retrieved as context for every prompt
- **Conversation Memory** — SQLite-backed session summaries provide rolling context across messages
- **LangGraph ReAct Agent** — State graph: retrieve context → reason → execute tools → generate response
- **Tool Augmentation** — Math, HTTP fetch, file I/O, datetime tools available to the agent
- **LLM Traceability** — Full LLM call tracing via Langfuse with cost tracking, latency breakdown, and session grouping
- **Evaluation Matrix** — Quality scoring (faithfulness, relevance, coherence) across model, skill, and agent dimensions
- **Responsible AI** — Built-in guardrails: PII detection, toxicity filtering, bias warnings, safety scoring
- **Full Observability** — Live stack health, Prometheus scrape targets, Grafana dashboards, Loki logs, OpenTelemetry pipeline
- **Workflow Orchestration** — n8n workflows for scheduled tasks, webhooks, web research, and RAG ingestion

## Prerequisites

- **Docker Desktop** with Compose v2 — [download](https://www.docker.com/products/docker-desktop)
- **8 GB RAM** minimum (16 GB recommended)
- **~6 GB disk** for Docker images + Ollama models

## Quick Start

```bash
# 1. Clone & enter the repo
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Start all services
docker compose up -d --build

# 3. Pull an Ollama model (first time only — ~4 GB)
docker exec ollama ollama pull llama3

# 4. (Optional) Pull additional models
docker exec ollama ollama pull mistral
docker exec ollama ollama pull phi3
```

Wait until all containers are healthy:

```bash
docker compose ps
```

Open the dashboard at **http://localhost:3001**.

## Using the Agent

### From the UI

1. Open **http://localhost:3001** → go to **Skills** and create a skill (prompt + tools + constraints)
2. Navigate to **Agents** → create an agent: pick a model, attach skills, upload knowledge, write the prompt
3. Go to **Run Agent** → select your agent, send a prompt, and watch it work in real-time
4. View response, tools used, trace links, and session history

### From curl

```bash
# Health checks
curl http://localhost:8010/health
curl http://localhost:8011/health

# Run agent with default model
curl -X POST http://localhost:8010/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 42 * 13?", "sessionId": "test-1"}'

# Run agent with specific model
curl -X POST http://localhost:8010/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing", "sessionId": "test-2", "provider": "ollama", "model": "mistral"}'

# List available models
curl http://localhost:8010/models

# Switch active model
curl -X POST http://localhost:8010/models/switch \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "llama3"}'
```

### Knowledge Base (RAG)

```bash
# Ingest a document
curl -X POST http://localhost:8010/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "LangGraph is a framework for building stateful agents...", "metadata": {"source": "docs"}}'

# Search the knowledge base
curl -X POST http://localhost:8010/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what is langgraph", "top_k": 3}'
```

Documents are automatically retrieved as context when you send a prompt — no extra configuration needed.

## Multi-Model LLM Configuration

### Ollama (Local — Free)

Ollama models are auto-detected. Pull any model and it appears in the UI:

```bash
docker exec ollama ollama pull llama3       # Meta Llama 3 (8B)
docker exec ollama ollama pull mistral      # Mistral 7B
docker exec ollama ollama pull phi3         # Microsoft Phi-3
docker exec ollama ollama pull codellama    # Code Llama
docker exec ollama ollama pull gemma2       # Google Gemma 2
docker exec ollama ollama pull llama3:70b   # Llama 3 70B (needs 40GB+ RAM)
```

### Azure OpenAI (Cloud)

Set these environment variables in `.env` or `docker-compose.yml`:

```env
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-06-01
LLM_PROVIDER=azure-openai    # Optional: set as default provider
```

Once configured, Azure OpenAI models appear in the UI model dropdown alongside Ollama models.

## Tools Available

| Endpoint            | Method | Description                                                        |
| ------------------- | ------ | ------------------------------------------------------------------ |
| `/tools/math`       | POST   | Safe arithmetic evaluation (`{"expression": "2+2"}`)               |
| `/tools/http-fetch` | POST   | Fetch a URL (allowlist: httpbin.org, jsonplaceholder.typicode.com) |
| `/tools/file-write` | POST   | Save a note (`{"filename": "todo.txt", "content": "..."}`)         |
| `/tools/file-read`  | POST   | Read a saved note (`{"filename": "todo.txt"}`)                     |
| `/tools/datetime`   | POST   | Current UTC date, time, and weekday                                |

## Project Structure

```
agentic-platform/
├── docker-compose.yml           # All 12 services
├── README.md
├── INSTALL.md                   # Detailed installation guide
├── CONTRIBUTING.md              # Contribution guidelines
├── pyproject.toml
├── data/                        # Mounted volumes (SQLite, notes)
├── docs/                        # Additional documentation
├── n8n/workflows/               # n8n workflow JSON files
├── observability/
│   ├── grafana/                 # Dashboards & provisioning
│   ├── loki/                    # Log aggregation config
│   └── prometheus/              # Metrics scrape config
├── scripts/                     # Health checks & utilities
├── services/
│   ├── agent/                   # FastAPI + LangGraph agent
│   │   ├── Dockerfile
│   │   ├── main.py              # API endpoints (/run, /agents, /skills, /a2a, /mcp, /sessions, /documents)
│   │   ├── requirements.txt
│   │   └── agent/
│   │       ├── graph.py         # LangGraph ReAct state graph
│   │       ├── llm.py           # Multi-provider LLM (Ollama + Azure OpenAI)
│   │       ├── memory.py        # SQLite memory + agent/skill/A2A/MCP registry
│   │       ├── tools.py         # Tool catalogue & HTTP client
│   │       ├── vectorstore.py   # ChromaDB vector store wrapper
│   │       └── observability.py # OpenTelemetry + Langfuse setup
│   ├── tools/                   # FastAPI tool endpoints
│   ├── ui/                      # Static UI (nginx)
│   ├── ui-console/              # Platform dashboard (Express.js + EJS)
│   │   ├── server.js            # API proxies & view routing
│   │   └── views/               # EJS templates (13 pages)
│   └── otel/                    # OpenTelemetry collector config
└── tests/
    ├── unit/                    # pytest + jest unit tests
    ├── integration/             # Integration tests
    ├── e2e/                     # End-to-end tests
    ├── contract/                # Contract tests
    ├── load/                    # k6 load tests
    └── smoke/                   # Smoke tests
```

## Configuration

| Variable                    | Default              | Description                                       |
| --------------------------- | -------------------- | ------------------------------------------------- |
| `OLLAMA_MODEL`              | `llama3`             | Default Ollama model                              |
| `LLM_PROVIDER`              | `ollama`             | Default LLM provider (`ollama` or `azure-openai`) |
| `AZURE_OPENAI_API_KEY`      | _(empty)_            | Azure OpenAI API key                              |
| `AZURE_OPENAI_ENDPOINT`     | _(empty)_            | Azure OpenAI endpoint URL                         |
| `AZURE_OPENAI_DEPLOYMENT`   | `gpt-4o-mini`        | Azure OpenAI deployment name                      |
| `AZURE_OPENAI_API_VERSION`  | `2024-06-01`         | Azure OpenAI API version                          |
| `N8N_USER` / `N8N_PASSWORD` | `admin` / `changeme` | n8n basic auth                                    |
| `LANGFUSE_PUBLIC_KEY`       | _(auto)_             | Langfuse public key                               |
| `LANGFUSE_SECRET_KEY`       | _(auto)_             | Langfuse secret key                               |

## Observability

| Tool           | URL                   | Purpose                 |
| -------------- | --------------------- | ----------------------- |
| **Langfuse**   | http://localhost:3012 | LLM tracing & analytics |
| **Grafana**    | http://localhost:3013 | Monitoring dashboards   |
| **Prometheus** | http://localhost:9090 | Metrics                 |
| **n8n**        | http://localhost:5678 | Workflow orchestration  |

## Development

Python services run with `uvicorn --reload` — source dirs are bind-mounted:

```bash
# View agent logs
docker compose logs -f agent-service

# Restart a single service
docker compose restart agent-service

# Rebuild after changing Dockerfile / requirements
docker compose up -d --build agent-service

# Run unit tests
cd services/langgraph-api && pytest -v
```

## Troubleshooting

| Problem                            | Fix                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------- |
| `agent-service` unhealthy          | Check Ollama is running: `curl http://localhost:11436/api/tags`. Pull a model if empty.     |
| n8n webhook returns 404            | Import the workflow JSON and **activate** it in the n8n UI.                                 |
| Model not showing in dropdown      | Pull it first: `docker exec ollama ollama pull <model>`. Refresh the page.                  |
| Azure OpenAI not available         | Set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` env vars and restart agent-service.  |
| `tools-service` connection refused | Run `docker compose ps` — make sure `tools-service` is `healthy`.                           |
| Ollama slow / OOM                  | Use a smaller model: `docker exec ollama ollama pull phi3` and select it in the UI.         |
| Langfuse not loading               | Verify port 3012 is free. Check `docker compose logs langfuse`.                             |
| Grafana not loading                | Verify port 3013 is free. Check `docker compose logs grafana`.                              |
| GPU not used                       | Uncomment the `deploy.resources.reservations` block in `docker-compose.yml` under `ollama`. |

## License

See [LICENSE](LICENSE).

## License

MIT
