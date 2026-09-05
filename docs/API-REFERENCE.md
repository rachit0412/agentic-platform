# API Reference

> **Comprehensive API endpoint documentation for the Agentic Platform**
> 
> Auto-generated from: `services/ui-console/server.js`  
> Total Endpoints: **192**  
> Last Updated: 2025-09-06

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

**6 endpoints** — User authentication and two-factor authentication (2FA) management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/auth/me` | Retrieve current authenticated user's session status and basic profile info (username, role, workspace). Returns 401 if not authenticated. |
| 🔍 GET | `/api/me` | Get complete current user profile including email, 2FA status, role, and account metadata. Requires active session. |
| ✏️ POST | `/api/change-password` | Update user password. Validates old password before accepting new one. Invalidates existing sessions. Body: `{oldPassword, newPassword}`. |
| ✏️ POST | `/api/setup-2fa` | Initiate 2FA setup, returns QR code and backup codes. User must confirm with `/api/confirm-2fa` to activate. |
| ✏️ POST | `/api/confirm-2fa` | Verify 2FA setup by providing TOTP code from authenticator app. Enables 2FA for account. Body: `{code}`. |
| ✏️ POST | `/api/disable-2fa` | Disable 2FA protection on account. Requires password verification. Body: `{password}`. |

---

## Users & Personas

**20 endpoints** — User account management and AI persona/role assignment

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/users` | List all platform users. Admin-only. Returns paginated list with user metadata. Query params: `?page=1&limit=50`. |
| 🔍 GET | `/api/users/:id` | Fetch specific user's complete profile including created_at, last_login, roles, and workspace associations. Admin-only. |
| ✏️ POST | `/api/users` | Create new user account. Admin-only. Body: `{username, email, password, role}`. Returns 400 if username already exists. |
| 🔄 PUT | `/api/users/:id` | Update user profile (email, display_name, avatar). Regular users can only edit their own profile. Admins can edit anyone. |
| 🗑️ DELETE | `/api/users/:id` | Delete user account and all associated data. Admin-only. Prevents deletion of last admin user (403 Forbidden). |
| ✏️ POST | `/api/users/:id/verify` | Manually verify user email address. Admin-only. Marks email_verified=true. |
| 🔍 GET | `/api/personas` | List all available AI personas in platform. Public personas visible to all, private personas only to owner/admins. |
| 🔍 GET | `/api/personas/:id` | Get specific persona definition including system prompt, personality traits, and capability constraints. |
| ✏️ POST | `/api/personas` | Create new AI persona. Admin-only. Body: `{name, description, system_prompt, capabilities, constraints}`. |
| 🔄 PUT | `/api/personas/:id` | Update persona configuration. Admin-only. Can modify all persona attributes. |
| 🗑️ DELETE | `/api/personas/:id` | Remove persona from platform. Admin-only. Cannot delete personas with active users. |
| 🔍 GET | `/api/users/:id/personas` | List personas assigned to specific user. Admin-only. Shows user's personalization scope. |
| ✏️ POST | `/api/users/:id/personas` | Assign persona to user, allowing them to switch into that persona context. Admin-only. |
| 🗑️ DELETE | `/api/users/:id/personas/:pid` | Remove persona from user's available list. Admin-only. |
| ✏️ POST | `/api/switch-persona` | Switch current session to use different persona. Client provides new persona_id. Affects agent execution context. |
| 🔍 GET | `/api/my-personas` | Get personas available to current user. Shows all assigned personas they can switch between. |
| ✏️ POST | `/api/update-profile` | Update own user profile (name, avatar, preferences). Cannot edit email or role (use `/api/users/:id` instead). |

---

## Workspaces

