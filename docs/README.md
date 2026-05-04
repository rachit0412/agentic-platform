# Documentation

## Guides

| Document                                          | Description                                              |
| ------------------------------------------------- | -------------------------------------------------------- |
| [README](../README.md)                            | Project overview, quick start, configuration             |
| [Architecture](ARCHITECTURE.md)                   | System overview, data flows, services, orchestration     |
| [Architecture Diagram](architecture-diagram.html) | Interactive visual system architecture (open in browser) |
| [Principles](PRINCIPLES.md)                       | 18 architecture principles guiding all design choices    |
| [Building Blocks](BUILDING-BLOCKS.md)             | 15 ABBs (abstract) and SBBs (solution) with traceability |
| [Decisions](DECISIONS.md)                         | 15 Architecture Decision Records (ADRs)                  |
| [Installation Guide](../INSTALL.md)               | Prerequisites, per-platform setup, GPU configuration     |
| [Contributing](../CONTRIBUTING.md)                | Code style, PR process, commit conventions               |

## Interactive API Console

The platform includes a built-in **REST Console** at **http://localhost:3000/rest** for interactively testing all 69 agent-service and 10 tools-service endpoints. Navigate to **Protocols → REST Console** in the dashboard.

## API Reference

Interactive API docs are available at **http://localhost:8010/docs** (agent-service) and **http://localhost:8011/docs** (tools-service) when the platform is running.

### Agent Service — `http://localhost:8010`

#### Agent Execution

| Method | Endpoint            | Description                  |
| ------ | ------------------- | ---------------------------- |
| POST   | `/agent-run`        | Run agent (blocking)         |
| POST   | `/agent-run/stream` | Run agent with SSE streaming |

#### Agent CRUD

| Method | Endpoint       | Description     |
| ------ | -------------- | --------------- |
| GET    | `/agents`      | List all agents |
| POST   | `/agents`      | Create agent    |
| GET    | `/agents/{id}` | Get agent by ID |
| PUT    | `/agents/{id}` | Update agent    |
| DELETE | `/agents/{id}` | Delete agent    |

**Agent fields:** `name`, `description`, `provider`, `model`, `temperature`, `top_p`, `system_prompt`, `skill_ids` (array), `tool_ids` (array), `sub_agent_ids` (array — for orchestration), `kb_collection`, `max_iterations`, `memory_enabled`

#### Skill CRUD

| Method | Endpoint       | Description     |
| ------ | -------------- | --------------- |
| GET    | `/skills`      | List all skills |
| POST   | `/skills`      | Create skill    |
| GET    | `/skills/{id}` | Get skill by ID |
| PUT    | `/skills/{id}` | Update skill    |
| DELETE | `/skills/{id}` | Delete skill    |

#### Prompt CRUD

| Method | Endpoint        | Description      |
| ------ | --------------- | ---------------- |
| GET    | `/prompts`      | List all prompts |
| POST   | `/prompts`      | Create prompt    |
| GET    | `/prompts/{id}` | Get prompt by ID |
| PUT    | `/prompts/{id}` | Update prompt    |
| DELETE | `/prompts/{id}` | Delete prompt    |

#### Tools

| Method | Endpoint             | Description            |
| ------ | -------------------- | ---------------------- |
| GET    | `/tools`             | List built-in + custom |
| GET    | `/custom-tools`      | List custom tools only |
| POST   | `/custom-tools`      | Create custom tool     |
| GET    | `/custom-tools/{id}` | Get custom tool        |
| PUT    | `/custom-tools/{id}` | Update custom tool     |
| DELETE | `/custom-tools/{id}` | Delete custom tool     |

#### A2A Protocol

| Method | Endpoint               | Description                     |
| ------ | ---------------------- | ------------------------------- |
| GET    | `/a2a/peers`           | List peer agents                |
| POST   | `/a2a/peers`           | Register peer agent             |
| GET    | `/a2a/peers/{id}`      | Get peer config                 |
| PUT    | `/a2a/peers/{id}`      | Update peer config              |
| DELETE | `/a2a/peers/{id}`      | Unregister peer                 |
| POST   | `/a2a/peers/{id}/ping` | Check peer health               |
| POST   | `/a2a/send`            | Send task to peer agent         |
| GET    | `/a2a/card`            | Get this agent's discovery card |

#### MCP Registry

