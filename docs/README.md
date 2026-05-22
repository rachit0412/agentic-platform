# Documentation

## Guides

| Document                              | Description                                     |
| ------------------------------------- | ----------------------------------------------- |
| [README](../README.md)                | Project overview, quick start, configuration    |
| [Architecture](ARCHITECTURE.md)       | System overview, data flows, services           |
| [Principles](PRINCIPLES.md)           | 18 architecture principles with maturity levels |
| [Building Blocks](BUILDING-BLOCKS.md) | 16 ABBs/SBBs with traceability                  |
| [Decisions](DECISIONS.md)             | 22 Architecture Decision Records                |
| [Installation](../INSTALL.md)         | Prerequisites, setup, GPU configuration         |
| [Contributing](../CONTRIBUTING.md)    | Code style, PR process, commit conventions      |

## Live API Docs

| Service       | URL                        | Description                       |
| ------------- | -------------------------- | --------------------------------- |
| Agent Service | http://localhost:8010/docs | FastAPI auto-docs (108 endpoints) |
| Tools Service | http://localhost:8011/docs | FastAPI auto-docs (33 endpoints)  |
| REST Console  | http://localhost:3000/rest | Interactive API testing UI        |

## API Quick Reference

### Agent Execution

```
POST /agent-run           # Run agent (blocking)
POST /agent-run/stream    # Run agent with SSE streaming
```

### CRUD Entities

| Entity       | Endpoints                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------- |
| Agents       | `GET/POST /agents`, `GET/PUT/DELETE /agents/{id}`                                                 |
| Skills       | `GET/POST /skills`, `GET/PUT/DELETE /skills/{id}`                                                 |
| Skill Files  | `POST /skills/{id}/files`, `GET /skills/{id}/files`, `GET/DELETE /skills/{id}/files/{cat}/{name}` |
| Prompts      | `GET/POST /prompts`, `GET/PUT/DELETE /prompts/{id}`                                               |
| Guardrails   | `GET/POST /guardrails`, `GET/PUT/DELETE /guardrails/{id}`                                         |
| Custom Tools | `GET/POST /custom-tools`, `GET/PUT/DELETE /custom-tools/{id}`                                     |

### Protocols

| Protocol | Endpoints                                                                               |
| -------- | --------------------------------------------------------------------------------------- |
| A2A      | `CRUD /a2a/peers`, `POST /a2a/send`, `GET /a2a/card`                                    |
| MCP      | `CRUD /mcp/servers`, `POST /mcp/servers/{id}/discover`, `POST /mcp/servers/{id}/invoke` |

### Knowledge Base

```
POST /documents/ingest    # Ingest text/URL/file
POST /documents/search    # Semantic search
GET  /documents           # List all documents
POST /documents/upload    # Upload file for RAG
```

### Platform Settings

```
GET  /security-considerations   # Read platform security considerations
PUT  /security-considerations   # Update security considerations (admin)
GET  /best-practices            # Read platform best practices
PUT  /best-practices            # Update best practices (admin)
```

### System

```
GET  /health              # Service health
GET  /models              # Available models + capabilities
POST /models/switch       # Change active model at runtime
GET  /export              # Export full platform config
POST /import              # Import platform config
GET  /audit-log           # Query audit trail
```