**8 endpoints** — Team workspace and member management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/workspaces` | List all workspaces current user is member of. Returns workspace metadata and member count. |
| ✏️ POST | `/api/workspaces` | Create new workspace. Creator becomes owner. Body: `{name, description, icon}`. Workspace isolated for data scoping. |
| 🔄 PUT | `/api/workspaces/:id` | Update workspace settings (name, description, permissions). Owner-only. |
| 🗑️ DELETE | `/api/workspaces/:id` | Remove workspace and cascade-delete all associated data (agents, skills, documents). Owner-only. |
| 🔍 GET | `/api/workspaces/:id/members` | List all members in workspace with their roles and permissions. |
| ✏️ POST | `/api/workspaces/:id/members` | Invite user to workspace with specified role (owner/editor/viewer). Owner-only. Body: `{userId, role}`. |
| 🗑️ DELETE | `/api/workspaces/:id/members/:userId` | Remove member from workspace. Owner-only. Cannot remove last owner. |

---

## Skills

**11 endpoints** — AI skill (reusable capability) lifecycle and file management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/skills` | List all skills accessible to current user. Returns skill metadata with version and last_modified timestamp. |
| ✏️ POST | `/api/skills` | Create new skill definition. Body: `{name, description, category, language, parameters}`. Skill empty until files uploaded. |
| 🔍 GET | `/api/skills/:id` | Get skill details including implementation files, version history, and usage statistics. |
| 🔄 PUT | `/api/skills/:id` | Update skill metadata or parameters. Cannot modify after deployment without version bump. |
| 🗑️ DELETE | `/api/skills/:id` | Remove skill and all versions. Returns 409 Conflict if skill actively used by agents. |
| 🔍 GET | `/api/skills/:id/files` | List all implementation files (source code, configs) for skill. Organized by file category. |
| ✏️ POST | `/api/skills/:id/files` | Upload skill implementation file (Python, JavaScript, config YAML). Category: code/config/test. |
| 🔍 GET | `/api/skills/:id/files/:category/:filename` | Download specific skill file content (raw binary or text). |
| 🗑️ DELETE | `/api/skills/:id/files/:category/:filename` | Remove skill file. Regenerate latest version. |
| ✏️ POST | `/api/skills/enrich` | AI-powered skill enhancement. Analyzes existing skill and suggests improvements. Body: `{skillId, aspect: 'performance'|'security'|'documentation'}`. |
| ✏️ POST | `/api/skills/decompose` | Break complex skill into smaller sub-skills. AI suggests decomposition. Body: `{skillId}`. |

---

## Agents

**8 endpoints** — AI agent creation, execution, and lifecycle management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/agents` | List all agents accessible to current user. Returns agent status, LLM model, and last execution time. |
| ✏️ POST | `/api/agents` | Create new agent. Body: `{name, description, model, skills, guardrails, system_prompt}`. Agent starts in draft status. |
| 🔍 GET | `/api/agents/:id` | Get complete agent definition including skills, tools, memory settings, and execution history. |
| 🔄 PUT | `/api/agents/:id` | Update agent configuration. Can modify skills, model, guardrails without re-creating. Version created on save. |
| 🗑️ DELETE | `/api/agents/:id` | Remove agent and cascade-delete associated conversations/sessions. Cannot delete published agents. |
| ✏️ POST | `/api/agent-run` | Execute agent synchronously (blocking). Body: `{agentId, input, context}`. Waits for completion, returns full output. Use for short tasks. |
| ✏️ POST | `/api/agent-run/stream` | Execute agent with streaming response. Connects via Server-Sent Events. Returns token-by-token output. Use for long-running tasks. |

---

## Documents

**18 endpoints** — Knowledge base document ingestion, indexing, search, and organization

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/documents` | List all documents in workspace. Returns doc metadata, type (pdf/docx/txt/url), and indexing status. |
| 🔍 GET | `/api/documents/collections` | List document collections (folders/projects) for organizing knowledge. |
| 🔍 GET | `/api/documents/folders` | Get folder hierarchy and document counts. |
| 🔍 GET | `/api/documents/registry` | List registered documents with deduplication metadata. Prevents duplicate ingestion. |
| 🔍 GET | `/api/documents/stats` | Get indexing statistics: total docs, vectors indexed, storage used, last indexed. |
| ✏️ POST | `/api/documents/upload` | Upload document file (PDF, DOCX, TXT, Markdown). Returns document ID and ingest status. Form: `multipart/form-data` with file. |
| ✏️ POST | `/api/documents/connect` | Connect external data source (S3, Google Drive, Confluence). Body: `{sourceType, credentials, path}`. |
| ✏️ POST | `/api/documents/fetch-url` | Fetch and ingest document from URL (web page, PDF link). Body: `{url, format}`. Follows redirects. |
| ✏️ POST | `/api/documents/ingest` | Process uploaded document: parse content, extract text, chunk into vectors. Can take 30+ seconds for large docs. |
| ✏️ POST | `/api/documents/search` | Semantic search across indexed documents. Body: `{query, limit: 10, threshold: 0.7}`. Returns matching chunks with relevance scores. |
| ✏️ POST | `/api/documents/copy` | Duplicate document and metadata. Returns new document ID. |
| ✏️ POST | `/api/documents/shortcut` | Create alias/symlink to document in another collection. |
| ✏️ POST | `/api/documents/:id/index` | Manually trigger re-indexing for document. Force-refreshes vector embeddings. |
| 🗑️ DELETE | `/api/documents/:source` | Delete document by source identifier. Cascade-deletes from index. |
| 🔍 GET | `/api/admin/documents/stats` | Admin view of document statistics across all workspaces. |
| 🔄 PUT | `/api/documents/registry/:id/folder` | Move document to different folder/collection. |
| 🔄 PUT | `/api/documents/registry/:id/tags` | Add/update document tags for filtering and organization. |
| 🗑️ DELETE | `/api/documents/registry/:id` | Remove document from registry (soft-delete). Can be restored. |

