# Architecture Principles

> Guiding principles for the Agentic Platform. Every design choice and ADR should trace back to one or more of these principles.
>
> **Validation status** is based on codebase audit (May 2026). Principles are categorised by **Enterprise Maturity Level**:
>
> | Level          | Meaning                                                            |
> | -------------- | ------------------------------------------------------------------ |
> | 🟢 **Current** | Principle is implemented and validated in the codebase today       |
> | 🟡 **Next**    | Foundations exist; targeted for the next development cycle         |
> | 🔴 **Target**  | Not yet implemented; required for production enterprise deployment |
>
> Principles AP-1 through AP-10 are **foundational** (platform architecture). Principles AP-11 through AP-18 are **enterprise** (production readiness).

---

## Enterprise Maturity Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TARGET STATE (Production)                        │
│  AP-11 Identity & Access    AP-14 Compliance & Governance               │
│  AP-13 Elastic Scaling      AP-16 Zero-Trust Networking                 │
│  AP-15 Disaster Recovery    AP-17 Agent Lifecycle Governance            │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                        NEXT STATE (Hardening)                           │
│  AP-1  API Versioning       AP-5  Always-On Telemetry                   │
│  AP-7  Full Service Split   AP-9  Complete Version Snapshots            │
│  AP-12 Cost & Metering      AP-18 Secret Management                    │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                        CURRENT STATE (Foundation)                       │
│  AP-2  Local-First ✅        AP-3  Container-Native ✅                   │
│  AP-4  Defence in Depth ✅   AP-6  Protocol Extensibility ✅             │
│  AP-8  Knowledge Mgmt ✅     AP-10 Graceful Degradation ✅               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AP-1 · API-First Design · 🟡 Next

| Attribute        | Detail                                                                                                                                                                                                                 |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | Every capability is exposed as a versioned REST API before any UI is built.                                                                                                                                            |
| **Rationale**    | APIs enable composability — agents, workflows, external systems, and the console all consume the same contract. It prevents the UI from becoming a monolith.                                                           |
| **Implications** | All agent, skill, prompt, tool, document, A2A, and MCP operations are proxied through `agent-service` REST endpoints. The UI console (`ui-console`) is a thin proxy layer — zero business logic lives in the frontend. |

| Validation                                  | Status                                                                                                                                                                 |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| APIs exposed for all capabilities           | **YES** — 69+ endpoints on agent-service, all capabilities have REST APIs                                                                                              |
| APIs are versioned                          | **NO** — All routes are unversioned (`/run`, `/agents`, `/skills`). FastAPI metadata shows `version="1.0.0"` but no `/v1/` prefix or version headers                   |
| UI is a thin proxy with zero business logic | **PARTIAL** — `server.js` is mostly a pure proxy layer. However, n8n auth logic (`n8nLogin()`, `n8nAutoSetup()`, `n8nFetchWithAuth()`) is business logic, not proxying |

### Future Vision

1. **API Versioning** — Add `/v1/` prefix to all agent-service routes using a FastAPI `APIRouter(prefix="/v1")`. This enables future breaking changes without disrupting existing clients.
2. **Extract n8n Auth** — Move n8n authentication logic out of `server.js` into a dedicated n8n-proxy service or middleware module to restore the zero-business-logic guarantee.

---

## AP-2 · Local-First, Cloud-Ready · 🟢 Current

| Attribute        | Detail                                                                                                                                                                                                            |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | The platform runs fully offline with local models via Ollama, but can switch to cloud LLM providers without code changes.                                                                                         |
| **Rationale**    | Developers need fast iteration without cloud costs or API keys. Enterprise deployments need Azure OpenAI, OpenAI, or Azure AI Foundry for production-grade inference.                                             |
| **Implications** | `LLM_PROVIDER` env var selects the active provider. `llm.py` abstracts all providers behind LangChain's `BaseChatModel` interface. Model switching is a runtime API call (`POST /models/switch`), not a redeploy. |

| Validation                              | Status                                                                                                                                                         |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Runs fully offline with Ollama          | **YES** — `LLM_PROVIDER` defaults to `ollama`. Cloud keys default to empty strings. No cloud dependency at startup                                             |
| Runtime model switching without restart | **YES** — `POST /models/switch` calls `set_active_model()` which rebuilds the LLM instance in-memory. Per-request agent config also supports per-run overrides |
| All 4 providers functional              | **YES** — Ollama, Azure OpenAI, OpenAI, Azure AI Foundry all implemented in `get_llm()`                                                                        |

**Status: FULLY MET** ✅

---

## AP-3 · Container-Native Composability · 🟢 Current

| Attribute        | Detail                                                                                                                                                                                                                  |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | Every service is a Docker container. The platform topology is defined entirely in `docker-compose.yml`.                                                                                                                 |
| **Rationale**    | Containers provide reproducible builds, isolated dependencies, and a clear service boundary. Compose enables one-command startup (`docker-compose up -d`) for the full 13-service stack.                                |
| **Implications** | Services communicate over a Docker bridge network using internal hostnames (`agent-service:8000`, `tools-service:8001`). Port mapping to the host is configurable via env vars. Health checks enforce startup ordering. |

