---
name: project-documentation
description: Generate update validate project documentation README API docs architecture principles building blocks decisions changelog contributing guidelines technical writing
argument-hint: "[readme|api|architecture|validate|changelog|all] - generate, update, or validate project documentation"
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