---

## Prompts

**8 endpoints** — Prompt template creation, generation, and validation

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/prompts` | List all prompt templates. Returns prompt metadata and usage statistics. |
| ✏️ POST | `/api/prompts` | Create prompt template. Body: `{name, category, template, variables, output_format}`. Template can include `{{variable}}` placeholders. |
| 🔍 GET | `/api/prompts/:id` | Get prompt template including edit history and performance metrics. |
| 🔄 PUT | `/api/prompts/:id` | Update prompt template. Tracks version history automatically. |
| 🗑️ DELETE | `/api/prompts/:id` | Delete prompt template. Cannot delete if used by active agents. |
| ✏️ POST | `/api/prompts/generate` | AI-powered prompt generation. Generates optimal prompt based on task description. Body: `{task, constraints, examples}`. |
| ✏️ POST | `/api/prompts/validate` | Test prompt with sample inputs. Returns execution time and output quality metrics. |

---

## Custom Tools

**6 endpoints** — Register and manage custom tool integrations

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/custom-tools` | List all custom tools registered in platform. Shows tool availability and documentation. |
| ✏️ POST | `/api/custom-tools` | Register new custom tool. Body: `{name, description, schema, endpoint, auth_type}`. Tools become available to agents immediately. |
| 🔍 GET | `/api/custom-tools/:id` | Get tool definition including parameters, return schema, and integration status. |
| 🔄 PUT | `/api/custom-tools/:id` | Update tool configuration or schema. Changes effective immediately. |
| 🗑️ DELETE | `/api/custom-tools/:id` | Unregister custom tool. Cannot delete if agents actively using it. |
| 🔍 GET | `/api/tools` | List all available tools (built-in + custom). Returns combined tool catalog. |

---

## Guardrails