| Validation                          | Status                                                                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| All 13 services containerised       | **YES** — All defined in `docker-compose.yml`                                                                                   |
| Health checks on critical services  | **YES** — ollama, chromadb, agent-service, tools-service, langfuse, langfuse-db, prometheus all have healthchecks               |
| `depends_on` with `service_healthy` | **YES** — agent-service waits for ollama, tools-service, chromadb. Grafana waits for prometheus. Langfuse waits for langfuse-db |
| Ports configurable via env vars     | **YES** — All ports use `${VAR:-default}` syntax                                                                                |

**Status: FULLY MET** ✅

---

## AP-4 · Defence in Depth · 🟢 Current

| Attribute        | Detail                                                                                                                                                                                                                                                                                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | Security is layered: input guardrails, tool sandboxing, output guardrails, and SSRF protection operate independently.                                                                                                                                                                                                                                         |
| **Rationale**    | LLM agents are attack surfaces for prompt injection, data exfiltration, and arbitrary code execution. No single layer can catch all threats.                                                                                                                                                                                                                  |
| **Implications** | The agent graph runs input guardrails (PII detection, prompt-injection detection, topic restriction) before LLM calls, and output guardrails (PII, data-leak, toxicity, length) after. Tool execution has its own sandboxing: code-execute blocks dangerous imports with a 10s timeout; HTTP-fetch uses URL whitelisting; file operations sanitize filenames. |

| Validation                       | Status                                                                                                                                    |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Input guardrails before LLM call | **YES** — `_check_guardrails_input()` runs in `reason()` node before LLM invocation. Can short-circuit the graph                          |
| Output guardrails after response | **YES** — `_check_guardrails_output()` runs in `generate_response()` after response is assembled                                          |
| HTTP fetch URL whitelist         | **YES** — `ALLOWED_DOMAINS = {"httpbin.org", "jsonplaceholder.typicode.com"}` in tools-service                                            |
| Code execution import blocking   | **YES** — `BLOCKED_PATTERNS` blocks `os`, `sys`, `subprocess`, `shutil`, `__import__`, `eval`, `exec`, `open`, `socket`, `http`, `urllib` |
| File I/O sanitisation            | **YES** — Filename sanitisation strips paths, allows only alphanumeric/dash/dot/space                                                     |

**Status: FULLY MET** ✅

---

## AP-5 · Observable by Default · 🟡 Next

| Attribute        | Detail                                                                                                                                                                                                                                                                                                                                                                     |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | Every agent run, LLM call, and tool invocation emits structured telemetry without requiring any application-level opt-in.                                                                                                                                                                                                                                                  |
| **Rationale**    | AI systems are non-deterministic. Observability is not optional — it is the only way to debug, evaluate, and audit agent behaviour in production.                                                                                                                                                                                                                          |
| **Implications** | Three telemetry pipelines run in parallel: (1) OpenTelemetry traces → OTel Collector → Prometheus metrics + Loki logs, (2) Langfuse SDK → Langfuse for LLM-specific traces with cost tracking, (3) Prometheus histograms and counters (`llm_call_duration_seconds`, `tool_calls_total`, `agent_runs_total`) exposed on `/metrics`. Grafana dashboards visualise all three. |

| Validation                                   | Status                                                                                                                                                                                                         |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Telemetry emitted without opt-in             | **NO** — Langfuse requires `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` env vars; falls back to no-op. OTel requires `OTEL_EXPORTER_OTLP_ENDPOINT`; disabled if unset. Telemetry is **opt-in**, not automatic |
| Prometheus metrics always registered         | **PARTIAL** — Metrics are defined (`llm_call_duration_seconds`, `tool_calls_total`, `agent_runs_total`) but fall back to `_NoOpMetric` if prometheus_client import fails                                       |
| Grafana dashboards cover all three pipelines | **NO** — `platform-health.json` has 13 panels but ALL use Prometheus datasource only. No Loki log panels. No Langfuse panels                                                                                   |

### Future Vision

1. **Always-On Prometheus Metrics** — Ensure `prometheus_client` is a hard dependency (already in requirements.txt). Remove the `_NoOpMetric` fallback. Metrics should always be recorded, even if no scraper is connected.
2. **Grafana Loki Panels** — Add log panels to `platform-health.json` using the existing Loki datasource. Minimum: agent-service logs, tools-service logs, error log stream.
3. **Grafana Langfuse Panel** — Add an iframe or link panel pointing to the Langfuse UI (`http://localhost:3012`) for LLM trace exploration.
4. **Default OTel** — Pre-configure `OTEL_EXPORTER_OTLP_ENDPOINT` in `docker-compose.yml` so tracing is on by default when the stack is running.
5. **Update Statement** — Reword from "without requiring any opt-in" to "with minimal configuration when the full stack is running" until the above steps are complete.

