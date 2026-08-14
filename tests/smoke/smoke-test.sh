#!/usr/bin/env bash
# Smoke test — quick sanity check that all services are alive
# Usage:  bash tests/smoke/smoke-test.sh
set -euo pipefail

AGENT_URL="${AGENT_URL:-http://localhost:8010}"
TOOLS_URL="${TOOLS_URL:-http://localhost:8011}"
CONSOLE_URL="${CONSOLE_URL:-http://localhost:3000}"
LANGFUSE_URL="${LANGFUSE_URL:-http://localhost:3002}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3003}"

pass=0
fail=0

check() {
  local name="$1" url="$2"
  if curl -sf --max-time 10 "$url" > /dev/null 2>&1; then
    echo "  ✓ $name"
    ((pass++))
  else
    echo "  ✗ $name ($url)"
    ((fail++))
  fi
}

echo "═══ Smoke Test ═══"
echo ""
echo "Health checks:"
check "Agent Service"   "$AGENT_URL/health"
check "Tools Service"   "$TOOLS_URL/health"
check "Dashboard"       "$CONSOLE_URL/health"
check "Langfuse"        "$LANGFUSE_URL/api/public/health"
check "Grafana"         "$GRAFANA_URL/api/health"

echo ""
echo "Functional checks:"

# Math tool
math_result=$(curl -sf --max-time 10 -X POST "$TOOLS_URL/tools/math" \
  -H "Content-Type: application/json" \
  -d '{"expression":"6*7"}' 2>/dev/null | grep -o '"result":42' || true)
if [ -n "$math_result" ]; then
  echo "  ✓ Math tool (6*7=42)"
  ((pass++))
else
  echo "  ✗ Math tool"
  ((fail++))
fi

# DateTime tool
dt_result=$(curl -sf --max-time 10 -X POST "$TOOLS_URL/tools/datetime" 2>/dev/null | grep -o '"timezone":"UTC"' || true)
if [ -n "$dt_result" ]; then
  echo "  ✓ DateTime tool"
  ((pass++))
else
  echo "  ✗ DateTime tool"
  ((fail++))
fi

# Console health-check API
console_api=$(curl -sf --max-time 15 "$CONSOLE_URL/api/health-check" 2>/dev/null | grep -o '"services"' || true)
if [ -n "$console_api" ]; then
  echo "  ✓ Console health-check API"
  ((pass++))
else
  echo "  ✗ Console health-check API"
  ((fail++))
fi

# Marketplace API
mkt=$(curl -sf --max-time 10 "$CONSOLE_URL/api/marketplace/templates" 2>/dev/null | grep -o '"templates"' || true)
if [ -n "$mkt" ]; then
  echo "  ✓ Marketplace API"
  ((pass++))
else
  echo "  ✗ Marketplace API"
  ((fail++))
fi

# Agent tools list
tools_list=$(curl -sf --max-time 10 "$AGENT_URL/tools" 2>/dev/null | grep -o '"tools"' || true)
if [ -n "$tools_list" ]; then
  echo "  ✓ Agent Tools API"
  ((pass++))
else
  echo "  ✗ Agent Tools API"
  ((fail++))
fi

# Agent models
models=$(curl -sf --max-time 10 "$AGENT_URL/models" 2>/dev/null | grep -o '"current_model"' || true)
if [ -n "$models" ]; then
  echo "  ✓ Agent Models API"
  ((pass++))
else
  echo "  ✗ Agent Models API"
  ((fail++))
fi

# Documents stats
doc_stats=$(curl -sf --max-time 10 "$AGENT_URL/documents/stats" 2>/dev/null | grep -o '"total_chunks"' || true)
if [ -n "$doc_stats" ]; then
  echo "  ✓ Documents Stats API"
  ((pass++))
else
  echo "  ✗ Documents Stats API"
  ((fail++))
fi

# ChromaDB heartbeat
chroma_hb=$(curl -sf --max-time 10 "http://localhost:8200/api/v1/heartbeat" 2>/dev/null || true)
if [ -n "$chroma_hb" ]; then
  echo "  ✓ ChromaDB"
  ((pass++))
else
  echo "  ✗ ChromaDB"
  ((fail++))
fi

# Code execution
code_exec=$(curl -sf --max-time 15 -X POST "$TOOLS_URL/tools/code-execute" \
  -H "Content-Type: application/json" \
  -d '{"code":"print(1+1)"}' 2>/dev/null | grep -o '"exit_code":0' || true)
if [ -n "$code_exec" ]; then
  echo "  ✓ Code Execute"
  ((pass++))
else
  echo "  ✗ Code Execute"
  ((fail++))
fi

echo ""
echo "═══ Results: $pass passed, $fail failed ═══"

if [ "$fail" -gt 0 ]; then
  exit 1
fi
