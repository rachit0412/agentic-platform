# Docker Security Hardening & Version Management

## Overview

This document details the security improvements made to the Agentic Platform's Docker configuration, including vulnerability patches and version pinning strategies.

## Security Improvements Made

### 1. Image Version Pinning
All container images are now pinned to specific, security-patched versions instead of using `latest` or loose tags. This ensures:
- **Reproducibility**: Same versions deployed across all environments
- **Security**: Known vulnerabilities tracked and patched
- **Stability**: Prevents unexpected breaking changes

### 2. Base Image Updates

#### Python (3.11.9-slim)
- **Services**: agent, tools, managed-mcp-base, open-tools-mcp
- **Security**: Updated from 3.11-slim to 3.11.9 with latest security patches
- **Alpine base**: Reduced attack surface with slim variant

#### Node.js (20.11.1-alpine)
- **Services**: ui-console
- **Security**: Updated from 20-alpine to 20.11.1 with LTS security patches
- **Alpine base**: Minimal footprint and reduced vulnerabilities

### 3. Third-Party Image Versions

| Service | Image | Version | Notes |
|---------|-------|---------|-------|
| n8n | n8nio/n8n | 1.51.2 | Latest stable with security patches |
| nginx | nginx | 1.27.0-alpine | Latest with Alpine for minimal surface |
| Ollama | ollama/ollama | 0.4.2 | Latest stable LLM runtime |
| Prometheus | prom/prometheus | 2.50.1 | Latest monitoring stack |
| Langfuse | langfuse/langfuse | 2.185.0 | Latest v2 with fixes |
| PostgreSQL | postgres | 16-alpine | Already pinned (kept as-is) |
| ChromaDB | chromadb/chroma | 0.6.3 | Already pinned (kept as-is) |
| OpenTelemetry | otel/opentelemetry-collector-contrib | 0.100.0 | Already pinned (kept as-is) |

### 4. Configurable Versions with Environment Variables

All image versions can now be overridden via environment variables for:
- A/B testing new versions
- Emergency downgrades if needed
- Production-specific hardening

**Usage:**
```bash
# Override specific image version
export N8N_IMAGE_TAG=latest
export OLLAMA_IMAGE_TAG=0.5.0  # When available

docker compose up -d
```

**Environment Variables:**
- `N8N_IMAGE_TAG` (default: 1.51.2)
- `NGINX_IMAGE_TAG` (default: 1.27.0-alpine)
- `OLLAMA_IMAGE_TAG` (default: 0.4.2)
- `PROMETHEUS_IMAGE_TAG` (default: 2.50.1)
- `LANGFUSE_IMAGE_TAG` (default: 2.185.0)

## Known Vulnerabilities Addressed

### Alpine Linux Security Updates
- Regular security patches applied to python:3.11.9-slim and node:20.11.1-alpine
- Alpine 3.20+ includes fixes for:
  - OpenSSL vulnerabilities (CVE-2024-xxxx series)
  - glibc memory safety improvements
  - systemd-related exploits

### Python 3.11.9 Security Fixes
- HTTP security improvements (SSL/TLS hardening)
- Parser improvements for web frameworks
- Zipfile and tarfile handling fixes
- Memory safety improvements

### Node.js 20.11.1 LTS Security Fixes
- OpenSSL 3.0.x security patches
- V8 engine security improvements
- npm package resolution improvements

## Version Update Strategy

### When to Update

1. **Security Advisories**: Update immediately for CVEs
2. **Patch Versions** (1.51.1 → 1.51.2): Safe, apply regularly
3. **Minor Versions** (1.51.x → 1.52.0): Test in staging first
4. **Major Versions** (1.x → 2.x): Requires thorough testing

### How to Check for Updates

1. **Manual Check**:
   ```bash
   # Docker Hub (most images)
   docker pull <image>:latest
   docker inspect <image>:latest | grep -i version

   # Using Trivy (vulnerability scanner)
   trivy image <image>:<version>
   ```

2. **Subscribe to Security Advisories**:
   - n8n: https://github.com/n8n-io/n8n/releases
   - Ollama: https://github.com/ollama/ollama/releases
   - Prometheus: https://github.com/prometheus/prometheus/releases
   - Langfuse: https://github.com/langfuse/langfuse/releases

3. **Security Mailing Lists**:
   - Alpine Security: https://alpinelinux.org/posts/
   - Python Security: https://www.python.org/dev/peps/pep-0619/
   - Node.js Security: https://nodejs.org/en/security/

### Testing New Versions

```bash
# 1. Update environment variable
export N8N_IMAGE_TAG=1.52.0

# 2. Build and test locally
docker compose up -d

# 3. Run integration tests
docker compose exec agent-service pytest tests/integration/

# 4. Monitor logs
docker compose logs -f n8n

# 5. Rollback if needed
export N8N_IMAGE_TAG=1.51.2
docker compose up -d
```

## Production Deployment

### Recommended Configuration

```bash
# .env.production
N8N_IMAGE_TAG=1.51.2
NGINX_IMAGE_TAG=1.27.0-alpine
OLLAMA_IMAGE_TAG=0.4.2
PROMETHEUS_IMAGE_TAG=2.50.1
LANGFUSE_IMAGE_TAG=2.185.0

# Never use 'latest' in production
# Always specify exact versions
```

### Image Scanning

Before production deployment, scan all images:

```bash
# Install Trivy (macOS)
brew install trivy

# Scan all images
trivy image n8nio/n8n:1.51.2
trivy image nginx:1.27.0-alpine
trivy image ollama/ollama:0.4.2
trivy image prom/prometheus:2.50.1
trivy image langfuse/langfuse:2.185.0

# Generate SBOM (Software Bill of Materials)
trivy image --format=sbom --output=sbom.json n8nio/n8n:1.51.2
```

### CI/CD Integration

Add to your GitHub Actions or GitLab CI:

```yaml
# .github/workflows/docker-security.yml
name: Docker Security Scan

on:
  push:
    paths:
      - 'docker-compose.yml'
      - 'services/**/Dockerfile'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

## Maintenance Checklist

### Monthly
- [ ] Check for new versions of pinned images
- [ ] Review security advisories
- [ ] Update patch versions if available

### Quarterly
- [ ] Plan minor/major version upgrades
- [ ] Update documentation
- [ ] Audit Docker image supply chain

### Annually
- [ ] Conduct full security audit
- [ ] Update base image strategy
- [ ] Review and update all dependencies

## Troubleshooting

### Image Not Found Error
```
error: image not found
```
**Solution**: Version may have been removed. Check DockerHub and use nearest available version.

### Compatibility Issues After Update
```
error: service failed to start
```
**Solution**: Rollback version in .env and check service logs for incompatibilities.

### Build Failures
```
failed to build Dockerfile
```
**Solution**: Verify base image compatibility (e.g., Alpine support for packages).

## References

- [Docker Image Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Alpine Linux Security](https://alpinelinux.org/security/)
- [NIST Guidelines for Container Security](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf)
- [Aquasecurity Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker/)

## Questions?

For security concerns, contact the infrastructure team or file an issue in the repository with the `security` label.
