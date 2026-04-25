#!/bin/bash
# Health check script for all services
# Usage: ./scripts/health-check.sh

set -e

echo "🏥 Agentic Platform - Health Check"
echo "===================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local name=$1
    local url=$2
    local expected=$3

    printf "%-20s" "$name: "

    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_port() {
    local name=$1
    local port=$2

    printf "%-20s" "$name: "

    if nc -z localhost "$port" 2>/dev/null || (timeout 1 bash -c "cat < /dev/null > /dev/tcp/localhost/$port") 2>/dev/null; then
        echo -e "${GREEN}✓ Listening${NC}"
        return 0
    else
        echo -e "${RED}✗ Not responding${NC}"
        return 1
    fi
}

echo "📊 Checking HTTP Services..."
echo "----------------------------"
check_service "Dashboard" "http://localhost:3000/health" || true
check_service "LangGraph API" "http://localhost:8000/health" || true
check_service "n8n" "http://localhost:5678" || true
check_service "Keycloak" "http://localhost:8080" || true
check_service "Langfuse" "http://localhost:3001" || true
check_service "Grafana" "http://localhost:3002" || true
check_service "Prometheus" "http://localhost:9090/-/healthy" || true
echo ""

echo "🔌 Checking Backend Services..."
echo "--------------------------------"
check_port "PostgreSQL" 5432 || true
check_port "Redis" 6379 || true
check_port "Ollama" 11434 || true
check_port "OPA" 8181 || true
check_port "Loki" 3100 || true
echo ""

echo "🤖 Checking Ollama Models..."
echo "----------------------------"
if docker exec ollama ollama list 2>/dev/null | grep -q "llama3"; then
    echo -e "${GREEN}✓ llama3 installed${NC}"
else
    echo -e "${YELLOW}⚠ llama3 not installed${NC}"
    echo "  Run: docker exec ollama ollama pull llama3"
fi

if docker exec ollama ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo -e "${GREEN}✓ nomic-embed-text installed${NC}"
else
    echo -e "${YELLOW}⚠ nomic-embed-text not installed${NC}"
    echo "  Run: docker exec ollama ollama pull nomic-embed-text"
fi
echo ""

echo "🐳 Docker Containers Status..."
echo "------------------------------"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "💾 Disk Usage..."
echo "----------------"
docker system df
echo ""

echo "===================================="
echo "Health check complete!"
echo ""
echo "Access Points:"
echo "  🎨 Dashboard:     http://localhost:3000"
echo "  📚 API Docs:     http://localhost:8000/docs"
echo "  🔄 Workflows:    http://localhost:5678"
echo "  📊 Monitoring:   http://localhost:3002"
echo ""