**6 endpoints** — Safety and compliance policy management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/guardrails` | List all active guardrails/policies. Returns policy type (input validation, output filtering, compliance). |
| 🔍 GET | `/api/guardrails/:id` | Get guardrail details including rules, actions on violation, and audit log. |
| 🔄 PUT | `/api/guardrails/:id` | Update guardrail configuration. Can enable/disable rules or adjust thresholds. |
| 🔍 GET | `/api/global-constraints` | Get global constraints (rate limits, token budgets, timeout policies) applied to all agents. |
| 🔄 PUT | `/api/global-constraints` | Update global constraints. Changes apply to all future agent runs. |
| 🔍 GET | `/api/admin/global-constraints` | Admin-only view of all constraint configurations and overrides. |

---

## Pipelines

**8 endpoints** — Data processing and orchestration pipelines

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/pipelines` | List all data pipelines. Shows status (active/paused/failed), next run time, and execution history. |
| ✏️ POST | `/api/pipelines` | Create new pipeline. Body: `{name, steps, schedule, error_handling}`. Steps are DAG-connected. |
| 🔍 GET | `/api/pipelines/:id` | Get pipeline definition including all steps, connections, and configuration. |
| 🔄 PUT | `/api/pipelines/:id` | Update pipeline configuration. Changes take effect on next scheduled run. |
| 🗑️ DELETE | `/api/pipelines/:id` | Delete pipeline. Cannot delete if currently running (423 Locked). |
| ✏️ POST | `/api/pipelines/:id/run` | Trigger immediate pipeline execution (ignoring schedule). Body: `{input_data}`. |
| 🔍 GET | `/api/pipelines/:id/runs` | Get execution history for pipeline. Returns past run status, duration, and result logs. |
| 🔍 GET | `/api/pipeline-runs` | List all pipeline runs across platform with execution status and duration. |

---

## Connectors

**10 endpoints** — Third-party data source integration and synchronization

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/connectors` | List all configured connectors. Shows status, last_sync, and next scheduled sync. |
| ✏️ POST | `/api/connectors` | Create new connector to external data source. Body: `{type, name, credentials, config}`. Supports: Salesforce, HubSpot, Slack, GitHub, Jira, etc. |
| 🔍 GET | `/api/connectors/:id` | Get connector configuration and sync metadata. |
| 🔄 PUT | `/api/connectors/:id` | Update connector settings or credentials. |
| 🗑️ DELETE | `/api/connectors/:id` | Remove connector and stop syncs. |
| 🔍 GET | `/api/connectors/:id/jobs` | List all sync jobs for connector including failed syncs. |
| ✏️ POST | `/api/connectors/:id/sync` | Trigger immediate sync (ignoring schedule). Returns sync job ID. |
| ✏️ POST | `/api/connectors/test` | Test connector credentials before saving. Body: `{type, credentials}`. Returns validation result. |
| 🔍 GET | `/api/connectors/catalog` | Get list of available connector types and their required credentials. |

---

## Chat & Sessions

**10 endpoints** — Conversation and session management for multi-turn interactions

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/sessions` | List user's sessions (conversations with agents). Shows last_message_at and message_count. |
| 🔍 GET | `/api/sessions/:id` | Get session details including participant info and metadata. |
| 🗑️ DELETE | `/api/sessions/:id` | Delete entire session and message history. Cascade-deletes all associated data. |
| 🔍 GET | `/api/sessions/:id/history` | Get full message history for session (paginated). Messages ordered by timestamp. |
| 🔍 GET | `/api/sessions/:id/summary` | Get AI-generated summary of session conversation. Cached per session. |
| 🔍 GET | `/api/chat/conversations` | List all conversations accessible to user. Filtered by workspace/scope. |
| 🔍 GET | `/api/chat/conversations/:conversationId` | Get conversation metadata and participants. |
| ✏️ POST | `/api/chat/message` | Send message in conversation. Body: `{conversationId, content, attachments}`. Returns message ID and timestamp. |

---

## Models