---

## AP-6 · Protocol-Driven Extensibility · 🟢 Current

| Attribute        | Detail                                                                                                                                                                                                                                                                                                                                                |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | The platform extends through open protocols (A2A, MCP) rather than tightly-coupled plugins.                                                                                                                                                                                                                                                           |
| **Rationale**    | Agent ecosystems are heterogeneous. Proprietary plugin APIs create lock-in. Open protocols enable any agent or tool server — regardless of language or framework — to participate.                                                                                                                                                                    |
| **Implications** | **A2A (Agent-to-Agent)**: Peer agents register by URL and expose agent cards describing capabilities; tasks are delegated via HTTP. **MCP (Model Context Protocol)**: External tool servers register in the MCP Registry; tools are auto-discovered and invoked on demand. Both protocols use JSON-over-HTTP with no framework-specific dependencies. |

| Validation              | Status                                                                                                                                                |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| A2A agent cards         | **YES** — `/.well-known/agent.json` returns a real card with capabilities (streaming, multi_turn, tool_use, rag), agent list, and tool list           |
| A2A peer ping/discovery | **YES** — `POST /a2a/peers/{id}/ping` fetches remote agent cards                                                                                      |
| MCP tool auto-discovery | **YES** — `POST /mcp/servers/{id}/discover` makes real HTTP calls to remote MCP servers using JSON-RPC 2.0 (`/tools/list`), with fallback to `/tools` |
| MCP tool invocation     | **YES** — `POST /mcp/servers/{id}/invoke` forwards calls to registered servers                                                                        |

**Status: FULLY MET** ✅

---

## AP-7 · Separation of Concerns · 🟡 Next

| Attribute        | Detail                                                                                                                                                                                                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | Agent reasoning, tool execution, UI rendering, and observability are isolated in separate services with clear contracts.                                                                                                                                                        |
| **Rationale**    | Co-locating LLM orchestration, business tools, and UI in one process creates deployment coupling, scaling bottlenecks, and testing complexity.                                                                                                                                  |
| **Implications** | `agent-service` owns reasoning and state. `tools-service` owns sandboxed tool execution. `ui-console` owns rendering. `otel-collector` owns telemetry routing. Each can be scaled, deployed, or replaced independently. The agent calls tools via HTTP, not in-process imports. |

| Validation                                | Status                                                                                                                                                                            |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent reasoning isolated in agent-service | **YES** — Graph, LLM, memory all in `services/agent/`                                                                                                                             |
| Tool execution isolated in tools-service  | **PARTIAL** — 7 proxy tools call tools-service via HTTP. However, `vector_search` and `vector_store` run **in-process** in agent-service, violating the stated HTTP-only contract |
| UI rendering isolated in ui-console       | **YES** — Express.js + EJS, thin proxy layer                                                                                                                                      |
| Telemetry routing in otel-collector       | **YES** — Dedicated container with its own config                                                                                                                                 |

### Future Vision

1. **Move Vector Tools to tools-service** — Migrate `vector_search` and `vector_store` from in-process execution in `tools.py` to HTTP endpoints on tools-service (similar to the existing `/tools/vector-search` and `/tools/vector-store` stubs that already exist). This restores the HTTP-only tool contract.
2. **Or Document the Exception** — If in-process vector tools are intentional for latency reasons (avoiding HTTP round-trip for RAG), explicitly document this as an accepted exception in ADR-003.

---

## AP-8 · Knowledge as a First-Class Resource · 🟢 Current

| Attribute        | Detail                                                                                                                                                                                                                                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Statement**    | Documents, embeddings, and retrieval are managed through dedicated APIs with full CRUD lifecycle, not embedded as static context.                                                                                                                                                                                        |
| **Rationale**    | RAG quality depends on knowledge freshness, organisation, and agent-specific relevance. Treating documents as first-class resources enables folder management, agent tagging, collection isolation, and cross-collection copying.                                                                                        |
| **Implications** | `vectorstore.py` manages ChromaDB collections. The document registry in SQLite tracks metadata, folders, and agent tags separately from embeddings. Documents can be ingested from text, URL, or file upload with configurable chunk size and overlap. Agents can be scoped to specific collections via `kb_collection`. |

| Validation                          | Status                                                                                                                                                              |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Full CRUD on documents              | **YES** — 13 document endpoints covering ingest, search, list, delete, copy, fetch-url                                                                              |
| Document registry with folders/tags | **YES** — SQLite `documents` table with folder, agent_tags, metadata fields                                                                                         |
| Agent-scoped collections            | **YES** — `agents` table has `kb_collection` column (auto-named `agent_{name}_kb`). `graph.py` passes `kb_coll` to `search_similar()` per agent run. Full isolation |
| Cross-collection copying            | **YES** — `POST /documents/copy` endpoint implemented in `vectorstore.py`                                                                                           |
| Per-agent KB isolation              | **YES** — Each agent gets a unique ChromaDB collection; documents uploaded for one agent are invisible to other agents' retrieval                                   |

