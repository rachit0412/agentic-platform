# Architecture Principles

## Maturity Model

```
┌───────────────────────────────────────────────────────┐
│  🔴 TARGET (Production)                               │
│  Identity & Access · Compliance · Elastic Scaling     │
│  Zero-Trust · Agent Lifecycle · Disaster Recovery     │
├───────────────────────────────────────────────────────┤
│  🟡 NEXT (Hardening)                                  │
│  API Versioning · Full Observability · Cost Metering  │
│  Complete Versioning · Secret Management              │
├───────────────────────────────────────────────────────┤
│  🟢 CURRENT (Foundation) ✅                            │
│  Local-First · Container-Native · Defence in Depth    │
│  Protocol Extensibility · Knowledge Mgmt · Graceful   │
│  Degradation                                          │
└───────────────────────────────────────────────────────┘
```

---

## Foundational Principles (Implemented)

### AP-1 · API-First Design · 🟡

Every capability exposed as REST before any UI is built. 69+ endpoints on agent-service. UI console is a thin proxy with zero business logic.

**Gap**: No `/v1/` versioning prefix yet.

### AP-2 · Local-First, Cloud-Ready · 🟢 ✅

Runs fully offline with Ollama. Switch to cloud LLMs via `LLM_PROVIDER` env var or `POST /models/switch` at runtime. No code changes needed.

### AP-3 · Container-Native Composability · 🟢 ✅

All services are Docker containers defined in `docker-compose.yml`. Internal communication via Docker bridge network. Health checks enforce startup ordering. All ports configurable via env vars.

### AP-4 · Defence in Depth · 🟢 ✅

Security is layered: input guardrails → tool sandboxing → output guardrails → SSRF protection. Each layer operates independently. Code execution blocks dangerous imports. HTTP fetch uses URL whitelist.

### AP-5 · Observable by Default · 🟡

Three telemetry pipelines: OTel → Prometheus/Loki, Langfuse SDK → LLM traces, Prometheus histograms on `/metrics`.

**Gap**: Telemetry is opt-in (requires keys). Grafana dashboard only has Prometheus panels.

### AP-6 · Protocol-Driven Extensibility · 🟢 ✅

Extends through open protocols (A2A, MCP) not proprietary plugins. Any agent framework can register as an A2A peer. Any MCP-compatible tool server integrates automatically.

### AP-7 · Separation of Concerns · 🟡

Agent reasoning, tool execution, UI rendering, and telemetry are isolated services. Each scales independently.

**Gap**: `vector_search`/`vector_store` still run in-process in agent-service for latency reasons.

### AP-8 · Knowledge as First-Class Resource · 🟢 ✅

Full CRUD on documents (24 endpoints), per-agent KB isolation, 5 retrieval modes, multi-format parsing (20+ formats), data connectors framework, cross-collection copying.

### AP-9 · Configuration over Code · 🟡

All entities (agents, skills, prompts, guardrails, tools) are runtime-configurable via CRUD APIs. Changes take effect on next agent run. Import/export and audit logging implemented.

**Gap**: No version snapshots for guardrails and custom tools.

### AP-10 · Graceful Degradation · 🟢 ✅

Platform remains functional when optional services are unavailable. Langfuse falls back to no-op. n8n is independent of agent execution. UI handles service failures gracefully.

---

## Enterprise Principles (Roadmap)

| # | Principle | Status | Key Gap |
|---|-----------|--------|---------|
| AP-11 | Identity & Access Control | 🔴 | No auth, no RBAC, all endpoints public |
| AP-12 | Cost Accountability | 🟡 | Token tracking exists; no enforcement |
| AP-13 | Elastic Scaling | 🔴 | Single-writer SQLite; no K8s |
| AP-14 | Compliance & Governance | 🔴 | No data classification or retention |
| AP-15 | Disaster Recovery | 🔴 | No automated backup or RTO/RPO |
| AP-16 | Zero-Trust Networking | 🔴 | Plain HTTP, single flat network |
| AP-17 | Agent Lifecycle Governance | 🔴 | No approval workflow or A/B testing |
| AP-18 | Secret Management | 🟡 | Secrets in env vars, no vault |

---

## Priority Roadmap

| Priority | Action | Principle |
|----------|--------|-----------|
| P1 | Pre-configure OTel endpoint in docker-compose | AP-5 |
| P1 | Add Loki + Langfuse panels to Grafana | AP-5 |
| P1 | Move secrets to vault integration | AP-18 |
| P2 | Add `/v1/` API prefix | AP-1 |
| P2 | JWT/OAuth2 middleware with RBAC | AP-11 |
| P2 | Enforce rate limiting from guardrail config | AP-12 |
| P3 | Agent lifecycle stages (draft → production) | AP-17 |
| P3 | Migrate SQLite → PostgreSQL for scaling | AP-13 |
| P4 | mTLS via service mesh | AP-16 |
| P4 | Data retention policies + GDPR delete | AP-14 |
| P4 | Automated backup + recovery runbook | AP-15 |
