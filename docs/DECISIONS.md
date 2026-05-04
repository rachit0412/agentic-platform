# Architecture Decision Records

> Each ADR captures a significant design choice, its context, the options considered, and the rationale for the chosen approach. Status: **Accepted** unless noted.

---

## ADR-001 · LangGraph over LangChain AgentExecutor

| Field            | Detail                                                                                                                                                                                                                             |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-10                                                                                                                                                                                                                            |
| **Status**       | Accepted                                                                                                                                                                                                                           |
| **Context**      | The agent needs a multi-step reasoning loop with explicit tool execution, guardrail gates, and retrieval context injection. LangChain's `AgentExecutor` provides a simpler interface but limited control over the execution graph. |
| **Decision**     | Use LangGraph `StateGraph` with explicit nodes (`retrieve_context`, `reason`, `execute_tools`, `generate_response`) and conditional edges.                                                                                         |
| **Alternatives** | (1) LangChain AgentExecutor — simpler but opaque; no guardrail injection points. (2) Custom async loop — full control but no graph visualisation or checkpoint support.                                                            |
| **Consequences** | Full visibility into each step. Guardrails can be inserted at any edge. State is typed (`AgentState` TypedDict). Trade-off: more boilerplate than AgentExecutor.                                                                   |
| **Principles**   | AP-7 Separation of Concerns, AP-5 Observable by Default                                                                                                                                                                            |

---

## ADR-002 · SQLite for Configuration and Memory

| Field            | Detail                                                                                                                                                                                                                                          |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-10                                                                                                                                                                                                                                         |
| **Status**       | Accepted                                                                                                                                                                                                                                        |
| **Context**      | The platform stores agents, skills, prompts, guardrails, custom tools, A2A peers, MCP servers, conversation history, and session summaries. The deployment target is a single-node Docker Compose stack.                                        |
| **Decision**     | Use SQLite at `/data/platform.db` for config/memory/audit (thread-local connections, stale-handle recovery). Document registry lives in PostgreSQL (`datastore-db` container, port 5433) for JSONB queries and horizontal-ready storage.        |
| **Alternatives** | (1) PostgreSQL — production-grade but adds another container and configuration burden for a dev platform. (2) In-memory dicts — fast but no persistence across restarts. (3) Redis — good for sessions but poor for relational queries.         |
| **Consequences** | Zero-config persistence. Single file backup/restore. No network latency. Thread-local connections avoid concurrency issues. Limitation: single-writer, unsuitable for horizontal scaling (acceptable for the current single-node architecture). |
| **Principles**   | AP-3 Container-Native Composability, AP-10 Graceful Degradation                                                                                                                                                                                 |

---

## ADR-003 · Separate Tools Service

| Field            | Detail                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-10                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Status**       | Accepted                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **Context**      | Agent tools (math eval, code execution, HTTP fetch, file I/O) execute untrusted or semi-trusted operations. Running them in the agent process creates security and stability risks.                                                                                                                                                                                                                                             |
| **Decision**     | Run tools in an isolated `tools-service` (FastAPI, port 8001). The agent calls tools via HTTP proxy, not in-process.                                                                                                                                                                                                                                                                                                            |
| **Alternatives** | (1) In-process tool functions — simpler but code-execute crashes can kill the agent. (2) Subprocess per tool call — isolation without a service boundary, but no independent scaling or health checks.                                                                                                                                                                                                                          |
| **Consequences** | Tool crashes do not affect agent reasoning. Tools can be scaled or replaced independently. HTTP overhead per tool call (~5ms on Docker network). Security controls (URL whitelist, import blocking, filename sanitisation) are enforced at the service boundary. **Exception:** `vector_search` and `vector_store` currently run in-process in agent-service for latency reasons — see AP-7 Future Vision for remediation plan. |
| **Principles**   | AP-4 Defence in Depth, AP-7 Separation of Concerns                                                                                                                                                                                                                                                                                                                                                                              |

---

## ADR-004 · Multi-Provider LLM with Runtime Switching

