# Architecture Decision Records

> Each ADR captures a significant design choice and its rationale.

---

## ADR Index

| ID  | Decision                                 | Principles        | Date    |
| --- | ---------------------------------------- | ----------------- | ------- |
| 001 | LangGraph over AgentExecutor             | AP-7, AP-5        | 2024-10 |
| 002 | SQLite for Config and Memory             | AP-3, AP-10       | 2024-10 |
| 003 | Separate Tools Service                   | AP-4, AP-7        | 2024-10 |
| 004 | Multi-Provider LLM Switching             | AP-2, AP-1        | 2024-11 |
| 005 | ChromaDB for Vector Storage              | AP-3, AP-8        | 2024-10 |
| 006 | Three-Pipeline Observability             | AP-5, AP-10       | 2024-11 |
| 007 | EJS + CSS Custom Properties              | AP-3              | 2024-11 |
| 008 | Guardrails as Graph Gates                | AP-4, AP-9        | 2024-12 |
| 009 | A2A and MCP Protocols                    | AP-6              | 2025-01 |
| 010 | Thin UI Proxy Pattern                    | AP-1, AP-7        | 2024-10 |
| 011 | Dual-Mode Multi-Agent Orchestration      | AP-7, AP-9, AP-6  | 2025-05 |
| 012 | Per-Agent KB Isolation                   | AP-8, AP-4        | 2025-05 |
| 013 | LlamaIndex Advanced Retrieval            | AP-8, AP-2        | 2025-06 |
| 014 | Data Connectors Framework                | AP-8, AP-3        | 2025-06 |
| 015 | Hybrid SQLite + PostgreSQL               | AP-10, AP-13      | 2025-06 |
| 016 | LLM-Based Guardrail Detection            | AP-4, AP-10       | 2025-06 |
| 017 | LLM Activity Tracking                    | AP-5, AP-1        | 2025-06 |
| 018 | Dynamic Model Capabilities               | AP-10, AP-9       | 2025-06 |
| 019 | Clickable Execution Details              | AP-5, AP-1        | 2025-06 |
| 020 | Skill File Attachments                   | AP-8, AP-4, AP-9  | 2025-05 |
| 021 | Comprehensive Admin Plane                | AP-5, AP-10, AP-1 | 2025-05 |
| 022 | Admin-Only Editing for Platform Settings | AP-4, AP-10, AP-1 | 2025-05 |
| 023 | Session Auth with PBKDF2 + RBAC          | AP-11, AP-4       | 2025-05 |
| 024 | React Login SPA                          | AP-11, AP-7       | 2025-05 |
| 025 | Workspace-Scoped Multi-Tenancy           | AP-11, AP-7, AP-4 | 2025-05 |

---

## ADR-001 · LangGraph over AgentExecutor

**Context**: Need multi-step reasoning with explicit tool execution, guardrail gates, and context injection.

**Decision**: Use LangGraph `StateGraph` with explicit nodes (`retrieve_context`, `reason`, `execute_tools`, `generate_response`) and conditional edges.

**Why not alternatives**:

- AgentExecutor — simpler but opaque, no guardrail injection points
- Custom async loop — full control but no graph visualisation

**Consequence**: Full visibility into each step. Guardrails inserted at any edge. More boilerplate than AgentExecutor.

---

## ADR-002 · SQLite for Config and Memory

**Context**: Platform stores agents, skills, prompts, guardrails, conversations. Single-node Docker Compose target.

**Decision**: SQLite at `/data/platform.db` for config/memory/audit. Thread-local connections.

**Why not alternatives**:

- PostgreSQL — overkill for single-node dev platform
- In-memory — no persistence across restarts

**Consequence**: Zero-config, single file backup. Limitation: single-writer (acceptable for current arch).

---

## ADR-003 · Separate Tools Service

**Context**: Tools execute untrusted operations (code exec, HTTP fetch). Running in agent process creates security/stability risks.

**Decision**: Isolated `tools-service` (FastAPI, port 8001). Agent calls tools via HTTP proxy.

**Consequence**: Tool crashes don't affect reasoning. Independent scaling. ~5ms HTTP overhead. Exception: vector tools run in-process for latency.

---

## ADR-004 · Multi-Provider LLM Switching