**4 endpoints** — LLM model selection and text embedding

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/models` | List all available LLM models. Shows model name, provider (OpenAI, Anthropic, local), and pricing. |
| ✏️ POST | `/api/models/switch` | Switch active model for current session or globally. Body: `{modelId, scope: 'session'|'workspace'|'global'}`. |
| ✏️ POST | `/api/models/embedding` | Get text embeddings using configured embedding model. Body: `{texts: [string]}`. Returns vector arrays. |

---

## MCP Servers

**14 endpoints** — Model Context Protocol server management and container orchestration

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/mcp/servers` | List all MCP servers configured in platform. Shows container status and capability endpoints. |
| ✏️ POST | `/api/mcp/servers` | Register new MCP server. Body: `{name, endpoint, capabilities, auth}`. Can be local or remote. |
| 🔍 GET | `/api/mcp/servers/:id` | Get MCP server definition including capabilities and documentation. |
| 🔄 PUT | `/api/mcp/servers/:id` | Update server configuration or capabilities. |
| 🗑️ DELETE | `/api/mcp/servers/:id` | Unregister MCP server. Stops container if managed. |
| ✏️ POST | `/api/mcp/servers/:id/discover` | Auto-discover server capabilities by introspection. Updates capability list. |
| ✏️ POST | `/api/mcp/servers/:id/invoke` | Call tool/resource on MCP server. Body: `{tool, args}`. Proxies request and returns result. |
| ✏️ POST | `/api/mcp/servers/:id/provision` | Deploy/provision server container. Body: `{image, config}`. Creates Docker container if needed. |
| ✏️ POST | `/api/mcp/servers/managed/code` | Provision code execution server (runs agent code safely). |
| ✏️ POST | `/api/mcp/servers/managed/config` | Provision configuration server (provides structured configs). |
| 🔍 GET | `/api/mcp/servers/:id/container/status` | Check container health: running/stopped/error. |
| 🔍 GET | `/api/mcp/servers/:id/container/logs` | Stream container logs (stdout/stderr). Useful for debugging. |
| ✏️ POST | `/api/mcp/servers/:id/container/start` | Start stopped container. |
| ✏️ POST | `/api/mcp/servers/:id/container/stop` | Stop running container. |
| ✏️ POST | `/api/mcp/servers/:id/container/restart` | Restart container (stop + start). |
| 🗑️ DELETE | `/api/mcp/servers/:id/container` | Delete container and volumes. Unrecoverable. |

---

## Admin - Docker

**19 endpoints** — Container image and vulnerability management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/admin/docker/images` | List all Docker images available in platform. Shows size, layers, and scan status. |
| 🔍 GET | `/api/admin/docker/images/:name` | Get detailed image metadata including base layers and tag history. |
| 🔍 GET | `/api/admin/docker/env-vars` | Get environment variables configured for all Docker containers. |
| ✏️ POST | `/api/admin/docker/provision` | Provision new container from image. Body: `{image, name, env, ports, volumes}`. |
| ✏️ POST | `/api/admin/docker/scan` | Scan specific container for vulnerabilities (ClamAV, Trivy, etc.). Long-running operation. |
| ✏️ POST | `/api/admin/docker/scan-all` | Scan all containers in parallel. Queues jobs and returns job IDs. |
| ✏️ POST | `/api/admin/docker/scan-image` | Scan Docker image before deployment. Returns CVE list and remediation. |
| ✏️ POST | `/api/admin/docker/scan/:name` | Scan specific image by name. Returns security report. |
| 🔍 GET | `/api/admin/docker/check-updates/:name` | Check if newer version of image available. |
| ✏️ POST | `/api/admin/docker/check-updates` | Check for updates across all images. |
| ✏️ POST | `/api/admin/docker/update-version` | Upgrade image to newer version. Restarts containers. Body: `{image, newVersion}`. |
| 🔍 GET | `/api/admin/docker/security-summary` | Get security dashboard: scan count, vulnerabilities found, remediation status. |
| 🔍 GET | `/api/admin/docker/reminder-status` | Get pending security reminders and maintenance tasks. |

---

## Admin - Compliance

**4 endpoints** — Compliance configuration and scanning

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/admin/compliance/config` | Get compliance configuration: standards enabled (SOC2, ISO27001, HIPAA, GDPR). |
| ✏️ POST | `/api/admin/compliance/config` | Update compliance standards and policies. Body: `{standards: {soc2, iso27001, hipaa, gdpr}}`. |
| ✏️ POST | `/api/admin/docker/scan` | Run compliance scan on all systems. Checks against configured standards. |
| ✏️ POST | `/api/admin/secret-scan` | Scan codebase and containers for exposed secrets using GitLeaks. Returns findings. |

