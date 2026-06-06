---
name: project-documentation
description: Generate update validate project documentation README API docs architecture principles evaluation building blocks ABB SBB decisions standards guidelines changelog contributing technical writing
argument-hint: "[readme|api|architecture|validate|principles|building-blocks|decisions|standards|guidelines|changelog|all] - generate, update, evaluate, or validate project documentation"
---

# Project Documentation

Generate and maintain comprehensive project documentation for the Agentic Platform.

## When to Use

- After adding new services, endpoints, or features
- When preparing a release or milestone
- During onboarding to generate up-to-date docs
- When existing documentation is stale or incomplete
- Before open-sourcing or sharing the project externally

## Procedure

### 1. Update README.md

Ensure `README.md` contains all required sections:

```markdown
# Project Name

![CI](badge-url) ![License](badge-url)

> One-line description

## Architecture

- High-level architecture diagram or description
- Service interaction overview

## Quick Start

- Prerequisites (Docker, Node.js, Python versions)
- Clone + `docker-compose up -d`
- Access URLs (UI, API, n8n, Grafana, Langfuse)

## Services

| Service       | Port  | Description           |
| ------------- | ----- | --------------------- |
| ui-console    | 3000  | Platform dashboard    |
| agent-service | 8010  | LangGraph AI agent    |
| tools-service | 8011  | Utility tools API     |
| n8n           | 5678  | Workflow orchestrator |
| ollama        | 11436 | Local LLM runtime     |
| chromadb      | 8200  | Vector database       |
| langfuse      | 3002  | LLM observability     |
| grafana       | 3003  | Metrics dashboards    |
| prometheus    | 9090  | Metrics collection    |
| loki          | 3100  | Log aggregation       |

## Configuration

- Environment variables reference
- `.env` file template

## Testing

- How to run unit/integration/e2e tests
- Test coverage expectations

## Contributing

- Link to CONTRIBUTING.md

## License

- License type and link
```

### 2. Document API Endpoints

For each service (`agent-service`, `tools-service`), document:

#### Agent Service (FastAPI)

Read `services/agent/main.py` and extract:

- `GET /health` — Health check
- `POST /chat` — Send message to agent
- `POST /ingest` — Ingest document to vector store
- `GET /search` — Search vector store
- `GET /memory` — Get conversation memory

#### Tools Service (FastAPI)

Read `services/tools/main.py` and extract:

- `GET /health` — Health check
- All tool endpoints with request/response schemas

#### UI Console (Express.js)

Read `services/ui-console/server.js` and document:

- Page routes (`/`, `/run-agent`, `/documents`, etc.)
- API proxy routes (`/api/*`)

### 3. Document Architecture

Create or update `docs/architecture.md` with:

- **System diagram**: Services and their connections
- **Data flow**: How a user query flows through the system
- **Technology stack**: Each service's tech choices
- **Network**: Docker network topology (`platform-net`)
- **Observability pipeline**: Metrics → OTel → Prometheus → Grafana

### 4. Generate CHANGELOG

Scan git log and generate `CHANGELOG.md`:

```bash
git log --oneline --no-merges --format="- %s (%h)" > CHANGELOG.md
```

Group by category:

- **Features** — `feat:` commits
- **Bug Fixes** — `fix:` commits
- **Documentation** — `docs:` commits
- **Infrastructure** — `chore:`, `ci:` commits

### 5. Verify Documentation Completeness

Check every service directory has:

- `README.md` or is documented in the root README
- API endpoints are documented
- Environment variables are listed
- Dockerfile build instructions are noted

### 6. Validate Links and References

- Ensure all internal links in markdown files resolve
- Verify port numbers match `docker-compose.yml`
- Confirm environment variable names match actual usage
- Check that code examples are runnable

### 7. Generate Documentation Report

Output:

