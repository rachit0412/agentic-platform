# Architecture Building Blocks

> ABBs define technology-agnostic capabilities. SBBs map each ABB to the concrete technology used in the Agentic Platform.

---

## ABB / SBB Catalogue

### 1. Agent Reasoning Engine

| Attribute             | ABB (Abstract)                                            | SBB (Solution)                                                                   |
| --------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Capability**        | Orchestrate multi-step reasoning with tool use            | LangGraph ReAct graph (`graph.py`)                                               |
| **Pattern**           | Retrieval → Reason → Act → Synthesise loop                | `retrieve_context` → `reason` → `execute_tools` → `generate_response` nodes      |
| **State Model**       | Typed agent state across graph nodes                      | `AgentState` TypedDict (prompt, history, kb_context, tool_calls, response)       |
| **Iteration Control** | Bounded reasoning with configurable max steps             | `MAX_REACT_ITERATIONS` env var (default 5), `should_continue()` conditional edge |
| **Principles**        | AP-7 Separation of Concerns, AP-9 Configuration over Code |

### 2. LLM Abstraction Layer

| Attribute      | ABB (Abstract)                               | SBB (Solution)                                         |
| -------------- | -------------------------------------------- | ------------------------------------------------------ |
| **Capability** | Uniform interface to multiple LLM providers  | LangChain `BaseChatModel` abstraction (`llm.py`)       |
| **Providers**  | Local inference, cloud inference             | Ollama (local), Azure OpenAI, OpenAI, Azure AI Foundry |
| **Selection**  | Runtime provider/model switching             | `LLM_PROVIDER` env var + `POST /models/switch` API     |
| **Embedding**  | Vector embeddings for semantic search        | `OllamaEmbeddings` with configurable model             |
| **Principles** | AP-2 Local-First Cloud-Ready, AP-1 API-First |

### 3. Knowledge Management (RAG)

| Attribute        | ABB (Abstract)                                        | SBB (Solution)                                                                                 |
| ---------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Capability**   | Ingest, chunk, embed, search, and manage documents    | ChromaDB vector store + SQLite document registry                                               |
| **Ingestion**    | Chunked document embedding pipeline                   | `RecursiveCharacterTextSplitter` (1000 chars / 200 overlap) → ChromaDB                         |
| **Retrieval**    | Semantic similarity search with score threshold       | `search_similar()` with cosine distance, k=5 default (called with k=3 in graph), threshold 0.8 |
| **Organisation** | Collections, folders, agent-scoped knowledge          | `kb_collection` per agent, folder management, agent tagging                                    |
| **Lifecycle**    | Full CRUD on documents, collections, registry entries | 13 document endpoints + `vectorstore.py` functions                                             |
| **Principles**   | AP-8 Knowledge as First-Class Resource                |

### 4. Conversation Memory

| Attribute      | ABB (Abstract)                                             | SBB (Solution)                                                 |
| -------------- | ---------------------------------------------------------- | -------------------------------------------------------------- |
| **Capability** | Persistent conversation history and rolling summaries      | SQLite `conversations` + `session_summaries` tables            |
| **Short-term** | Recent message history per session                         | `get_history(session_id, limit)` from `conversations` table    |
| **Long-term**  | Compressed session summaries for context window efficiency | `session_summaries` table, rolling text kept under ~2000 chars |
| **Isolation**  | Per-session state without cross-talk                       | `session_id` partitioning on all memory operations             |
| **Principles** | AP-9 Configuration over Code                               |

### 5. Tool Execution Runtime

| Attribute          | ABB (Abstract)                                                   | SBB (Solution)                                                                           |
| ------------------ | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Capability**     | Sandboxed execution of agent tools                               | `tools-service` FastAPI (port 8001)                                                      |
| **Built-in Tools** | Math, HTTP fetch, file I/O, datetime, web search, code execution | 7 proxy tools via `/tools/*` endpoints + 2 local vector tools + 1 delegation tool        |
| **Custom Tools**   | User-defined API integrations                                    | SQLite `custom_tools` table → dynamic `StructuredTool` generation                        |
| **Delegation**     | Cross-agent task routing                                         | `delegate_to_agent` tool — in-process call to sub-agent’s `run_agent()` with full config |
| **Sandboxing**     | Prevent SSRF, injection, and resource abuse                      | URL whitelist, filename sanitisation, blocked imports, 10s timeout, AST-safe math eval   |
| **Principles**     | AP-4 Defence in Depth, AP-7 Separation of Concerns               |

### 6. Guardrails Engine