**Status: FULLY MET** ✅

---

## AP-9 · Configuration over Code · 🟡 Next

| Attribute        | Detail                                                                                                                                                                                                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Statement**    | Agents, skills, prompts, guardrails, and tools are runtime-configurable data, not compiled code.                                                                                                                                                                                                 |
| **Rationale**    | Redeploying containers to change a system prompt or add a tool is too slow for experimentation. CRUD APIs enable the UI, CI/CD, and external scripts to manage agent configurations without touching source code.                                                                                |
| **Implications** | All entity definitions (agents, skills, prompts, guardrails, custom tools) are stored in SQLite with full CRUD endpoints. Changes take effect on the next agent run — no restart required. Import/export endpoints enable environment migration. Versioning and audit logs track every mutation. |

| Validation              | Status                                                                                                                               |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| CRUD for all entities   | **YES** — Agents, skills, prompts, guardrails, custom tools, A2A peers, MCP servers all have full CRUD                               |
| Changes without restart | **YES** — Agent config is loaded per-request from SQLite, not cached at startup                                                      |
| Import/export           | **YES** — `GET /export` and `POST /import` with merge mode                                                                           |
| Audit logging           | **YES** — `log_audit()` called on create/update/delete for skills, agents, prompts. Queryable via `GET /audit-log` with filters      |
| Version snapshots       | **PARTIAL** — `save_version()` implemented for skills, agents, prompts on update. Guardrails and custom tools do NOT have versioning |

### Future Vision

1. **Version Snapshots for Guardrails** — Add `save_version()` calls to `update_guardrail()` in `memory.py` to enable rollback of guardrail configuration changes.
2. **Version Snapshots for Custom Tools** — Add `save_version()` calls to custom tool update operations.

---

## AP-10 · Graceful Degradation · 🟢 Current

| Attribute        | Detail                                                                                                                                                                                                                                                                                                                |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | The platform remains functional when optional services (Langfuse, n8n, Grafana) are unavailable.                                                                                                                                                                                                                      |
| **Rationale**    | Not every deployment needs full observability or workflow automation. Hard dependencies on optional infrastructure create fragile systems.                                                                                                                                                                            |
| **Implications** | Langfuse tracing falls back to no-op spans when keys are not configured. Health checks report per-service status independently. The UI console shows service health chips and continues to function when individual services are offline. n8n workflows are optional — core agent execution has no dependency on n8n. |

| Validation                             | Status                                                                                                                                                   |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Langfuse no-op fallback                | **YES** — `_NoOpSpan` class provides empty `update()` and `end()` when Langfuse keys are absent                                                          |
| n8n independent of agent execution     | **YES** — agent-service has zero n8n imports or calls. n8n is only used in ui-console proxy layer                                                        |
| UI functions when services are offline | **YES** — API proxy calls in `server.js` have try/catch returning `{ error: e.message }` gracefully. Pages render with error states rather than crashing |

**Status: FULLY MET** ✅

---

## Validation Summary

### Foundational Principles (AP-1 – AP-10)

| Principle                                | Maturity   | Status       | Gaps                                                       |
| ---------------------------------------- | ---------- | ------------ | ---------------------------------------------------------- |
| AP-1 · API-First Design                  | 🟡 Next    | ⚠️ PARTIAL   | No API versioning; n8n auth logic in UI                    |
| AP-2 · Local-First, Cloud-Ready          | 🟢 Current | ✅ FULLY MET | —                                                          |
| AP-3 · Container-Native Composability    | 🟢 Current | ✅ FULLY MET | —                                                          |
| AP-4 · Defence in Depth                  | 🟢 Current | ✅ FULLY MET | —                                                          |
| AP-5 · Observable by Default             | 🟡 Next    | ❌ NOT MET   | Telemetry is opt-in; Grafana dashboard has Prometheus only |
| AP-6 · Protocol-Driven Extensibility     | 🟢 Current | ✅ FULLY MET | —                                                          |
| AP-7 · Separation of Concerns            | 🟡 Next    | ⚠️ PARTIAL   | vector_search/vector_store run in-process                  |
| AP-8 · Knowledge as First-Class Resource | 🟢 Current | ✅ FULLY MET | —                                                          |
| AP-9 · Configuration over Code           | 🟡 Next    | ⚠️ PARTIAL   | No versioning for guardrails and custom tools              |
| AP-10 · Graceful Degradation             | 🟢 Current | ✅ FULLY MET | —                                                          |

### Enterprise Principles (AP-11 – AP-18)

