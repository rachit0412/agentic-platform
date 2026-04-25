---
name: project-documentation
description: Generate update project documentation README API docs architecture diagrams changelog contributing guidelines technical writing
argument-hint: "[readme|api|architecture|changelog|all] - generate or update project documentation"
---

# Project Documentation

Generate and maintain comprehensive project documentation for the Agentic Platform.

## When to Use

- After adding new services, endpoints, or features
- When preparing a release or milestone
- During onboarding to generate up-to-date docs
- When existing documentation is stale or incomplete
- Before open-sourcing or sharing the project externally

## Procedure

### 1. Update README.md

Ensure `README.md` contains all required sections:

```markdown
# Project Name

![CI](badge-url) ![License](badge-url)

> One-line description

## Architecture
- High-level architecture diagram or description
- Service interaction overview

## Quick Start
- Prerequisites (Docker, Node.js, Python versions)
- Clone + `docker-compose up -d`
- Access URLs (UI, API, n8n, Grafana, Langfuse)

## Services
| Service | Port | Description |
|---------|------|-------------|
| ui-console | 3000 | Platform dashboard |
| agent-service | 8010 | LangGraph AI agent |
| tools-service | 8011 | Utility tools API |
| n8n | 5678 | Workflow orchestrator |
| ollama | 11436 | Local LLM runtime |
| chromadb | 8200 | Vector database |
| langfuse | 3002 | LLM observability |
| grafana | 3003 | Metrics dashboards |
| prometheus | 9090 | Metrics collection |
| loki | 3100 | Log aggregation |

## Configuration
- Environment variables reference
- `.env` file template

## Testing
- How to run unit/integration/e2e tests
- Test coverage expectations

## Contributing
- Link to CONTRIBUTING.md

## License
- License type and link
```

### 2. Document API Endpoints

For each service (`agent-service`, `tools-service`), document:

#### Agent Service (FastAPI)
Read `services/agent/main.py` and extract:
- `GET /health` — Health check
- `POST /chat` — Send message to agent
- `POST /ingest` — Ingest document to vector store
- `GET /search` — Search vector store
- `GET /memory` — Get conversation memory

#### Tools Service (FastAPI)
Read `services/tools/main.py` and extract:
- `GET /health` — Health check
- All tool endpoints with request/response schemas

#### UI Console (Express.js)
Read `services/ui-console/server.js` and document:
- Page routes (`/`, `/run-agent`, `/documents`, etc.)
- API proxy routes (`/api/*`)

### 3. Document Architecture

Create or update `docs/architecture.md` with:

- **System diagram**: Services and their connections
- **Data flow**: How a user query flows through the system
- **Technology stack**: Each service's tech choices
- **Network**: Docker network topology (`platform-net`)
- **Observability pipeline**: Metrics → OTel → Prometheus → Grafana

### 4. Generate CHANGELOG

Scan git log and generate `CHANGELOG.md`:

```bash
git log --oneline --no-merges --format="- %s (%h)" > CHANGELOG.md
```

Group by category:
- **Features** — `feat:` commits
- **Bug Fixes** — `fix:` commits
- **Documentation** — `docs:` commits
- **Infrastructure** — `chore:`, `ci:` commits

### 5. Verify Documentation Completeness

Check every service directory has:
- `README.md` or is documented in the root README
- API endpoints are documented
- Environment variables are listed
- Dockerfile build instructions are noted

### 6. Validate Links and References

- Ensure all internal links in markdown files resolve
- Verify port numbers match `docker-compose.yml`
- Confirm environment variable names match actual usage
- Check that code examples are runnable

### 7. Generate Documentation Report

Output:

| Document | Status | Last Updated | Action Needed |
|----------|--------|--------------|---------------|
| README.md | CURRENT/STALE | date | Details |
| CONTRIBUTING.md | CURRENT/STALE | date | Details |
| INSTALL.md | CURRENT/STALE | date | Details |
| docs/architecture.md | EXISTS/MISSING | date | Details |
| CHANGELOG.md | EXISTS/MISSING | date | Details |
| API Documentation | COMPLETE/PARTIAL | date | Details |
