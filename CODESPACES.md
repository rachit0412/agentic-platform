# GitHub Codespaces

Quick start, configuration, and deployment guide for running the Agentic Platform in GitHub Codespaces.

## Getting Started

1. **Open in Codespaces**: Code → Codespaces → Create codespace on main (initial setup 3-5 min)
2. **Check status**: `docker-compose ps`
3. **Access the UI**: PORTS tab → click 🌐 next to port **3001**

## Services

| Service        | Port  | Purpose                         |
| -------------- | ----- | ------------------------------- |
| **UI Console** | 3001  | Platform dashboard (Express.js) |
| **Agent API**  | 8010  | FastAPI + LangGraph agent       |
| **Tools API**  | 8011  | FastAPI tool endpoints          |
| **n8n**        | 5678  | Workflow automation             |
| **Langfuse**   | 3012  | LLM tracing                     |
| **Grafana**    | 3013  | Monitoring dashboards           |
| **Prometheus** | 9090  | Metrics collection              |
| **Ollama**     | 11436 | Local LLM runtime               |
| **ChromaDB**   | 8200  | Vector store for RAG            |

**Default credentials:** n8n: `admin` / `changeme` · Grafana: `admin` / `admin`

## Working with AI Models

```bash
docker exec ollama ollama pull llama3            # Default chat model
docker exec ollama ollama pull nomic-embed-text   # Embedding model for RAG
docker exec ollama ollama list                    # List installed models
```

## Development Workflow

```bash
# Logs
docker-compose logs -f                  # All services
docker-compose logs --tail=50 agent-service  # Specific service

# Manage services
docker-compose down                     # Stop all
docker-compose up -d                    # Start all
docker-compose restart agent-service    # Restart one
docker stats                            # Resource usage
```

## Database Access

```bash
docker exec -it postgres psql -U agentic -d agentic_platform
```

## VS Code Tasks

Press `Ctrl+Shift+P` → "Run Task":
🚀 Start All · 🛑 Stop All · 🔄 Restart · 📝 View Logs · 🤖 Pull Models · 🗄️ Connect PostgreSQL · 🧹 Clean Docker

## Repository Maintainer Setup

1. **Enable Prebuilds**: Settings → Codespaces → Enable prebuilds (main branch, 8-core recommended)
2. **Set Secrets**: Settings → Secrets → Codespaces → add `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
3. **Machine types**: Configured in `.github/codespaces.json` (min 4-core, recommended 8-core 16GB)

## Troubleshooting

```bash
docker-compose ps                       # Check status
docker-compose logs [service-name]      # View logs
docker-compose down && docker-compose up -d  # Full restart
docker system prune -a                  # Free disk space
curl http://localhost:11436/api/tags    # Check Ollama
```

## 📚 Quick Links

- 📖 [Full Documentation](.devcontainer/README.md)
- 🏗️ [Architecture Guide](README.md#-architecture)
- 🤝 [Contributing](CONTRIBUTING.md)
- 📦 [Installation Guide](INSTALL.md)

## 💡 Pro Tips

1. **Secrets**: Use Codespaces Secrets (Settings → Secrets) instead of .env for sensitive API keys
2. **Prebuilds**: Enable in repo settings for instant startup
3. **Port Visibility**: Make ports public in PORTS tab to share with team
4. **Extensions**: All recommended extensions auto-install from .vscode/extensions.json
5. **Persistence**: Everything in /workspaces persists between sessions
6. **Resource Monitor**: Use `docker stats` to monitor container resource usage

## 🆘 Need Help?

- Check [Troubleshooting](#-troubleshooting) section above
- Review logs: `docker-compose logs -f [service-name]`
- View service status: `docker-compose ps`
- Open an issue on GitHub
- Check the [docs](README.md) for detailed information

---

**Happy Coding! 🎉**