---

## Admin - Observability

**6 endpoints** — Monitoring metrics and distributed tracing

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/observability/health` | Get observability stack health: Prometheus, Grafana, Jaeger status. |
| 🔍 GET | `/api/observability/prometheus/targets` | List all Prometheus scrape targets and their health. |
| 🔍 GET | `/api/observability/prometheus/query` | Execute Prometheus query. Body: `{query: "up{job='api'}"}`. Returns time series data. |
| 🔍 GET | `/api/observability/prometheus/query_range` | Query Prometheus over time range. Body: `{query, start, end, step}`. |
| 🔍 GET | `/api/traces` | List distributed traces (Jaeger). Returns trace IDs and metadata. |
| 🔍 GET | `/api/traces/:traceId` | Get detailed trace including all spans and timing. |

---

## Admin - Overviews

**12 endpoints** — Administrative dashboards and analytics

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/admin/overview` | Admin dashboard summary: user count, agent count, token usage, system health. |
| 🔍 GET | `/api/admin/metrics` | Get key metrics: requests/sec, latency p50/p95/p99, error rate. |
| 🔍 GET | `/api/admin/llm-summary` | LLM usage summary: tokens consumed, cost, by model, by user. |
| 🔍 GET | `/api/llm-activity` | Activity log of all LLM API calls including input tokens, output tokens, cost. |
| 🔍 GET | `/api/llm-activity/summary` | Summary of LLM activity: total spend, daily average, model breakdown. |
| 🔍 GET | `/api/admin/memory-stats` | Get memory usage: RSS, heap, external, buffer. Useful for identifying leaks. |
| 🔍 GET | `/api/memory/stats` | Detailed memory statistics and allocation breakdown. |
| 🔍 GET | `/api/chromadb/stats` | ChromaDB vector store statistics: collections, vectors indexed, storage used. |
| 🔍 GET | `/api/admin/chromadb/collections` | List ChromaDB collections and their metadata. |
| 🔍 GET | `/api/admin/n8n/workflows` | List n8n workflows and their execution status. |
| 🔍 GET | `/api/admin/best-practices` | Get security and architecture best practices. |
| 🔄 PUT | `/api/admin/best-practices` | Update best practices documentation. |

---

## A2A Networking

**6 endpoints** — Agent-to-Agent networking and discovery

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/a2a/card` | Get this agent's A2A service card: endpoints, capabilities, auth requirements. |
| 🔍 GET | `/api/a2a/peers` | List all discovered A2A peers in network. Shows status and capabilities. |
| ✏️ POST | `/api/a2a/peers` | Register new A2A peer. Body: `{name, endpoint, card}`. Makes peer discoverable. |
| 🔄 PUT | `/api/a2a/peers/:id` | Update peer registration. |
| 🗑️ DELETE | `/api/a2a/peers/:id` | Unregister A2A peer. |
| ✏️ POST | `/api/a2a/peers/:id/ping` | Check peer health and connectivity. Returns latency. |
| ✏️ POST | `/api/a2a/send` | Send message to A2A peer. Body: `{peerId, message, data}`. |

---

## N8N Integration

**6 endpoints** — n8n workflow automation platform integration

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/n8n/workflows` | List n8n workflows accessible from platform. |
| 🔍 GET | `/api/n8n/executions` | Get n8n workflow execution history. |
| 🔍 GET | `/api/n8n/agent-discovery` | Discover agents available via n8n integration. |
| ✏️ POST | `/api/n8n/workflows/:id/activate` | Activate n8n workflow (enable execution). |
| ✏️ POST | `/api/n8n/workflows/:id/deactivate` | Deactivate n8n workflow (stop execution). |

---

## Audit & Monitoring

