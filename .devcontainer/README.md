# Agentic Platform - Codespaces Setup

This directory contains the configuration for running the Agentic Platform in GitHub Codespaces.

## 🚀 Quick Start

1. **Open in Codespaces**
   - Click "Code" → "Codespaces" → "Create codespace on main"
   - Wait for the environment to build (first time takes ~5-10 minutes)

2. **Access Services**
   - Once ready, check the "PORTS" tab in VS Code
   - Click on the forwarded port links to access services
   - Main interfaces:
     - Dashboard (port 3000) - Platform dashboard
     - n8n (port 5678) - Workflow builder
     - LangGraph API (port 8000) - Agent orchestration
     - Grafana (port 3002) - Monitoring dashboards

3. **Pull AI Models**

   ```bash
   # Pull default models (runs automatically in background)
   docker exec ollama ollama pull llama3
   docker exec ollama ollama pull nomic-embed-text

   # Check available models
   docker exec ollama ollama list
   ```

## 📋 What's Included

### Development Container Features

- Python 3.11
- Node.js 20
- Docker-in-Docker (for running docker-compose)
- Git with Oh My Zsh
- VS Code extensions for Python, Docker, YAML, etc.

### Services

All services from docker-compose.yml are available:

- Dashboard - Platform dashboard & agent UI
- LangGraph API - Agent orchestration layer
- n8n - Workflow automation
- Ollama - Local LLM runtime
- PostgreSQL + pgvector - Database and embeddings
- Redis - Caching
- Keycloak - Authentication
- OPA - Policy enforcement
- Langfuse - LLM observability
- Prometheus - Metrics
- Grafana - Dashboards
- Loki - Logs

## 🔧 Configuration

### Environment Variables

Edit `.env` file in the root directory to customize:

- Database credentials
- API keys
- Service passwords
- OAuth settings

### Resource Considerations

- **Minimum**: 4-core, 8GB RAM codespace
- **Recommended**: 8-core, 16GB RAM for optimal performance
- **GPU**: Not available in standard codespaces (Ollama will use CPU)

## 🛠️ Development Workflow

### Working with LangGraph API

```bash
# Navigate to the service
cd services/langgraph-api

# Install dependencies
pip install -r requirements.txt

# Run tests (if available)
pytest

# Hot reload is enabled - edit files and changes reflect immediately
```

### Managing Services

```bash
# View all running services
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Restart a service
docker-compose restart [service-name]

# Stop all services
docker-compose down

# Start all services
docker-compose up -d
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U agentic -d agentic_platform

# Or use the SQL Tools extension in VS Code
```

## 🐛 Troubleshooting

### Services not starting

```bash
# Check service status
docker-compose ps

# View logs for specific service
docker-compose logs langgraph-api

# Restart everything
docker-compose down && docker-compose up -d
```

### Port conflicts

- Codespaces automatically handles port forwarding
- Check the PORTS tab to see which ports are active
- Make ports public if you need to share them

### Out of resources

- Stop unused services: `docker-compose stop [service-name]`
- Upgrade codespace machine type in settings
- Clean up Docker: `docker system prune -a`

## 📚 Additional Resources

- [GitHub Codespaces Docs](https://docs.github.com/en/codespaces)
- [Dev Container Specification](https://containers.dev/)
- [Project README](../README.md)
- [Contributing Guide](../CONTRIBUTING.md)

## 💡 Tips

1. **Persistent Storage**: `/workspaces` is persisted between codespace sessions
2. **Secrets**: Use Codespaces secrets for sensitive values instead of .env
3. **Prebuilds**: Enable prebuilds in repo settings for faster startup
4. **Extensions**: Additional extensions auto-install from devcontainer.json
5. **Model Storage**: Ollama models persist in Docker volumes between sessions
