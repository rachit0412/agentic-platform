# Building Blocks

> ABBs (Architecture Building Blocks) define capabilities. SBBs (Solution Building Blocks) map each to concrete technology.

## Core Platform

| #   | Capability                 | Technology                                                                                                                                                                                                        | Source                                        |
| --- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 1   | Agent Reasoning Engine     | LangGraph ReAct StateGraph                                                                                                                                                                                        | `graph.py`                                    |
| 2   | LLM Abstraction            | LangChain BaseChatModel — Ollama, Azure OpenAI, OpenAI, Foundry                                                                                                                                                   | `llm.py`                                      |
| 3   | Knowledge Management (RAG) | ChromaDB + LlamaIndex + PostgreSQL doc registry                                                                                                                                                                   | `vectorstore.py`, `advanced_retrieval.py`     |
| 4   | Conversation Memory        | SQLite conversations + rolling session summaries                                                                                                                                                                  | `memory.py`                                   |
| 5   | Tool Execution             | tools-service FastAPI (sandboxed) + delegate_to_agent                                                                                                                                                             | `tools.py`, tools `main.py`                   |
| 6   | Guardrails Engine          | LLM-based classifier + regex fallback, input & output gates                                                                                                                                                       | `graph.py`                                    |
| 7   | Configuration Store        | SQLite CRUD — 16 tables (incl. `platform_settings`), full versioning & audit                                                                                                                                      | `memory.py`                                   |
| 7b  | Skill File Store           | Disk-based per-skill isolated file storage (scripts, refs, assets)                                                                                                                                                | `memory.py`, `/data/filestore/skills/`        |
| 8   | A2A Protocol               | HTTP peer registry, agent cards, task dispatch                                                                                                                                                                    | `main.py`                                     |
| 9   | MCP Protocol               | Server registry, JSON-RPC tool discovery & invocation                                                                                                                                                             | `main.py`                                     |
| 10  | Observability              | OTel + Langfuse + Prometheus + Loki + Grafana                                                                                                                                                                     | `observability.py`                            |
| 11  | Workflow Automation        | n8n — 5 pre-built templates incl. multi-agent orchestration                                                                                                                                                       | `n8n/workflows/`                              |
| 12  | Platform Dashboard         | Express.js + EJS, 25 pages, thin API proxy                                                                                                                                                                        | `server.js`, `views/`                         |
| 13  | Multi-Agent Orchestration  | sub_agent_ids + delegate_to_agent + n8n DAGs                                                                                                                                                                      | `tools.py`, `graph.py`                        |
| 13b | Skill Workflow             | Sequential / Router skill execution ordering in Agent Builder                                                                                                                                                     | `agent-builder.ejs`                           |
| 14  | Data Connectors            | DB, REST API, Cloud Storage, Google Drive, SharePoint                                                                                                                                                             | `connectors/`                                 |
| 15  | LlamaIndex Integration     | Multi-format parsing, 5 retrieval modes, structured queries                                                                                                                                                       | `llamaindex_loader.py`, `structured_query.py` |
| 16  | Admin Plane                | 6-tab control centre: service health, LLM management, DB ops, config (security considerations, best practices), audit. Hash-based tab navigation. Platform-wide settings editable here only (read-only elsewhere) | `admin.ejs`, `server.js`                      |
| 17  | Authentication & IAM       | PBKDF2-SHA256 password hashing, session auth, RBAC (admin/member/viewer), email verification, password reset, workspace scoping                                                                                   | `memory.py`, `main.py`, `server.js`           |
| 18  | Login UI                   | React 18 + Vite SPA — login, register, email verify, forgot/reset password                                                                                                                                        | `ui-login/`, `public/login-app/`              |

## Detail: Agent Reasoning Engine

```
retrieve_context → reason → execute_tools → generate_response
                     ↑            │
                     └────────────┘  (loop until done or max iterations)
```

- **State**: `AgentState` TypedDict (prompt, history, kb_context, tool_calls, response)
- **Iteration Control**: `MAX_REACT_ITERATIONS` env var (default 5), `should_continue()` edge
- **Guardrail Injection**: Input guardrails in `reason()`, output guardrails in `generate_response()`

## Detail: LLM Layer

| Provider         | Use Case              | Selection                       |
| ---------------- | --------------------- | ------------------------------- |
| Ollama           | Local dev, zero cost  | Default — `LLM_PROVIDER=ollama` |
| Azure OpenAI     | Enterprise compliance | `LLM_PROVIDER=azure-openai`     |
| OpenAI           | Latest models         | `LLM_PROVIDER=openai`           |
| Azure AI Foundry | Managed deployment    | `LLM_PROVIDER=azure-foundry`    |

