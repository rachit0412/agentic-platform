# 📦 Installation Guide - Agentic Platform

Complete installation guide for all platforms and deployment scenarios.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Install](#quick-install)
3. [Platform-Specific Instructions](#platform-specific-instructions)
4. [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **CPU:** 4 cores
- **RAM:** 8 GB
- **Disk:** 20 GB free space
- **OS:** Windows 10/11, macOS 11+, Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- **Docker:** Version 20.10+
- **Docker Compose:** Version 2.0+

### Recommended Requirements

- **CPU:** 8+ cores
- **RAM:** 16 GB
- **Disk:** 50 GB SSD
- **GPU:** NVIDIA GPU with 8GB+ VRAM (for faster inference)
- **Network:** High-speed internet for initial model downloads

## Quick Install

### Windows (PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Run automated setup
.\setup.ps1

# 3. Access the application
Start-Process "http://localhost:3000"
```

### Linux/macOS (Bash)

```bash
# 1. Clone repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Run setup script
chmod +x setup.sh
./setup.sh

# 3. Access the application
open http://localhost:3000  # macOS
xdg-open http://localhost:3000  # Linux
```

## Platform-Specific Instructions

### Windows

#### Prerequisites

1. **Install Docker Desktop**
   ```powershell
   # Download and install from:
   # https://www.docker.com/products/docker-desktop
   
   # Or use winget
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
   - Open Docker Desktop
   - Go to Settings → Resources
   - Allocate at least 8 GB RAM
   - Allocate at least 4 CPUs
   - Apply & Restart

#### Installation

```powershell
# 1. Clone the repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Copy environment file
Copy-Item .env.example .env

# 3. Run setup script
.\setup.ps1

# 4. Wait for setup to complete (5-15 minutes)

# 5. Verify installation
.\manage.ps1 status
.\manage.ps1 test
```

#### GPU Support (Windows)

```powershell
# 1. Install NVIDIA drivers
# Download from: https://www.nvidia.com/Download/index.aspx

# 2. Install NVIDIA Container Toolkit
# Follow: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

# 3. Enable GPU in Docker Desktop
# Settings → Resources → WSL Integration → Enable GPU

# 4. Restart Docker Desktop
```

### Linux (Ubuntu/Debian)

#### Prerequisites

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker installation
docker version
docker compose version
```

#### Installation

```bash
# 1. Clone repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Copy environment file
cp .env.example .env

# 3. Make scripts executable
chmod +x setup.sh manage.sh

# 4. Run setup
./setup.sh

# 5. Verify installation
./manage.sh status
./manage.sh test
```

#### GPU Support (Linux)

```bash
# 1. Install NVIDIA drivers
sudo ubuntu-drivers autoinstall

# 2. Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 3. Test GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### macOS

#### Prerequisites

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Or download from:
# https://www.docker.com/products/docker-desktop

# Install Git (if not installed)
brew install git
```

#### Installation

```bash
# 1. Clone repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Copy environment file
cp .env.example .env

# 3. Make scripts executable
chmod +x setup.sh manage.sh

# 4. Run setup
./setup.sh

# 5. Verify installation
./manage.sh status
```

#### Note for Apple Silicon (M1/M2/M3)

```bash
# Some images may need platform specification
# Edit docker-compose.yml to add:
# platform: linux/amd64

# Or pull ARM-compatible images when available
```

## Manual Installation

If automated scripts fail, follow these steps:

### Step 1: Prepare Environment

```bash
# 1. Clone repository
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform

# 2. Create environment file
cp .env.example .env

# 3. Edit .env file with your values
nano .env  # or vim, VSCode, etc.
```

### Step 2: Create Necessary Directories

```bash
mkdir -p database/init
mkdir -p services/langgraph-api/agents
mkdir -p n8n/workflows
mkdir -p keycloak/realms
mkdir -p opa/policies
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/datasources
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/loki
```

### Step 3: Start Services

```bash
# Pull images
docker-compose pull

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### Step 4: Download Models

```bash
# Wait for Ollama to be ready (check logs)
docker-compose logs -f ollama

# Pull base model (7B, ~4GB)
docker exec ollama ollama pull llama3

# Pull embedding model (~274MB)
docker exec ollama ollama pull nomic-embed-text

# Verify models
docker exec ollama ollama list
```

### Step 5: Initialize Databases

```bash
# Database initialization happens automatically via init scripts
# Check logs to verify
docker-compose logs postgres

# Test connection
docker exec postgres psql -U aiuser -d ai_chat -c "SELECT 1"
```

## Configuration

### Essential Configuration

Edit `.env` file:

```bash
# REQUIRED: Change these before production
POSTGRES_PASSWORD=your-strong-password-here
WEBUI_SECRET_KEY=$(openssl rand -hex 32)
KEYCLOAK_CLIENT_SECRET=$(openssl rand -hex 32)
LANGFUSE_NEXTAUTH_SECRET=$(openssl rand -hex 32)
LANGFUSE_SALT=$(openssl rand -hex 16)

# Optional: API keys for external services
OPENAI_API_KEY=sk-...
```

### Generate Secure Keys

```bash
# Linux/macOS
openssl rand -hex 32

# PowerShell
-join ((65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

### Resource Allocation

Edit `docker-compose.yml` to adjust resources:

```yaml
services:
  langgraph-api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### Network Ports

Default ports used:

| Service | Port | Configurable |
|---------|------|--------------|
| OpenWebUI | 3000 | Yes |
| LangGraph API | 8000 | Yes |
| n8n | 5678 | Yes |
| Keycloak | 8080 | Yes |
| PostgreSQL | 5432 | Yes |
| Redis | 6379 | Yes |
| Ollama | 11434 | Yes |
| Langfuse | 3001 | Yes |
| Grafana | 3002 | Yes |
| Prometheus | 9090 | Yes |
| OPA | 8181 | Yes |
| Loki | 3100 | Yes |

To change ports, edit `docker-compose.yml`:

```yaml
services:
  open-webui:
    ports:
      - "8080:8080"  # Change 3000 to desired port
```

## Verification

### Check Service Health

```bash
# Using management script (Windows)
.\manage.ps1 test

# Using management script (Linux/Mac)
./manage.sh test

# Manual checks
curl http://localhost:8000/health
curl http://localhost:3000
curl http://localhost:9090/-/healthy
```

### Access Services

After installation, verify you can access:

- ✅ OpenWebUI: http://localhost:3000
- ✅ API Docs: http://localhost:8000/docs
- ✅ n8n: http://localhost:5678
- ✅ Keycloak: http://localhost:8080
- ✅ Grafana: http://localhost:3002
- ✅ Langfuse: http://localhost:3001
- ✅ Prometheus: http://localhost:9090

### Test Chat Functionality

```bash
# Test chat API
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello!",
    "user_id": "test",
    "model": "llama3"
  }'
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f langgraph-api

# Last 100 lines
docker-compose logs --tail=100
```

## Troubleshooting

### Installation Issues

#### Docker not starting

```bash
# Windows: Restart Docker Desktop
# Linux: Check Docker service
sudo systemctl status docker
sudo systemctl restart docker

# Verify installation
docker version
```

#### Permission denied errors

```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker ps
```

#### Port already in use

```bash
# Find process using port
# Windows
netstat -ano | findstr :3000

# Linux/Mac
lsof -i :3000

# Stop conflicting service or change port in docker-compose.yml
```

### Service Issues

#### Services won't start

```bash
# Check logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Full restart
docker-compose down
docker-compose up -d
```

#### Out of disk space

```bash
# Clean up Docker
docker system prune -a
docker volume prune

# Check disk usage
docker system df
```

#### Models not downloading

```bash
# Check Ollama logs
docker-compose logs ollama

# Manually pull models
docker exec ollama ollama pull llama3

# Check available space
df -h  # Linux/Mac
Get-PSDrive C | Select-Object Used,Free  # Windows
```

### Performance Issues

#### Slow responses

```bash
# Check resource usage
docker stats

# Increase memory limit in Docker settings
# Or allocate more resources in docker-compose.yml
```

#### Model loading slow

```bash
# Keep models in memory
docker exec ollama ollama show llama3

# Configure in docker-compose.yml
OLLAMA_KEEP_ALIVE=24h
```

### Database Issues

#### Connection errors

```bash
# Check PostgreSQL status
docker exec postgres pg_isready -U aiuser

# Restart database
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

#### Reset database

```bash
# Backup first!
docker exec postgres pg_dump -U aiuser ai_chat > backup.sql

# Reset
docker-compose down -v
docker-compose up -d
```

## Getting Help

If you encounter issues:

1. **Check logs**: `docker-compose logs [service-name]`
2. **Search issues**: [GitHub Issues](https://github.com/rachit0412/agentic-platform/issues)
3. **Ask questions**: [GitHub Discussions](https://github.com/rachit0412/agentic-platform/discussions)
4. **Read docs**: Check other documentation files in `docs/`

## Next Steps

After successful installation:

1. ✅ Access OpenWebUI at http://localhost:3000
2. ✅ Create your first chat conversation
3. ✅ Explore API documentation at http://localhost:8000/docs
4. ✅ Create workflows in n8n
5. ✅ Monitor performance in Grafana
6. ✅ Review traces in Langfuse

Happy building! 🚀
