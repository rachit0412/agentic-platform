#!/bin/bash
set -e

echo "🚀 Setting up Agentic Platform development environment..."

# Install Python dependencies for LangGraph API
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r services/langgraph-api/requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# PostgreSQL
POSTGRES_USER=agentic
POSTGRES_PASSWORD=agentic123
POSTGRES_DB=agentic_platform

# WebUI
WEBUI_SECRET_KEY=super-secret-key-change-in-production

# Keycloak
KEYCLOAK_CLIENT_SECRET=your-client-secret-here

# n8n
N8N_USER=admin
N8N_PASSWORD=admin123

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-test
LANGFUSE_SECRET_KEY=sk-lf-test

# Redis
REDIS_PASSWORD=redis123
EOF
    echo "✅ .env file created with default values"
fi

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Pull default Ollama models (in background)
echo "🤖 Pulling Ollama models (this may take a while)..."
(
    docker exec ollama ollama pull llama3 2>/dev/null || echo "⚠️  Ollama not ready yet, you can pull models later with: docker exec ollama ollama pull llama3"
    docker exec ollama ollama pull nomic-embed-text 2>/dev/null || echo "⚠️  Skipping nomic-embed-text"
) &

echo "✅ Development environment setup complete!"
echo ""
echo "📌 Available Services:"
echo "   - OpenWebUI:    http://localhost:3000"
echo "   - n8n:          http://localhost:5678"
echo "   - LangGraph:    http://localhost:8000"
echo "   - Ollama:       http://localhost:11434"
echo "   - Keycloak:     http://localhost:8080"
echo "   - Langfuse:     http://localhost:3001"
echo "   - Grafana:      http://localhost:3002"
echo ""
echo "🎯 Next steps:"
echo "   1. Wait for all services to start (check docker-compose logs)"
echo "   2. Access OpenWebUI at port 3000"
echo "   3. Configure your agents in the LangGraph API"
echo ""