| Principle                              | Maturity  | Status     | Gaps                                                         |
| -------------------------------------- | --------- | ---------- | ------------------------------------------------------------ |
| AP-11 · Identity & Access Control      | 🔴 Target | ❌ NOT MET | No auth; no RBAC; all endpoints public                       |
| AP-12 · Cost Accountability & Metering | 🟡 Next   | ⚠️ PARTIAL | Token tracking exists; no enforcement, no per-user metering  |
| AP-13 · Elastic Scaling                | 🔴 Target | ❌ NOT MET | Single-writer SQLite; no K8s; no horizontal scaling          |
| AP-14 · Compliance & Data Governance   | 🔴 Target | ❌ NOT MET | No data classification; no retention; no encryption at rest  |
| AP-15 · Disaster Recovery & Continuity | 🔴 Target | ❌ NOT MET | No backup strategy; no replication; no RTO/RPO               |
| AP-16 · Zero-Trust Networking          | 🔴 Target | ❌ NOT MET | Plain HTTP; no mTLS; single flat network                     |
| AP-17 · Agent Lifecycle Governance     | 🔴 Target | ⚠️ PARTIAL | Version history exists; no approval workflow; no A/B testing |
| AP-18 · Secret & Key Management        | 🟡 Next   | ❌ NOT MET | Secrets in plain text; no vault integration                  |

### Priority Roadmap

| Priority | Action                                                            | Principle | Effort |
| -------- | ----------------------------------------------------------------- | --------- | ------ |
| **P1**   | Pre-configure OTel endpoint in docker-compose.yml                 | AP-5      | Low    |
| **P1**   | Add Loki log panels to Grafana dashboard                          | AP-5      | Medium |
| **P1**   | Move secrets to `.env` and add vault integration guide            | AP-18     | Medium |
| **P2**   | Add `/v1/` API prefix via FastAPI router                          | AP-1      | Medium |
| **P2**   | Add version snapshots for guardrails and custom tools             | AP-9      | Low    |
| **P2**   | Implement rate limiting middleware from existing guardrail config | AP-12     | Medium |
| **P2**   | Add JWT/OAuth2 middleware with RBAC roles                         | AP-11     | High   |
| **P3**   | Move vector tools to tools-service or document exception          | AP-7      | Medium |
| **P3**   | Extract n8n auth into separate module                             | AP-1      | Low    |
| **P3**   | Add agent promotion workflow (draft → staging → production)       | AP-17     | High   |
| **P4**   | Migrate SQLite → PostgreSQL for multi-writer support              | AP-13     | High   |
| **P4**   | Add Kubernetes manifests and Helm charts                          | AP-13     | High   |
| **P4**   | Add mTLS between services via service mesh                        | AP-16     | High   |
| **P4**   | Implement data retention policies and GDPR delete                 | AP-14     | Medium |
| **P4**   | Add automated backup with scheduled export + S3/blob upload       | AP-15     | Medium |

---

# Enterprise Principles

> AP-11 through AP-18 define what separates a demo platform from a production enterprise AI platform. These principles address identity, cost control, scaling, compliance, resilience, networking, lifecycle governance, and secret management.

---

## AP-11 · Identity & Access Control · 🔴 Target

| Attribute        | Detail                                                                                                                                                                                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Statement**    | Every API call and UI action is authenticated against a verified identity and authorised against role-based policies.                                                                                                                                                    |
| **Rationale**    | Enterprise AI platforms handle sensitive data and high-value operations. Unauthenticated access to agent configuration, knowledge bases, and tool execution is unacceptable in regulated environments. Multi-user teams need role separation (admin, developer, viewer). |
| **Implications** | All endpoints require a valid JWT or API key. RBAC roles (admin, editor, viewer) control which operations are permitted. Audit logs capture the authenticated `user_id`, not `"system"`. SSO/OIDC integration enables enterprise identity providers (Azure AD, Okta).    |

| Validation                 | Status                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------- |
| Authentication middleware  | **NO** — All 69+ endpoints on agent-service are public. CORS is `allow_origins=["*"]` |
| RBAC roles                 | **NO** — No user table, no role definitions, no permission checks                     |
| User identity in audit log | **NO** — `performed_by` always defaults to `"system"` in `log_audit()`                |
| SSO/OIDC integration       | **NO** — No OAuth2, no JWT validation, no identity provider config                    |

### How to Achieve

| Phase       | Action                                                                                                                                        | Effort |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Add FastAPI `Depends()` middleware for JWT validation. Create `users` table with `id`, `email`, `role`. Pass `user_id` to `log_audit()`       | Medium |
| **Phase 2** | Add RBAC decorator (`@require_role("admin")`) to admin endpoints (delete, import, export, guardrail management). Viewers get read-only access | Medium |
| **Phase 3** | Integrate OIDC provider (Azure AD / Okta). Add `POST /auth/login` and `POST /auth/token/refresh`. Store sessions in DB or Redis               | High   |
| **Phase 4** | Add API key management for machine-to-machine access. Keys scoped to specific agents or capabilities                                          | Medium |

---

