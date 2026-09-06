# Testing Guide

## Overview

The Agentic Platform includes comprehensive automated tests across multiple categories to ensure reliability, functionality, and performance. This guide explains how to run tests and understand test coverage.

## Test Structure

Tests are organized in `/tests/` directory with the following structure:

```
tests/
├── unit/              # Unit tests for individual components
├── integration/       # Service-to-service integration tests
├── e2e/               # End-to-end workflow tests
├── contract/          # API contract validation tests
├── smoke/             # Quick sanity checks
├── load/              # Performance/load testing
├── conftest.py        # Pytest fixtures and configuration
└── test_workspace_rbac.py  # Workspace RBAC tests
```

### Test Categories

#### 1. Unit Tests (`tests/unit/`)
**Purpose:** Validate individual components in isolation

**Files:**
- `test_agent.py` - Agent graph logic, parsing, endpoints
- `test_llm.py` - LLM service integration
- `test_tools.py` - Tool handling and execution
- `test_vectorstore.py` - Vector store (ChromaDB) functionality

**Run unit tests:**
```bash
pytest tests/unit/ -v
```

**Coverage:** Component logic, error handling, edge cases

---

#### 2. Integration Tests (`tests/integration/`)
**Purpose:** Verify service-to-service communication and health

**File:** `test_integration.py`

**Tests:**
- Service health checks (all 16 containers)
- Cross-service communication (agent ↔ tools, agent ↔ n8n)
- Database connectivity (PostgreSQL, ChromaDB)
- Observability pipeline (Langfuse, Prometheus, Loki)

**Run integration tests:**
```bash
pytest tests/integration/ -v
```

---

#### 3. End-to-End Tests (`tests/e2e/`)
**Purpose:** Validate complete user workflows from start to finish

**Files:**
- `test_platform_comprehensive.py` (63KB) - **Most comprehensive**, covers all major features
- `test_edge_cases.py` (59KB) - Edge cases and error scenarios
- `test_api_endpoints.py` (27KB) - API endpoint validation
- `test_orchestration_e2e.py` - Multi-agent orchestration workflows
- `test_e2e.py` - Basic E2E tests using Playwright

**Coverage:**
- Agent creation and execution
- Skill and prompt management
- Tool execution and MCP integration
- RAG pipeline (ingest → embed → retrieve)
- Multi-agent delegation
- RBAC and workspace isolation
- LLM provider switching
- API contracts

**Run E2E tests:**
```bash
pytest tests/e2e/ -v --tb=short
```

---

#### 4. Contract Tests (`tests/contract/`)
**Purpose:** Validate API contracts against OpenAPI schema

**File:** `test_contracts.py`

**Tests:**
- Request/response schema validation
- Required field validation
- Data type validation
- HTTP status code validation

**Run contract tests:**
```bash
pytest tests/contract/ -v
```

---

#### 5. Smoke Tests (`tests/smoke/`)
**Purpose:** Quick sanity checks that services are running

**File:** `smoke-test.sh` (Bash script)

**Tests:**
- 13 quick functional tests
- Service port accessibility
- Basic API responses
- Health endpoint verification

**Run smoke tests:**
```bash
./tests/smoke/smoke-test.sh
```

---

#### 6. Load Tests (`tests/load/`)
**Purpose:** Performance testing under concurrent load

**File:** `load-test.js` (k6 JavaScript)

**Configuration:**
- 10-20 concurrent virtual users
- 2-5 minute test duration
- Common workflow scenarios (login, agent execution, tool calls)

**Run load tests:**
```bash
k6 run tests/load/load-test.js
```

---

#### 7. RBAC Tests
**Purpose:** Validate workspace isolation and role-based access

**File:** `test_workspace_rbac.py`

**Tests:**
- Multi-workspace isolation
- Persona switching and permissions
- Admin vs member vs viewer access
- Session-based authentication

---

## Quick Test Commands

### Run All Tests
```bash
pytest tests/ -v
```

### Run Tests by Category
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration only
pytest tests/integration/ -v

# E2E only
pytest tests/e2e/ -v

# Contract only
pytest tests/contract/ -v
```

### Run Tests with Coverage
```bash
pytest tests/ --cov=services/agent --cov-report=html
# View coverage report in htmlcov/index.html
```

### Run Specific Test
```bash
pytest tests/e2e/test_platform_comprehensive.py::test_agent_execution -v
```

### Run Tests Matching Pattern
```bash
pytest tests/ -k "rag" -v  # Run all tests with "rag" in the name
```

### Run Tests with Output Capture
```bash
pytest tests/ -s  # Show print statements and logging
```

---

## Alternative Test Scripts

The `/scripts/` directory contains standalone test scripts for quick validation:

| Script | Purpose | Usage |
|--------|---------|-------|
| `test_final_v2.py` | Comprehensive platform testing | `python3 scripts/test_final_v2.py` |
| `test_comprehensive.py` | Full feature validation | `python3 scripts/test_comprehensive.py` |
| `test_everything.py` | Broad coverage | `python3 scripts/test_everything.py` |
| `test_all_tools.py` | Tool catalog testing | `python3 scripts/test_all_tools.py` |
| `test_tools.py` | Tool endpoint testing | `python3 scripts/test_tools.py` |
| `test_n8n.py` | n8n integration testing | `python3 scripts/test_n8n.py` |

**Note:** These scripts require `requests` module. Install with:
```bash
pip install requests httpx
```

---

## Test Environment Setup

### Prerequisites
- Docker and Docker Compose running
- All 16 containers healthy (`docker compose ps`)
- Python 3.9+ (for pytest/scripts)
- pytest installed: `pip install pytest pytest-asyncio anyio httpx playwright`

### Quick Setup
```bash
# 1. Start containers
cd agentic-platform
docker compose up -d

