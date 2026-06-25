<!--
  GitHub Topics (set these in repo settings → About → Topics):
  ai-agents, llm, langchain, langgraph, rag, ollama, openai, azure-openai,
  mcp, a2a-protocol, multi-agent, agent-framework, vector-database, chromadb,
  observability, langfuse, fastapi, docker, self-hosted, ai-platform
-->

<div align="center">

# 🤖 Agentic Platform

### The open-source agent factory I wish existed when I started building AI apps.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-One%20Command-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![LangGraph](https://img.shields.io/badge/LangGraph-ReAct%20Agent-1C3C3C?logo=langchain&logoColor=white)](#the-stack--why-every-piece-matters)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLMs-000000?logo=ollama&logoColor=white)](#the-stack--why-every-piece-matters)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)
[![145 API Endpoints](https://img.shields.io/badge/API-145%20Endpoints-orange)](#-whats-inside)
[![16 Services](https://img.shields.io/badge/Services-16%20Containers-purple)](#-whats-inside)

**One `docker compose up` → 16 containers → your own AI agent factory, running locally, with zero API costs.**

[Quick Start](#-quick-start) · [Why Fork This](#-why-fork-this) · [The Stack](#the-stack--why-every-piece-matters) · [Screenshots](#-screenshots) · [Architecture](docs/ARCHITECTURE.md) · [Install Guide](INSTALL.md)

</div>

> **TL;DR** — 16 services, 145 API endpoints, 26-page dashboard, 4 LLM providers (+ Anthropic/Gemini/Groq/Mistral on the roadmap), full RAG pipeline, multi-agent orchestration, persona-based RBAC, end-to-end observability with LLM cost tracking — all running locally with one command.

---

## 👋 Hey — a word from the builder

I'm Rachit — a solo developer who got tired of the gap between _"cool AI demo"_ and _"production-ready AI system."_

Every agent framework I tried gave me one piece of the puzzle: a ReAct loop here, a vector store there, maybe tracing if I wired it up myself. But nowhere could I find a single repo where I could spin up a full agent factory — agents, skills, prompts, knowledge base, memory, tool servers, workflows, tracing, evaluation, observability — all wired together, all running locally, all under my control.

So I built it. Nights and weekends. One service at a time.

This isn't a tutorial. It's not a toy. It's the platform I actually use to prototype, evaluate, and ship AI agents — and I'm sharing it because I think **every developer deserves a full-stack agent lab they can run on their laptop.**

If you're the kind of person who'd rather understand the full picture than glue SaaS APIs together — you're in the right place.

---

## � How This Compares

| Feature                   | Agentic Platform | LangServe | Dify | AutoGen | CrewAI |
| ------------------------- | :--------------: | :-------: | :--: | :-----: | :----: |
| Full UI dashboard         |   ✅ 26 pages    |    ❌     |  ✅  |   ❌    |   ❌   |
| Local LLMs (zero cost)    |    ✅ Ollama     |    ❌     |  ✅  |   ❌    |   ❌   |
| Multi-agent orchestration |        ✅        |    ❌     |  ⚠️  |   ✅    |   ✅   |
| RAG pipeline              |   ✅ Auto-RAG    |    ❌     |  ✅  |   ❌    |   ⚠️   |
| MCP tool servers          |    ✅ Managed    |    ❌     |  ❌  |   ❌    |   ❌   |
| A2A protocol              |        ✅        |    ❌     |  ❌  |   ⚠️    |   ⚠️   |
| Persona RBAC              |        ✅        |    ❌     |  ⚠️  |   ❌    |   ❌   |
| End-to-end observability  |  ✅ Full stack   |    ❌     |  ⚠️  |   ❌    |   ❌   |
| One-command deploy        |    ✅ Docker     |    ⚠️     |  ✅  |   ❌    |   ❌   |
| 100% open source          |      ✅ MIT      |    ✅     |  ⚠️  |   ✅    |   ⚠️   |

> ⚠️ = Partial or requires additional setup

---

## �📸 Screenshots

<details>
<summary><b>Click to expand — Dark & Light themes</b></summary>

> **Coming soon** — screenshots of the dashboard, agent builder, persona switcher, admin panel, and more. In the meantime, run it locally — it's one command!

</details>

---

## 🎯 Why Fork This

Most agent repos give you a chatbot. This gives you a **factory**.

| What you get                   | Why it matters                                                                                                                                                                                                         |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent Registry**             | Create dozens of agents, each with its own model, skills, tools, knowledge, and personality — not just one hardcoded bot                                                                                               |
| **Multi-Agent Orchestration**  | One orchestrator agent delegates to specialist sub-agents at runtime. LLM decides who handles what. Plus n8n pipelines for sequential/parallel flows                                                                   |
| **Skills System**              | Package a prompt + tools + constraints + file attachments (scripts, references, assets) into a reusable skill. Input parameters let skills prompt for structured data at runtime                                       |
| **4 LLM Providers**            | Ollama (free, local), OpenAI, Azure OpenAI, Azure AI Foundry — switch models from the UI, no code changes                                                                                                              |
| **Auto-RAG**                   | Upload a PDF → it's chunked, embedded, stored in ChromaDB → every prompt auto-retrieves relevant context. Per-agent isolated KB                                                                                        |
| **A2A Protocol**               | Agents can delegate sub-tasks to other agents over HTTP. Build hierarchies, not monoliths                                                                                                                              |
| **MCP Registry + Managed MCP** | Connect to external tool servers, or **create and host** your own from the UI — config mode (no-code HTTP proxies) or code mode (custom Python functions). Each managed server deploys as an isolated Docker container |
| **Full Traceability**          | Every LLM call traced in Langfuse — cost, latency, tokens, session grouping. No black boxes                                                                                                                            |
| **Responsible AI**             | PII detection, toxicity filtering, bias warnings, safety scoring — built in, not bolted on                                                                                                                             |
| **Persona-Based RBAC**         | Multi-persona role switching (inspired by Snowflake/Databricks). Admins define personas with granular nav + action permissions, assign multiple to each user, users switch at runtime — sidebar adapts instantly       |
| **26-page Dashboard**          | Not a CLI-only project. A real UI for building, running, monitoring, and integrating agents                                                                                                                            |
| **One-command setup**          | `docker compose up -d` — that's it. No Python version hell, no dependency conflicts                                                                                                                                    |
| **Enterprise IAM**             | Session-based authentication with email verification, login rate limiting, role-based access control (admin/member/viewer), per-user workspace isolation, editable profiles, admin user management panel               |

<details>
<summary><b>📋 Full feature list</b></summary>

- **Prompt Library** — Create, categorize, and tag prompt templates; attach to skills or agents
- **Conversation Memory** — SQLite-backed session summaries for rolling context across messages
- **LangGraph ReAct Agent** — State graph: retrieve context → reason → execute tools → respond
- **Skill Files** — Attach scripts, reference docs, and template assets to any skill — files are per-skill isolated and auto-injected into agent context
- **9 Built-in Tools** — Math, HTTP fetch, file I/O, datetime, web search, code execution, text transforms, JSON/CSV/YAML ops, regex, hashing, vector search & ingest
- **Multi-Agent Delegation** — Orchestrator agents delegate to sub-agents via `delegate_to_agent` tool; LLM decides routing
- **MCP Runtime Integration** — Agents with bound MCP servers see MCP tools in their system prompt and invoke them natively in the ReAct loop — no manual wiring
- **Managed MCP Servers** — Create and host MCP servers from the UI: config mode (HTTP endpoint proxies) or code mode (Python functions). Each deploys as an isolated Docker container
- **Per-Agent Knowledge Base** — Each agent gets its own isolated ChromaDB collection; documents don't cross-contaminate
- **Evaluation Matrix** — Quality scoring (faithfulness, relevance, coherence) across models and agents
- **Workflow Orchestration** — n8n workflows for scheduled tasks, webhooks, web research, RAG ingestion, multi-agent pipelines
- **Full Observability** — Prometheus + Grafana dashboards + Loki logs + OpenTelemetry pipeline
- **Security Hardening** — XSS protection, input validation, SSRF protection, path traversal prevention
- **Enterprise Authentication** — Login page with gate animation, session-based auth (express-session), bcrypt password hashing, email verification with 6-digit codes, login rate limiting (5 attempts per 5-minute window per IP), role-based access control (admin/member/viewer), user management UI in admin panel, editable profile with display name, change password with current-password verification
- **Persona System** — Multi-persona RBAC inspired by Snowflake/Databricks: define personas with granular navigation + action permissions, assign multiple personas per user, switch active persona at runtime from the sidebar, UI adapts instantly (nav items show/hide, actions gate). 4 seed personas (Admin, Developer, Analyst, Viewer)
- **Workspace & RBAC** — Multi-tenant workspace isolation, scope-aware resources (global vs workspace), role-gated admin access, per-user default workspace, admin-created users are pre-verified
- **Data Connectors** — Hybrid ingestion framework: built-in connectors (Database, REST API, Cloud Storage, Google Drive, SharePoint) with full ETL pipeline visualization
- **Marketplace** — Browse and install agent/skill/workflow templates
- **Dark & Light Themes** — Full theme support with CSS custom properties, smooth transitions, theme-aware components
- **GPU Support** — Uncomment one block in docker-compose.yml for NVIDIA GPU acceleration

</details>

---

## The Stack — Why Every Piece Matters

This isn't a random grab bag of tools. Every layer was chosen because it solves a real problem I hit while building agents:

```
┌─────────────────────────────────────────────────────────────────┐
│  🖥️  UI Console (Express.js + EJS)                :3005        │
│  26 pages — build, run, evaluate, trace agents from the browser│
├─────────────────────────────────────────────────────────────────┤
│  🧠 Agent Service (FastAPI + LangGraph)            :8010        │
│  ReAct agent loop, 145 endpoints, skill/agent/persona registry │
├──────────────────────┬──────────────────────────────────────────┤
│  🔧 Tools Service    │  📚 ChromaDB        │  💾 SQLite         │
│  :8011               │  :8200              │  (embedded)        │
│  32 tool endpoints   │  Vector store / RAG │  Memory & registry │
├──────────────────────┴──────────────────────┴───────────────────┤
│  🤖 LLM Layer                                                  │
│  Ollama (local) · OpenAI · Azure OpenAI · Azure AI Foundry     │
├─────────────────────────────────────────────────────────────────┤
│  📡 Observability                                               │
│  Langfuse (traces) · Prometheus (metrics) · Grafana (dashboards)│
│  Loki (logs) · OpenTelemetry Collector (pipeline)               │
├─────────────────────────────────────────────────────────────────┤
│  ⚡ Orchestration                                               │
│  n8n (workflows, webhooks, scheduled jobs)                      │
└─────────────────────────────────────────────────────────────────┘
```

**Why this specific stack?**

| Layer             | Tech                            | Why                                                                                       |
| ----------------- | ------------------------------- | ----------------------------------------------------------------------------------------- |
| **Agent runtime** | LangGraph + LangChain           | State-machine agent with full control over the ReAct loop — not a black-box `agent.run()` |
| **API layer**     | FastAPI                         | Async, typed, auto-docs — 145 endpoints. Agents need to be APIs, not scripts              |
| **Local LLMs**    | Ollama                          | Zero API costs during development. Pull a model, use it instantly                         |
| **Cloud LLMs**    | OpenAI / Azure OpenAI / Foundry | When you need GPT-4o or enterprise compliance — just set env vars                         |
| **Vector store**  | ChromaDB                        | Embedded, no external infra, persists across restarts. RAG that just works                |
| **Tracing**       | Langfuse                        | See every LLM call: prompt, response, cost, latency. Non-negotiable for production        |
| **Observability** | Prometheus + Grafana + Loki     | Industry-standard monitoring. Not a toy dashboard — real SRE tooling                      |
| **Workflows**     | n8n                             | Visual automation — schedule RAG ingestion, chain agents, trigger webhooks                |
| **Dashboard**     | Express.js + EJS                | Server-rendered, fast, no build step. 26 pages for full platform control                  |
| **Identity**      | bcrypt + express-session        | Enterprise IAM with persona-based RBAC, not just simple API keys                          |

---

## 🚀 Quick Start

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop) (8 GB RAM minimum)

```bash
git clone https://github.com/rachit0412/agentic-platform.git
cd agentic-platform
docker compose up -d --build
docker exec ollama ollama pull llama3    # first time only (~4 GB)
```

Open **http://localhost:3005** — you're running a full agent factory.

> 📖 **Detailed installation** (Windows/Mac/Linux, GPU setup, troubleshooting): **[INSTALL.md](INSTALL.md)**

### Authentication & Personas

The platform ships with enterprise-grade authentication and persona-based access control:

| Feature                 | Details                                                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Login**               | Session-based auth with bcrypt password hashing, rate limiting (5 attempts / 5 min per IP)                                                 |
| **Registration**        | Self-service with 6-digit email verification code                                                                                          |
| **User Roles**          | `admin`, `member`, `viewer` — admin-only pages are role-gated                                                                              |
| **Personas**            | Multi-persona RBAC — assign personas (Admin, Developer, Analyst, Viewer) to users, switch at runtime from the sidebar, UI adapts instantly |
| **Profile**             | Editable display name from the user dropdown menu                                                                                          |
| **Change Password**     | Requires current password verification before allowing change                                                                              |
| **Admin Panel**         | Full user management — create, edit, delete, verify, enable/disable users + persona admin                                                  |
| **Default Credentials** | `admin` / `Admin@Platform2026!`                                                                                                            |

### Your first agent in 60 seconds

1. **Skills** → Create a skill (name it, write a prompt, pick tools, optionally upload scripts/references/assets)
2. **Agents** → Create an agent (pick a model, attach skills, set constraints, optionally upload docs for RAG)
3. **Run Agent** → Select your agent, type a prompt, watch it reason and act in real-time
4. **Traceability** → Click the trace link to see exactly what the LLM did

### Or use the API

```bash
curl -X POST http://localhost:8010/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 42 * 13?", "sessionId": "demo"}'
```

---

## 🗺️ What's Inside

### Services (16 containers)

| Service              | Port    | Purpose                                                                                     |
| -------------------- | ------- | ------------------------------------------------------------------------------------------- |
| **ui-console**       | `3005`  | Platform dashboard — 26 pages for building, running, monitoring agents                      |
| **agent-service**    | `8010`  | FastAPI + LangGraph — 145 endpoints: ReAct agent, registry, auto-RAG, personas, managed MCP |
| **tools-service**    | `8011`  | 32 endpoints: web search, code exec, HTTP fetch, file I/O, text transforms, more            |
| **ollama**           | `11436` | Local LLM runtime — llama3, mistral, deepseek-r1, and more                                  |
| **chromadb**         | `8200`  | Vector store for knowledge base and RAG retrieval                                           |
| **datastore-db**     | `5433`  | PostgreSQL 16 for structured data and connector state                                       |
| **n8n**              | `5678`  | Workflow orchestration, webhooks, multi-agent pipelines, and scheduled automation           |
| **n8n-proxy**        | `5679`  | Reverse proxy for n8n cross-origin access                                                   |
| **brave-search-mcp** | —       | Pre-built managed MCP server for Brave web search                                           |
| **open-tools-mcp**   | —       | MCP server exposing 60+ community tools (filesystem, math, web, AI, dev)                    |
| **langfuse**         | `3012`  | LLM tracing, cost tracking, evaluation, prompt analytics                                    |
| **grafana**          | `3013`  | Monitoring dashboards (pre-configured with Prometheus + Loki)                               |
| **prometheus**       | `9090`  | Metrics collection and alerting                                                             |
| **loki**             | `3100`  | Log aggregation from all services                                                           |
| **otel-collector**   | `4317`  | OpenTelemetry pipeline — traces, metrics, logs routing                                      |
| **langfuse-db**      | —       | PostgreSQL backend for Langfuse (internal)                                                  |

### Dashboard Pages (26)

| Page             | What you do there                                                                                                                                                                                                                                         |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overview         | Platform stats, architecture, quick-start guide                                                                                                                                                                                                           |
| Run Agent        | Execute agents, stream responses, browse sessions                                                                                                                                                                                                         |
| Agent Builder    | Visual agent composition with skill workflow orchestration, sub-agents, and live test                                                                                                                                                                     |
| AI Studio        | IDE-style code editor with chat, preview, and projects                                                                                                                                                                                                    |
| Agent Hub        | Agent factory overview dashboard                                                                                                                                                                                                                          |
| Agent Registry   | Create and manage agent definitions                                                                                                                                                                                                                       |
| Skills           | Build reusable skill packages with file attachments (scripts, references, assets). Platform-wide settings (security, best practices) shown read-only                                                                                                      |
| Prompts          | Prompt template library                                                                                                                                                                                                                                   |
| Tools            | Manage agent tools and capabilities                                                                                                                                                                                                                       |
| Knowledge Base   | Upload, search, manage RAG docs                                                                                                                                                                                                                           |
| Workflows        | n8n workflow monitoring                                                                                                                                                                                                                                   |
| A2A Protocol     | Register peer agents for inter-agent delegation                                                                                                                                                                                                           |
| MCP Registry     | Create, host, and manage MCP tool servers — config mode (no-code), code mode (Python), or register external servers                                                                                                                                       |
| REST Console     | Interactive API console — test all 145 endpoints                                                                                                                                                                                                          |
| Intelligence Hub | Operational intelligence — traces, LLM cost & token analytics, guardrail status, model breakdown chart, recent call table, 8-stat dashboard                                                                                                               |
| Traceability     | Langfuse trace timeline and deep-dive                                                                                                                                                                                                                     |
| Evaluation       | Agent quality scoring and model comparison                                                                                                                                                                                                                |
| Observability    | Stack health — Prometheus, Grafana, Loki status                                                                                                                                                                                                           |
| Guardrails       | Runtime safety controls and policy enforcement                                                                                                                                                                                                            |
| Data Ingestion   | ETL pipeline — Extract (5 connectors), Transform (chunking, embedding), Load (ChromaDB)                                                                                                                                                                   |
| LLM Activity     | Full token usage log — per-call provider/model/tokens/cost/latency, cost trend chart, model comparison breakdown                                                                                                                                          |
| Marketplace      | Browse and install templates                                                                                                                                                                                                                              |
| Admin            | 8-tab admin plane — service health, **user & access management**, **persona definitions & user persona assignments**, platform overview, LLM management, DB & data, config (security, best practices), audit log. Role-gated: only admin users can access |
| Documentation    | Auto-generated API & architecture docs                                                                                                                                                                                                                    |

---

## 🧬 How the Agent Thinks

```
User Prompt
  │
  ▼
┌──────────────────────────────────────────┐
│  1. Retrieve context (ChromaDB → RAG)    │
│  2. Load memory (SQLite → session)       │
│  3. Inject skills + files + system prompt │
│  3b. Bind MCP tools (per-agent)          │
│  4. LLM reasoning (ReAct loop)           │
│  5. Tool execution (if needed)           │
│  5b. MCP tool invocation (if needed)     │
│  5c. Delegate to sub-agent (if needed)   │
│  6. Generate response                    │
│  7. Save memory + emit traces            │
└──────────────────────────────────────────┘
  │
  ├──→ Langfuse (full trace)
  ├──→ OpenTelemetry (metrics + logs)
  └──→ Response to user
```

> Deep dive: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — embedding pipeline, LLM provider details, protocol specs

---

## 🔧 Configuration

All ports and credentials are configurable via environment variables. Copy `.env.example` to `.env` and customise:

```bash
cp .env.example .env
```

Key settings:

| Variable               | Default  | What it does                                                              |
| ---------------------- | -------- | ------------------------------------------------------------------------- |
| `LLM_PROVIDER`         | `ollama` | Default LLM backend (`ollama`, `azure-openai`, `openai`, `azure-foundry`) |
| `OLLAMA_MODEL`         | `llama3` | Default local model                                                       |
| `AZURE_OPENAI_API_KEY` | —        | Enables Azure OpenAI models                                               |
| `OPENAI_API_KEY`       | —        | Enables OpenAI models                                                     |
| `UI_PORT`              | `3005`   | Dashboard port                                                            |

> Full configuration reference with 20+ variables: see the **Configuration** section in **[INSTALL.md](INSTALL.md)**

---

## 🧪 Testing

The platform has **459 automated tests** across Python and JavaScript:

```bash
# All Python tests (156 tests — comprehensive platform + API endpoint coverage)
python -m pytest tests/e2e/test_platform_comprehensive.py tests/e2e/test_api_endpoints.py -v

# UI Console tests (29 tests — Express routes, proxies, marketplace)
cd services/ui-console && node node_modules/jest/bin/jest.js --forceExit

# Smoke test (service health)
bash tests/smoke/smoke-test.sh

# Load test (k6)
k6 run tests/load/load-test.js
```

**Test coverage includes:**

- Data ingestion (connectors, sync jobs, document lifecycle)
- Agent CRUD and multi-agent orchestration
- Skills (with file upload/download/delete), prompts, custom tools management
- A2A protocol and MCP registry
- Guardrails (input/output safety gates)
- Versioning and audit logging
- Export/import, sessions, model switching
- UI routes, API proxies, marketplace install/uninstall

---

## 📁 Project Structure

```
agentic-platform/
├── docker-compose.yml           # All 16 containers — one command to rule them all
├── README.md                    # You are here
├── INSTALL.md                   # Detailed install guide (Windows/Mac/Linux/GPU)
├── CONTRIBUTING.md              # Contribution guidelines
├── docs/ARCHITECTURE.md         # Deep-dive architecture & protocols
├── services/
│   ├── agent/                   # 🧠 FastAPI + LangGraph agent (145 API endpoints)
│   │   └── agent/connectors/    # 🔌 Data connectors (DB, API, Cloud, Drives)
│   ├── managed-mcp-base/        # 🔗 Generic MCP server runtime (config + code modes)
│   ├── open-tools-mcp/          # 🧰 Community tool server (60+ tools via MCP)
│   ├── tools/                   # 🔧 FastAPI tool endpoints (32 endpoints)
│   ├── ui-console/              # 🖥️  Express.js dashboard (26 pages)
│   │   └── views/               # 📄 EJS templates (dark/light theme support)
│   └── otel/                    # 📡 OpenTelemetry collector config
├── n8n/workflows/               # ⚡ Pre-built n8n workflow templates (incl. multi-agent orchestration)
├── observability/               # 📊 Grafana dashboards, Prometheus, Loki config
└── tests/                       # 🧪 Unit, integration, e2e, contract, load, smoke
```

---

## 📖 Documentation

| Doc                                                    | What's in it                                                                                        |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| **[INSTALL.md](INSTALL.md)**                           | Full installation guide — Windows, Mac, Linux, GPU setup, troubleshooting, all 20+ config variables |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**       | Deep-dive — embedding pipeline, LLM providers, telemetry flow, protocol specs, service map          |
| **[CONTRIBUTING.md](CONTRIBUTING.md)**                 | How to contribute — code style, PR workflow, development setup                                      |
| **[docs/PRINCIPLES.md](docs/PRINCIPLES.md)**           | Architecture principles — the "why" behind every design decision                                    |
| **[docs/BUILDING-BLOCKS.md](docs/BUILDING-BLOCKS.md)** | Building blocks — how each component fits together                                                  |
| **[docs/DECISIONS.md](docs/DECISIONS.md)**             | Architecture decision records — tradeoffs and rationale                                             |

---

## 🆕 What's New

<details>
<summary><b>Latest changes</b></summary>

### Persona-Based RBAC

- **Multi-persona system** inspired by Snowflake/Databricks — a single user can have multiple personas (e.g., an admin can switch between Admin and Developer views)
- **4 seed personas**: Admin (full access), Developer (build & test), Analyst (data & reports), Viewer (read-only)
- **Granular permissions**: each persona defines allowed navigation items and action capabilities
- **Runtime switching**: click a persona chip in the sidebar → nav adapts instantly, no page reload
- **Admin UI**: dedicated Personas tab in admin panel for creating/editing personas and managing user assignments

### Intelligence Hub & LLM Observability Upgrade

- **8-stat dashboard** — expanded from 4 to 8 KPI cards: traces, agents, health, + LLM calls, total tokens, estimated cost, guardrail status
- **LLM Activity & Cost Analysis** — new section with per-model token breakdown bar chart, cost/token trend (Chart.js), and last-8-calls table
- **Real-time cost tracking** — `estimated_cost` computed per call from token counts and stored in the `llm_usage_log` table
- **Guardrail status widget** — shows active/total guardrails inline in the hub

### Architecture Section Refresh

- **Overview page architecture diagram** updated with 2025/2026 roadmap technologies
- Added planned providers: `Anthropic Claude`, `Google Gemini`, `Groq`, `Mistral AI`
- Added planned frameworks: `LangGraph HITL`, `Checkpointing`, `Structured Output`
- Added planned protocols: `Google A2A (open)`, `MCP 1.x Streamable HTTP Transport`
- Added planned knowledge: `Hybrid Search (BM25+Vec)`, `Re-Ranking`
- Added planned guardrails: `Azure AI Content Safety`, `Jailbreak Detection`

### Platform Expansion

- **16 containers** (up from 14) — added PostgreSQL datastore, Brave Search MCP, Open Tools MCP
- **145 API endpoints** (up from 117) — personas, structured query, enhanced connectors
- **26 dashboard pages** (up from 25)
- **Dark & light themes** with full CSS custom property support
- **Login rate limiting** — 5 attempts per 5-minute window per IP
- **bcrypt password hashing** (upgraded from PBKDF2)

</details>

---

## 🗺️ Roadmap

Have ideas? [Open an issue](https://github.com/rachit0412/agentic-platform/issues) or start a [discussion](https://github.com/rachit0412/agentic-platform/discussions).

- [ ] Agent-to-agent real-time streaming
- [ ] Plugin SDK for custom UI pages
- [ ] Multi-model agent routing (cost vs quality)
- [ ] Kubernetes deployment manifests
- [ ] OAuth2 / SSO integration (Google, GitHub, Microsoft)
- [ ] Mobile-responsive dashboard
- [ ] Anthropic Claude, Google Gemini, Groq, Mistral AI providers
- [ ] LangGraph HITL (human-in-the-loop interrupt nodes)
- [ ] LangGraph Checkpointing (persistent state across runs)
- [ ] Structured Output mode (JSON enforcement via Pydantic)
- [ ] Google A2A interoperability standard
- [ ] MCP 1.x Streamable HTTP transport
- [ ] Hybrid Search (BM25 + vector) + Re-ranking
- [ ] Response Feedback UI (thumbs up/down)
- [ ] Prompt Auto-Optimizer
- [ ] Azure AI Content Safety + Jailbreak Detection
- [ ] LLM-as-Judge evaluation
- [ ] Policy-as-Code (OPA/Rego), AI Governance Framework (ISO 42001)

---

## 🤝 Contributing

I built this solo, but I'd love collaborators. Whether it's a bug fix, a new tool, a better prompt template, or a whole new agent type — PRs are welcome.

```bash
git clone https://github.com/YOUR_USERNAME/agentic-platform.git
cd agentic-platform
docker compose up -d --build
# hack away, then open a PR
```

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

---

## 📄 License

MIT — use it, fork it, ship it. See [LICENSE](LICENSE).

---

<div align="center">

---

### 🌟 If this saves you time, consider giving it a ⭐

It helps others find this project and motivates continued development.

**Built with mass mass mass amounts of caffeine by [Rachit](https://github.com/rachit0412)**

[![Star History Chart](https://api.star-history.com/svg?repos=rachit0412/agentic-platform&type=Date)](https://star-history.com/#rachit0412/agentic-platform&Date)

</div>
