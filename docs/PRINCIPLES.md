# Architecture Principles

## Maturity Model

**🟢 CURRENT (Foundation)** ✅
- Local-First · Container-Native · Defence in Depth  
- Protocol Extensibility · Knowledge Mgmt · Graceful Degradation  
- Identity & Access Control · Security Scanning

**🟡 NEXT (Hardening)**
- API Versioning · Full Observability · Cost Metering  
- Complete Versioning · Secret Management  
- Advanced Compliance Automation

**🔴 TARGET (Production)**
- Compliance · Elastic Scaling · Zero-Trust  
- Agent Lifecycle · Disaster Recovery  
- Multi-tenancy & High Availability

---

## Foundational Principles (Implemented)

### AP-1 · API-First Design · 🟡

Every capability exposed as REST before any UI is built. 116 endpoints on agent-service. UI console is a thin proxy with zero business logic.

**Gap**: No `/v1/` versioning prefix yet.

### AP-2 · Local-First, Cloud-Ready · 🟢 ✅

Runs fully offline with Ollama. Switch to cloud LLMs via `LLM_PROVIDER` env var or `POST /models/switch` at runtime. No code changes needed.

### AP-3 · Container-Native Composability · 🟢 ✅

All services are Docker containers defined in `docker-compose.yml`. Internal communication via Docker bridge network. Health checks enforce startup ordering. All ports configurable via env vars.

### AP-4 · Defence in Depth · 🟢 ✅

Security is layered: input guardrails → tool sandboxing → output guardrails → SSRF protection → ClamAV malware scanning. Each layer operates independently. Code execution blocks dangerous imports. HTTP fetch uses URL whitelist.

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

## Enterprise Principles

| # | Principle | Status | Implementation |
|---|-----------|--------|-----------------|
| AP-11 | Identity & Access Control | 🟢 ✅ | Session auth + RBAC + Workspace isolation |
| AP-12 | Cost Accountability | 🟡 | Token tracking exists; no enforcement |
| AP-13 | Elastic Scaling | 🔴 | Single-writer SQLite; no K8s |
| AP-14 | Compliance & Governance | 🟢 ✅ | ClamAV + GitLeaks + OWASP + Audit Log |
| AP-15 | Disaster Recovery | 🔴 | No automated backup or RTO/RPO |
| AP-16 | Zero-Trust Networking | 🔴 | Plain HTTP, single flat network |
| AP-17 | Agent Lifecycle Governance | 🔴 | No approval workflow or A/B testing |
| AP-18 | Secret Management | 🟡 | Secrets in env vars, no vault |

---

## New: Compliance & Security (AP-14) 🟢 ✅

### Security Scanning Suite

- **GitLeaks Secret Scanning**: Real-time credential detection with progress visualization
  - 1000+ regex patterns for AWS, private keys, API tokens, cloud credentials
  - Entropy detection with Shannon analysis
  - Full git history scanning with cache
  - Live credential verification when enabled

- **OWASP Top 10 Assessment**: Comprehensive vulnerability scanning
  - All 10 OWASP items with detailed implementation status
  - Real-time progress indicators for each check
  - Risk severity breakdown (Critical, High, Medium, Low)
  - Remediation guidance for identified issues
  - PDF report generation and download

- **ClamAV Antivirus & Malware Detection**: File scanning on upload
  - Byte scanning with signature-based malware detection
  - Size validation and integrity checking
  - Heuristic analysis for unknown threats
  - Archive scanning (ZIP, TAR, 7Z, RAR)
  - Magic byte detection via libmagic (detect spoofed files)
  - PE executable analysis
  - Real-time file upload monitoring across platform
  - Recent scan history with threat details

- **Compliance Audit Log**: Event tracking and retention
  - Policy changes, access reviews, compliance checks
  - Security incidents with detailed context
  - Event filtering and search capabilities
  - Timestamp and user tracking

---

## Priority Roadmap

| Priority | Action | Principle |
|----------|--------|-----------|
| P1 | API versioning with `/v1/` prefix | AP-1 |
| P1 | Database secrets vault integration | AP-18 |
| P1 | Full Grafana observability dashboard | AP-5 |
| P2 | ClamAV integration with API endpoints | AP-14 |
| P2 | Automated compliance report generation | AP-14 |
| P3 | Agent lifecycle approval workflow | AP-17 |
| P3 | PostgreSQL migration for scaling | AP-13 |
| P4 | mTLS via service mesh | AP-16 |
| P4 | Data retention policies + GDPR delete | AP-14 |

---

## Detail: Identity & Access Control (AP-11) ✅

### Authentication Stack

- **Password Hashing**: PBKDF2-SHA256 (600,000 iterations, 32-byte salt)
- **Session Management**: Express-session with HttpOnly, SameSite=Strict cookies
- **Login Flow**: Verification → session creation → redirect
- **Registration**: Validation → duplicate check → PBKDF2 hash → 6-digit verification code
- **Email Verification**: Code-based with resend capability
- **Password Reset**: Secure recovery flow with token-based reset

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| admin | Full platform access, user management, delete protection |
| member | Standard access, no admin functions |
| viewer | Read-only access to resources |

### Workspace Scoping

- Multi-tenant isolation via `workspace_id` on all entities
- ContextVar-based request-scoped workspace selection
- Default workspace pre-created and protected from deletion

### Compliance Integration

- UI-based scanning controls in Admin Plane
- Real-time threat detection across file uploads
- Audit trail of all scanning activity
- Downloadable compliance reports