## AP-12 · Cost Accountability & Metering · 🟡 Next

| Attribute        | Detail                                                                                                                                                                                       |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | Every LLM call, tool invocation, and agent run is metered with token counts and cost attribution, enabling usage quotas and chargeback.                                                      |
| **Rationale**    | Enterprise AI costs scale with usage. Without metering, teams cannot budget, optimise, or allocate costs. Without rate limiting, a single runaway agent can exhaust API quotas and budgets.  |
| **Implications** | Token usage is tracked per agent, per session, and per user. Rate limits are enforced (not just configured). Usage dashboards show cost trends. Quota breaches trigger alerts or throttling. |

| Validation           | Status                                                                                                                                                         |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Token tracking       | **PARTIAL** — `prompt_tokens` and `completion_tokens` captured in `graph.py` streaming, logged to Langfuse. Not persisted in platform DB per user/session      |
| Rate limiting config | **EXISTS BUT NOT ENFORCED** — `gr-rate-limit` guardrail defines `max_calls_per_minute: 20` and `max_calls_per_session: 100` in SQLite, but no code enforces it |
| Cost dashboard       | **NO** — No cost tracking endpoint or UI                                                                                                                       |
| Per-user metering    | **NO** — No user identity means no per-user cost attribution                                                                                                   |

### How to Achieve

| Phase       | Action                                                                                                                                                                                            | Effort |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Create `usage_log` table (`session_id`, `agent_id`, `provider`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `timestamp`). Persist token counts from `graph.py` after each LLM call | Low    |
| **Phase 2** | Enforce `gr-rate-limit` guardrail — add rate counter in `reason()` node that checks calls per minute/session before LLM invocation                                                                | Medium |
| **Phase 3** | Add `GET /usage/summary` endpoint with filters by agent, session, date range. Add cost panel to overview dashboard                                                                                | Medium |
| **Phase 4** | Add per-user quotas (requires AP-11). Alert on quota breach via webhook or email                                                                                                                  | Medium |

---

## AP-13 · Elastic Scaling · 🔴 Target

| Attribute        | Detail                                                                                                                                                                                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Statement**    | The platform scales horizontally to handle concurrent users and workloads without architectural changes.                                                                                                                                                                       |
| **Rationale**    | Single-writer SQLite and Docker Compose are sufficient for development and demos. Enterprise deployments serve multiple teams with concurrent agent runs, requiring multi-writer databases, container orchestration, and stateless service design.                             |
| **Implications** | The data layer migrates from SQLite to PostgreSQL (or equivalent multi-writer database). Services are deployed on Kubernetes with horizontal pod autoscaling. Agent-service is stateless — all state lives in the database. Load balancers distribute traffic across replicas. |

| Validation            | Status                                                                                                                         |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Multi-writer database | **NO** — SQLite is single-writer. ADR-002 explicitly notes "unsuitable for horizontal scaling"                                 |
| Kubernetes manifests  | **NO** — No K8s, Helm, or Terraform files exist. `CONTRIBUTING.md` lists K8s manifests as a TODO                               |
| Stateless services    | **PARTIAL** — Agent-service is functionally stateless (all state in SQLite). But SQLite is file-based, requiring a single node |
| Connection pooling    | **YES** — Thread-local connections in `memory.py`, but this is SQLite-specific                                                 |

### How to Achieve

| Phase       | Action                                                                                                                                            | Effort |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Abstract database layer — create `db.py` interface that supports both SQLite and PostgreSQL. Use SQLAlchemy or raw driver with connection pooling | High   |
| **Phase 2** | Add PostgreSQL option to `docker-compose.yml` with `DB_ENGINE=postgres` env var. Migrate schema DDL to be dialect-agnostic                        | High   |
| **Phase 3** | Create Kubernetes manifests (`k8s/`) with Deployments, Services, ConfigMaps, and HPA for agent-service and tools-service                          | High   |
| **Phase 4** | Add Helm chart or Terraform module for one-command cloud deployment (AKS, EKS, GKE)                                                               | High   |

---

## AP-14 · Compliance & Data Governance · 🔴 Target

| Attribute        | Detail                                                                                                                                                                                                                                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Statement**    | Data is classified, retained, encrypted, and deletable in accordance with regulatory requirements (GDPR, SOC 2, ISO 27001).                                                                                                                                                                            |
| **Rationale**    | Enterprise AI platforms ingest sensitive documents, process PII through LLMs, and store conversation histories. Regulatory frameworks require data classification, retention policies, encryption, and the right to deletion. Without governance, the platform is unsuitable for regulated industries. |
| **Implications** | Documents and conversations have sensitivity labels. Retention policies auto-purge data beyond TTL. SQLite/PostgreSQL data is encrypted at rest. A GDPR "forget me" endpoint deletes all data for a given user/tenant. Data residency controls ensure processing stays within geographic boundaries.   |

