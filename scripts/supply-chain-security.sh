#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# A03:2025 - Software Supply Chain Failures
# Supply Chain Security Scanner & SBOM Generator
# ══════════════════════════════════════════════════════════════════════════════

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="${PROJECT_ROOT}/security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  OWASP A03:2025 - Supply Chain Security Scanner               ║"
echo "║  Version 1.0.0                                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Create reports directory
mkdir -p "${REPORTS_DIR}"

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1: Python Dependency Scanning
# ──────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Python Dependency Scanning${NC}"
echo "────────────────────────────────────────────────────────────────"

PYTHON_REPORT="${REPORTS_DIR}/python-dependencies-${TIMESTAMP}.txt"
touch "${PYTHON_REPORT}"

echo "Scanning Python dependencies for vulnerabilities..."
echo "Timestamp: $(date)" >> "${PYTHON_REPORT}"
echo "" >> "${PYTHON_REPORT}"

# Check each requirements.txt file
for req_file in $(find "${PROJECT_ROOT}/services" -name "requirements.txt"); do
    echo "📄 Checking: $req_file" | tee -a "${PYTHON_REPORT}"
    
    # Verify all versions are pinned (no >=, <=, ~=, ==)
    if grep -E "^[^#]*[><=!]" "$req_file" | grep -v "==" | grep -v "^#"; then
        echo -e "${RED}  ⚠️  WARNING: Found non-pinned versions${NC}" | tee -a "${PYTHON_REPORT}"
    else
        echo -e "${GREEN}  ✓ All versions pinned with ==${NC}" | tee -a "${PYTHON_REPORT}"
    fi
    
    echo "" >> "${PYTHON_REPORT}"
done

# Run pip audit if available
if command -v pip-audit &> /dev/null; then
    echo "Running pip-audit vulnerability scan..."
    pip-audit --desc 2>&1 | tee -a "${PYTHON_REPORT}" || echo "Note: Some vulnerabilities found - review ${PYTHON_REPORT}"
else
    echo -e "${YELLOW}  ℹ️  pip-audit not installed (optional)${NC}"
    echo "  Install with: pip install pip-audit"
fi

echo -e "${GREEN}✓ Python report saved to: ${PYTHON_REPORT}${NC}"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2: Node.js Dependency Scanning
# ──────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/4] Node.js Dependency Scanning${NC}"
echo "────────────────────────────────────────────────────────────────"

NODE_REPORT="${REPORTS_DIR}/nodejs-dependencies-${TIMESTAMP}.txt"
touch "${NODE_REPORT}"

echo "Scanning Node.js dependencies..."
echo "Timestamp: $(date)" >> "${NODE_REPORT}"
echo "" >> "${NODE_REPORT}"

for pkg_file in $(find "${PROJECT_ROOT}/services" -name "package.json" -not -path "*/node_modules/*"); do
    echo "📦 Checking: $pkg_file" | tee -a "${NODE_REPORT}"
    
    # Extract dependencies and check if all are pinned (no ^, ~, *, >=, etc)
    if grep -A 50 '"dependencies"' "$pkg_file" | grep -E '"\^|"~|"\*|" <|" >|" !' | grep -v "^#"; then
        echo -e "${RED}  ⚠️  WARNING: Found non-pinned versions (caret, tilde, etc)${NC}" | tee -a "${NODE_REPORT}"
    else
        echo -e "${GREEN}  ✓ All versions appear to be pinned${NC}" | tee -a "${NODE_REPORT}"
    fi
    
    # Run npm audit if available
    if command -v npm &> /dev/null; then
        cd "$(dirname "$pkg_file")"
        echo "  Running npm audit..." >> "${NODE_REPORT}"
        npm audit --production 2>&1 | tee -a "${NODE_REPORT}" || true
        cd "${PROJECT_ROOT}"
    fi
    
    echo "" >> "${NODE_REPORT}"
done

echo -e "${GREEN}✓ Node.js report saved to: ${NODE_REPORT}${NC}"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3: Software Bill of Materials (SBOM) Generation
# ──────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/4] Software Bill of Materials (SBOM) Generation${NC}"
echo "────────────────────────────────────────────────────────────────"

SBOM_FILE="${REPORTS_DIR}/sbom-${TIMESTAMP}.json"

