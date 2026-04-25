# Agentic Platform

Minimal, containerised developer platform: **UI → n8n → Agent (LangGraph + Ollama) → Tools → Memory**

Start everything with one command, submit a prompt from the browser (or `curl`), and get a tool-augmented LLM response back.

## Architecture

```
 Browser / curl
      │  POST /webhook/agent-run
      ▼
 ┌──────────┐      ┌────────────────┐      ┌──────────────┐
 │   n8n    │─────►│  agent-service │─────►│ tools-service │
 │  :5678   │      │  :8000         │      │  :8001        │
 └──────────┘      │  (LangGraph)   │      └──────────────┘
                   │       │        │
                   │       ▼        │
                   │    Ollama      │
                   │   :11434       │
                   │       │        │
                   │   SQLite mem   │
                   └────────────────┘
```

| Service                   | Port  | Purpose                                                       |
| ------------------------- | ----- | ------------------------------------------------------------- |
| **ui-console**            | 3000  | Platform dashboard & agent UI (Express.js)                    |
| **n8n**                   | 5678  | Webhook entry-point & workflow orchestrator                   |
| **agent-service**         | 8000  | FastAPI + LangGraph agent loop                                |
| **tools-service**         | 8001  | FastAPI tool endpoints (math, http-fetch, file I/O, datetime) |
| **ollama**                | 11434 | Local LLM runtime                                             |
| **chromadb** _(optional)_ | 8200  | Vector memory (enable with `--profile vector`)                |

## Prerequisites

- **Docker Desktop** with Compose v2 — [download](https://www.docker.com/products/docker-desktop)
- **8 GB RAM** minimum (16 GB recommended)
- **~6 GB disk** for Docker images + Ollama model

## Quick Start

```bash
# 1. Clone & enter the repo
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. (Optional) copy and customise env vars
cp .env.example .env

# 3. Start all services
docker compose up -d --build

# 4. Pull an Ollama model (first time only — ~4 GB)
docker exec ollama ollama pull llama3
```

Wait until all containers are healthy:

```bash
docker compose ps
```

## Import the n8n Workflow

The agent workflow must be imported into n8n once:

1. Open **http://localhost:5678** (login: `admin` / `changeme`)
2. Click **Workflows → Import from File**
3. Select `n8n/workflows/agent-workflow.json`
4. Open the imported workflow and click **Active** (toggle ON)

The webhook endpoint is now live at `POST http://localhost:5678/webhook/agent-run`.

## Test with curl

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health

# Call a tool directly
curl -X POST http://localhost:8001/tools/math \
  -H "Content-Type: application/json" \
  -d '{"expression": "42 * 13"}'

# Trigger the full pipeline via n8n webhook
curl -X POST http://localhost:5678/webhook/agent-run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 42 * 13?", "sessionId": "test-1"}'
```

**Expected response:**

```json
{
  "sessionId": "test-1",
  "response": "42 × 13 = 546",
  "tools_used": ["math"],
  "request_id": "a1b2c3d4"
}
```

## Use the UI

Open **http://localhost:3000** in your browser. The dashboard provides an overview of all services, agent execution, RAG document management, workflow orchestration, LLM tracing, observability, a template marketplace, and admin controls. Navigate to **Run Agent** to send prompts and view tool-augmented responses.

## Tools Available

| Endpoint            | Method | Description                                                        |
| ------------------- | ------ | ------------------------------------------------------------------ |
| `/tools/math`       | POST   | Safe arithmetic evaluation (`{"expression": "2+2"}`)               |
| `/tools/http-fetch` | POST   | Fetch a URL (allowlist: httpbin.org, jsonplaceholder.typicode.com) |
| `/tools/file-write` | POST   | Save a note (`{"filename": "todo.txt", "content": "..."}`)         |
| `/tools/file-read`  | POST   | Read a saved note (`{"filename": "todo.txt"}`)                     |
| `/tools/datetime`   | POST   | Current UTC date, time, and weekday                                |

## Optional: ChromaDB Vector Memory

```bash
docker compose --profile vector up -d
```

Set `CHROMA_URL=http://chromadb:8000` in `.env` for the agent to use it.

## Project Structure

```
agentic-platform/
├── docker-compose.yml
├── .env.example
├── README.md
├── data/                        # Mounted volume (SQLite DB + notes)
├── n8n/
│   └── workflows/
│       └── agent-workflow.json  # Import into n8n UI
├── services/
│   ├── agent/                   # FastAPI + LangGraph agent
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── agent/
│   │       ├── graph.py         # LangGraph state graph
│   │       ├── memory.py        # SQLite conversation memory
│   │       └── tools.py         # Tool catalogue + HTTP client
│   ├── tools/                   # FastAPI tool endpoints
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   └── ui-console/              # Platform dashboard (Express.js)
│       ├── Dockerfile
│       ├── server.js
│       ├── package.json
│       └── views/               # EJS templates
```

## Configuration

All tunables live in `.env` (see `.env.example`):

| Variable                    | Default              | Description                          |
| --------------------------- | -------------------- | ------------------------------------ |
| `OLLAMA_MODEL`              | `llama3`             | Ollama model name                    |
| `N8N_USER` / `N8N_PASSWORD` | `admin` / `changeme` | n8n basic auth                       |
| `AGENT_PORT`                | `8000`               | Agent service port                   |
| `TOOLS_PORT`                | `8001`               | Tools service port                   |
| `UI_PORT`                   | `3000`               | Dashboard UI port                    |
| `N8N_PORT`                  | `5678`               | n8n port                             |
| `CHROMA_URL`                | _(empty)_            | Set to enable ChromaDB vector memory |

## Development

Both Python services run with `uvicorn --reload` — edit code in `services/agent/` or `services/tools/` and changes apply instantly (the source dirs are bind-mounted).

```bash
# View agent logs
docker compose logs -f agent-service

# View all logs
docker compose logs -f

# Restart a single service
docker compose restart agent-service

# Rebuild after changing Dockerfile / requirements
docker compose up -d --build agent-service
```

## Troubleshooting

| Problem                            | Fix                                                                                                     |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `agent-service` unhealthy          | Check Ollama is running: `curl http://localhost:11434/api/tags`. Pull a model if empty.                 |
| n8n webhook returns 404            | Import the workflow JSON and **activate** it in the n8n UI.                                             |
| `tools-service` connection refused | Run `docker compose ps` — make sure `tools-service` is `healthy`.                                       |
| Ollama slow / OOM                  | Use a smaller model: `docker exec ollama ollama pull mistral` and set `OLLAMA_MODEL=mistral` in `.env`. |
| UI can't reach n8n                 | Ensure n8n is on the same host. The UI calls `http://localhost:5678` from the browser.                  |
| GPU not used                       | Uncomment the `deploy.resources.reservations` block in `docker-compose.yml` under `ollama`.             |
| ChromaDB not starting              | Run with profile: `docker compose --profile vector up -d`.                                              |

## License

MIT