| Document             | Status           | Last Updated | Action Needed |
| -------------------- | ---------------- | ------------ | ------------- |
| README.md            | CURRENT/STALE    | date         | Details       |
| CONTRIBUTING.md      | CURRENT/STALE    | date         | Details       |
| INSTALL.md           | CURRENT/STALE    | date         | Details       |
| docs/architecture.md | EXISTS/MISSING   | date         | Details       |
| CHANGELOG.md         | EXISTS/MISSING   | date         | Details       |
| API Documentation    | COMPLETE/PARTIAL | date         | Details       |

### 8. In-App Documentation Portal

The platform includes a built-in documentation portal at `/docs` (see `services/ui-console/views/docs.ejs`).

When updating documentation:

- Update both `docs/ARCHITECTURE.md` (auto-generated) AND the in-app docs portal
- The docs portal has 15 sections: Overview, Quick Start, Installation, Architecture, Services, Data Flow, Agents, LLM Providers, Memory, Guardrails, Tools/MCP, Observability, Workflows, Deployment, API Reference, Configuration
- Mermaid.js diagrams are rendered client-side via CDN
- The portal is searchable with instant filter

### 9. Auto-Documentation Workflow

The GitHub Actions workflow (`.github/workflows/update-docs.yml`) automatically:

- Triggers on push to main or PRs that modify services/docker-compose
- Runs `scripts/generate-docs.sh` to regenerate `docs/ARCHITECTURE.md`
- Auto-commits if docs changed (push events only)

---

## Architecture Document Validation

When creating, updating, or reviewing architecture documentation (`docs/PRINCIPLES.md`, `docs/BUILDING-BLOCKS.md`, `docs/DECISIONS.md`), validate every claim against the actual codebase. Do NOT trust documentation at face value.

### 10. Validate PRINCIPLES.md

For each Architecture Principle (AP-1 through AP-10):

1. **Read the principle's claims** — extract every verifiable statement
2. **Search the codebase** for evidence supporting or contradicting each claim
3. **Classify each principle** as:
   - **FULLY MET** — all claims verified in code
   - **PARTIAL** — some claims verified, others not
   - **NOT MET** — key claims are aspirational, not implemented
4. **For PARTIAL or NOT MET**, add a `### Future Vision` section listing:
   - What is missing
   - Concrete steps required to close the gap
   - Priority (P1/P2/P3)
5. **Update the Validation Summary table** at the bottom

#### Common Principle Validation Checks

| Principle             | Key Checks                                                                                                         |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| AP-1 API-First        | Are routes versioned (`/v1/`)? Is UI pure proxy (no business logic in `server.js`)?                                |
| AP-2 Local-First      | Does Ollama work without cloud keys? Does `POST /models/switch` work at runtime?                                   |
| AP-3 Container-Native | Do all critical services have healthchecks? Are `depends_on` conditions `service_healthy`?                         |
| AP-4 Defence in Depth | Do input guardrails run before LLM call? Output guardrails after? URL whitelist present? Import blocklist present? |
| AP-5 Observable       | Is telemetry always-on or opt-in? Does Grafana dashboard cover Prometheus + Loki + Langfuse?                       |
| AP-6 Protocols        | Does `/.well-known/agent.json` return a real agent card? Does MCP `/discover` make actual HTTP calls?              |
| AP-7 Separation       | Do ALL tools call tools-service via HTTP? Any in-process tools?                                                    |
| AP-8 Knowledge        | Is `kb_collection` used when running agents? Full CRUD on documents?                                               |
| AP-9 Config over Code | Is `log_audit()` called on ALL CRUD operations? Version snapshots for all entities? Config loaded per-request?     |
| AP-10 Degradation     | Does Langfuse fall back to `_NoOpSpan`? No n8n imports in agent-service? UI handles errors gracefully?             |

### 11. Validate BUILDING-BLOCKS.md

For each ABB/SBB pair (1–12):

1. **Verify SBB technology matches actual code**:
   - Check env var names (e.g. `MAX_REACT_ITERATIONS`, not `MAX_ITERATIONS`)
   - Check function signatures and default parameter values
   - Check table names in `init_db()` match documented list
   - Check actual API endpoint paths match documented paths