**8 endpoints** — Audit logging and security monitoring

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/audit-log` | Get audit log of all user actions: login, logout, resource modifications, deletions. Query params: `?type=login&action=create&limit=100`. |
| 🔍 GET | `/api/security-considerations` | Get current security assessment and recommendations. |
| 🔄 PUT | `/api/admin/security-considerations` | Update security configuration. |
| 🔍 GET | `/api/admin/security-considerations` | Admin view of all security configurations. |
| 🔍 GET | `/api/admin/sso-config` | Get SSO (Single Sign-On) configuration: provider, endpoints, mapping. |
| 🔄 PUT | `/api/admin/sso-config` | Update SSO settings. Body: `{provider, clientId, clientSecret, domain}`. |
| 🔍 GET | `/api/admin/services/health` | Check health of all platform services: database, cache, message queue, search. |

---

## Health & System

**5 endpoints** — System status and version management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/health-check` | Get system health status. Returns status: OK/Degraded/Down and component health. |
| 🔍 GET | `/api/tools-health` | Check health of all available tools (custom tools, integrations). |
| 🔍 GET | `/api/versions/:entityType/:entityId` | Get version history for entity (agent, skill, prompt). |
| 🔍 GET | `/api/versions/detail/:versionId` | Get detailed diff of specific version including changes made. |
| ✏️ POST | `/api/versions/:entityType/:entityId/rollback/:versionId` | Rollback entity to previous version. Restores configuration. |

---

## Database & Export

**4 endpoints** — Database management and data export/import

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/db-stats` | Get database statistics: table sizes, row counts, storage used. |
| 🔍 GET | `/api/export` | Export all platform data as JSON/CSV. Body: `{format, include: ['agents', 'skills', 'documents']}`. |
| ✏️ POST | `/api/import` | Import platform data from export file. Body: `multipart/form-data` with file. Validates format first. |

---

## Versioning

**4 endpoints** — Configuration and entity version control

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/versions/:entityType/:entityId` | Get all versions of entity with timestamps and author. |
| 🔍 GET | `/api/versions/detail/:versionId` | Get detailed change log for specific version. |
| ✏️ POST | `/api/versions/:entityType/:entityId/rollback/:versionId` | Restore entity to specific version. Creates new version record. |

---

## Tools & Models

**4 endpoints** — Tool and model catalog management

| Method | Path | Description |
|--------|------|-------------|
| 🔍 GET | `/api/tools` | Get complete tool catalog (built-in + custom). Includes all tool definitions. |
| 🔄 PUT | `/api/tools/:name/toggle` | Enable/disable tool globally. Body: `{enabled: true/false}`. |
| 🔍 GET | `/api/models` | List available LLM models with pricing and provider info. |
| ✏️ POST | `/api/models/switch` | Switch active model. Body: `{modelId, scope}`. |

---

## API Usage Guide

### Authentication

All endpoints except `/api/auth/*` and `/api/health-check` require active session:

```bash
curl -X POST http://localhost:3005/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  -c cookies.txt

curl http://localhost:3005/api/agents -b cookies.txt
```

### Response Format

```json
{
  "status": "success",
  "data": {...},
  "timestamp": "2025-09-06T14:32:15Z"
}
```

### Error Codes

- `400` — Bad Request (invalid parameters)
- `401` — Unauthorized (no valid session)
- `403` — Forbidden (insufficient permissions)
- `404` — Not Found (resource doesn't exist)
- `409` — Conflict (resource in use, can't delete)
- `423` — Locked (resource locked, try later)
- `500` — Internal Server Error

### Rate Limiting

- Auth endpoints: 5 attempts/5 min per IP
- General endpoints: No limit (session-based)
- Scan endpoints: 1 concurrent per resource

### Pagination

```bash
GET /api/users?page=1&limit=50
GET /api/documents?offset=100&count=25
```

### Filtering & Sorting

```bash
GET /api/agents?status=active&sort=name
GET /api/prompts?search=welcome&created_after=2025-01-01
```

---

Generated: 2025-09-06
