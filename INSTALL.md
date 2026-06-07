# Installation Guide — Agentic Platform

Complete installation guide for all platforms and deployment scenarios.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Install](#quick-install)
3. [Platform-Specific Instructions](#platform-specific-instructions)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **CPU:** 4 cores
- **RAM:** 8 GB
- **Disk:** 20 GB free space
- **OS:** Windows 10/11, macOS 11+, Linux (Ubuntu 20.04+, Debian 11+)
- **Docker:** Version 20.10+
- **Docker Compose:** Version 2.0+

### Recommended Requirements

- **CPU:** 8+ cores
- **RAM:** 16 GB
- **Disk:** 50 GB SSD
- **GPU:** NVIDIA GPU with 8 GB+ VRAM (for faster local inference)
- **Network:** High-speed internet for initial model downloads (~4 GB per model)

## Quick Install

```bash
# 1. Clone repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. (Optional) Copy and customise environment
cp .env.example .env

# 3. Start all 16 containers
docker compose up -d --build

# 4. Pull a model (first time only — ~4 GB)
docker exec ollama ollama pull llama3

# 5. Wait for containers to become healthy
docker compose ps

# 6. Open the dashboard
# http://localhost:3005
```

## Platform-Specific Instructions

### Windows

#### Prerequisites

1. **Install Docker Desktop**

   ```powershell
   # Download from https://www.docker.com/products/docker-desktop
   # Or use winget:
   winget install Docker.DockerDesktop
   ```

2. **Enable WSL 2** (Recommended)

   ```powershell
   # Run as Administrator
   wsl --install
   wsl --set-default-version 2
   # Restart your computer
   ```

3. **Configure Docker Desktop**
   - Open Docker Desktop → Settings → Resources
   - Allocate at least 8 GB RAM and 4 CPUs
   - Apply & Restart

#### Installation

```powershell
# Clone the repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# (Optional) Customise environment
Copy-Item .env.example .env

# Start all services
docker compose up -d --build

# Pull a model
docker exec ollama ollama pull llama3

# Verify
docker compose ps
```

#### GPU Support (Windows)

```powershell
# 1. Install NVIDIA drivers from https://www.nvidia.com/Download/index.aspx
# 2. Enable GPU in Docker Desktop: Settings → Resources → WSL Integration → Enable GPU
# 3. Uncomment the GPU block in docker-compose.yml under the ollama service
# 4. Restart Docker Desktop
```

### Linux (Ubuntu/Debian)

#### Prerequisites

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y ca-certificates curl gnupg git

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (log out and back in after)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker version
docker compose version
```

#### Installation

```bash
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

cp .env.example .env          # optional
docker compose up -d --build
docker exec ollama ollama pull llama3

docker compose ps              # verify all healthy
```

#### GPU Support (Linux)

```bash
# 1. Install NVIDIA drivers
sudo ubuntu-drivers autoinstall

# 2. Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 3. Test GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 4. Uncomment the GPU block in docker-compose.yml under ollama
```

### macOS

#### Prerequisites

```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Install Git (if needed)
brew install git
```

#### Installation

```bash
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

cp .env.example .env          # optional
docker compose up -d --build
docker exec ollama ollama pull llama3

docker compose ps              # verify all healthy
```

#### Apple Silicon (M1/M2/M3/M4)

All images used are multi-arch compatible. No special configuration needed.

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and edit as needed. Key variables:

| Variable                    | Default              | Description                                                            |
| --------------------------- | -------------------- | ---------------------------------------------------------------------- |
| `UI_PORT`                   | `3005`               | UI Console host port                                                   |
| `AGENT_PORT`                | `8010`               | Agent Service host port                                                |
| `TOOLS_PORT`                | `8011`               | Tools Service host port                                                |
| `OLLAMA_PORT`               | `11436`              | Ollama host port                                                       |
| `OLLAMA_MODEL`              | `llama3`             | Default Ollama model                                                   |
| `LLM_PROVIDER`              | `ollama`             | Default provider (`ollama`, `azure-openai`, `openai`, `azure-foundry`) |
| `AZURE_OPENAI_API_KEY`      | _(empty)_            | Azure OpenAI API key                                                   |
| `AZURE_OPENAI_ENDPOINT`     | _(empty)_            | Azure OpenAI endpoint URL                                              |
| `AZURE_OPENAI_DEPLOYMENT`   | `gpt-4o-mini`        | Azure OpenAI deployment name                                           |
| `N8N_USER` / `N8N_PASSWORD` | `admin` / `changeme` | n8n basic auth                                                         |
| `LANGFUSE_PORT`             | `3012`               | Langfuse host port                                                     |
| `GRAFANA_PORT`              | `3013`               | Grafana host port                                                      |

### Resource Allocation

To adjust container resources, edit `docker-compose.yml`:

```yaml
services:
  agent-service:
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 8G
```

## Verification

### Check Service Health

```bash
# All containers
docker compose ps

# API health checks
curl http://localhost:8010/health   # agent-service
curl http://localhost:8011/health   # tools-service
curl http://localhost:3005/health   # ui-console

# Multi-service health check
curl http://localhost:3005/api/health-check
```

### Access Services

| Service        | URL                        | Credentials                 |
| -------------- | -------------------------- | --------------------------- |
| UI Console     | http://localhost:3005      | admin / Admin@Platform2026! |
| Agent API Docs | http://localhost:8010/docs | —                           |
| Tools API Docs | http://localhost:8011/docs | —                           |
| n8n            | http://localhost:5678      | admin / changeme            |
| Langfuse       | http://localhost:3012      | admin@local.dev / changeme  |
| Grafana        | http://localhost:3013      | admin / admin               |
| Prometheus     | http://localhost:9090      | —                           |

### Test Agent

```bash
# List available models
curl http://localhost:8010/models

# Run agent
curl -X POST http://localhost:8010/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 42 * 13?", "sessionId": "test-1"}'
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f agent-service

# Last 100 lines
docker compose logs --tail=100
```

## Troubleshooting

### Docker Issues

| Problem             | Fix                                                            |
| ------------------- | -------------------------------------------------------------- |
| Docker not starting | Restart Docker Desktop. Linux: `sudo systemctl restart docker` |
| Permission denied   | Linux: `sudo usermod -aG docker $USER` then log out/in         |
| Port already in use | Change port via env var: `UI_PORT=3001 docker compose up -d`   |
| Out of disk space   | `docker system prune -a` and `docker volume prune`             |

### Service Issues

| Problem                   | Fix                                                                               |
| ------------------------- | --------------------------------------------------------------------------------- |
| `agent-service` unhealthy | Check Ollama: `curl http://localhost:11436/api/tags`. Pull a model.               |
| Model not in UI dropdown  | Pull it: `docker exec ollama ollama pull <model>`. Refresh.                       |
| Azure OpenAI unavailable  | Set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` in `.env`, restart.        |
| `tools-service` refused   | `docker compose ps` — ensure it's healthy. `docker compose restart tools-service` |
| Langfuse not loading      | Verify port 3012 is free. Check `docker compose logs langfuse`                    |
| Grafana not loading       | Verify port 3013 is free. Check `docker compose logs grafana`                     |

### Performance Issues

| Problem            | Fix                                                            |
| ------------------ | -------------------------------------------------------------- |
| Slow responses     | `docker stats` — check resources. Allocate more RAM in Docker. |
| Ollama OOM         | Use smaller model: `docker exec ollama ollama pull phi3`       |
| Model loading slow | Model is kept in memory with `OLLAMA_KEEP_ALIVE=24h` (default) |
| GPU not used       | Uncomment GPU block in `docker-compose.yml` under `ollama`     |

## Next Steps

After successful installation:

1. Open the UI at http://localhost:3005
2. Create a **Skill** (prompt + tools + constraints + optional file attachments: scripts, references, assets)
3. Create an **Agent** (model + skills + knowledge base)
4. Run your agent in **Run Agent**
5. Pull additional models: `docker exec ollama ollama pull mistral`
6. Ingest documents into the knowledge base
7. Explore API docs at http://localhost:8010/docs
8. Use the **REST Console** at http://localhost:3005/rest to test all 145 endpoints
9. Create workflows in n8n at http://localhost:5678
10. Review LLM traces in Langfuse at http://localhost:3012
11. Monitor platform health in Grafana at http://localhost:3013

---

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

### OpenAI (Cloud)

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
LLM_PROVIDER=openai           # Optional: set as default provider
```

### Azure AI Foundry (Cloud)

```env
AZURE_FOUNDRY_ENDPOINT=https://your-foundry.openai.azure.com/
AZURE_FOUNDRY_API_KEY=your-key-here
AZURE_FOUNDRY_MODELS=model1,model2
LLM_PROVIDER=azure-foundry    # Optional: set as default provider
```

Once configured, cloud models appear in the UI model dropdown alongside Ollama models.

---

## API Reference (curl examples)

### Agent Service

```bash
# Health check
curl http://localhost:8010/health

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
  -d '{"text": "LangGraph is a framework for building stateful agents...", "source": "docs"}'

# Search the knowledge base
curl -X POST http://localhost:8010/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what is langgraph", "k": 3}'
```

### Tools Service

| Endpoint               | Method | Description                                                        |
| ---------------------- | ------ | ------------------------------------------------------------------ |
| `/tools/math`          | POST   | Safe arithmetic evaluation (`{"expression": "2+2"}`)               |
| `/tools/http-fetch`    | POST   | Fetch a URL (allowlist: httpbin.org, jsonplaceholder.typicode.com) |
| `/tools/file-write`    | POST   | Save a note (`{"filename": "todo.txt", "content": "..."}`)         |
| `/tools/file-read`     | POST   | Read a saved note (`{"filename": "todo.txt"}`)                     |
| `/tools/datetime`      | POST   | Current UTC date, time, and weekday                                |
| `/tools/web-search`    | POST   | Web search via DuckDuckGo (`{"query": "...", "max_results": 5}`)   |
| `/tools/code-execute`  | POST   | Execute Python code in a sandbox                                   |
| `/tools/vector-search` | POST   | Search documents in ChromaDB                                       |
| `/tools/vector-store`  | POST   | Ingest documents into ChromaDB                                     |
