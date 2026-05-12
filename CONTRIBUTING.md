# Contributing to Agentic Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints

## How to Contribute

### Reporting Bugs

1. Check if the bug already exists in [Issues](https://github.com/rachit0412/agentic-platform/issues)
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)
   - Relevant logs

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its use case
3. Explain why it would be valuable
4. Discuss implementation approach if possible

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages**:

   ```
   feat: Add new agent type for data analysis

   - Implemented DataAnalystAgent class
   - Added tests for new agent
   - Updated documentation
   ```

6. **Push to your fork**: `git push origin feature/your-feature`
7. **Open a Pull Request** with:
   - Clear description of changes
   - Link to related issues
   - Screenshots/demos if applicable

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/agentic-platform.git
cd agentic-platform

# Copy environment file
cp .env.example .env

# Start development environment
docker compose up -d --build

# Pull a model
docker exec ollama ollama pull llama3

# View logs
docker compose logs -f
```

### Key Concepts for Contributors

- **Agent** = `LLM + Tools + Memory + Control Logic + Context` — an autonomous loop, not just a model
- **Skill** = A self-contained capability package (instructions + tools + constraints + optional file attachments: scripts, references, assets). Files are per-skill isolated on disk at `/data/filestore/skills/{id}/{category}/`
- **Prompt** = The instructional context given to a model or skill — defines behavior and output format
- All agent/skill CRUD is in `services/agent/main.py`, storage in `services/agent/agent/memory.py` (SQLite + disk filestore)

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Write docstrings for functions/classes
- Use meaningful variable names

```python
def create_agent(model: str, temperature: float = 0.7) -> Agent:
    """
    Create a new agent instance.

    Args:
        model: Model name to use
        temperature: Sampling temperature

    Returns:
        Configured agent instance
    """
    # Implementation
```

### JavaScript (UI Console)

- Use ES6+ features
- Consistent indentation (2 spaces)
- Clear variable names
- XSS protection: always use `escapeHtml()` for user-generated content in EJS templates

### Docker

- Multi-stage builds when possible
- Minimize image size
- Use specific versions, not `latest` (except for Ollama/n8n)
- Add health checks

## Testing

### Run Tests

```bash
# All Python tests (unit, integration, contract, e2e)
cd tests && pytest -v

# Unit tests only
cd tests && pytest unit/ -v

# Specific test file
cd tests && pytest unit/test_agent.py -v

# JavaScript tests
cd tests/unit && npx jest test_console.test.js

# Smoke tests (requires running services)
bash tests/smoke/smoke-test.sh

# Load tests (requires k6)
k6 run tests/load/load-test.js
```

### Test Coverage

- Aim for >80% coverage
- Test edge cases
- Include integration tests

### Test Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_agent.py        # Agent graph, LLM, memory
│   ├── test_llm.py          # LLM provider switching
│   ├── test_tools.py        # Tool endpoints
│   ├── test_vectorstore.py  # ChromaDB operations
│   └── test_console.test.js # UI console routes (Jest)
├── integration/             # Cross-service tests
│   └── test_integration.py
├── contract/                # API schema contracts
│   └── test_contracts.py
├── e2e/                     # Full user journeys
│   └── test_e2e.py
├── load/                    # Performance tests
│   └── load-test.js
└── smoke/                   # Service connectivity
    └── smoke-test.sh
```

## Documentation

Update documentation when:

- Adding new features
- Changing APIs
- Modifying configuration
- Fixing bugs that affect usage

### Documentation Files

| File                                         | Content                                   |
| -------------------------------------------- | ----------------------------------------- |
| [README.md](README.md)                       | Overview, quick start, configuration      |
| [INSTALL.md](INSTALL.md)                     | Detailed installation, per-platform setup |
| [CONTRIBUTING.md](CONTRIBUTING.md)           | This file — code style, PR process        |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flows, telemetry      |
| [docs/README.md](docs/README.md)             | API reference & documentation index       |

## Commit Messages

Format:

```
<type>: <subject>

<body>

<footer>
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Example:

```
feat: Add web-search tool to tools-service

- Implemented DuckDuckGo search endpoint
- Added SSRF protection via domain allowlist
- Updated tool catalogue in agent-service

Closes #123
```

## Review Process

1. Maintainers review PRs within 1-2 weeks
2. Address feedback promptly
3. Keep PRs focused and reasonably sized
4. Squash commits before merging

## Project Structure

```
agentic-platform/
├── services/
│   ├── agent/               # FastAPI + LangGraph agent (port 8010)
│   │   ├── main.py          # 69 REST endpoints
│   │   └── agent/           # graph, llm, memory, tools, vectorstore, observability
│   ├── tools/               # FastAPI tool endpoints (port 8011)
│   │   └── main.py          # math, fetch, file-read/write, search, code-execute
│   ├── ui-console/          # Express.js + EJS dashboard (port 3000)
│   │   ├── server.js        # Routes + API proxy
│   │   ├── views/           # 22 EJS page templates (includes REST Console)
│   │   └── public/          # Static assets
│   ├── ui/                  # Legacy static UI
│   └── otel/                # OpenTelemetry Collector config
├── data/                    # SQLite DB + notes files (bind-mounted)
├── n8n/workflows/           # 5 workflow templates
├── observability/           # Prometheus, Grafana, Loki configs
├── tests/                   # unit, integration, contract, e2e, load, smoke
├── scripts/                 # health-check.sh
├── docs/                    # ARCHITECTURE.md, API reference
├── docker-compose.yml       # 12 services on platform-net
├── .env.example             # Environment variable template
└── pyproject.toml           # Python project metadata
```

## Areas for Contribution

### High Priority

- [ ] Additional agent implementations
- [ ] More n8n workflow templates
- [ ] Grafana dashboards
- [ ] Performance optimizations
- [ ] Test coverage

### Documentation

- [ ] Tutorial videos
- [ ] Blog posts
- [ ] Use case examples

### Infrastructure

- [ ] Kubernetes manifests
- [ ] Terraform modules
- [ ] CI/CD pipelines
- [ ] Monitoring alerts

## Getting Help

- [GitHub Discussions](https://github.com/rachit0412/agentic-platform/discussions)
- [Issues](https://github.com/rachit0412/agentic-platform/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be:

- Listed in CONTRIBUTORS.md
- Mentioned in release notes