| Attribute         | ABB (Abstract)                                               | SBB (Solution)                                                                       |
| ----------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| **Capability**    | Input and output safety gates on agent reasoning             | `_check_guardrails_input()` / `_check_guardrails_output()` in `graph.py`             |
| **Input Guards**  | Block dangerous prompts before LLM call                      | PII detection (email, phone, SSN, CC), prompt-injection detection, topic restriction |
| **Output Guards** | Filter harmful or leaking responses                          | PII flagging, data-leak blocking, toxicity detection, output-length enforcement      |
| **Configuration** | Per-guardrail enable/disable, severity levels, custom config | 10 default guardrails in SQLite with CRUD API                                        |
| **Principles**    | AP-4 Defence in Depth, AP-9 Configuration over Code          |

### 7. Agent Configuration Store

| Attribute        | ABB (Abstract)                                                                                                           | SBB (Solution)                                                                                                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Capability**   | CRUD management of agents, skills, prompts, guardrails, tools                                                            | SQLite database at `/data/memory.db` via `memory.py`                                                                                                                                  |
| **Entities**     | Agent definitions, skill templates, prompt library, guardrail rules, custom tools, conversations, documents, audit trail | 12 tables: `agents`, `skills`, `prompts`, `guardrails`, `custom_tools`, `a2a_peers`, `mcp_servers`, `conversations`, `session_summaries`, `documents`, `version_history`, `audit_log` |
| **Agent Schema** | Agent config with orchestration support                                                                                  | `agents` table includes `sub_agent_ids` (JSON array), `skill_ids`, `tool_ids`, `kb_collection` for full agent composition                                                             |
| **Versioning**   | Audit trail of every configuration change                                                                                | Audit log API + version history with rollback                                                                                                                                         |
| **Migration**    | Import/export for environment portability                                                                                | `GET /export` → JSON, `POST /import` with merge mode                                                                                                                                  |
| **Principles**   | AP-9 Configuration over Code, AP-1 API-First                                                                             |

### 8. Agent-to-Agent Protocol (A2A)

| Attribute         | ABB (Abstract)                                | SBB (Solution)                                                                                                              |
| ----------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Capability**    | Cross-agent task delegation via open protocol | A2A peer registry + HTTP task dispatch                                                                                      |
| **Discovery**     | Agent card describing capabilities            | JSON agent cards with `capabilities` (streaming, multi_turn, tool_use, rag), `agents` list, `tools` list, protocol versions |
| **Communication** | Send tasks across agent boundaries            | `POST /a2a/send` with peer selection                                                                                        |
| **Lifecycle**     | Register, ping, update, remove peers          | Full CRUD on `a2a_peers` table + `POST /a2a/peers/:id/ping`                                                                 |
| **Principles**    | AP-6 Protocol-Driven Extensibility            |

### 9. Model Context Protocol (MCP)

| Attribute        | ABB (Abstract)                               | SBB (Solution)                                         |
| ---------------- | -------------------------------------------- | ------------------------------------------------------ |
| **Capability**   | Dynamic tool discovery from external servers | MCP server registry with tool auto-discovery           |
| **Registration** | Central registry of MCP tool servers         | SQLite `mcp_servers` table with URL, transport, status |
| **Discovery**    | Enumerate tools a server exposes             | `POST /mcp/servers/:id/discover`                       |
| **Invocation**   | Call external tools on demand                | `POST /mcp/servers/:id/invoke`                         |
| **Principles**   | AP-6 Protocol-Driven Extensibility           |

### 10. Observability Stack

| Attribute      | ABB (Abstract)                                         | SBB (Solution)                                                                   |
| -------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------- |
| **Capability** | End-to-end observability: traces, metrics, logs        | Three-pipeline telemetry architecture                                            |
| **Tracing**    | Distributed trace context across services              | OpenTelemetry SDK → OTel Collector + Langfuse SDK for LLM traces                 |
| **Metrics**    | Quantitative performance indicators                    | Prometheus (`llm_call_duration_seconds`, `tool_calls_total`, `agent_runs_total`) |
| **Logs**       | Structured log aggregation                             | Loki via OTel Collector                                                          |
| **Dashboards** | Visual monitoring and alerting                         | Grafana with Prometheus + Loki datasources                                       |
| **Principles** | AP-5 Observable by Default, AP-10 Graceful Degradation |

### 11. Workflow Automation

| Attribute       | ABB (Abstract)                               | SBB (Solution)                                                                                                                |
| --------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Capability**  | Visual workflow orchestration with webhooks  | n8n (port 5678) with nginx proxy (port 5679)                                                                                  |
| **Templates**   | Pre-built agent workflows                    | 6 workflow templates: agent-workflow, create-workflow, rag-ingest, scheduled-summary, web-research, multi-agent-orchestration |
| **Multi-Agent** | Sequential and parallel agent pipelines      | `multi-agent-orchestration.json` — Router → Sequential (A→B) or Parallel (A+B→Merge)                                          |
| **Integration** | Trigger agent runs from workflows            | HTTP nodes calling `agent-service` REST API with per-branch `agent_id`                                                        |
| **Principles**  | AP-10 Graceful Degradation (n8n is optional) |

