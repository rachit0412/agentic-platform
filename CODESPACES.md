# 🚀 Quick Start Guide for GitHub Codespaces

Welcome to the Agentic Platform on GitHub Codespaces! This guide will help you get started quickly.

## ⚡ Getting Started (2 minutes)

1. **Open in Codespaces**
   - You're already here! If not: Code → Codespaces → Create codespace on main
   - Initial setup takes 3-5 minutes (automatic after first time)

2. **Check Service Status**
   ```bash
   docker-compose ps
   ```

3. **Access the UI**
   - Go to the **PORTS** tab (bottom panel)
   - Click the 🌐 icon next to port **3000** (OpenWebUI)
   - Create your account and start chatting!

## 🎯 Main Services

| Service | Port | Access | Purpose |
|---------|------|--------|---------|
| **OpenWebUI** | 3000 | [Open](http://localhost:3000) | Chat interface |
| **LangGraph API** | 8000 | [Docs](http://localhost:8000/docs) | Agent orchestration |
| **n8n** | 5678 | [Open](http://localhost:5678) | Workflows |
| **Grafana** | 3002 | [Open](http://localhost:3002) | Monitoring |
| **Langfuse** | 3001 | [Open](http://localhost:3001) | LLM tracing |

**Default credentials:**
- n8n: `admin` / `changeme`
- Grafana: `admin` / `admin`

## 🤖 Working with AI Models

### Pull Models
```bash
# Pull default chat model (recommended)
docker exec ollama ollama pull llama3

# Pull embedding model for RAG
docker exec ollama ollama pull nomic-embed-text

# List available models
docker exec ollama ollama list
```

### Other Popular Models
```bash
# Smaller/faster models
docker exec ollama ollama pull llama3:8b
docker exec ollama ollama pull phi3

# Specialized models
docker exec ollama ollama pull codellama    # For coding
docker exec ollama ollama pull mistral      # General purpose
```

## 💻 Development Workflow

### Working with LangGraph API

```bash
# Navigate to the service
cd services/langgraph-api

# Edit files - changes auto-reload!
code main.py

# Install new dependencies
pip install some-package
echo "some-package==1.0.0" >> requirements.txt

# Restart service to apply changes
docker-compose restart langgraph-api
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f langgraph-api

# Last 50 lines only
docker-compose logs --tail=50 langgraph-api
```

### Managing Services

```bash
# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Restart one service
docker-compose restart [service-name]

# View resource usage
docker stats
```

## 🗄️ Database Access

### PostgreSQL

```bash
# Connect via CLI
docker exec -it postgres psql -U agentic -d agentic_platform

# Or use SQL Tools extension in VS Code
# 1. Open Command Palette (Ctrl+Shift+P)
# 2. Search "SQLTools: Connect"
# 3. Create connection:
#    - Host: localhost
#    - Port: 5432
#    - Database: agentic_platform
#    - Username: agentic
#    - Password: agentic123
```

### Common SQL Queries

```sql
-- List all tables
\dt

-- View schema
\d+ table_name

-- View recent activity
SELECT * FROM conversations ORDER BY created_at DESC LIMIT 10;
```

## 🎨 VS Code Tasks

Press `Ctrl+Shift+P` and search for "Run Task" to access:

- 🚀 Start All Services
- 🛑 Stop All Services
- 📝 View Logs
- 🤖 Pull Ollama Models
- 🗄️ Connect to PostgreSQL
- 🧹 Clean Docker Resources

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check what's wrong
docker-compose ps
docker-compose logs [service-name]

# Nuclear option - restart everything
docker-compose down
docker-compose up -d
```

### Port Already in Use

Codespaces handles port forwarding automatically. If you see conflicts:
1. Check the PORTS tab
2. Stop conflicting services
3. Or change ports in docker-compose.yml

### Out of Memory

```bash
# Stop unused services
docker-compose stop grafana prometheus loki

# Clean up Docker
docker system prune -a

# Or upgrade machine type in Codespace settings
```

### Models Not Loading

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull models manually
docker exec ollama ollama pull llama3

# Check disk space
df -h
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