2. **Known trouble spots** (check these every time):

   | ABB                | What to verify                        | Where to check                                              |
   | ------------------ | ------------------------------------- | ----------------------------------------------------------- |
   | Agent Reasoning    | Env var name for max iterations       | `graph.py` — look for `os.environ.get` or `os.getenv`       |
   | Knowledge Mgmt     | Default k value in `search_similar()` | `vectorstore.py` function signature vs `graph.py` call site |
   | Config Store       | Total table count and names           | `memory.py` — grep for `CREATE TABLE`                       |
   | A2A Protocol       | Agent card JSON structure             | `main.py` — look for `.well-known/agent.json` route handler |
   | Platform Dashboard | EJS view count                        | `services/ui-console/views/` — count `.ejs` files           |

3. **Validate the Traceability Matrix**:
   - Every source file listed must exist
   - Every service name must match `docker-compose.yml`
   - Every SBB technology must match what the code actually uses

### 12. Validate DECISIONS.md

For each ADR (001–010):

1. **Verify the Decision field** — does the code actually implement the stated decision?
2. **Verify the Consequences field** — are stated consequences accurate?
3. **Check for architectural violations**:
   - ADR-003 says "HTTP proxy, not in-process" — verify no tools run in-process
   - ADR-010 says "zero business logic in proxy" — verify no logic in `server.js` beyond forwarding
4. **Check numeric claims**:
   - Container counts (ADR-006)
   - Port numbers (ADR-005: internal vs external)
5. **Add notes for known exceptions** — if code intentionally deviates from an ADR, document it in the Consequences field with a cross-reference to the relevant PRINCIPLES.md Future Vision section

#### Cross-Reference Checklist

All three documents must be consistent:

| Check                                                | Files                              |
| ---------------------------------------------------- | ---------------------------------- |
| Principle IDs referenced in ABBs match PRINCIPLES.md | BUILDING-BLOCKS.md ↔ PRINCIPLES.md |
| ADR principle references match PRINCIPLES.md         | DECISIONS.md ↔ PRINCIPLES.md       |
| SBB technologies match ADR decisions                 | BUILDING-BLOCKS.md ↔ DECISIONS.md  |
| Table names in ABB-7 match ADR-002                   | BUILDING-BLOCKS.md ↔ DECISIONS.md  |
| Tool execution model in ABB-5 matches ADR-003        | BUILDING-BLOCKS.md ↔ DECISIONS.md  |
| View count in ABB-12 matches ADR-007                 | BUILDING-BLOCKS.md ↔ DECISIONS.md  |

### 13. Architecture Validation Report

After validation, output a summary:

```markdown
## Validation Report

| Document           | Item  | Claim          | Actual               | Severity |
| ------------------ | ----- | -------------- | -------------------- | -------- |
| BUILDING-BLOCKS.md | ABB-1 | MAX_ITERATIONS | MAX_REACT_ITERATIONS | HIGH     |
| ...                | ...   | ...            | ...                  | ...      |

### Actions Taken

- [ ] Fixed in documentation
- [ ] Added Future Vision section
- [ ] Cross-references updated
```

---

## Architecture Document Update & Evaluation

When the user requests updates to architecture documents (not just validation), follow these procedures to modify `docs/PRINCIPLES.md`, `docs/BUILDING-BLOCKS.md`, and `docs/DECISIONS.md` based on codebase reality.

### 14. Update & Evaluate PRINCIPLES.md

Update architecture principles to reflect current implementation state and evaluate their effectiveness.

#### 14a. Principle Evaluation Procedure

For each principle (AP-1 through AP-11+):

1. **Run validation** (Section 10) to determine current status (FULLY MET / PARTIAL / NOT MET)
2. **Evaluate effectiveness** — assess whether the principle is:
   - **Delivering value** — measurable benefit to the platform (e.g., AP-4 Defence in Depth prevents prompt injection)
   - **Aspirational** — not yet delivering value but on roadmap (e.g., /v1/ versioning)
   - **Needs revision** — principle wording doesn't match actual architecture direction