| Field            | Detail                                                                                                                                                                                                                           |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-11                                                                                                                                                                                                                          |
| **Status**       | Accepted                                                                                                                                                                                                                         |
| **Context**      | Different use cases require different LLM providers: Ollama for offline development, Azure OpenAI for enterprise compliance, OpenAI for latest models, Azure AI Foundry for managed deployments.                                 |
| **Decision**     | Abstract all providers behind LangChain's `BaseChatModel`. Selection via `LLM_PROVIDER` env var at startup; runtime switching via `POST /models/switch` API.                                                                     |
| **Alternatives** | (1) Hardcoded Ollama — simplest but blocks cloud deployment. (2) Config file per environment — requires redeploy to switch. (3) LiteLLM proxy — adds another service; overkill for 4 providers.                                  |
| **Consequences** | Provider switch is a single API call. New providers require adding one `elif` branch in `get_llm()`. API key validation rejects placeholder values at init time. Active model is tracked as global state (single-writer design). |
| **Principles**   | AP-2 Local-First Cloud-Ready, AP-1 API-First                                                                                                                                                                                     |

---

## ADR-005 · ChromaDB for Vector Storage

| Field            | Detail                                                                                                                                                                                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-10                                                                                                                                                                                                                                                       |
| **Status**       | Accepted                                                                                                                                                                                                                                                      |
| **Context**      | RAG requires a vector database for document embeddings. The platform runs on developer laptops and must start with a single `docker-compose up`.                                                                                                              |
| **Decision**     | Use ChromaDB (HTTP mode, internal port 8000, external port 8200) with LangChain's `Chroma` wrapper and Ollama embeddings.                                                                                                                                     |
| **Alternatives** | (1) Pinecone — managed but requires cloud account and API key. (2) Weaviate — heavier container footprint. (3) FAISS — in-process, no persistence without custom serialisation. (4) pgvector — requires PostgreSQL, not justified when SQLite handles config. |
| **Consequences** | Simple Docker container, cosine distance search, collection isolation per agent. Embeddings are tied to Ollama model — switching embed model requires re-ingestion. HTTP client avoids in-process memory overhead.                                            |
| **Principles**   | AP-3 Container-Native Composability, AP-8 Knowledge as First-Class Resource                                                                                                                                                                                   |

---

## ADR-006 · Three-Pipeline Observability

| Field            | Detail                                                                                                                                                                                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Date**         | 2024-11                                                                                                                                                                                                                                                |
| **Status**       | Accepted                                                                                                                                                                                                                                               |
| **Context**      | AI agent debugging requires three distinct data types: (1) structured traces showing LLM inputs/outputs and costs, (2) quantitative metrics for latency and throughput, (3) log aggregation for error diagnosis. No single tool covers all three well. |
| **Decision**     | Run three observability pipelines in parallel: Langfuse for LLM traces, Prometheus for metrics, Loki for logs. OpenTelemetry Collector routes telemetry. Grafana unifies dashboards.                                                                   |
| **Alternatives** | (1) Langfuse only — good for LLM traces but no metrics or logs. (2) Jaeger + Prometheus — no LLM-specific cost/token tracking. (3) Datadog/New Relic — SaaS dependency, cost.                                                                          |
| **Consequences** | Full observability coverage. Six additional containers (otel-collector, prometheus, grafana, loki, langfuse, langfuse-db). All optional — agent-service degrades to no-op tracing if keys are absent.                                                  |
| **Principles**   | AP-5 Observable by Default, AP-10 Graceful Degradation                                                                                                                                                                                                 |

---

## ADR-007 · EJS Templates with CSS Custom Properties

| Field            | Detail                                                                                                                                                                                                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-11                                                                                                                                                                                                                                                                   |
| **Status**       | Accepted                                                                                                                                                                                                                                                                  |
| **Context**      | The UI console needs 24 pages with light/dark theme support, fast server-side rendering, and zero build step.                                                                                                                                                             |
| **Decision**     | Use Express.js + EJS templates with a CSS custom property design system (`style.css`). Theme switching toggles a `.dark` class on `<html>`.                                                                                                                               |
| **Alternatives** | (1) React/Next.js SPA — better DX for complex UIs but adds a build pipeline, node_modules in production image, and client-side hydration overhead. (2) HTMX — lighter but less ecosystem support for complex interactions. (3) Svelte — good DX but requires compilation. |
| **Consequences** | Zero build step. Pages render in <50ms server-side. Theme tokens are enforced via the `theme-tokens` Copilot skill. Trade-off: no component model — each EJS file is self-contained with inline `<style>` and `<script>`.                                                 |
| **Principles**   | AP-3 Container-Native Composability                                                                                                                                                                                                                                       |

