# A08:2025 - Software or Data Integrity Failures

## Overview

Software and data integrity failures occur when applications rely on untrusted sources for code/data updates, lack verification mechanisms, or have insecure CI/CD pipelines. This document details comprehensive protections against integrity attacks.

## Vulnerabilities Addressed

- ❌ Insecure deserialization (malicious objects)
- ❌ Untrusted updates/patches
- ❌ Code tampering during build/deployment
- ❌ Compromised dependencies
- ❌ Non-reproducible builds
- ❌ Unsigned artifacts
- ❌ Integrity validation gaps

## Implementation

### 1. Secure Deserialization

**Status**: ✅ IMPLEMENTED

The `data_integrity.py` module provides `SecureJSONDecoder` with depth validation:

```python
from services.agent.agent.data_integrity import SecureJSONDecoder

# Safe JSON deserialization with depth limits
data = SecureJSONDecoder.safe_loads(json_string, max_depth=10)

# Prevents:
# - JSON bomb attacks (deeply nested objects)
# - Quadratic blowup attacks
# - Resource exhaustion
```

#### Key Features
- **Depth Validation**: Limits nesting depth (default: 10 levels)
- **Size Limits**: Prevents memory exhaustion
- **Type Checking**: Validates JSON types
- **Error Handling**: Safe exception handling

#### Configuration
```python
# Maximum nesting depth (adjust for your use case)
MAX_JSON_DEPTH = 10  # Conservative default

# Maximum request body size
MAX_BODY_SIZE = 10_485_760  # 10 MB
```

### 2. Cryptographic Integrity Verification

**Status**: ✅ IMPLEMENTED

#### Request/Response Signing
```python
from services.agent.agent.data_integrity import IntegrityValidator

validator = IntegrityValidator(secret_key="your-64-char-key")

# Sign data
data_b64, sig_b64 = validator.sign_data({"user": "john", "role": "admin"})

# Verify signature
is_valid = validator.verify_signature(data_b64, sig_b64)

# Features:
# ✓ HMAC-SHA256 signing
# ✓ Base64 encoding
# ✓ Constant-time comparison (timing attack prevention)
```

#### Hash Verification
```python
# Compute hash
file_hash = validator.compute_hash(file_data, algorithm="sha256")

# Verify against expected hash
is_valid = validator.verify_hash(file_data, expected_hash)

# Algorithms supported: sha256, sha512, sha1
```

### 3. Artifact Integrity Verification

**Status**: ✅ IMPLEMENTED

#### SBOM & Manifest Generation
```python
from services.agent.agent.data_integrity import ArtifactVerifier

# Generate manifest with file hashes
manifest = ArtifactVerifier.generate_manifest({
    "main.py": "...",
    "requirements.txt": "..."
})

# Result structure:
# {
#   "version": "1.0.0",
#   "timestamp": "2025-09-03T...",
#   "files": {
#     "main.py": "sha256hash...",
#     "requirements.txt": "sha256hash..."
#   },
#   "hash": "manifestsha256hash..."
# }

# Verify artifacts
is_valid = ArtifactVerifier.verify_manifest(manifest, files)
```

### 4. Build Reproducibility

**Status**: ✅ IMPLEMENTED

#### Reproducible Builds
```bash
# Run automated build reproducibility tests
# File: .github/workflows/data-integrity.yml

Steps:
1. Build 1: Create fresh environment and compile
2. Build 2: Create fresh environment and compile
3. Compare: Verify outputs are identical

Results:
- ✓ Python: bytecode-compatible
- ✓ Node.js: identical node_modules (via package-lock.json)
- ✓ Docker: same image digest
```

#### Requirements
- Pinned dependencies (no floating versions)
- Locked lockfiles (package-lock.json, poetry.lock)
- Deterministic build scripts
- No timestamps/UUIDs in artifacts

### 5. Docker Image Security

**Status**: ✅ IMPLEMENTED

#### Dockerfile Best Practices
```dockerfile
# ✓ Specific base image version
FROM python:3.12.4-slim-bullseye

# ✓ Non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# ✓ Pinned dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ✓ Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# ✓ Specific tag (not 'latest')
# Build: docker build -t agentic-platform-service:1.2.3 .
```