### 12. Platform Dashboard

| Attribute      | ABB (Abstract)                                      | SBB (Solution)                                                                                                                                                                                                                          |
| -------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Capability** | Unified management UI for all platform capabilities | Express.js + EJS (`ui-console`, port 3000)                                                                                                                                                                                              |
| **Pages**      | 23 views (22 purpose-built + 1 layout template)     | Overview, Run Agent, Agent Builder, AI Studio, Agent Hub, Intelligence Hub, Documents, Docs, Workflows, A2A, MCP, Guardrails, REST Console, Admin, Evaluation, Observability, Traceability, Prompts, Skills, Tools, Marketplace, Agents |
| **API Layer**  | Thin proxy to backend services                      | All `/api/*` routes proxy to `agent-service`, `tools-service`, n8n, Langfuse                                                                                                                                                            |
| **Theming**    | Light/dark mode with design token system            | CSS custom properties in `style.css`, `.dark` class toggle                                                                                                                                                                              |
| **Principles** | AP-1 API-First, AP-7 Separation of Concerns         |

---

### 13. Multi-Agent Orchestration

| Attribute              | ABB (Abstract)                                             | SBB (Solution)                                                                                                    |
| ---------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Capability**         | Hierarchical agent delegation with autonomous task routing | Orchestrator agents with `sub_agent_ids` + `delegate_to_agent` tool                                               |
| **Runtime Delegation** | LLM-driven decision to invoke sub-agents                   | `delegate_to_agent` tool loads sub-agent config, calls `run_agent()` in-process with isolated session             |
| **Configuration**      | Composable agent hierarchies                               | `sub_agent_ids` JSON array on agent record; `reason` node injects sub-agent names/descriptions into system prompt |
| **Skill Composition**  | Multi-skill agents with merged prompts                     | `skill_ids` array → each skill’s `system_prompt` merged into reasoning context                                    |
| **KB Isolation**       | Per-agent knowledge base                                   | `kb_collection` field → ChromaDB collection named `agent_{name}_kb`; uploads isolated to agent scope              |
| **Pipeline Patterns**  | Pre-planned sequential and parallel multi-agent flows      | n8n `multi-agent-orchestration.json` workflow (deterministic DAG orchestration)                                   |
| **Safety**             | Bounded recursion                                          | Delegation depth guard prevents infinite agent→agent loops                                                        |
| **Principles**         | AP-7 Separation of Concerns, AP-9 Configuration over Code  |

---

## ABB → SBB Traceability Matrix

| ABB                       | SBB Technology                                | Service                                             | Source                                   |
| ------------------------- | --------------------------------------------- | --------------------------------------------------- | ---------------------------------------- |
| Agent Reasoning Engine    | LangGraph ReAct                               | agent-service                                       | `graph.py`                               |
| LLM Abstraction           | LangChain + multi-provider                    | agent-service                                       | `llm.py`                                 |
| Knowledge Management      | ChromaDB + SQLite registry                    | agent-service + chromadb                            | `vectorstore.py`, `memory.py`            |
| Conversation Memory       | SQLite                                        | agent-service                                       | `memory.py`                              |
| Tool Execution            | FastAPI sandboxed runtime + delegation        | tools-service + agent-service                       | `tools.py`, `main.py`                    |
| Guardrails Engine         | Regex + rule-based gates                      | agent-service                                       | `graph.py`                               |
| Configuration Store       | SQLite CRUD                                   | agent-service                                       | `memory.py`                              |
| A2A Protocol              | HTTP peer registry                            | agent-service                                       | `memory.py`, `main.py`                   |
| MCP Protocol              | HTTP tool registry                            | agent-service                                       | `memory.py`, `main.py`                   |
| Observability             | OTel + Langfuse + Prometheus + Loki + Grafana | otel-collector, langfuse, prometheus, loki, grafana | `observability.py`                       |
| Workflow Automation       | n8n                                           | n8n, n8n-proxy                                      | `n8n/workflows/`                         |
| Platform Dashboard        | Express.js + EJS                              | ui-console                                          | `server.js`, `views/`                    |
| Multi-Agent Orchestration | delegate_to_agent + sub_agent_ids + n8n DAGs  | agent-service + n8n                                 | `tools.py`, `graph.py`, `n8n/workflows/` |