---

## ADR-008 · Guardrails as Graph Gates, Not Middleware

| Field            | Detail                                                                                                                                                                                                                                              |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-12                                                                                                                                                                                                                                             |
| **Status**       | Accepted                                                                                                                                                                                                                                            |
| **Context**      | Safety checks (PII detection, prompt injection, toxicity) need to run at specific points in the reasoning pipeline — before LLM calls and after response generation.                                                                                |
| **Decision**     | Implement guardrails as functions called within graph nodes, not as FastAPI middleware. Input guardrails run in `reason()` before the LLM call. Output guardrails run in `generate_response()` before returning.                                    |
| **Alternatives** | (1) FastAPI middleware — runs on every request, not just agent runs; can't access agent state. (2) Separate guardrails service — adds latency and another container. (3) LLM-based guardrails — expensive, slow, and recursive.                     |
| **Consequences** | Guardrails have full access to `AgentState`. They can short-circuit the graph. Configuration is stored in SQLite with per-guardrail enable/disable and severity. Regex-based detection is fast (<1ms) but less nuanced than LLM-based alternatives. |
| **Principles**   | AP-4 Defence in Depth, AP-9 Configuration over Code                                                                                                                                                                                                 |

---

## ADR-009 · A2A and MCP as First-Class Protocols

| Field            | Detail                                                                                                                                                                                                                                                   |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2025-01                                                                                                                                                                                                                                                  |
| **Status**       | Accepted                                                                                                                                                                                                                                                 |
| **Context**      | The platform needs to interact with external agents and external tool servers. Proprietary plugin APIs would create vendor lock-in.                                                                                                                      |
| **Decision**     | Implement Google's Agent-to-Agent (A2A) protocol for agent communication and Anthropic's Model Context Protocol (MCP) for tool discovery. Both use JSON-over-HTTP.                                                                                       |
| **Alternatives** | (1) Custom RPC — flexible but non-standard. (2) gRPC — efficient but harder to debug and requires proto compilation. (3) GraphQL subscriptions — good for real-time but overkill for task delegation.                                                    |
| **Consequences** | Any agent framework can register as an A2A peer. Any tool server implementing MCP can be added to the registry. The platform is interoperable by default. Trade-off: protocol specs are still evolving; implementation may need updates as specs mature. |
| **Principles**   | AP-6 Protocol-Driven Extensibility                                                                                                                                                                                                                       |

---

## ADR-010 · Thin UI Proxy Pattern

| Field            | Detail                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2024-10                                                                                                                                                                                                                                                                                                                                                                       |
| **Status**       | Accepted                                                                                                                                                                                                                                                                                                                                                                      |
| **Context**      | The UI console needs to call agent-service, tools-service, n8n, and Langfuse APIs. Direct browser-to-service calls fail due to CORS and internal Docker networking (containers use internal hostnames).                                                                                                                                                                       |
| **Decision**     | `ui-console` acts as a thin API proxy. All `/api/*` routes forward to backend services using internal Docker URLs. Zero business logic in the proxy layer.                                                                                                                                                                                                                    |
| **Alternatives** | (1) API Gateway (Kong, Traefik) — heavyweight for a dev platform. (2) Nginx reverse proxy — static config, no request transformation. (3) Direct browser calls — blocked by Docker internal networking.                                                                                                                                                                       |
| **Consequences** | Single external entry point (port 3000). CORS is handled once. Backend services are not exposed to the browser. The proxy layer adds ~2ms latency per call. Service URL configuration is centralised in env vars. **Note:** n8n auth logic (`n8nLogin`, `n8nAutoSetup`, `n8nFetchWithAuth`) currently lives in the proxy layer — see AP-1 Future Vision for remediation plan. |
| **Principles**   | AP-1 API-First, AP-7 Separation of Concerns                                                                                                                                                                                                                                                                                                                                   |

---

## ADR-011 · Dual-Mode Multi-Agent Orchestration