#### Image Verification
```bash
# Verify digest (immutability)
docker inspect --format='{{.RepoDigests}}' agentic-platform-ui-console:1.2.3

# Result: agentic-platform-ui-console@sha256:abcd1234...
# This digest uniquely identifies this exact image
```

### 6. Code Signing & Provenance

**Status**: ✅ IMPLEMENTED - CI/CD READY

#### Release Artifact Signing
```bash
# Generate signed release
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# GitHub Actions automatically:
# 1. Generates release manifest
# 2. Signs with GPG (if secrets.GPG_PRIVATE_KEY provided)
# 3. Uploads artifacts with signatures
# 4. Creates SBOM
# 5. Verifies integrity
```

#### Setup GPG Signing
```bash
# Generate GPG key
gpg --gen-key

# Export private key
gpg --armor --export-secret-key your-email@example.com > private-key.asc

# Add to GitHub Secrets as GPG_PRIVATE_KEY
gh secret set GPG_PRIVATE_KEY < private-key.asc

# GPG public key
gpg --armor --export your-email@example.com > public-key.asc
# Share with consumers for verification
```

### 7. CI/CD Pipeline Security

**Status**: ✅ IMPLEMENTED

#### Workflow: `.github/workflows/data-integrity.yml`

**Stage 1: Code Integrity**
```yaml
- Generate code manifest (SHA256 of all source files)
- Verify no unauthorized modifications
- Detect suspicious files/permissions
- Upload manifest artifact (90-day retention)
```

**Stage 2: Dependency Lock Files**
```yaml
- Verify package-lock.json exists
- Validate all dependencies are pinned (==)
- Check for VCS dependencies (rejected)
- Verify JSON validity
```

**Stage 3: Build Reproducibility**
```yaml
- Build Python environment twice
- Build Node.js environment twice
- Compare outputs for differences
- Fail if builds are non-deterministic
```

**Stage 4: Container Image Security**
```yaml
- Scan Dockerfiles for security issues
- Verify specific base image versions
- Ensure non-root user configuration
- Detect non-pinned dependencies
- Build images and capture digests
```

**Stage 5: Code Signing (main branch only)**
```yaml
- Generate release manifest
- Import GPG key (if provided)
- Sign release artifacts
- Upload to artifact storage (1-year retention)
```

### 8. Decorator-Based Route Protection

**Status**: ✅ IMPLEMENTED

#### Signature Validation
```python
from fastapi import FastAPI
from services.agent.agent.data_integrity import (
    create_integrity_validator,
    require_signature_validation
)

app = FastAPI()
validator = create_integrity_validator(secret_key="your-secret-key")

@app.post("/admin/secure-operation")
@require_signature_validation(validator)
async def secure_operation(request: Request):
    # Only reached if request signature is valid
    # Request must include:
    #   X-Payload-Signature: base64-encoded HMAC-SHA256
    #   X-Payload-Hash: sha256 hash of body
    return {"status": "success"}
```

#### Artifact Verification
```python
@app.post("/deploy/verify-package")
@verify_artifact_integrity(validator)
async def verify_deployment(request: Request):
    # Validates manifest and file hashes
    return {"status": "package verified"}
```

## Configuration

### Environment Variables
```bash
# FastAPI data integrity
DATA_INTEGRITY_SECRET_KEY=<64-character-hex-string>
JSON_MAX_DEPTH=10
MAX_BODY_SIZE=10485760  # 10 MB

# Docker build
DOCKER_BUILD_CACHE=true
DOCKER_TAG_VERSION=true  # Always include version in tag
```

### GitHub Actions Secrets
```bash
# GPG signing (optional)
GPG_PRIVATE_KEY=<gpg-private-key-armored>
GPG_PASSPHRASE=<gpg-passphrase>

# Artifact signing
ARTIFACT_SIGNING_KEY=<signing-key>
```

## Running Locally

### Verify Code Integrity
```bash
# Generate manifest
python -c "
import hashlib
import json
from pathlib import Path

files = {}
for f in Path('services').rglob('*.py'):
    with open(f, 'rb') as fp:
        files[str(f)] = hashlib.sha256(fp.read()).hexdigest()

with open('code-manifest.json', 'w') as fp:
    json.dump({'files': files}, fp)
"

# Check manifest
cat code-manifest.json | jq '.files | length'
```