3. **Score each principle** on Implementation Maturity (1–5):
   - 1 = Not started
   - 2 = Proof of concept
   - 3 = Partially implemented with gaps
   - 4 = Fully implemented, minor gaps
   - 5 = Fully implemented and battle-tested
4. **Update the Validation Summary table** in PRINCIPLES.md with current scores and dates

#### 14b. Adding New Principles

When the codebase implements patterns not captured by existing principles:

1. Scan for emergent patterns (e.g., new cross-cutting concerns like rate limiting, caching, multi-tenancy)
2. Assign the next AP-N ID sequentially
3. Follow the existing principle template:

```markdown
### AP-N · [Principle Name]

> **Statement**: One-line principle statement.

**Why**: Rationale for adopting this principle.

| Claim                | Status       | Evidence                   |
| -------------------- | ------------ | -------------------------- |
| "Verifiable claim 1" | ✅ / ❌ / 🟡 | Code file + line reference |
| "Verifiable claim 2" | ✅ / ❌ / 🟡 | Code file + line reference |

**Validation Status**: FULLY MET / PARTIAL / NOT MET
```

4. Add the new principle to the Validation Summary table
5. Cross-reference in BUILDING-BLOCKS.md and DECISIONS.md where applicable

#### 14c. Updating Existing Principles

When code has evolved beyond what a principle documents:

1. **Update claims** — replace outdated numbers (e.g., endpoint counts, table counts) with verified actuals
2. **Update evidence** — refresh code file paths and line numbers
3. **Update status** — promote from PARTIAL → FULLY MET if gaps are closed, or demote if regression detected
4. **Update the Future Vision section** — remove completed items, add newly discovered gaps
5. **Update the Priority Roadmap** — re-rank P1–P4 items based on current importance

### 15. Update BUILDING-BLOCKS.md (ABBs & SBBs)

Update Architecture Building Blocks (abstract capabilities) and Solution Building Blocks (concrete implementations).

#### 15a. Update Existing ABB/SBB Pairs

For each ABB (ABB-1 through ABB-18):

1. **Verify the ABB description** still matches the capability's scope
2. **Update SBB technology mapping**:
   - Check package versions in `requirements.txt`, `package.json`
   - Check actual library imports in source files
   - Check docker-compose service definitions for image versions
3. **Update numeric claims**:
   - Table counts → grep `CREATE TABLE` in `memory.py`
   - Endpoint counts → count `@app.` decorators in `main.py`
   - Tool counts → count registered tools in tools-service `server.py`
   - View counts → count `.ejs` files in `services/ui-console/views/`
   - File type counts → check parser registrations
4. **Update configuration details**:
   - Env var names and defaults
   - Port numbers (verify against docker-compose.yml)
   - Default parameter values (verify against function signatures)
5. **Update the Traceability Matrix** row for this ABB

#### 15b. Adding New ABBs

When the codebase introduces new architectural capabilities:

1. Identify the new capability (e.g., "Rate Limiting", "Multi-Tenant Isolation", "Prompt Management")
2. Assign the next ABB-N ID sequentially
3. Define the ABB (abstract capability):

```markdown
### ABB-N · [Capability Name]

**Purpose**: What architectural need this addresses.

| Aspect       | Detail                          |
| ------------ | ------------------------------- |
| Scope        | What this building block covers |
| Interfaces   | APIs/protocols it exposes       |
| Dependencies | Other ABBs it depends on        |
```

4. Define the SBB (concrete implementation):

```markdown
#### SBB-N · [Implementation Name]

| Component | Technology        | Evidence                  |
| --------- | ----------------- | ------------------------- |
| Runtime   | Library/framework | File path + line          |
| Storage   | Database/cache    | Docker service name       |
| API       | Endpoints         | Route paths               |
| Config    | Env vars          | Variable names + defaults |
```