| Field            | Detail                                                                                                                                                                                                                                                                                                                 |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2025-05                                                                                                                                                                                                                                                                                                                |
| **Status**       | Accepted                                                                                                                                                                                                                                                                                                               |
| **Context**      | The platform needs multi-agent orchestration where one agent delegates sub-tasks to specialist agents. Two patterns emerged: (1) the orchestrator LLM autonomously decides which sub-agent to invoke (runtime), and (2) deterministic pipelines where agents always run in a fixed sequence or parallel (pre-planned). |
| **Decision**     | Implement both patterns with clear separation: runtime LLM-driven delegation via `delegate_to_agent` tool in agent-service; pre-planned sequential/parallel pipelines via n8n workflows calling `/run` with different `agent_id` per branch.                                                                           |
| **Alternatives** | (1) All orchestration in n8n — inflexible, LLM can't decide dynamically. (2) All orchestration in agent-service — reinvents workflow engine for fixed patterns. (3) External orchestrator service — adds complexity without benefit.                                                                                   |
| **Consequences** | No redundancy between n8n and agent-service. Agent-service owns "which agent" (LLM decides); n8n owns "in what order" (DAG decides). `sub_agent_ids` on agent config enables the `reason` node to inject sub-agent descriptions so the LLM knows its delegation options. Recursion guard prevents infinite delegation. |
| **Principles**   | AP-7 Separation of Concerns, AP-9 Configuration over Code, AP-6 Protocol-Driven Extensibility                                                                                                                                                                                                                          |

---

## ADR-012 · Per-Agent Knowledge Base Isolation

| Field            | Detail                                                                                                                                                                                                                                        |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2025-05                                                                                                                                                                                                                                       |
| **Status**       | Accepted                                                                                                                                                                                                                                      |
| **Context**      | When multiple agents exist, documents uploaded for one agent's KB should not pollute another agent's retrieval results. The original design used a single shared ChromaDB collection.                                                         |
| **Decision**     | Each agent gets a dedicated ChromaDB collection named `agent_{name}_kb` (auto-generated from agent name). The `kb_collection` field on the agent config controls which collection is used for RAG retrieval during that agent's runs.         |
| **Alternatives** | (1) Shared collection with metadata filtering — simpler but risks cross-contamination if filters fail. (2) Namespace prefixes within one collection — Chroma doesn't natively support namespaces. (3) Separate ChromaDB instances — overkill. |
| **Consequences** | Complete isolation. Each agent's `retrieve_context` node reads from its own collection. Multi-agent orchestration naturally uses each sub-agent's isolated KB. Trade-off: more collections to manage; collection names must be unique.        |
| **Principles**   | AP-8 Knowledge as First-Class Resource, AP-4 Defence in Depth                                                                                                                                                                                 |

---

## ADR-013 · LlamaIndex Advanced Retrieval

| Field            | Detail                                                                                                                                                                                                                                                                                             |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2025-06                                                                                                                                                                                                                                                                                            |
| **Status**       | Accepted                                                                                                                                                                                                                                                                                           |
| **Context**      | Basic cosine-similarity retrieval (ChromaDB direct) is insufficient for complex queries — it misses cross-chunk context, struggles with keyword-heavy queries, and has no relevance ranking beyond vector distance.                                                                                |
| **Decision**     | Integrate LlamaIndex as an advanced retrieval layer. Each agent can set `retrieval_mode` to `basic` (direct ChromaDB), `advanced` (LlamaIndex pipeline), or `none`. Advanced mode supports 5 strategies: `hybrid`, `reranked`, `sentence_window`, `auto_merging`, and `basic` (LlamaIndex simple). |
| **Alternatives** | (1) LangChain retrievers — tightly coupled to LangChain; we use LangGraph independently. (2) Custom retrieval pipeline — maintenance burden. (3) Haystack — good but smaller ecosystem for document parsing.                                                                                       |
| **Consequences** | LlamaIndex also provides `SimpleDirectoryReader` for 20+ file formats (PDF, DOCX, XLSX, PPTX, EPUB, etc.) via `llamaindex_loader.py`. Dependencies add ~50MB to image. `retrieval_mode` is a per-agent config field defaulting to `basic`.                                                         |
| **Principles**   | AP-8 Knowledge as First-Class Resource, AP-2 Cloud- and Model-Agnostic                                                                                                                                                                                                                             |

---

## ADR-014 · Data Connectors Framework