| Method | Endpoint                     | Description                |
| ------ | ---------------------------- | -------------------------- |
| GET    | `/mcp/servers`               | List MCP servers           |
| POST   | `/mcp/servers`               | Register MCP server        |
| GET    | `/mcp/servers/{id}`          | Get MCP server config      |
| PUT    | `/mcp/servers/{id}`          | Update MCP server          |
| DELETE | `/mcp/servers/{id}`          | Unregister MCP server      |
| POST   | `/mcp/servers/{id}/discover` | Discover tools from server |
| POST   | `/mcp/servers/{id}/invoke`   | Invoke MCP tool            |

#### Sessions & Memory

| Method | Endpoint                 | Description           |
| ------ | ------------------------ | --------------------- |
| GET    | `/sessions`              | List all sessions     |
| GET    | `/sessions/{id}/history` | Get message history   |
| GET    | `/sessions/{id}/summary` | Get session summary   |
| DELETE | `/sessions/{id}`         | Delete session        |
| GET    | `/memory/stats`          | Get memory & KB stats |

#### Documents / RAG

| Method | Endpoint                          | Description                    |
| ------ | --------------------------------- | ------------------------------ |
| GET    | `/documents`                      | List documents by collection   |
| GET    | `/documents/stats`                | Get vector store stats         |
| GET    | `/documents/collections`          | List ChromaDB collections      |
| POST   | `/documents/ingest`               | Ingest text into vector store  |
| POST   | `/documents/search`               | Search documents by similarity |
| POST   | `/documents/fetch-url`            | Fetch & extract text from URL  |
| DELETE | `/documents/{source}`             | Delete document by source      |
| POST   | `/documents/copy`                 | Copy docs between collections  |
| GET    | `/documents/registry`             | List docs with filters         |
| GET    | `/documents/folders`              | List folder paths with counts  |
| PUT    | `/documents/registry/{id}/tags`   | Set agent tags for document    |
| PUT    | `/documents/registry/{id}/folder` | Move document to folder        |
| DELETE | `/documents/registry/{id}`        | Delete from registry           |

#### Guardrails

| Method | Endpoint           | Description               |
| ------ | ------------------ | ------------------------- |
| GET    | `/guardrails`      | List all guardrails       |
| GET    | `/guardrails/{id}` | Get guardrail config      |
| PUT    | `/guardrails/{id}` | Update guardrail settings |

#### Models

| Method | Endpoint         | Description                          |
| ------ | ---------------- | ------------------------------------ |
| GET    | `/models`        | List available models + active model |
| POST   | `/models/switch` | Switch active LLM provider/model     |

#### System

| Method | Endpoint    | Description              |
| ------ | ----------- | ------------------------ |
| GET    | `/health`   | Health check             |
| GET    | `/db-stats` | Database record counts   |
| GET    | `/export`   | Export all data as JSON  |
| POST   | `/import`   | Import/merge data backup |

#### Versions & Audit

| Method | Endpoint                                                    | Description            |
| ------ | ----------------------------------------------------------- | ---------------------- |
| GET    | `/versions/{entity_type}/{entity_id}`                       | List version history   |
| GET    | `/versions/detail/{version_id}`                             | Get version snapshot   |
| POST   | `/versions/{entity_type}/{entity_id}/rollback/{version_id}` | Rollback to version    |
| GET    | `/audit-log`                                                | List audit log entries |

### Tools Service — `http://localhost:8011`

| Method | Endpoint               | Description                                |
| ------ | ---------------------- | ------------------------------------------ |
| GET    | `/health`              | Health check                               |
| POST   | `/tools/math`          | Evaluate math expression (AST-based, safe) |
| POST   | `/tools/http-fetch`    | Fetch URL content (domain allowlist)       |
| POST   | `/tools/file-write`    | Write note to `/data/notes/`               |
| POST   | `/tools/file-read`     | Read note from `/data/notes/`              |
| POST   | `/tools/datetime`      | Get current UTC date/time                  |
| POST   | `/tools/web-search`    | Web search via DuckDuckGo                  |
| POST   | `/tools/code-execute`  | Execute Python code (sandboxed)            |
| POST   | `/tools/vector-search` | Search documents (proxy to agent-service)  |
| POST   | `/tools/vector-store`  | Ingest documents (proxy to agent-service)  |

## Service URLs

| Service        | URL                        | Credentials                |
| -------------- | -------------------------- | -------------------------- |
| UI Console     | http://localhost:3000      | —                          |
| REST Console   | http://localhost:3000/rest | —                          |
| Agent API Docs | http://localhost:8010/docs | —                          |
| Tools API Docs | http://localhost:8011/docs | —                          |
| n8n            | http://localhost:5678      | admin / changeme           |
| Langfuse       | http://localhost:3012      | admin@local.dev / changeme |
| Grafana        | http://localhost:3013      | admin / admin              |
| Prometheus     | http://localhost:9090      | —                          |