5. Map to principles — list which AP-N principles this ABB supports
6. Add to the Traceability Matrix
7. Cross-reference in DECISIONS.md if an ADR drove the technology choice

#### 15c. ABB/SBB Consistency Checks

After any update, verify:

| Check                                                             | How                                       |
| ----------------------------------------------------------------- | ----------------------------------------- |
| Every ABB has a matching SBB                                      | No abstract blocks without implementation |
| Every SBB technology is in docker-compose.yml or requirements.txt | No phantom dependencies                   |
| SBB port numbers match docker-compose.yml `ports:`                | No port mismatches                        |
| SBB env vars exist in code (os.getenv/os.environ)                 | No documented-but-unused vars             |
| ABB principle mappings reference valid AP-N IDs                   | No broken cross-references                |

### 16. Update DECISIONS.md (ADRs)

Update Architecture Decision Records to track evolving decisions.

#### 16a. Update Existing ADRs

For each ADR:

1. **Verify Status field** — should be one of: `Accepted`, `Superseded`, `Deprecated`, `Proposed`
2. **Check if decision is still valid** — does the code still implement this decision?
3. **Update Consequences** — add newly discovered consequences (positive or negative)
4. **Add supersession links** — if a newer ADR replaces this one, add `Superseded by: ADR-NNN`
5. **Refresh code evidence** — update file paths and line numbers

#### 16b. Adding New ADRs

When architectural decisions are made but not documented:

1. Scan for undocumented decisions:
   - New service additions not covered by existing ADRs
   - Technology swaps (e.g., database migration, new LLM provider)
   - Architectural pattern changes (e.g., adding event-driven patterns)
   - Security decisions (e.g., auth mechanism changes)
2. Assign the next ADR-NNN ID sequentially (3-digit, zero-padded)
3. Follow the ADR template:

```markdown
### ADR-NNN · [Decision Title]

| Field      | Value      |
| ---------- | ---------- |
| Status     | Accepted   |
| Date       | YYYY-MM-DD |
| Principles | AP-N, AP-M |

**Context**: Why this decision was needed.

**Decision**: What was decided and chosen.

**Consequences**:

- ✅ Positive consequence 1
- ✅ Positive consequence 2
- ⚠️ Trade-off or risk
```

4. Cross-reference the relevant principles (AP-N) and building blocks (ABB-N)
5. Update the ADR index table at the top of DECISIONS.md

#### 16c. ADR Lifecycle Management

| Current Status | Valid Transitions | When                            |
| -------------- | ----------------- | ------------------------------- |
| Proposed       | → Accepted        | After implementation and review |
| Accepted       | → Superseded      | When replaced by a newer ADR    |
| Accepted       | → Deprecated      | When the feature is removed     |
| Superseded     | (terminal)        | Link to replacement ADR         |
| Deprecated     | (terminal)        | Note removal date               |

### 17. Update Standards & Guidelines

Maintain platform-wide standards and guidelines that complement principles and decisions.

#### 17a. Coding Standards

Document and enforce coding standards derived from the codebase:

1. **API Design Standards**:
   - Endpoint naming conventions (e.g., plural nouns for collections: `/agents`, `/skills`)
   - HTTP method usage (GET for reads, POST for creates/actions, PUT for full updates, PATCH for partial, DELETE for removal)
   - Response format standards (JSON envelope with `status`, `data`, `error` fields)
   - Error response format (`{"detail": "message"}` for FastAPI, `{"error": "message"}` for Express)
   - Pagination conventions (query params: `skip`, `limit`)

2. **Service Structure Standards**:
   - Each service must have: `Dockerfile`, `requirements.txt` or `package.json`, health endpoint
   - Entry point naming: `main.py` (Python/FastAPI), `server.js` (Node.js/Express)
   - Port allocation: document the port registry (which service owns which port)

3. **Configuration Standards**:
   - Environment variable naming: `UPPER_SNAKE_CASE`
   - Default values: always provide sensible defaults via `os.getenv("VAR", "default")`
   - Secrets: never commit; use `.env` files excluded from git