Runtime switching via `POST /models/switch`. Per-model capabilities exposed on `GET /models`.

## Detail: RAG Pipeline

```
Ingest:   Document → Chunk (1000/200) → Embed → ChromaDB collection
Retrieve: Query → Embed → Similarity search → Top-K context → Inject into prompt
```

**Retrieval Modes** (per-agent `retrieval_mode`):

- `basic` — Direct ChromaDB cosine similarity
- `hybrid` — Keyword + vector search combined
- `reranked` — Cross-encoder reranking
- `sentence_window` — Surrounding sentence context
- `auto_merging` — Hierarchical chunk merging

## Detail: Tool Execution

35 tools, split across two services:

| Location                   | Tools                                                                                           | Why                              |
| -------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------- |
| tools-service (HTTP)       | math, http_fetch, file ops, datetime, web_search, code_execute, etc.                            | Crash isolation, SSRF protection |
| agent-service (in-process) | vector_search, vector_store, delegate_to_agent, advanced_search, query_database, query_csv_data | Low-latency RAG + delegation     |

**Sandboxing**: URL whitelist, blocked imports, filename sanitisation, 10s timeout, AST-safe eval.

### Tool Reference

| #   | Tool                   | Type  | Endpoint                         | Parameters                                                                                                     | Status                        |
| --- | ---------------------- | ----- | -------------------------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| 1   | `math`                 | proxy | POST /tools/math                 | `expression` (string)                                                                                          | ✅                            |
| 2   | `http_fetch`           | proxy | POST /tools/http-fetch           | `url` (string)                                                                                                 | ⚠️ Requires external internet |
| 3   | `file_write`           | proxy | POST /tools/file-write           | `filename` (string), `content` (string)                                                                        | ✅                            |
| 4   | `file_read`            | proxy | POST /tools/file-read            | `filename` (string)                                                                                            | ✅                            |
| 5   | `file_list`            | proxy | POST /tools/file-list            | `directory` (string), `pattern` (string)                                                                       | ✅                            |
| 6   | `file_search_content`  | proxy | POST /tools/file-search-content  | `query` (string), `pattern` (string), `max_results` (int)                                                      | ✅                            |
| 7   | `datetime_tool`        | proxy | POST /tools/datetime             | _(none)_                                                                                                       | ✅                            |
| 8   | `web_search`           | proxy | POST /tools/web-search           | `query` (string), `max_results` (int)                                                                          | ✅                            |
| 9   | `code_execute`         | proxy | POST /tools/code-execute         | `code` (string), `language` (string)                                                                           | ✅                            |
| 10  | `text_summarize`       | proxy | POST /tools/text-summarize       | `text` (string), `max_sentences` (int)                                                                         | ✅                            |
| 11  | `text_transform`       | proxy | POST /tools/text-transform       | `text` (string), `operation` (string)                                                                          | ✅                            |
| 12  | `text_diff`            | proxy | POST /tools/text-diff            | `text_a` (string), `text_b` (string), `context_lines` (int)                                                    | ✅                            |
| 13  | `text_extract`         | proxy | POST /tools/text-extract         | `text` (string), `extract_type` (string)                                                                       | ✅                            |
| 14  | `json_transform`       | proxy | POST /tools/json-transform       | `data` (string), `operation` (string), `jq_path` (string)                                                      | ✅                            |
| 15  | `csv_parse`            | proxy | POST /tools/csv-parse            | `csv_text` (string), `operation` (string), `filter_column` (string), `filter_value` (string), `max_rows` (int) | ✅                            |
| 16  | `yaml_convert`         | proxy | POST /tools/yaml-convert         | `content` (string), `direction` (string)                                                                       | ✅                            |
| 17  | `base64_codec`         | proxy | POST /tools/base64-codec         | `text` (string), `operation` (string)                                                                          | ✅                            |
| 18  | `hash_generate`        | proxy | POST /tools/hash-generate        | `text` (string), `algorithm` (string)                                                                          | ✅                            |
| 19  | `uuid_generate`        | proxy | POST /tools/uuid-generate        | `count` (int)                                                                                                  | ✅                            |
| 20  | `regex_match`          | proxy | POST /tools/regex-match          | `text` (string), `pattern` (string), `flags` (string)                                                          | ✅                            |
| 21  | `url_parse`            | proxy | POST /tools/url-parse            | `url` (string)                                                                                                 | ✅                            |
| 22  | `html_strip`           | proxy | POST /tools/html-strip           | `html` (string), `keep_links` (bool)                                                                           | ✅                            |
| 23  | `markdown_to_html`     | proxy | POST /tools/markdown-to-html     | `markdown` (string)                                                                                            | ✅                            |
| 24  | `webpage_extract`      | proxy | POST /tools/webpage-extract      | `url` (string), `max_length` (int)                                                                             | ⚠️ Requires external internet |
| 25  | `dns_lookup`           | proxy | POST /tools/dns-lookup           | `hostname` (string)                                                                                            | ✅                            |
| 26  | `json_schema_validate` | proxy | POST /tools/json-schema-validate | `data` (string), `schema_def` (string)                                                                         | ✅                            |
| 27  | `cron_parse`           | proxy | POST /tools/cron-parse           | `expression` (string)                                                                                          | ✅                            |
| 28  | `jwt_decode`           | proxy | POST /tools/jwt-decode           | `token` (string)                                                                                               | ✅                            |
| 29  | `environment_info`     | proxy | POST /tools/environment-info     | _(none)_                                                                                                       | ✅                            |
| 30  | `delegate_to_agent`    | local | in-process                       | `agent_id` (string), `task` (string)                                                                           | ✅                            |
| 31  | `vector_search`        | local | in-process (ChromaDB)            | `query` (string), `k` (int)                                                                                    | ✅                            |
| 32  | `vector_store`         | local | in-process (ChromaDB)            | `text` (string), `source` (string)                                                                             | ✅                            |
| 33  | `advanced_search`      | local | in-process (LlamaIndex)          | `query` (string), `mode` (string), `k` (int)                                                                   | ✅                            |
| 34  | `query_database`       | local | in-process (SQL)                 | `question` (string), `connection_string` (string), `tables` (string)                                           | ✅                            |
| 35  | `query_csv_data`       | local | in-process (Pandas)              | `question` (string), `csv_path` (string)                                                                       | ✅                            |