| Validation            | Status                                                                                               |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| Data classification   | **NO** — No sensitivity labels on documents or conversations                                         |
| Retention policies    | **NO** — No TTL, no auto-purge. Manual deletion only                                                 |
| Encryption at rest    | **NO** — SQLite file is unencrypted. No disk encryption config                                       |
| Encryption in transit | **NO** — All inter-service communication is plain HTTP                                               |
| Right-to-deletion     | **NO** — No "delete all data by user" endpoint (no user concept)                                     |
| Data residency        | **NO** — No region-aware deployment; Ollama runs locally, but cloud LLM calls have no region pinning |

### How to Achieve

| Phase       | Action                                                                                                                                            | Effort |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Add `sensitivity` field to `documents` table (`public`, `internal`, `confidential`, `restricted`). Filter document access by classification level | Low    |
| **Phase 2** | Add retention policy config — `retention_days` per entity type. Create background job that purges expired records daily                           | Medium |
| **Phase 3** | Add `DELETE /users/{user_id}/data` endpoint that cascade-deletes all sessions, documents, and audit entries for a user (requires AP-11)           | Medium |
| **Phase 4** | Enable encryption at rest — use SQLCipher for SQLite or PostgreSQL TDE. Configure volume encryption in Kubernetes                                 | High   |
| **Phase 5** | Add data residency config — pin cloud LLM calls to specific Azure regions via `AZURE_OPENAI_ENDPOINT` per tenant                                  | Medium |

---

## AP-15 · Disaster Recovery & Continuity · 🔴 Target

| Attribute        | Detail                                                                                                                                                                                                                                                                     |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | The platform has defined RTO/RPO targets, automated backups, and tested recovery procedures.                                                                                                                                                                               |
| **Rationale**    | Agent configurations, knowledge bases, and conversation histories represent significant organisational investment. Data loss from hardware failure, corruption, or human error is unacceptable in enterprise settings. Recovery must be automated, tested, and documented. |
| **Implications** | SQLite/PostgreSQL is backed up on a schedule. Backups are stored offsite (S3, Azure Blob). ChromaDB collections are snapshotted. Recovery procedures are documented and tested. RTO (time to recover) and RPO (acceptable data loss) are defined per data tier.            |

| Validation          | Status                                                                               |
| ------------------- | ------------------------------------------------------------------------------------ |
| Automated backups   | **NO** — Only manual `GET /export` endpoint. No scheduled backup, no offsite storage |
| ChromaDB backup     | **NO** — No snapshot or backup mechanism for vector data                             |
| Recovery procedures | **NO** — No documented recovery runbook                                              |
| RTO/RPO targets     | **NO** — No SLA or recovery objectives defined                                       |

### How to Achieve

| Phase       | Action                                                                                                                                                  | Effort |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Create `scripts/backup.sh` that calls `/export`, timestamps the JSON, and stores locally. Run via cron or Docker health check sidecar                   | Low    |
| **Phase 2** | Add offsite upload — push backups to S3/Azure Blob with retention (keep last 30 days)                                                                   | Medium |
| **Phase 3** | Add ChromaDB backup — use ChromaDB's persist directory snapshot or collection export API                                                                | Medium |
| **Phase 4** | Document RTO/RPO targets in `docs/DR-PLAN.md`. Define tiers: Tier 1 (config, <1h RPO), Tier 2 (conversations, <4h RPO), Tier 3 (telemetry, best-effort) | Low    |
| **Phase 5** | Add `POST /restore` endpoint that re-imports from backup JSON. Test full recovery quarterly                                                             | Medium |

---

## AP-16 · Zero-Trust Networking · 🔴 Target

| Attribute        | Detail                                                                                                                                                                                                                                                                                              |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | All inter-service communication is encrypted and authenticated. No service is trusted by default, regardless of network position.                                                                                                                                                                   |
| **Rationale**    | A flat Docker network with plain HTTP is acceptable for local development but is a critical vulnerability in production. Compromising one container should not grant access to all others. Enterprise deployments require mTLS, network policies, and egress controls.                              |
| **Implications** | All inter-service calls use TLS (preferably mTLS via a service mesh). Network policies restrict which services can communicate. Egress is controlled — only approved external endpoints are reachable. The OTel collector, Prometheus, and Grafana are on a separate observability network segment. |

| Validation           | Status                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Inter-service TLS    | **NO** — All URLs are `http://`. Langfuse explicitly disables HTTPS (`LANGFUSE_CSP_ENFORCE_HTTPS=false`)                  |
| Network segmentation | **NO** — All 13 containers on single `platform-net` network                                                               |
| Egress control       | **PARTIAL** — tools-service has `ALLOWED_DOMAINS` whitelist for `http_fetch`, but other services have unrestricted egress |
| mTLS / service mesh  | **NO** — No Istio, Linkerd, or similar                                                                                    |

### How to Achieve