| Field            | Detail                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2025-06                                                                                                                                                                                                                                                                                                                                                                       |
| **Status**       | Accepted                                                                                                                                                                                                                                                                                                                                                                      |
| **Context**      | Agents need to ingest knowledge from external systems — databases, REST APIs, cloud storage, collaboration tools — not just uploaded files. A pluggable connector framework is needed.                                                                                                                                                                                        |
| **Decision**     | Six connector types in `services/agent/agent/connectors/`: `database.py` (PostgreSQL, MySQL, MSSQL via SQLAlchemy), `api_connector.py` (REST with OAuth2/API-key auth), `cloud_storage.py` (S3, Azure Blob, GCS), `drives.py` (Google Drive, SharePoint), `sync_engine.py` (Airbyte protocol, 300+ sources). Each connector implements `test_connection()` and `sync_data()`. |
| **Alternatives** | (1) Airbyte-only — covers 300+ sources but heavy (Java runtime). (2) Direct SDK integrations — no unified interface. (3) Apache NiFi — overkill for document ingestion.                                                                                                                                                                                                       |
| **Consequences** | Connectors are registered via `POST /connectors` and synced via `POST /connectors/{id}/sync`. Airbyte connector is optional (requires separate Airbyte instance). All connectors feed into the same ChromaDB + PostgreSQL pipeline.                                                                                                                                           |
| **Principles**   | AP-8 Knowledge as First-Class Resource, AP-3 Container-Native Composability                                                                                                                                                                                                                                                                                                   |

---

## ADR-015 · Hybrid SQLite + PostgreSQL Storage

| Field            | Detail                                                                                                                                                                                                                                                                |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Date**         | 2025-06                                                                                                                                                                                                                                                               |
| **Status**       | Accepted (amends ADR-002)                                                                                                                                                                                                                                             |
| **Context**      | The document registry needs richer queries (JSONB metadata, full-text search, folder hierarchy) and multi-writer support that SQLite cannot provide. Agent config, memory, and skills remain lightweight and single-writer.                                           |
| **Decision**     | Add PostgreSQL (`datastore-db`, port 5433) for the document registry. SQLite remains for agent configs, conversations, skills, prompts, A2A peers, MCP servers, guardrails, and evaluation results. `psycopg2-binary` connects agent-service to PostgreSQL.           |
| **Alternatives** | (1) Migrate everything to PostgreSQL — adds operational complexity for tables that don't need it. (2) Use ChromaDB metadata — limited query capabilities for non-vector data. (3) Embedded DuckDB — no multi-writer.                                                  |
| **Consequences** | Two data stores to manage. SQLite remains zero-config. PostgreSQL is auto-initialized via `docker-compose` with a dedicated volume (`datastore-db-data`). Migration path: if horizontal scaling is needed, SQLite tables can be migrated to PostgreSQL incrementally. |
| **Principles**   | AP-10 Minimal-Config Local-First, AP-13 Production-Ready by Default                                                                                                                                                                                                   |

---

## ADR Index

| ID      | Title                               | Principles       |
| ------- | ----------------------------------- | ---------------- |
| ADR-001 | LangGraph over AgentExecutor        | AP-7, AP-5       |
| ADR-002 | SQLite for Config and Memory        | AP-3, AP-10      |
| ADR-003 | Separate Tools Service              | AP-4, AP-7       |
| ADR-004 | Multi-Provider LLM Switching        | AP-2, AP-1       |
| ADR-005 | ChromaDB for Vector Storage         | AP-3, AP-8       |
| ADR-006 | Three-Pipeline Observability        | AP-5, AP-10      |
| ADR-007 | EJS + CSS Custom Properties         | AP-3             |
| ADR-008 | Guardrails as Graph Gates           | AP-4, AP-9       |
| ADR-009 | A2A and MCP Protocols               | AP-6             |
| ADR-010 | Thin UI Proxy Pattern               | AP-1, AP-7       |
| ADR-011 | Dual-Mode Multi-Agent Orchestration | AP-7, AP-9, AP-6 |
| ADR-012 | Per-Agent KB Isolation              | AP-8, AP-4       |
| ADR-013 | LlamaIndex Advanced Retrieval       | AP-8, AP-2       |
| ADR-014 | Data Connectors Framework           | AP-8, AP-3       |
| ADR-015 | Hybrid SQLite + PostgreSQL Storage  | AP-10, AP-13     |
