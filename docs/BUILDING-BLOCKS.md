# Building Blocks

> ABBs (Architecture Building Blocks) define capabilities. SBBs (Solution Building Blocks) map each to concrete technology.

## Core Platform

| #   | Capability                 | Technology                                                         | Source                                        |
| --- | -------------------------- | ------------------------------------------------------------------ | --------------------------------------------- |
| 1   | Agent Reasoning Engine     | LangGraph ReAct StateGraph                                         | `graph.py`                                    |
| 2   | LLM Abstraction            | LangChain BaseChatModel — Ollama, Azure OpenAI, OpenAI, Foundry    | `llm.py`                                      |
| 3   | Knowledge Management (RAG) | ChromaDB + LlamaIndex + PostgreSQL doc registry                    | `vectorstore.py`, `advanced_retrieval.py`     |
| 4   | Conversation Memory        | SQLite conversations + rolling session summaries                   | `memory.py`                                   |
| 5   | Tool Execution             | tools-service FastAPI (sandboxed) + delegate_to_agent              | `tools.py`, tools `main.py`                   |
| 6   | Guardrails Engine          | LLM-based classifier + regex fallback, input & output gates        | `graph.py`                                    |
| 7   | Configuration Store        | SQLite CRUD — 15 tables, full versioning & audit                   | `memory.py`                                   |
| 7b  | Skill File Store           | Disk-based per-skill isolated file storage (scripts, refs, assets) | `memory.py`, `/data/filestore/skills/`        |
| 8   | A2A Protocol               | HTTP peer registry, agent cards, task dispatch                     | `main.py`                                     |
| 9   | MCP Protocol               | Server registry, JSON-RPC tool discovery & invocation              | `main.py`                                     |
| 10  | Observability              | OTel + Langfuse + Prometheus + Loki + Grafana                      | `observability.py`                            |
| 11  | Workflow Automation        | n8n — 6 pre-built templates incl. multi-agent orchestration        | `n8n/workflows/`                              |
| 12  | Platform Dashboard         | Express.js + EJS, 24 pages, thin API proxy                         | `server.js`, `views/`                         |
| 13  | Multi-Agent Orchestration  | sub_agent_ids + delegate_to_agent + n8n DAGs                       | `tools.py`, `graph.py`                        |
| 13b | Skill Workflow             | Sequential / Router skill execution ordering in Agent Builder      | `agent-builder.ejs`                           |
| 14  | Data Connectors            | DB, REST API, Cloud Storage, Google Drive, SharePoint, Airbyte     | `connectors/`                                 |
| 15  | LlamaIndex Integration     | Multi-format parsing, 5 retrieval modes, structured queries        | `llamaindex_loader.py`, `structured_query.py` |

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

| Location                   | Tools                                                                | Why                              |
| -------------------------- | -------------------------------------------------------------------- | -------------------------------- |
| tools-service (HTTP)       | math, http_fetch, file ops, datetime, web_search, code_execute, etc. | Crash isolation, SSRF protection |
| agent-service (in-process) | vector_search, vector_store, delegate_to_agent                       | Low-latency RAG + delegation     |

**Sandboxing**: URL whitelist, blocked imports, filename sanitisation, 10s timeout, AST-safe eval.

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
| Connectors      | agent-service                             | `connectors/`                             |