**Context**: Different use cases need different providers — Ollama for offline, Azure for compliance, OpenAI for latest models.

**Decision**: Abstract behind LangChain `BaseChatModel`. Runtime switching via `POST /models/switch`.

**Consequence**: Provider switch is one API call. New providers = one `elif` branch in `get_llm()`.

---

## ADR-005 · ChromaDB for Vector Storage

**Context**: RAG needs a vector DB. Must start with single `docker-compose up`.

**Decision**: ChromaDB (HTTP mode, port 8200) with Ollama embeddings.

**Why not alternatives**:

- Pinecone — requires cloud account
- FAISS — no persistence without custom serialisation
- pgvector — not justified when SQLite handles config

**Consequence**: Simple container, cosine distance, collection isolation. Embed model change requires re-ingestion.

---

## ADR-006 · Three-Pipeline Observability

**Context**: AI debugging needs LLM traces, quantitative metrics, AND log aggregation. No single tool covers all three.

**Decision**: Langfuse (LLM traces) + Prometheus (metrics) + Loki (logs). OTel Collector routes telemetry. Grafana unifies dashboards.

**Consequence**: Full coverage. Six extra containers, all optional — agent degrades to no-op tracing if keys absent.

---

## ADR-007 · EJS + CSS Custom Properties

**Context**: 25 pages, light/dark theme, fast SSR, zero build step needed.

**Decision**: Express.js + EJS + CSS custom properties. Theme via `.dark` class toggle.

**Consequence**: Zero build step. <50ms server render. No component model — each page is self-contained.

---

## ADR-008 · Guardrails as Graph Gates

**Context**: Safety checks need to run at specific pipeline points — before LLM calls and after responses.

**Decision**: Guardrails as functions within graph nodes. Input in `reason()`, output in `generate_response()`. LLM-based detection is primary method (amended by ADR-016).

**Consequence**: Full access to AgentState. Can short-circuit the graph. Per-guardrail config via SQLite.

---

## ADR-009 · A2A and MCP Protocols

**Context**: Platform needs to interact with external agents and tool servers without vendor lock-in.

**Decision**: Google A2A for agent communication, Anthropic MCP for tool discovery. Both JSON-over-HTTP.

**Consequence**: Interoperable by default. Any framework can participate. Trade-off: specs still evolving.

---

## ADR-010 · Thin UI Proxy Pattern

**Context**: Browser can't reach internal Docker hostnames. Need unified entry point.

**Decision**: `ui-console` proxies all `/api/*` to backend services. Zero business logic in proxy.

**Consequence**: Single entry point (port 3000). CORS handled once. ~2ms proxy overhead.

---

## ADR-011 · Dual-Mode Multi-Agent Orchestration

**Context**: Need both autonomous delegation (LLM decides) and deterministic pipelines (fixed order).

**Decision**: Runtime delegation via `delegate_to_agent` tool. Pre-planned pipelines via n8n workflows.

**Consequence**: No redundancy — agent-service owns "which agent", n8n owns "in what order". Recursion guard prevents infinite loops.

---

## ADR-012 · Per-Agent KB Isolation

**Context**: Multiple agents sharing one collection causes cross-contamination.

**Decision**: Each agent gets dedicated ChromaDB collection (`agent_{name}_kb`).

**Consequence**: Complete isolation. Multi-agent orchestration uses each sub-agent's own KB.

---

## ADR-013 · LlamaIndex Advanced Retrieval

**Context**: Basic cosine similarity misses cross-chunk context and keyword-heavy queries.

**Decision**: LlamaIndex as advanced retrieval layer. 5 strategies: hybrid, reranked, sentence_window, auto_merging, basic.

**Consequence**: Also provides 20+ file format parsing. Adds ~50MB to image. Mode is per-agent config.

---

## ADR-014 · Data Connectors Framework

**Context**: Agents need knowledge from databases, APIs, cloud storage — not just uploaded files.

**Decision**: Five connector types (database, API, cloud storage, Google Drive, SharePoint) with test + sync lifecycle.

**Consequence**: Unified ingestion interface. All feed into ChromaDB pipeline.

---

## ADR-015 · Hybrid SQLite + PostgreSQL

**Context**: Document registry needs JSONB queries and multi-writer. Config/memory remains lightweight.

