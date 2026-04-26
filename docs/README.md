# Agentic Platform Documentation

Production-ready **agent factory** — build, register, and run hundreds of autonomous AI agents, each with its own model, skills, tools, knowledge base, and control logic.

## Quick Links

- [Installation Guide](../INSTALL.md)
- [Contributing](../CONTRIBUTING.md)
- [License](../LICENSE)

## Core Concepts

| Concept            | Definition                                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent**          | `LLM + Tools + Memory + Control Logic` — an autonomous loop that observes, reasons, acts, and repeats until done.                                  |
| **Skill**          | A packaged capability that performs a specific task — reusable logic + tools + optional data access. Think: _reusable function with intelligence_. |
| **Prompt**         | The instructional context given to a model or skill — defines what to do, how to behave, and what output is expected.                              |
| **Knowledge Base** | ChromaDB vector store — upload documents that the agent auto-retrieves via RAG.                                                                    |

## Overview

Complete stack for building AI agent applications with:

- **Agent Registry** — Create, configure, and manage multiple agents with independent configurations
- **Skills System** — Define reusable skill packages (prompt + tools + constraints) and attach to agents
- **Multi-Model LLM** — Switch between Ollama local models (llama3, mistral, phi3) and Azure OpenAI (gpt-4o, gpt-4o-mini) at runtime
- **LangGraph ReAct Agent** — State graph orchestration with tool calling, auto-RAG retrieval, and conversation memory
- **LangChain Integration** — LangChain Core + langchain-ollama + langchain-openai for unified LLM abstraction
- **Auto-RAG Knowledge Base** — ChromaDB vector store with inline upload from agent form and automatic context retrieval
- **Conversation Memory** — SQLite-backed rolling session summaries for multi-turn context
- **Workflow Automation** — n8n workflows for scheduled tasks, web research, and data ingestion (use n8n when you need triggers, schedules, or external API chains; use the agent directly for interactive chat)
- **Full Observability** — Langfuse LLM tracing, Prometheus metrics, Grafana dashboards, OpenTelemetry

## Service Architecture

| Service           | Port  | Purpose                                        |
| ----------------- | ----- | ---------------------------------------------- |
| **ui-console**    | 3001  | Platform dashboard & agent UI (Express.js)     |
| **agent-service** | 8010  | FastAPI + LangGraph agent with multi-model LLM |
| **tools-service** | 8011  | FastAPI tool endpoints                         |
| **ollama**        | 11436 | Local LLM runtime                              |
| **chromadb**      | 8200  | Vector store for RAG                           |
| **n8n**           | 5678  | Workflow orchestration                         |
| **langfuse**      | 3012  | LLM tracing & prompt analytics                 |
| **grafana**       | 3013  | Monitoring dashboards                          |
| **prometheus**    | 9090  | Metrics collection                             |

## API Endpoints (Agent Service — :8010)

| Endpoint                 | Method | Description                                                    |
| ------------------------ | ------ | -------------------------------------------------------------- |
| `/health`                | GET    | Health check                                                   |
| `/run`                   | POST   | Run agent (accepts prompt, sessionId, provider, model)         |
| `/run/stream`            | POST   | Run agent with SSE streaming                                   |
| `/models`                | GET    | List available models across providers                         |
| `/models/switch`         | POST   | Switch active LLM provider/model                               |
| `/skills`                | GET    | List all skills                                                |
| `/skills`                | POST   | Create a skill (name, description, prompt, tools, constraints) |
| `/skills/{id}`           | PUT    | Update a skill                                                 |
| `/skills/{id}`           | DELETE | Delete a skill                                                 |
| `/agents`                | GET    | List all registered agents                                     |
| `/agents`                | POST   | Create an agent (model, skills, tools, prompt, KB)             |
| `/agents/{id}`           | PUT    | Update an agent                                                |
| `/agents/{id}`           | DELETE | Delete an agent                                                |
| `/sessions`              | GET    | List conversation sessions                                     |
| `/sessions/{id}/summary` | GET    | Get session summary                                            |
| `/memory/stats`          | GET    | Memory & knowledge base statistics                             |
| `/documents/ingest`      | POST   | Ingest document into knowledge base                            |
| `/documents/search`      | POST   | Search knowledge base                                          |
| `/tools`                 | GET    | List available agent tools                                     |

## Tech Stack

- **Python 3.11** — Agent & tools services
- **FastAPI + Uvicorn** — Async HTTP framework
- **LangGraph 0.2.60** — Agent state graph orchestration
- **LangChain Core 0.3.29** — LLM abstraction layer
- **langchain-ollama** — Ollama LLM & embeddings provider
- **langchain-openai** — Azure OpenAI LLM provider
- **ChromaDB** — Vector database for RAG
- **SQLite** — Conversation memory storage
- **Node.js 20** — UI console (Express.js + EJS)
- **Docker Compose** — Container orchestration (12 services)
- **Langfuse** — LLM observability & tracing
- **Prometheus + Grafana** — Infrastructure monitoring
- **OpenTelemetry** — Distributed tracing
