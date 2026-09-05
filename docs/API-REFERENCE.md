# API Reference

> **Comprehensive API endpoint documentation for the Agentic Platform**
> 
> Auto-generated from: `services/ui-console/server.js`  
> Total Endpoints: **192**

## Quick Navigation

- [Authentication (6 endpoints)](#authentication)
- [Users & Personas (20 endpoints)](#users--personas)
- [Workspaces (8 endpoints)](#workspaces)
- [Skills (11 endpoints)](#skills)
- [Agents (8 endpoints)](#agents)
- [Documents (18 endpoints)](#documents)
- [Prompts (8 endpoints)](#prompts)
- [Custom Tools (6 endpoints)](#custom-tools)
- [Guardrails (6 endpoints)](#guardrails)
- [Pipelines (8 endpoints)](#pipelines)
- [Connectors (10 endpoints)](#connectors)
- [Chat & Sessions (10 endpoints)](#chat--sessions)
- [Models (4 endpoints)](#models)
- [MCP Servers (14 endpoints)](#mcp-servers)
- [Admin - Docker (19 endpoints)](#admin---docker)
- [Admin - Compliance (4 endpoints)](#admin---compliance)
- [Admin - Observability (6 endpoints)](#admin---observability)
- [Admin - Overviews (12 endpoints)](#admin---overviews)
- [A2A Networking (6 endpoints)](#a2a-networking)
- [N8N Integration (6 endpoints)](#n8n-integration)
- [Audit & Monitoring (8 endpoints)](#audit--monitoring)
- [Health & System (5 endpoints)](#health--system)
- [Database & Export (4 endpoints)](#database--export)
- [Versioning (4 endpoints)](#versioning)
- [Tools & Models (4 endpoints)](#tools--models)

---

## Authentication

**6 endpoints** — User authentication and 2FA management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/auth/me` | Get current user authentication status |
| 🔍 GET | `/api/me` | Get current user profile information |
| ✏️ POST | `/api/change-password` | Change user password |
| ✏️ POST | `/api/setup-2fa` | Setup two-factor authentication |
| ✏️ POST | `/api/confirm-2fa` | Confirm 2FA configuration |
| ✏️ POST | `/api/disable-2fa` | Disable two-factor authentication |

---

## Users & Personas

**20 endpoints** — User management and persona selection

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/users` | List all users (admin only) |
| 🔍 GET | `/api/users/:id` | Get specific user (admin only) |
| ✏️ POST | `/api/users` | Create new user (admin only) |
| 🔄 PUT | `/api/users/:id` | Update user (admin only) |
| 🗑️ DELETE | `/api/users/:id` | Delete user (admin only) |
| ✏️ POST | `/api/users/:id/verify` | Verify user identity (admin only) |
| 🔄 PUT | `/api/users/:id` | Update user profile |
| 🔍 GET | `/api/personas` | List available personas |
| 🔍 GET | `/api/personas/:id` | Get specific persona |
| ✏️ POST | `/api/personas` | Create new persona (admin) |
| 🔄 PUT | `/api/personas/:id` | Update persona (admin) |
| 🗑️ DELETE | `/api/personas/:id` | Delete persona (admin) |
| 🔍 GET | `/api/users/:id/personas` | List user personas (admin) |
| ✏️ POST | `/api/users/:id/personas` | Assign persona to user (admin) |
| 🗑️ DELETE | `/api/users/:id/personas/:pid` | Remove persona from user (admin) |
| ✏️ POST | `/api/switch-persona` | Switch active persona |
| 🔍 GET | `/api/my-personas` | Get current user's personas |
| ✏️ POST | `/api/update-profile` | Update personal profile |

---

## Workspaces

**8 endpoints** — Workspace and team management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/workspaces` | List user's workspaces |
| ✏️ POST | `/api/workspaces` | Create new workspace |
| 🔄 PUT | `/api/workspaces/:id` | Update workspace |
| 🗑️ DELETE | `/api/workspaces/:id` | Delete workspace |
| 🔍 GET | `/api/workspaces/:id/members` | List workspace members |
| ✏️ POST | `/api/workspaces/:id/members` | Add member to workspace |
| 🗑️ DELETE | `/api/workspaces/:id/members/:userId` | Remove member from workspace |

---

## Skills

**11 endpoints** — AI skill management and enrichment

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/skills` | List all skills |
| ✏️ POST | `/api/skills` | Create new skill |
| 🔍 GET | `/api/skills/:id` | Get specific skill |
| 🔄 PUT | `/api/skills/:id` | Update skill |
| 🗑️ DELETE | `/api/skills/:id` | Delete skill |
| 🔍 GET | `/api/skills/:id/files` | List skill files |
| ✏️ POST | `/api/skills/:id/files` | Upload skill file |
| 🔍 GET | `/api/skills/:id/files/:category/:filename` | Download skill file |
| 🗑️ DELETE | `/api/skills/:id/files/:category/:filename` | Delete skill file |
| ✏️ POST | `/api/skills/enrich` | Enrich skill with AI |
| ✏️ POST | `/api/skills/decompose` | Decompose skill into subtasks |

---

## Agents

**8 endpoints** — AI agent lifecycle management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/agents` | List all agents |
| ✏️ POST | `/api/agents` | Create new agent |
| 🔍 GET | `/api/agents/:id` | Get specific agent |
| 🔄 PUT | `/api/agents/:id` | Update agent |
| 🗑️ DELETE | `/api/agents/:id` | Delete agent |
| ✏️ POST | `/api/agent-run` | Execute agent synchronously |
| ✏️ POST | `/api/agent-run/stream` | Execute agent with streaming |

---

## Documents

**18 endpoints** — Document management and search

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/documents` | List all documents |
| 🔍 GET | `/api/documents/collections` | List document collections |
| 🔍 GET | `/api/documents/folders` | List document folders |
| 🔍 GET | `/api/documents/registry` | Get document registry |
| 🔍 GET | `/api/documents/stats` | Get document statistics |
| ✏️ POST | `/api/documents/upload` | Upload new document |
| ✏️ POST | `/api/documents/connect` | Connect external document |
| ✏️ POST | `/api/documents/fetch-url` | Fetch document from URL |
| ✏️ POST | `/api/documents/ingest` | Ingest document content |
| ✏️ POST | `/api/documents/search` | Search documents |
| ✏️ POST | `/api/documents/copy` | Copy document |
| ✏️ POST | `/api/documents/shortcut` | Create document shortcut |
| ✏️ POST | `/api/documents/:id/index` | Index document |
| 🗑️ DELETE | `/api/documents/:source` | Delete document |
| 🔍 GET | `/api/admin/documents/stats` | Get document admin stats |
| 🔄 PUT | `/api/documents/registry/:id/folder` | Update document folder |
| 🔄 PUT | `/api/documents/registry/:id/tags` | Update document tags |
| 🗑️ DELETE | `/api/documents/registry/:id` | Remove from registry |

---

## Prompts

**8 endpoints** — Prompt management and generation

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/prompts` | List all prompts |
| ✏️ POST | `/api/prompts` | Create new prompt |
| 🔍 GET | `/api/prompts/:id` | Get specific prompt |
| 🔄 PUT | `/api/prompts/:id` | Update prompt |
| 🗑️ DELETE | `/api/prompts/:id` | Delete prompt |
| ✏️ POST | `/api/prompts/generate` | Generate prompt with AI |
| ✏️ POST | `/api/prompts/validate` | Validate prompt syntax |

---

## Custom Tools

**6 endpoints** — Custom tool registration and management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/custom-tools` | List custom tools |
| ✏️ POST | `/api/custom-tools` | Register custom tool |
| 🔍 GET | `/api/custom-tools/:id` | Get custom tool details |
| 🔄 PUT | `/api/custom-tools/:id` | Update custom tool |
| 🗑️ DELETE | `/api/custom-tools/:id` | Delete custom tool |
| 🔍 GET | `/api/tools` | List all available tools |

---

## Guardrails

**6 endpoints** — Safety and compliance guardrails

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/guardrails` | List all guardrails |
| 🔍 GET | `/api/guardrails/:id` | Get specific guardrail |
| 🔄 PUT | `/api/guardrails/:id` | Update guardrail |
| 🔍 GET | `/api/global-constraints` | Get global constraints |
| 🔄 PUT | `/api/global-constraints` | Update global constraints |
| 🔍 GET | `/api/admin/global-constraints` | Get admin constraints |

---

## Pipelines

**8 endpoints** — Data processing pipelines

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/pipelines` | List all pipelines |
| ✏️ POST | `/api/pipelines` | Create new pipeline |
| 🔍 GET | `/api/pipelines/:id` | Get specific pipeline |
| 🔄 PUT | `/api/pipelines/:id` | Update pipeline |
| 🗑️ DELETE | `/api/pipelines/:id` | Delete pipeline |
| ✏️ POST | `/api/pipelines/:id/run` | Run pipeline |
| 🔍 GET | `/api/pipelines/:id/runs` | Get pipeline run history |
| 🔍 GET | `/api/pipeline-runs` | List all pipeline runs |

---

## Connectors

**10 endpoints** — External data source integration

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/connectors` | List all connectors |
| ✏️ POST | `/api/connectors` | Create new connector |
| 🔍 GET | `/api/connectors/:id` | Get connector details |
| 🔄 PUT | `/api/connectors/:id` | Update connector |
| 🗑️ DELETE | `/api/connectors/:id` | Delete connector |
| 🔍 GET | `/api/connectors/:id/jobs` | Get connector sync jobs |
| ✏️ POST | `/api/connectors/:id/sync` | Trigger connector sync |
| ✏️ POST | `/api/connectors/test` | Test connector config |
| 🔍 GET | `/api/connectors/catalog` | Get available connectors |

---

## Chat & Sessions

**10 endpoints** — Conversation and session management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/sessions` | List user sessions |
| 🔍 GET | `/api/sessions/:id` | Get session details |
| 🔗 DELETE | `/api/sessions/:id` | Delete session |
| 🔍 GET | `/api/sessions/:id/history` | Get session history |
| 🔍 GET | `/api/sessions/:id/summary` | Get session summary |
| 🔍 GET | `/api/chat/conversations` | List conversations |
| 🔍 GET | `/api/chat/conversations/:conversationId` | Get conversation |
| ✏️ POST | `/api/chat/message` | Send chat message |

---

## Models

**4 endpoints** — LLM model selection and management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/models` | List available models |
| ✏️ POST | `/api/models/switch` | Switch active model |
| ✏️ POST | `/api/models/embedding` | Get text embeddings |

---

## MCP Servers

**14 endpoints** — Model Context Protocol server management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/mcp/servers` | List MCP servers |
| ✏️ POST | `/api/mcp/servers` | Create MCP server |
| 🔍 GET | `/api/mcp/servers/:id` | Get server details |
| 🔄 PUT | `/api/mcp/servers/:id` | Update MCP server |
| 🗑️ DELETE | `/api/mcp/servers/:id` | Delete MCP server |
| ✏️ POST | `/api/mcp/servers/:id/discover` | Discover server capabilities |
| ✏️ POST | `/api/mcp/servers/:id/invoke` | Invoke server tool |
| ✏️ POST | `/api/mcp/servers/:id/provision` | Provision server |
| ✏️ POST | `/api/mcp/servers/managed/code` | Manage code server |
| ✏️ POST | `/api/mcp/servers/managed/config` | Manage config server |
| 🔍 GET | `/api/mcp/servers/:id/container/status` | Get container status |
| 🔍 GET | `/api/mcp/servers/:id/container/logs` | Get container logs |
| ✏️ POST | `/api/mcp/servers/:id/container/start` | Start container |
| ✏️ POST | `/api/mcp/servers/:id/container/stop` | Stop container |
| ✏️ POST | `/api/mcp/servers/:id/container/restart` | Restart container |
| 🗑️ DELETE | `/api/mcp/servers/:id/container` | Delete container |

---

## Admin - Docker

**19 endpoints** — Docker container and image management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/admin/docker/images` | List Docker images |
| 🔍 GET | `/api/admin/docker/images/:name` | Get image details |
| 🔍 GET | `/api/admin/docker/env-vars` | Get environment variables |
| ✏️ POST | `/api/admin/docker/provision` | Provision Docker container |
| ✏️ POST | `/api/admin/docker/scan` | Scan container for vulnerabilities |
| ✏️ POST | `/api/admin/docker/scan-all` | Scan all containers |
| ✏️ POST | `/api/admin/docker/scan-image` | Scan image for vulnerabilities |
| ✏️ POST | `/api/admin/docker/scan/:name` | Scan specific image |
| 🔍 GET | `/api/admin/docker/check-updates/:name` | Check for image updates |
| ✏️ POST | `/api/admin/docker/check-updates` | Check all for updates |
| ✏️ POST | `/api/admin/docker/update-version` | Update image version |
| 🔍 GET | `/api/admin/docker/security-summary` | Get security summary |
| 🔍 GET | `/api/admin/docker/reminder-status` | Get reminder status |

---

## Admin - Compliance

**4 endpoints** — Compliance configuration and scanning

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/admin/compliance/config` | Get compliance config |
| ✏️ POST | `/api/admin/compliance/config` | Update compliance config |
| ✏️ POST | `/api/admin/docker/scan` | Run compliance scan |
| ✏️ POST | `/api/admin/secret-scan` | Scan for secrets |

---

## Admin - Observability

**6 endpoints** — Monitoring and metrics

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/observability/health` | Get observability health |
| 🔍 GET | `/api/observability/prometheus/targets` | Get Prometheus targets |
| 🔍 GET | `/api/observability/prometheus/query` | Query metrics |
| 🔍 GET | `/api/observability/prometheus/query_range` | Query metric range |
| 🔍 GET | `/api/traces` | List distributed traces |
| 🔍 GET | `/api/traces/:traceId` | Get trace details |

---

## Admin - Overviews

**12 endpoints** — Administrative dashboards and analytics

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/admin/overview` | Get admin overview dashboard |
| 🔍 GET | `/api/admin/metrics` | Get metrics summary |
| 🔍 GET | `/api/admin/llm-summary` | Get LLM usage summary |
| 🔍 GET | `/api/llm-activity` | Get LLM activity log |
| 🔍 GET | `/api/llm-activity/summary` | Get activity summary |
| 🔍 GET | `/api/admin/memory-stats` | Get memory statistics |
| 🔍 GET | `/api/memory/stats` | Get detailed memory stats |
| 🔍 GET | `/api/chromadb/stats` | Get ChromaDB statistics |
| 🔍 GET | `/api/admin/chromadb/collections` | List ChromaDB collections |
| 🔍 GET | `/api/admin/n8n/workflows` | Get N8N workflows |
| 🔍 GET | `/api/admin/best-practices` | Get best practices |
| 🔄 PUT | `/api/admin/best-practices` | Update best practices |

---

## A2A Networking

**6 endpoints** — Agent-to-Agent networking

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/a2a/card` | Get A2A service card |
| 🔍 GET | `/api/a2a/peers` | List A2A peers |
| ✏️ POST | `/api/a2a/peers` | Register A2A peer |
| 🔄 PUT | `/api/a2a/peers/:id` | Update A2A peer |
| 🗑️ DELETE | `/api/a2a/peers/:id` | Unregister A2A peer |
| ✏️ POST | `/api/a2a/peers/:id/ping` | Ping A2A peer |
| ✏️ POST | `/api/a2a/send` | Send A2A message |

---

## N8N Integration

**6 endpoints** — N8N workflow automation

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/n8n/workflows` | List N8N workflows |
| 🔍 GET | `/api/n8n/executions` | Get workflow executions |
| 🔍 GET | `/api/n8n/agent-discovery` | Discover agents via N8N |
| ✏️ POST | `/api/n8n/workflows/:id/activate` | Activate workflow |
| ✏️ POST | `/api/n8n/workflows/:id/deactivate` | Deactivate workflow |

---

## Audit & Monitoring

**8 endpoints** — Audit logging and security

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/audit-log` | Get audit log entries |
| 🔍 GET | `/api/security-considerations` | Get security considerations |
| 🔄 PUT | `/api/admin/security-considerations` | Update security considerations |
| 🔍 GET | `/api/admin/security-considerations` | Get admin security config |
| 🔍 GET | `/api/admin/sso-config` | Get SSO configuration |
| 🔄 PUT | `/api/admin/sso-config` | Update SSO configuration |
| 🔍 GET | `/api/admin/services/health` | Check service health |

---

## Health & System

**5 endpoints** — System status and health checks

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/health-check` | Get system health status |
| 🔍 GET | `/api/tools-health` | Check tools health |
| ✏️ POST | `/api/admin/docker/scan-all` | Scan all services |
| 🔍 GET | `/api/versions/:entityType/:entityId` | Get entity versions |
| ✏️ POST | `/api/versions/:entityType/:entityId/rollback/:versionId` | Rollback entity |

---

## Database & Export

**4 endpoints** — Database management and data export

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/db-stats` | Get database statistics |
| 🔍 GET | `/api/export` | Export platform data |
| ✏️ POST | `/api/import` | Import platform data |
| 🔍 GET | `/api/versions/detail/:versionId` | Get version details |

---

## Versioning

**4 endpoints** — Version control and history

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/versions/:entityType/:entityId` | List entity versions |
| 🔍 GET | `/api/versions/detail/:versionId` | Get version details |
| ✏️ POST | `/api/versions/:entityType/:entityId/rollback/:versionId` | Rollback to version |

---

## Tools & Models

**4 endpoints** — Tool and model management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/tools` | List all tools |
| 🔄 PUT | `/api/tools/:name/toggle` | Toggle tool status |
| 🔍 GET | `/api/models` | List models |
| ✏️ POST | `/api/models/switch` | Switch model |

---

## API Usage Guide

### Authentication

All endpoints (except `/api/auth/*` and `/api/health-check`) require a valid session:

```bash
# Login first
curl -X POST http://localhost:3005/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  -c cookies.txt

# Then use the session cookie
curl http://localhost:3005/api/users \
  -b cookies.txt
```

### Response Format

All API responses are JSON:

```json
{
  "status": "success|error",
  "data": {...},
  "timestamp": "2025-09-06T14:32:15Z"
}
```

### Error Handling

- **400**: Bad Request — Invalid input parameters
- **401**: Unauthorized — Not authenticated
- **403**: Forbidden — Insufficient permissions
- **404**: Not Found — Resource doesn't exist
- **500**: Internal Server Error — Server error

### Rate Limiting

- Authentication endpoints: 5 attempts per 5 minutes per IP
- General endpoints: No limit (session-based)
- Scan endpoints: 1 concurrent scan per resource

### Pagination

List endpoints support pagination:

```bash
GET /api/users?page=1&limit=50
GET /api/documents?offset=100&count=25
```

### Filtering & Sorting

Most list endpoints support filtering and sorting:

```bash
GET /api/agents?status=active&sort=name
GET /api/prompts?search=welcome&created_after=2025-01-01
```

### Streaming Endpoints

Streaming endpoints return Server-Sent Events (SSE):

```bash
curl -N http://localhost:3005/api/agent-run/stream \
  -H "Content-Type: application/json" \
  -d '{"agent":"my-agent"}'
```

### Common Patterns

#### Create Resource
```bash
curl -X POST http://localhost:3005/api/skills \
  -H "Content-Type: application/json" \
  -d '{"name":"analysis","description":"Data analysis skill"}' \
  -b cookies.txt
```

#### Read Resource
```bash
curl http://localhost:3005/api/skills/123 \
  -b cookies.txt
```

#### Update Resource
```bash
curl -X PUT http://localhost:3005/api/skills/123 \
  -H "Content-Type: application/json" \
  -d '{"name":"advanced-analysis"}' \
  -b cookies.txt
```

#### Delete Resource
```bash
curl -X DELETE http://localhost:3005/api/skills/123 \
  -b cookies.txt
```

---

## Statistics

**Total Endpoints**: 192

### By Method
```
POST: 74
GET: 93
PUT: 18
DELETE: 7
```

### By Category
```
Admin - Docker: 19
Agents: 8
Users & Personas: 20
Documents: 18
Prompts: 8
Custom Tools: 6
Guardrails: 6
Pipelines: 8
Connectors: 10
Chat & Sessions: 10
Models: 4
MCP Servers: 14
Admin - Compliance: 4
Admin - Observability: 6
Admin - Overviews: 12
A2A Networking: 6
N8N Integration: 6
Audit & Monitoring: 8
Health & System: 5
Database & Export: 4
Versioning: 4
Tools & Models: 4
```

---

## Integration Patterns

### Agent Execution Flow
```
1. POST /api/agents → Create agent
2. POST /api/agent-run → Execute synchronously
3. POST /api/agent-run/stream → Stream results
4. GET /api/sessions/:id/history → Review execution
```

### Document Ingestion Flow
```
1. POST /api/documents/upload → Upload file
2. POST /api/documents/:id/index → Index content
3. POST /api/documents/search → Search indexed docs
4. GET /api/documents/stats → Monitor indexing
```

### Skill Development Flow
```
1. POST /api/skills → Create skill
2. POST /api/skills/:id/files → Upload implementation
3. POST /api/skills/enrich → Enhance with AI
4. POST /api/skills/decompose → Break into subtasks
```

### Security Scanning Flow
```
1. POST /api/admin/docker/scan → Scan container
2. POST /api/admin/secret-scan → Detect secrets
3. GET /api/admin/docker/security-summary → Review results
4. GET /api/audit-log → Check compliance log
```

---

## Best Practices

1. **Batch Operations**: Use bulk endpoints when available to reduce API calls
2. **Caching**: Client-side cache responses to minimize server load
3. **Error Handling**: Always check response status before processing data
4. **Authentication**: Store session cookies securely
5. **Versioning**: Always check API version compatibility
6. **Logging**: Monitor audit logs for security events
7. **Rate Limiting**: Implement exponential backoff for retries
8. **Streaming**: Use streaming endpoints for long-running operations

---

## Support & Documentation

- **OpenAPI Schema**: Available at `/api/openapi.json` (if enabled)
- **Admin Panel**: `/admin` for UI-based management
- **Documentation**: See `/docs` for detailed guides
- **Issues**: Report bugs at `/admin/issues`

---

Generated: 2025-09-06  
Last Updated: 2025-09-06