| Phase       | Action                                                                                                                                   | Effort |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Split Docker network into `app-net` (agent, tools, ui) and `obs-net` (prometheus, loki, grafana, otel). Only otel-collector bridges both | Low    |
| **Phase 2** | Add TLS termination at ui-console via nginx or Traefik reverse proxy with Let's Encrypt or self-signed certs                             | Medium |
| **Phase 3** | Enable inter-service TLS — generate internal CA, issue certs per service, configure HTTPS in FastAPI and Express                         | High   |
| **Phase 4** | Add service mesh (Istio/Linkerd) in Kubernetes deployment for automatic mTLS and network policies                                        | High   |

---

## AP-17 · Agent Lifecycle Governance · 🔴 Target

| Attribute        | Detail                                                                                                                                                                                                                                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Statement**    | Agents progress through governed lifecycle stages (draft → testing → staging → production) with approval gates, evaluation benchmarks, and rollback capability.                                                                                                                                            |
| **Rationale**    | In enterprise settings, deploying an agent to production without review is as risky as deploying untested code. Agents can generate harmful, inaccurate, or non-compliant outputs. Lifecycle governance ensures agents are evaluated, approved, and monitored before they serve real users.                |
| **Implications** | Agent records have a `status` field (draft, testing, staging, production). Promotion requires evaluation scores above a threshold. Rollback restores a previous version snapshot. A/B testing allows traffic splitting between agent versions. Only `production`-status agents are available to end users. |

| Validation               | Status                                                                                           |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| Agent status/stage field | **NO** — Agents have no lifecycle status. All agents are immediately active                      |
| Evaluation benchmarks    | **PARTIAL** — Evaluation UI exists (`/evaluation`), but scores are not linked to promotion gates |
| Version rollback         | **PARTIAL** — `version_history` table captures snapshots. No one-click rollback endpoint         |
| Approval workflow        | **NO** — Changes take effect immediately; no approval or review step                             |
| A/B testing              | **NO** — No traffic splitting or canary routing between agent versions                           |

### How to Achieve

| Phase       | Action                                                                                                                                                                                      | Effort |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Add `status` column to `agents` table (`draft`, `testing`, `staging`, `production`). Filter agent availability by status in `POST /run` — only `production` agents are invocable by default | Low    |
| **Phase 2** | Add `POST /agents/{id}/promote` endpoint that checks evaluation scores before changing status. Require minimum score threshold (configurable)                                               | Medium |
| **Phase 3** | Add `POST /agents/{id}/rollback?version={n}` endpoint that restores a previous version from `version_history`                                                                               | Low    |
| **Phase 4** | Add A/B routing — `POST /run` accepts `agent_version` parameter. Traffic splitting weighted by percentage between two agent versions                                                        | High   |
| **Phase 5** | Add approval workflow — promotion from `testing` → `staging` requires explicit approval via API or UI (optional webhook to Slack/Teams)                                                     | Medium |

---

## AP-18 · Secret & Key Management · 🟡 Next

| Attribute        | Detail                                                                                                                                                                                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Statement**    | Secrets (API keys, database credentials, signing keys) are stored in a centralised secret manager, never in source code, environment files, or container images.                                                                                                               |
| **Rationale**    | Secrets in `docker-compose.yml` or `.env` files are visible to anyone with filesystem access, appear in process listings, and risk being committed to version control. Enterprise deployments require centralised secret management with rotation, audit, and access control.  |
| **Implications** | API keys (Ollama, Azure OpenAI, OpenAI, Langfuse) are fetched from a secret manager at startup. Secrets are rotated on a schedule without redeployment. Secret access is logged and auditable. No secret appears in any config file, log output, or environment variable dump. |

| Validation                    | Status                                                                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Secrets in docker-compose.yml | **YES** — API keys stored as `${VAR:-default}` with plain-text defaults (`Changeme1!`, `pk-lf-local-dev`, `sk-lf-local-dev`) |
| Vault integration             | **NO** — No HashiCorp Vault, Azure Key Vault, or AWS Secrets Manager                                                         |
| .env in .gitignore            | **YES** — `.env`, `.env.local`, `.env.*.local` are gitignored                                                                |
| Secrets in logs               | **PARTIAL** — LLM API keys are validated at startup but logged content is not scrubbed                                       |

### How to Achieve

| Phase       | Action                                                                                                                                                                     | Effort |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Phase 1** | Remove all plain-text default secrets from `docker-compose.yml`. Replace `Changeme1!` and `pk-lf-local-dev` with empty defaults that require explicit `.env` configuration | Low    |
| **Phase 2** | Add Docker secrets support — use `docker secret create` and mount secrets as files in containers instead of env vars                                                       | Medium |
| **Phase 3** | Add Azure Key Vault integration — create `secrets.py` module that fetches secrets on startup via `DefaultAzureCredential`. Fall back to env vars for local dev             | Medium |
| **Phase 4** | Add secret rotation — Key Vault references auto-refresh on a TTL. Agent-service reloads LLM clients when keys change without restart                                       | High   |