**⚠️ Network-dependent tools**: `http_fetch` and `webpage_extract` require outbound internet access from the Docker container. Behind corporate proxies, set `HTTP_PROXY` / `HTTPS_PROXY` environment variables in docker-compose.yml for the `tools-service`.

## Detail: Guardrails

```
Input:  PII detection, prompt injection (17 patterns), toxicity, topic restriction
Output: PII flagging, data-leak blocking, toxicity, length enforcement, hallucination check
```

- Single LLM call evaluates all enabled guardrails simultaneously
- Azure content filter auto-triggers toxicity detection
- Regex fallback ensures availability if LLM fails
- Per-agent guardrail assignment via `guardrail_ids`

## Detail: Skill Workflow

When an agent has 2+ skills attached, the Agent Builder displays a visual workflow editor:

| Mode       | Behavior                                                             |
| ---------- | -------------------------------------------------------------------- |
| Sequential | Skills execute in user-defined order — drag to reorder               |
| Router     | LLM dynamically selects the best skill per request (fan-out pattern) |

- Workflow config (`workflow_mode`, `workflow_order`) persisted with agent definition
- Visual flow: Start node → skill nodes (numbered, with tool counts) → End node
- Drag-and-drop reordering in sequential mode

## Traceability Matrix

| Capability      | Service                                   | Key File                                  |
| --------------- | ----------------------------------------- | ----------------------------------------- |
| Agent Reasoning | agent-service                             | `graph.py`                                |
| LLM Abstraction | agent-service                             | `llm.py`                                  |
| Knowledge/RAG   | agent-service + chromadb                  | `vectorstore.py`, `advanced_retrieval.py` |
| Memory          | agent-service                             | `memory.py`                               |
| Tool Execution  | tools-service + agent-service             | `tools.py`, tools `main.py`               |
| Guardrails      | agent-service                             | `graph.py`                                |
| Config Store    | agent-service                             | `memory.py`                               |
| A2A / MCP       | agent-service                             | `main.py`                                 |
| Observability   | otel, langfuse, prometheus, loki, grafana | `observability.py`                        |
| Workflows       | n8n                                       | `n8n/workflows/`                          |
| Dashboard       | ui-console                                | `server.js`, `views/`                     |
| Auth & IAM      | agent-service + ui-console + ui-login     | `memory.py`, `main.py`, `server.js`       |
| Connectors      | agent-service                             | `connectors/`                             |
