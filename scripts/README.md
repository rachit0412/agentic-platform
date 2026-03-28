# Health Check Scripts

This directory contains utility scripts for managing and monitoring the Agentic Platform.

## Available Scripts

### health-check.sh
Comprehensive health check for all services.

**Usage:**
```bash
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

**Checks:**
- HTTP services (OpenWebUI, API, n8n, etc.)
- Backend services (PostgreSQL, Redis, Ollama)
- Ollama models installation
- Docker container status
- Disk usage

### Quick Health Check (one-liner)
```bash
curl -f http://localhost:8000/health && echo "✓ API is healthy"
```

## Common Tasks

### Start Everything
```bash
docker-compose up -d
```

### Stop Everything
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f [service-name]
```

### Restart Service
```bash
docker-compose restart [service-name]
```

## Troubleshooting

If services are unhealthy:

1. Check logs: `docker-compose logs -f [service-name]`
2. Check resources: `docker stats`
3. Restart: `docker-compose restart [service-name]`
4. Nuclear option: `docker-compose down && docker-compose up -d`