**Decision**: PostgreSQL (`datastore-db`, port 5433) for documents. SQLite remains for everything else.

**Consequence**: Two stores. SQLite is zero-config. PostgreSQL auto-initialised via docker-compose.

---

## ADR-016 · LLM-Based Guardrail Detection

**Context**: Regex misses natural-language PII, international formats, obfuscated patterns.

**Decision**: LLM as primary safety classifier. Single call evaluates all guardrails, returns per-guardrail JSON. Regex fallback for availability.

**Consequence**: Near-complete detection. ~200-500ms extra latency. Azure content filter provides additional layer.

---

## ADR-017 · LLM Activity Tracking

**Context**: No visibility into usage patterns, token consumption, or cost.

**Decision**: `llm_usage_log` table with per-request metrics. Dashboard with timeseries, filters, CSV export.

**Consequence**: Full usage visibility without external deps. Auto-refreshes every 30s.

---

## ADR-018 · Dynamic Model Capabilities

**Context**: Models have different capabilities (temperature, max_tokens). Static UI causes API errors.

**Decision**: Per-model `capabilities` metadata on `GET /models`. UI disables unsupported controls. Temperature retry loop.

**Consequence**: No API errors from unsupported params. New models need only a capabilities entry.

---

## ADR-019 · Clickable Execution Details

**Context**: Trace/Request IDs displayed as static text. Users had to manually copy and navigate.

**Decision**: Trace ID links to `/traceability?traceId=X`, Request ID links to `/llm-activity?requestId=X`. Target pages auto-filter.

**Consequence**: Single-click navigation. Deep-link URLs are shareable. Minimal code change.

---

## ADR-020 · Skill File Attachments

**Context**: Skills only supported instruction text. Real-world skills often need executable scripts, reference documentation, and template assets.

**Decision**: Each skill can have files in three categories: `scripts/` (executable code: .py, .sh, .js, etc.), `references/` (supporting documentation: .md, .txt, .pdf, etc.), and `assets/` (templates and format files: .json, .yaml, .tmpl, etc.). Files are stored on disk under `/data/filestore/skills/{skill_id}/{category}/` with metadata in SQLite (`files` JSON column on `skills` table). Text file contents are auto-injected into the agent’s system prompt at runtime.

**Key constraints**: 1 MB per file, 5 MB total per skill, ~20 allowed extensions, sanitised filenames.

**Why not alternatives**:

- Blob column in SQLite — poor for large files, no streaming
- Shared file pool — breaks isolation between skills
- External object store — overkill for single-node deployment

**Consequence**: Skills become self-contained packages (instructions + code + docs + templates). Files are strictly per-skill isolated — no cross-skill file sharing. Deleting a skill cascade-deletes its files.

---

## ADR-021 · Comprehensive Admin Plane

**Context**: The admin page only showed basic DB stats and export/import. No visibility into service health, LLM usage, platform configuration, or audit trails from a single pane.

**Decision**: Rebuild the admin page as a 6-tab control plane:

1. **Service Health** — Live checks for 10 services with latency, HTTP status, endpoints table, version matrix
2. **Platform Overview** — Entity counts, 18 capability indicators, memory/storage stats
3. **LLM & Models** — Active config, provider/model switcher, available models, usage summary with per-model breakdown
4. **Database & Data** — SQLite table stats with percentage bars, export/import, ChromaDB collections, document stats
5. **Configuration** — Global constraints JSON editor, guardrails registry, n8n workflows, quick links
6. **Audit Log** — Filterable audit trail (9 entity types × 4 action types)

Added 9 new server-side API endpoints (`/api/admin/*`) to aggregate data from agent-service, tools-service, ChromaDB, Prometheus, n8n, and Ollama.

**Why not alternatives**:

- Grafana-only — limited to metrics, no config editing or entity management
- Separate admin service — overkill for single-node deployment

**Consequence**: Single pane of glass for platform operations. Auth-gated (client-side session). All tabs load data lazily on switch.

---

## ADR-022 · Admin-Only Editing for Platform Settings

**Context**: Platform-wide settings — security considerations and best practices — were either hardcoded or stored in `localStorage`, meaning each browser had its own copy. Skills page users could edit these freely, creating inconsistency across the team.