# 2. Wait for all services to be healthy
docker compose ps

# 3. Run tests
pytest tests/ -v
```

---

## Expected Test Results

### Success Criteria
- ✅ All unit tests pass (< 2 min)
- ✅ All integration tests pass (< 5 min)
- ✅ All E2E tests pass (< 15 min)
- ✅ All contract tests pass (< 1 min)
- ✅ Smoke tests pass (< 1 min)
- ✅ Code coverage > 75% for critical paths

### Common Issues & Solutions

#### "Connection refused" errors
**Cause:** Services not fully healthy  
**Fix:**
```bash
docker compose ps  # Verify all containers are "Up"
docker compose logs agent-service  # Check logs
```

#### "pytest not found"
**Fix:**
```bash
pip install pytest pytest-asyncio anyio httpx playwright
```

#### Timeout errors in E2E tests
**Cause:** Services responding slowly or overloaded  
**Fix:**
```bash
# Increase timeout in test configuration
# Or run with fewer concurrent tests:
pytest tests/e2e/ -n 1  # Run serially
```

---

## Continuous Integration

Tests are automatically run on:
- **Push to main:** Full test suite via GitHub Actions
- **Pull requests:** Lint + unit + integration tests
- **Manual trigger:** Can run full suite including load tests

See `.github/workflows/ci.yml` for CI/CD pipeline configuration.

---

## Test Coverage by Feature

| Feature | Coverage | Status |
|---------|----------|--------|
| Agent Execution | E2E + Unit | ✅ Full |
| LLM Provider Switching | E2E | ✅ Full |
| RAG Pipeline | E2E + Integration | ✅ Full |
| Multi-Agent Orchestration | E2E | ✅ Full |
| n8n Workflows | E2E + Integration | ✅ Full |
| MCP Tool Servers | E2E | ✅ Full |
| Authentication & SSO | E2E | ⚠️ Basic (SSO needs OAuth setup) |
| RBAC & Workspaces | E2E + Unit | ✅ Full |
| API Endpoints | Contract | ✅ Full |
| Guardrails & Safety | E2E | ✅ Full |
| Performance | Load Test | ✅ Basic |

---

## Debugging Failed Tests

### 1. Get Full Error Output
```bash
pytest tests/e2e/test_platform_comprehensive.py -v -s --tb=long
```

### 2. Check Service Logs
```bash
docker compose logs agent-service      # Agent errors
docker compose logs tools-service      # Tools errors
docker compose logs ui-console         # UI errors
docker compose logs n8n                # n8n errors
docker compose logs -f agent-service   # Follow logs in real-time
```

### 3. Database Inspection
```bash
# Connect to PostgreSQL
docker exec -it datastore-db psql -U agentic -d datastore

# Check agent registry
SELECT * FROM agents LIMIT 5;
SELECT * FROM skills LIMIT 5;
```

### 4. API Testing with curl
```bash
# Test agent endpoint
curl http://localhost:8010/models | python3 -m json.tool

# Test tools
curl http://localhost:8011/health

# Test UI
curl -L http://localhost:3005
```

---

## Performance Baselines

These are expected baseline metrics (may vary by hardware):

| Operation | Expected Time | Status |
|-----------|----------------|--------|
| Agent startup | < 2s | ✅ |
| Tool execution | < 500ms | ✅ |
| RAG retrieval | < 1s | ✅ |
| LLM inference (local) | 5-30s | ✅ |
| API endpoint response | < 100ms | ✅ |
| Dashboard page load | < 2s | ✅ |

---

## Contributing Tests

When adding new features, include tests:

1. **Unit test** for new functions/classes
2. **Integration test** for service interactions
3. **E2E test** for user workflows
4. **Contract test** for API changes

See `CONTRIBUTING.md` for full guidelines.

---

## Test Dependencies

```
pytest                  # Test framework
pytest-asyncio          # Async test support
pytest-cov              # Coverage reporting
anyio                   # Async I/O
httpx                   # HTTP client
playwright              # Browser automation
k6                      # Load testing (optional)
```

Install all with:
```bash
pip install pytest pytest-asyncio pytest-cov anyio httpx playwright
npm install -g k6
```
