---
name: enterprise-structure
description: Enterprise project structure validation linting directory organization conventions naming standards microservices architecture
argument-hint: "[check|fix|report] - validate and enforce enterprise project structure"
---

# Enterprise Project Structure

Validate and enforce enterprise-grade project organization for the Agentic Platform.

## When to Use

- After adding new services, modules, or directories
- During code reviews to verify structural consistency
- When onboarding new contributors to explain project layout
- To audit the project for missing standard files

## Procedure

### 1. Verify Top-Level Structure

Ensure the following required directories and files exist at the project root:

```
agentic-platform/
├── .github/               # CI/CD, skills, issue/PR templates
│   ├── workflows/         # GitHub Actions CI/CD pipelines
│   └── skills/            # Copilot agent skills
├── data/                  # Runtime data (notes, memory DB)
├── docs/                  # Project documentation
├── n8n/workflows/         # n8n workflow definitions
├── observability/         # Monitoring stack configs
│   ├── grafana/           # Dashboards + provisioning
│   ├── loki/              # Log aggregation config
│   └── prometheus/        # Metrics scraping config
├── scripts/               # Utility & health-check scripts
├── services/              # Microservice source code
│   ├── agent/             # FastAPI + LangGraph agent service
│   ├── tools/             # FastAPI tools service
│   ├── ui/                # Static UI (nginx)
│   ├── ui-console/        # Express.js dashboard (EJS views)
│   └── otel/              # OpenTelemetry collector config
├── tests/                 # Test suites by type
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── contract/
│   ├── load/
│   └── smoke/
├── docker-compose.yml     # Full local dev stack
├── pyproject.toml         # Python project metadata
├── README.md              # Project overview
├── CONTRIBUTING.md        # Contribution guidelines
├── LICENSE                # License file
└── INSTALL.md             # Installation guide
```

### 2. Verify Each Service Has Required Files

For every directory under `services/`, confirm:

- `Dockerfile` — Container build definition
- `requirements.txt` (Python) or `package.json` (Node.js) — Dependencies
- `main.py` or `server.js` — Entrypoint file

### 3. Verify Naming Conventions

- **Directories**: lowercase, hyphen-separated (e.g., `ui-console`, `agent-service`)
- **Python files**: lowercase, underscore-separated (e.g., `test_agent.py`)
- **JavaScript files**: lowercase, dot-separated for test suffix (e.g., `test_console.test.js`)
- **Config files**: lowercase, hyphen or dot separated (e.g., `docker-compose.yml`, `otel-collector.yaml`)

### 4. Verify Test Organization

- Unit tests: `tests/unit/` — One test file per source module
- Integration tests: `tests/integration/` — Cross-service tests
- E2E tests: `tests/e2e/` — Full pipeline tests
- Contract tests: `tests/contract/` — API contract validation
- Load tests: `tests/load/` — Performance benchmarks
- Smoke tests: `tests/smoke/` — Quick health verification

### 5. Verify Documentation Files

Required docs at root:

- `README.md` — Project overview with badges, quickstart, architecture
- `CONTRIBUTING.md` — How to contribute, PR process, coding standards
- `INSTALL.md` — Detailed installation instructions
- `LICENSE` — Open-source license

### 6. Verify Observability Stack

- `observability/prometheus/prometheus.yml` — Scrape targets
- `observability/grafana/provisioning/datasources/` — Auto-provisioned data sources
- `observability/grafana/provisioning/dashboards/` — Dashboard provisioning
- `observability/grafana/dashboards/` — Dashboard JSON definitions
- `observability/loki/loki-config.yaml` — Log aggregation config
- `services/otel/otel-collector.yaml` — Telemetry pipeline

### 7. Generate Report

Output a summary table:

| Category            | Status    | Details                         |
| ------------------- | --------- | ------------------------------- |
| Top-level structure | PASS/FAIL | Missing items                   |
| Service scaffolding | PASS/FAIL | Services without required files |
| Naming conventions  | PASS/FAIL | Non-conforming names            |
| Test organization   | PASS/FAIL | Missing test categories         |
| Documentation       | PASS/FAIL | Missing docs                    |
| Observability       | PASS/FAIL | Missing configs                 |