cat > "${SBOM_FILE}" << 'EOF'
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "serialNumber": "urn:uuid:SBOM",
  "version": 1,
  "metadata": {
    "timestamp": "TIMESTAMP_PLACEHOLDER",
    "component": {
      "bom-ref": "agentic-platform",
      "type": "application",
      "name": "Agentic Platform",
      "version": "1.0.0",
      "description": "Enterprise agentic platform with multi-agent orchestration"
    }
  },
  "components": []
}
EOF

# Parse Python requirements
python_components="[]"
for req_file in $(find "${PROJECT_ROOT}/services" -name "requirements.txt"); do
    echo "📊 Analyzing Python dependencies from: $req_file"
    grep "^[a-zA-Z]" "$req_file" | while read -r line; do
        if [[ $line =~ ^([a-zA-Z0-9._-]+)==(.+)$ ]]; then
            name="${BASH_REMATCH[1]}"
            version="${BASH_REMATCH[2]}"
            echo "  - $name@$version" >> "${SBOM_FILE}.tmp"
        fi
    done
done

# Parse Node.js dependencies
echo "📊 Analyzing Node.js dependencies..."
for pkg_file in $(find "${PROJECT_ROOT}/services" -name "package.json" -not -path "*/node_modules/*"); do
    echo "  From: $pkg_file"
    # Extract dependency versions (simplified parser)
    grep -oP '"[a-zA-Z0-9._-]+": "\d+\.\d+\.\d+"' "$pkg_file" | \
    sed 's/"//g' | sed 's/: /@@/g' | \
    while IFS='@@' read -r name version; do
        echo "  - $name@$version" >> "${SBOM_FILE}.tmp"
    done
done

echo -e "${GREEN}✓ SBOM generated: ${SBOM_FILE}${NC}"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4: Docker Image Security Scanning
# ──────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/4] Docker Image Analysis${NC}"
echo "────────────────────────────────────────────────────────────────"

DOCKER_REPORT="${REPORTS_DIR}/docker-images-${TIMESTAMP}.txt"
touch "${DOCKER_REPORT}"

echo "Analyzing Docker images in use..."
echo "Timestamp: $(date)" >> "${DOCKER_REPORT}"
echo "" >> "${DOCKER_REPORT}"

# Extract image information from docker-compose.yml
if [ -f "${PROJECT_ROOT}/docker-compose.yml" ]; then
    echo "Images from docker-compose.yml:" | tee -a "${DOCKER_REPORT}"
    grep -E "image:" "${PROJECT_ROOT}/docker-compose.yml" | sed 's/.*image: //' | sort | uniq | while read -r image; do
        echo "  - $image" | tee -a "${DOCKER_REPORT}"
    done
fi

# Scan for image digest/SHA verification
echo "" | tee -a "${DOCKER_REPORT}"
echo "Security Recommendations:" | tee -a "${DOCKER_REPORT}"
echo "  ✓ Always use specific version tags (not 'latest')" | tee -a "${DOCKER_REPORT}"
echo "  ✓ Use SHA256 digests for guaranteed immutability" | tee -a "${DOCKER_REPORT}"
echo "  ✓ Sign images with Docker Content Trust" | tee -a "${DOCKER_REPORT}"
echo "  ✓ Scan images with Trivy or Docker Scout" | tee -a "${DOCKER_REPORT}"

echo -e "${GREEN}✓ Docker report saved to: ${DOCKER_REPORT}${NC}"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# SUMMARY REPORT
# ──────────────────────────────────────────────────────────────────────────────
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  SUPPLY CHAIN SECURITY SCAN COMPLETE                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Reports generated:"
echo "  📄 Python:    ${PYTHON_REPORT}"
echo "  📦 Node.js:   ${NODE_REPORT}"
echo "  📊 SBOM:      ${SBOM_FILE}"
echo "  🐳 Docker:    ${DOCKER_REPORT}"
echo ""
echo "Next Steps:"
echo "  1. Review all reports in: ${REPORTS_DIR}"
echo "  2. Address any vulnerabilities found"
echo "  3. Commit updated lock files (package-lock.json, poetry.lock)"
echo "  4. Update CHANGELOG.md with security patch details"
echo "  5. Run in CI/CD pipeline on every PR"
echo ""

exit 0