4. **Testing Standards**:
   - Test directory structure: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/contract/`, `tests/smoke/`, `tests/load/`
   - Naming: `test_*.py` (Python), `*.test.js` (JavaScript)
   - Coverage expectations per test type

#### 17b. Security Guidelines

Document security practices observed in the codebase:

1. **Authentication**: Session-based auth with PBKDF2-SHA256, HttpOnly cookies, CSRF protection
2. **Authorization**: RBAC with admin/member/viewer roles, workspace-scoped access
3. **Input Validation**: Guardrails engine for LLM inputs, sanitization for user inputs
4. **Output Filtering**: PII detection, data-leak prevention on LLM outputs
5. **Tool Execution Safety**: URL whitelist, import blocklist, filename sanitization, execution timeout
6. **Dependency Security**: Pin exact versions, audit for known vulnerabilities

#### 17c. Operational Guidelines

Document operational practices:

1. **Health Checks**: Every service exposes `/health`; docker-compose uses healthchecks with `depends_on` conditions
2. **Logging**: Structured JSON logging via OTel Collector → Loki
3. **Monitoring**: Prometheus metrics → Grafana dashboards
4. **Backup**: SQLite database at `/data/platform.db`; document backup procedures
5. **Scaling**: Horizontal scaling via Docker Compose replicas or Kubernetes

### 18. Cross-Reference Integrity

After updating any architecture document, validate cross-references across all three:

#### 18a. Automated Cross-Reference Checks

| Source Document    | Reference Type          | Target Document    | Validation         |
| ------------------ | ----------------------- | ------------------ | ------------------ |
| PRINCIPLES.md      | "See ABB-N"             | BUILDING-BLOCKS.md | ABB-N must exist   |
| PRINCIPLES.md      | "See ADR-NNN"           | DECISIONS.md       | ADR-NNN must exist |
| BUILDING-BLOCKS.md | "Supports AP-N"         | PRINCIPLES.md      | AP-N must exist    |
| BUILDING-BLOCKS.md | "See ADR-NNN"           | DECISIONS.md       | ADR-NNN must exist |
| DECISIONS.md       | "Principles: AP-N"      | PRINCIPLES.md      | AP-N must exist    |
| DECISIONS.md       | "Superseded by ADR-NNN" | DECISIONS.md       | ADR-NNN must exist |

#### 18b. Consistency Checks

After every update cycle:

1. **ID continuity** — no gaps in AP-N, ABB-N, or ADR-NNN sequences
2. **Status alignment** — if a principle is FULLY MET, the corresponding ABB should show verified SBB
3. **Date freshness** — last-validated dates should be within the current quarter
4. **Orphan detection** — no ABBs without principle mapping; no ADRs without principle references

### 19. Documentation Update Report

After performing updates (not just validation), output a change summary:

```markdown
## Documentation Update Report

**Date**: YYYY-MM-DD
**Scope**: [principles|building-blocks|decisions|standards|all]

### Changes Made

| Document           | Section | Change Type | Description                     |
| ------------------ | ------- | ----------- | ------------------------------- |
| PRINCIPLES.md      | AP-1    | Updated     | Endpoint count 145 → 157        |
| BUILDING-BLOCKS.md | ABB-7   | Updated     | Table count 16 → 23             |
| DECISIONS.md       | ADR-026 | Added       | New ADR for guardrails engine   |
| PRINCIPLES.md      | AP-12   | Added       | New principle for rate limiting |

### Evaluation Summary

| Principle | Score | Trend | Notes                    |
| --------- | ----- | ----- | ------------------------ |
| AP-1      | 4/5   | ↑     | Improved: more endpoints |
| AP-5      | 3/5   | →     | Unchanged: still opt-in  |

### Cross-Reference Status

- [ ] All AP-N → ABB-N links valid
- [ ] All ADR-NNN → AP-N links valid
- [ ] All SBB technologies verified in code
- [ ] No orphaned references
```
