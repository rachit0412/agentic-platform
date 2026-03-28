# 🤖 Agentic Platform - Production-Ready AI Chat Application

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Required-blue)](https://www.docker.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)

A comprehensive, production-ready AI chat application stack with modern best-in-class open-source components for local development and cloud deployment.

## 🌟 Features

- **🎯 Modern Chat Interface** - OpenWebUI for intuitive user experience
- **🤖 Multi-Agent Orchestration** - LangGraph for dynamic, controllable agent workflows
- **🔄 Workflow Automation** - n8n for deterministic integrations
- **📊 Vector Database** - PostgreSQL + pgvector for RAG capabilities
- **🔐 Enterprise Security** - Keycloak SSO + OPA policy enforcement
- **📈 Full Observability** - Langfuse tracing, Prometheus metrics, Grafana dashboards
- **🚀 Local LLM Runtime** - Ollama for CPU/GPU model serving

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [GitHub Codespaces](#-github-codespaces)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Development](#-development)
- [Production Deployment](#-production-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Interface                          │
│                     OpenWebUI (Port 3000)                        │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────────────────────┐
│                    Orchestration Layer                           │
│  ┌──────────────────┐              ┌────────────────────┐       │
│  │  n8n Workflows   │              │  LangGraph Agents  │       │
│  │  (Port 5678)     │◄────────────►│  (Port 8000)       │       │
│  └──────────────────┘              └────────────────────┘       │
└────────────────┬────────────────────────────┬───────────────────┘
                 │                            │
┌────────────────┴────────────────┐  ┌───────┴───────────────────┐
│      Model Runtime              │  │    Data & Memory          │
│  ┌──────────────────┐           │  │  ┌──────────────────┐     │
│  │  Ollama          │           │  │  │  PostgreSQL      │     │
│  │  (Port 11434)    │           │  │  │  + pgvector      │     │
│  └──────────────────┘           │  │  │  (Port 5432)     │     │
└─────────────────────────────────┘  │  └──────────────────┘     │
                                     │  ┌──────────────────┐     │
                                     │  │  Redis Cache     │     │
                                     │  │  (Port 6379)     │     │
                                     │  └──────────────────┘     │
                                     └────────────────────────────┘
```

### Components

| Component | Version | Purpose | Port |
|-----------|---------|---------|------|
| **OpenWebUI** | Latest | Modern chat interface | 3000 |
| **LangGraph API** | Custom | Agent orchestration | 8000 |
| **n8n** | Latest | Workflow automation | 5678 |
| **Ollama** | Latest | Local LLM serving | 11434 |
| **PostgreSQL** | 16 + pgvector | Database + embeddings | 5432 |
| **Redis** | 7 | Caching & sessions | 6379 |
| **Keycloak** | Latest | SSO/OIDC auth | 8080 |
| **OPA** | Latest | Policy enforcement | 8181 |
| **Langfuse** | Latest | LLM tracing | 3001 |
| **Prometheus** | Latest | Metrics collection | 9090 |
| **Grafana** | Latest | Monitoring dashboards | 3002 |
| **Loki** | Latest | Log aggregation | 3100 |

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (with compose v2) - [Download](https://www.docker.com/products/docker-desktop)
- **8GB RAM minimum** (16GB recommended)
- **10GB free disk space** for Docker images and models
- **(Optional) NVIDIA GPU** with drivers for accelerated inference

### 1-Command Setup

```powershell
# Clone the repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# Run automated setup (Windows)
.\setup.ps1

# Or manually (Linux/Mac)
docker-compose up -d
docker exec ollama ollama pull llama3
docker exec ollama ollama pull nomic-embed-text
```

**Setup time:** 5-15 minutes depending on your internet speed.

## ☁️ GitHub Codespaces

### One-Click Cloud Development

Get started instantly in a fully configured cloud development environment with zero local setup required.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=rachit0412/agentic-platform)

### Features
- ✅ **Zero Installation** - No Docker, Python, or dependencies needed locally
- ✅ **Full Stack Running** - All 12 services pre-configured and ready
- ✅ **Pre-installed Tools** - Python 3.11, Node.js 20, Docker, Git, VS Code extensions
- ✅ **Automated Setup** - Models and dependencies install automatically
- ✅ **Persistent Storage** - Your work is saved between sessions
- ✅ **Access Anywhere** - Code from browser or VS Code desktop

### Quick Start in Codespaces

1. **Launch Codespace**
   - Click the badge above or go to: Code → Codespaces → Create codespace
   - Wait 3-5 minutes for initial build (cached afterwards)

2. **Access Services**
   - Check the **PORTS** tab in VS Code
   - Click port URLs to access:
     - Port 3000: OpenWebUI (Chat Interface)
     - Port 5678: n8n (Workflows)
     - Port 8000: LangGraph API
     - Port 3002: Grafana (Monitoring)

3. **Start Coding**
   - All services auto-start via docker-compose
   - Python environment ready in `services/langgraph-api`
   - Changes hot-reload automatically

### Recommended Machine Type
- **Minimum**: 4-core (for basic usage)
- **Recommended**: 8-core, 16GB RAM (for full performance)

📖 See [.devcontainer/README.md](.devcontainer/README.md) for complete Codespaces documentation.

### Access Your Services

Once setup completes, access these URLs:

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| 🎨 **Chat UI** | http://localhost:3000 | Create account on first visit |
| 📚 **API Docs** | http://localhost:8000/docs | N/A (interactive docs) |
| 🔄 **Workflows** | http://localhost:5678 | `admin` / `changeme` |
| 🔐 **Auth** | http://localhost:8080 | `admin` / `admin` |
| 📊 **Monitoring** | http://localhost:3002 | `admin` / `admin` |
| 🔍 **Tracing** | http://localhost:3001 | Create account on first visit |

## 📥 Installation

### Detailed Installation Steps

#### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# Copy environment template
cp .env.example .env

# Edit .env and update passwords/secrets
# At minimum, change:
# - POSTGRES_PASSWORD
# - WEBUI_SECRET_KEY
# - KEYCLOAK_CLIENT_SECRET
# - LANGFUSE_NEXTAUTH_SECRET
```

#### 2. Start Services

```bash
# Start all containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### 3. Download AI Models

```bash
# Required: Base chat model (7B, ~4GB)
docker exec ollama ollama pull llama3

# Required: Embedding model for RAG (~274MB)
docker exec ollama ollama pull nomic-embed-text

# Optional: Coding model (7B, ~4GB)
docker exec ollama ollama pull codellama

# List downloaded models
docker exec ollama ollama list
```

#### 4. Verify Setup

```powershell
# Use management script
.\manage.ps1 test

# Or manually test endpoints
curl http://localhost:8000/health
curl http://localhost:3000
```

### Platform-Specific Installation

<details>
<summary><b>Windows</b></summary>

```powershell
# Prerequisites
# 1. Install Docker Desktop from https://www.docker.com/products/docker-desktop
# 2. Enable WSL 2 (recommended) or Hyper-V
# 3. Allocate at least 8GB RAM in Docker Desktop settings

# Run setup script
.\setup.ps1

# Manage services
.\manage.ps1 start
.\manage.ps1 stop
.\manage.ps1 logs
```

</details>

<details>
<summary><b>Linux</b></summary>

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Run setup
chmod +x setup.sh
./setup.sh
```

</details>

<details>
<summary><b>macOS</b></summary>

```bash
# Install Docker Desktop
# Download from https://www.docker.com/products/docker-desktop

# Or use Homebrew
brew install --cask docker

# Run setup
chmod +x setup.sh
./setup.sh
```

</details>

## 💻 Usage

### Chat Interface (OpenWebUI)

1. Navigate to http://localhost:3000
2. Create an account
3. Start chatting with AI
4. Upload documents for RAG
5. Customize model settings

### API Usage

#### Simple Chat Request

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing",
    "user_id": "user-123",
    "model": "llama3"
  }'
```

#### RAG Query

```bash
curl -X POST http://localhost:8000/api/v1/rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features?",
    "user_id": "user-123",
    "top_k": 5
  }'
```

See [API_EXAMPLES.md](API_EXAMPLES.md) for more examples.

### Create Workflows with n8n

1. Access n8n at http://localhost:5678
2. Login with `admin` / `changeme`
3. Import pre-built workflows from `n8n/workflows/`
4. Create custom automation workflows
5. Connect to 400+ integrations

### Monitor with Grafana

1. Access Grafana at http://localhost:3002
2. Login with `admin` / `admin`
3. View pre-configured dashboards
4. Monitor LLM performance, latency, costs
5. Set up alerts

## ⚙️ Configuration

### Environment Variables

Key configuration in `.env`:

```bash
# Database
POSTGRES_USER=aiuser
POSTGRES_PASSWORD=strong-password-here
POSTGRES_DB=ai_chat

# Security
WEBUI_SECRET_KEY=generate-random-key
KEYCLOAK_CLIENT_SECRET=generate-secret

# Observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### Model Configuration

Configure Ollama models in `docker-compose.yml`:

```yaml
ollama:
  environment:
    - OLLAMA_KEEP_ALIVE=24h  # Keep models loaded
    - OLLAMA_NUM_PARALLEL=4   # Concurrent requests
```

### Resource Limits

Adjust container resources:

```yaml
services:
  langgraph-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

## 🛠️ Development

### Project Structure

```
agentic-platform/
├── docker-compose.yml          # Service orchestration
├── .env.example                # Environment template
├── README.md                   # This file
├── INSTALL.md                  # Detailed installation
│
├── services/
│   └── langgraph-api/          # Agent orchestration
│       ├── agents/             # Agent implementations
│       ├── main.py             # FastAPI app
│       └── requirements.txt
│
├── database/
│   └── init/                   # PostgreSQL schemas
│
├── n8n/workflows/              # Workflow templates
├── keycloak/realms/            # Auth configuration
├── opa/policies/               # Authorization policies
└── monitoring/                 # Observability configs
```

### Running in Development Mode

```bash
# Start with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Rebuild after code changes
docker-compose build langgraph-api
docker-compose up -d langgraph-api
```

### Adding Custom Agents

1. Create new agent in `services/langgraph-api/agents/`
2. Define LangGraph workflow
3. Register endpoint in `main.py`
4. Restart service

Example:
```python
# services/langgraph-api/agents/custom_agent.py
from langgraph.graph import StateGraph

def create_custom_agent():
    workflow = StateGraph(AgentState)
    # Define nodes and edges
    return workflow.compile()
```

### Testing

```bash
# Run API tests
pytest services/langgraph-api/tests/

# Test specific service
curl http://localhost:8000/health

# Load test
ab -n 1000 -c 10 http://localhost:8000/api/v1/chat
```

## 🚢 Production Deployment

### Security Hardening

- [ ] Change all default passwords
- [ ] Enable SSL/TLS (add nginx/traefik reverse proxy)
- [ ] Configure firewall rules
- [ ] Enable Keycloak email verification
- [ ] Use secrets management (HashiCorp Vault, AWS Secrets Manager)
- [ ] Enable OPA fail-closed policies
- [ ] Set up rate limiting
- [ ] Enable audit logging

### Scaling Considerations

- [ ] Move to Kubernetes for orchestration
- [ ] Use external managed databases (RDS, CloudSQL)
- [ ] Implement horizontal pod autoscaling
- [ ] Add load balancer
- [ ] Use managed Keycloak (Red Hat SSO)
- [ ] Cluster Redis for high availability
- [ ] Replace Ollama with vLLM for better throughput

### Cloud Deployment

<details>
<summary><b>AWS ECS</b></summary>

```bash
# Install AWS CLI and ECS CLI
aws ecs create-cluster --cluster-name agentic-platform

# Push images to ECR
docker tag langgraph-api:latest <account>.dkr.ecr.<region>.amazonaws.com/langgraph-api
docker push <account>.dkr.ecr.<region>.amazonaws.com/langgraph-api

# Deploy with ECS
ecs-cli compose --file docker-compose.yml up
```

</details>

<details>
<summary><b>Azure Container Instances</b></summary>

```bash
# Login to Azure
az login

# Create resource group
az group create --name agentic-platform --location eastus

# Deploy with ACI
az container create --resource-group agentic-platform \
  --file docker-compose.yml
```

</details>

<details>
<summary><b>GCP Cloud Run</b></summary>

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/langgraph-api

# Deploy to Cloud Run
gcloud run deploy langgraph-api \
  --image gcr.io/PROJECT_ID/langgraph-api \
  --platform managed
```

</details>

## 🔧 Troubleshooting

### Common Issues

**Services won't start**
```bash
# Check Docker is running
docker version

# Check logs
docker-compose logs [service-name]

# Restart a service
docker-compose restart [service-name]
```

**Out of memory**
```bash
# Increase Docker memory in settings
# Or stop unused services
docker-compose stop grafana loki prometheus
```

**Models not loading**
```bash
# Check available space
docker system df

# Pull models again
docker exec ollama ollama pull llama3

# Check model list
docker exec ollama ollama list
```

**Database connection errors**
```bash
# Check PostgreSQL is healthy
docker exec postgres pg_isready -U aiuser

# Restart database
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Getting Help

- 📖 Check [detailed documentation](docs/)
- 🐛 [Report issues](https://github.com/rachit0412/agentic-platform/issues)
- 💬 [Discussions](https://github.com/rachit0412/agentic-platform/discussions)

## 📚 Documentation

- [Installation Guide](INSTALL.md) - Detailed setup instructions
- [API Documentation](API_EXAMPLES.md) - Code examples
- [Architecture](ARCHITECTURE.md) - System design
- [Configuration](docs/configuration.md) - Advanced config
- [Development Guide](docs/development.md) - Contributing

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- Additional agent implementations
- New n8n workflow templates
- Grafana dashboard templates
- Documentation improvements
- Bug fixes and performance optimizations

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with amazing open-source projects:

- [OpenWebUI](https://github.com/open-webui/open-webui) - Chat interface
- [LangChain/LangGraph](https://github.com/langchain-ai/langgraph) - Agent framework
- [n8n](https://github.com/n8n-io/n8n) - Workflow automation
- [Ollama](https://github.com/ollama/ollama) - LLM runtime
- [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) - Database
- [Keycloak](https://www.keycloak.org/) - Authentication
- [OPA](https://www.openpolicyagent.org/) - Authorization
- [Langfuse](https://langfuse.com/) - LLM observability
- [Prometheus](https://prometheus.io/) + [Grafana](https://grafana.com/) - Monitoring

## 📬 Contact

- **Author:** Rachit Gupta
- **GitHub:** [@rachit0412](https://github.com/rachit0412)
- **Repository:** [agentic-platform](https://github.com/rachit0412/agentic-platform)

---

⭐ **Star this repo** if you find it useful!

Made with ❤️ for the AI community
