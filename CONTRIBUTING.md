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
docker-compose up -d

# View logs
docker-compose logs -f
```

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

### JavaScript/TypeScript (n8n workflows)
- Use ES6+ features
- Consistent indentation (2 spaces)
- Clear variable names

### Docker
- Multi-stage builds when possible
- Minimize image size
- Use specific versions, not `latest`
- Add health checks

## Testing

### Run Tests
```bash
# Python tests
pytest services/langgraph-api/tests/

# Integration tests
./scripts/integration-tests.sh
```

### Test Coverage
- Aim for >80% coverage
- Test edge cases
- Include integration tests

## Documentation

Update documentation when:
- Adding new features
- Changing APIs
- Modifying configuration
- Fixing bugs that affect usage

### Documentation Files
- `README.md` - Overview and quick start
- `INSTALL.md` - Detailed installation
- `docs/` - In-depth guides
- Code comments - Implementation details

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
feat: Add RAG support with pgvector

- Implemented document ingestion
- Added vector similarity search
- Updated API with RAG endpoint

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
├── services/           # Microservices
│   └── langgraph-api/  # Agent orchestration
├── database/           # DB schemas
├── n8n/                # Workflows
├── monitoring/         # Observability configs
└── docs/               # Documentation
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
- [ ] API reference

### Infrastructure
- [ ] Kubernetes manifests
- [ ] Terraform modules
- [ ] CI/CD pipelines
- [ ] Monitoring alerts

## Getting Help

- 💬 [GitHub Discussions](https://github.com/rachit0412/agentic-platform/discussions)
- 🐛 [Issues](https://github.com/rachit0412/agentic-platform/issues)
- 📧 Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Acknowledged in documentation

Thank you for contributing! 🎉