### Test Secure Deserialization
```python
from services.agent.agent.data_integrity import SecureJSONDecoder

# Test 1: Valid JSON
data = SecureJSONDecoder.safe_loads('{"key": "value"}')
print(data)  # {'key': 'value'}

# Test 2: Depth limit
try:
    # Deeply nested JSON (will fail with max_depth=3)
    nested = SecureJSONDecoder.safe_loads('{"a":{"b":{"c":{"d":"deep"}}}}', max_depth=3)
except ValueError as e:
    print(f"Caught attack: {e}")
```

### Test Artifact Verification
```python
from services.agent.agent.data_integrity import ArtifactVerifier

# Create and verify manifest
files = {
    "app.py": "import fastapi\napp = fastapi.FastAPI()",
    "requirements.txt": "fastapi==0.115.0"
}

manifest = ArtifactVerifier.generate_manifest(files)
print(manifest['hash'])  # Manifest hash

# Verify
is_valid = ArtifactVerifier.verify_manifest(manifest, files)
print(f"Integrity verified: {is_valid}")  # True
```

## Testing & Validation

### Unit Tests
```bash
# Test secure deserialization
pytest tests/unit/test_data_integrity.py::test_secure_json_decoder -v

# Test signature verification
pytest tests/unit/test_data_integrity.py::test_signature_validation -v

# Test artifact verification
pytest tests/unit/test_data_integrity.py::test_artifact_integrity -v
```

### Integration Tests
```bash
# Test secure endpoints
pytest tests/integration/test_secure_endpoints.py -v

# Test CI/CD integrity verification
pytest tests/integration/test_cicd_integrity.py -v
```

### CI/CD Validation
```bash
# Run data integrity workflow locally (via act)
act push --job build-reproducibility

# Check workflow results
gh workflow view data-integrity.yml
gh run list --workflow=data-integrity.yml
```

## Compliance & Standards

### OWASP Top 10:2025
- ✅ A08 - Software or Data Integrity Failures

### Standards
- **SLSA Framework**: Build integrity requirements
- **NIST SP 800-53**: Integrity controls
- **CISA SSDF**: Software supply chain security

## Troubleshooting

### Builds Not Reproducible
```bash
# Check for timestamps
find . -name "*.py" -exec grep -l "datetime.now()\|time.time()" {} \;

# Check for random values
find . -name "*.py" -exec grep -l "random\|uuid" {} \;

# Use SOURCE_DATE_EPOCH for build timestamps
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
docker build ...
```

### Signature Verification Failed
```python
# Debug signature issues
validator = IntegrityValidator(secret_key)

# Check if keys match
old_sig = "..."  # From earlier
new_sig = validator.sign_data(data)[1]
print(f"Signatures match: {hmac.compare_digest(old_sig, new_sig)}")
```

### GPG Signing Not Working
```bash
# Verify GPG configuration
gpg --list-secret-keys

# Test signing
gpg --armor --detach-sign test.txt

# Configure git signing
git config --global user.signingkey <keyid>
git config --global commit.gpgSign true
```

## Future Enhancements

### Phase 2 (Next Quarter)
- [ ] cosign for container image signing
- [ ] SLSA L3 provenance generation
- [ ] Artifact transparency log (Rekor)
- [ ] Dependency scanning with drift detection

### Phase 3 (Later)
- [ ] Hardware security module (HSM) integration
- [ ] SLSA L4 hermetic builds
- [ ] Offline supply chain validation
- [ ] Keyless signing (Sigstore)

## References

- **OWASP A08:2025**: https://owasp.org/Top10/A08_2025-Software_and_Data_Integrity_Failures/
- **SLSA Framework**: https://slsa.dev/
- **CycloneDX SBOM**: https://cyclonedx.org/
- **NIST SSDF**: https://csrc.nist.gov/Projects/secure-software-development-framework/

---

**Last Updated**: 2025-09-03  
**Version**: 1.0.0  
**Maintained By**: Security & Infrastructure Team