**Decision**: Migrate security considerations and best practices to backend storage (`platform_settings` table in SQLite via `GET/PUT /security-considerations` and `GET/PUT /best-practices` endpoints). Make them **editable only in the admin plane** (Configuration tab, "Security & Best Practices" card) and **read-only on the skills page**. Global constraints follow the same pattern — editable in admin, read-only on skills.

**Key changes**:

- New DB functions: `get_security_considerations()`, `set_security_considerations()`, `get_best_practices()`, `set_best_practices()` in `memory.py`
- New backend endpoints: `GET/PUT /security-considerations`, `GET/PUT /best-practices` in agent-service
- New proxy routes in `server.js`: `/api/admin/security-considerations`, `/api/admin/best-practices` (and non-admin variants)
- Admin page uses hash-based tab navigation (`/admin#config` deep links work)

**Why not alternatives**:

- `localStorage` — per-browser, no team consistency, no audit trail
- Env vars — requires restart to change, no UI editing
- Separate settings service — overkill for single-node deployment

**Consequence**: Single source of truth for governance content. All users see the same security/best-practices text. Changes are auditable. Skills page consumers cannot accidentally modify platform policy.

---

## ADR-023 · Session Auth with PBKDF2 + RBAC

**Context**: All API endpoints were public (AP-11 gap). Need authentication without external IdP dependency for local-first platform.

**Decision**: PBKDF2-SHA256 with 600 000 iterations and `os.urandom(32)` salt. Express-session with `agentic.sid` cookie (HttpOnly, SameSite=Strict). Three roles: `admin`, `member`, `viewer`. In-memory rate limiter (5 attempts per 5-minute window per IP).

**Key changes**:

- `memory.py`: `create_user()`, `authenticate_user()`, `reset_user_password()`, `verify_user_email()`, `_hash_password()`, `_verify_password()`
- `main.py`: `/auth/login`, `/auth/register`, `/auth/verify-email`, `/auth/resend-code`, `/auth/forgot-password`, `/auth/reset-password`, `/users` CRUD (7 endpoints)
- `server.js`: `requireAuth` and `requireAdmin` middleware, session-backed route protection
- Pydantic models enforce input validation (min_length, max_length, pattern) at API boundary

**Why not alternatives**:

- JWT — stateless but harder to revoke; session store is simpler for server-rendered UI
- bcrypt — requires C extension (`bcrypt`); PBKDF2 is stdlib (`hashlib`)
- OAuth2/OIDC — requires external IdP; violates local-first principle (AP-2)
- Argon2 — best-in-class but requires `argon2-cffi` C dep

**Consequence**: Zero external dependencies for auth. All users stored in SQLite `users` table. Admin user seeded on first `init_db()`. Password stored as `algorithm$iterations$salt$hash`. Rate limiting prevents brute force. Admin cannot be deleted (403).

---

## ADR-024 · React Login SPA

**Context**: Login, registration, email verification, and password reset need interactive forms with real-time validation. EJS server-rendered pages are too static for this UX.

**Decision**: React 18 + Vite SPA in `services/ui-login/`. Builds to `services/ui-console/public/login-app/`. Served at `/login` path. Multi-step flows: login → register → verify email → forgot password → reset password.

**Why not alternatives**:

- EJS form — no client-side validation, page reloads on every step
- Full SPA — overkill; only auth flows need interactivity

**Consequence**: Fast iteration on auth UX. Build step required (`npm run build`). Output committed to `public/login-app/` for zero-build deployment. Rest of UI stays EJS.

---

## ADR-025 · Workspace-Scoped Multi-Tenancy

**Context**: All entities (agents, skills, prompts, tools) were globally visible. Multi-team usage requires isolation.

**Decision**: `ContextVar`-based scoping in `workspace.py`. Each request sets `workspace_id` and `user_id`. All entities have `workspace_id`, `created_by`, and `scope` columns. Default workspace pre-created and non-deletable.

**Why not alternatives**:

- Schema-per-tenant — too heavyweight for SQLite
- Row-level security — SQLite has no RLS; manual WHERE clause filtering

**Consequence**: Queries filter by workspace. Scope column allows `global` entities visible to all workspaces. ContextVar is thread-safe for async FastAPI.
