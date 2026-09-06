# Environment Variables Reference

Complete guide to all environment variables used in the Agentic Platform, organized by category.

## Docker Image Versions

Control Docker image versions used by platform services. All are optional with secure defaults provided.

### n8n Workflow Orchestrator
```bash
N8N_IMAGE_TAG=2.37.4-dacee6c-arm64
```
- **Service**: Workflow automation and orchestration
- **Default**: Latest tested stable version
- **Override**: `export N8N_IMAGE_TAG=latest` for bleeding edge
- **Registry**: https://hub.docker.com/r/n8nio/n8n
- **Security**: Check releases for vulnerability patches

### nginx Reverse Proxy
```bash
NGINX_IMAGE_TAG=1.27.0-alpine
```
- **Service**: n8n reverse proxy for iframe embedding
- **Default**: Alpine-based for minimal attack surface
- **Latest**: 1.27.1-alpine
- **Registry**: https://hub.docker.com/_/nginx
- **Purpose**: High-performance reverse proxy

### Ollama LLM Runtime
```bash
OLLAMA_IMAGE_TAG=0.4.2
```
- **Service**: Local LLM inference engine
- **Default**: Stable version with proven compatibility
- **Registry**: https://hub.docker.com/r/ollama/ollama
- **Models**: Downloads from Ollama library
- **Note**: First startup downloads base model (~5GB)

### Prometheus Metrics
```bash
PROMETHEUS_IMAGE_TAG=2.50.1
```
- **Service**: Time-series metrics database
- **Default**: Latest stable release
- **Latest**: 2.51.0+
- **Registry**: https://hub.docker.com/r/prom/prometheus
- **Config**: `./observability/prometheus/prometheus.yml`
- **Retention**: Configure time-series retention period

### Langfuse LLM Observability
```bash
LANGFUSE_IMAGE_TAG=2.185.0
```
- **Service**: LLM monitoring and debugging
- **Default**: Latest v2 minor version
- **Registry**: https://hub.docker.com/r/langfuse/langfuse
- **Note**: Uses separate PostgreSQL database
- **WebUI**: http://localhost:3012

---

## LLM Provider Selection

Choose which LLM provider to use as default for agent inference.

### Ollama (Local, Free)
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
OLLAMA_PORT=11436
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_KEEP_ALIVE=24h
```
- **Cost**: Free (runs locally)
- **Models**: llama3, mistral, neural-chat, etc.
- **Speed**: Depends on hardware
- **Privacy**: All data stays on your server

### Azure OpenAI (Fast, Requires Credits)
```bash
LLM_PROVIDER=azure-openai
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-06-01
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```
- **Cost**: Pay per token (fast)
- **Models**: GPT-4, GPT-4o-mini, etc.
- **Speed**: Best latency (~1-2s)
- **Setup**: Get credentials from Azure Portal

### OpenAI API (Fast, Pay-as-you-go)
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```
- **Cost**: Pay per token
- **Models**: GPT-4, GPT-4o, etc.
- **Speed**: Fast (~2-3s)
- **Setup**: Get key from https://platform.openai.com

### Azure AI Foundry (Enterprise)
```bash
LLM_PROVIDER=azure-foundry
AZURE_FOUNDRY_API_KEY=your-key
AZURE_FOUNDRY_ENDPOINT=https://xxx.models.ai.azure.com
AZURE_FOUNDRY_MODEL=your-model
AZURE_FOUNDRY_API_VERSION=2024-10-21
AZURE_FOUNDRY_EMBEDDING_DEPLOYMENT=your-embedding-model
```
- **Cost**: Varies (enterprise pricing)
- **Models**: Varies by deployment
- **Setup**: Configure in Azure AI Foundry

### Groq (Ultra-fast)
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```
- **Cost**: Generous free tier
- **Speed**: ~500 tokens/second
- **Models**: Llama, Mixtral, QwQ
- **Setup**: https://console.groq.com/keys

### Anthropic Claude (Advanced Reasoning)
```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```
- **Cost**: Pay per token
- **Strength**: Advanced reasoning, code generation
- **Setup**: https://console.anthropic.com

---

## Observability & Monitoring

### OpenTelemetry Collector
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_HTTP_PORT=4318
OTEL_GRPC_PORT=4317
```
- **Purpose**: Collects traces, metrics, logs
- **Config**: `./services/otel/otel-collector.yaml`
- **Exporters**: Prometheus, Jaeger, Loki

### Grafana Dashboard
```bash
GRAFANA_PORT=3013
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```
- **Access**: http://localhost:3013
- **Data Sources**: Prometheus, Loki
- **Dashboards**: Auto-provisioned from `./observability/grafana/dashboards/`
- **⚠️ Security**: Change default password in production

### Prometheus Metrics
```bash
PROMETHEUS_PORT=9090
```
- **Access**: http://localhost:9090
- **Scrape**: Every 15 seconds
- **Retention**: Default 15 days (configurable)

### Loki Log Aggregation
```bash
LOKI_PORT=3100
```
- **Purpose**: Central log storage and search
- **Config**: `./observability/loki/loki-config.yaml`
- **Query**: Via Grafana

---

## Database Connections

### PostgreSQL (Datastore)
```bash
DATASTORE_DB_URL=postgresql://agentic:${DATASTORE_DB_PASSWORD}@datastore-db:5432/datastore
DATASTORE_DB_PASSWORD=agentic
DATASTORE_DB_PORT=5433
```
- **Purpose**: Document registry, workspace data
- **Version**: 16-alpine
- **Backup**: Volume `datastore-db-data`

### PostgreSQL (Langfuse)
```bash
DATABASE_URL=postgresql://langfuse:${LANGFUSE_DB_PASSWORD}@langfuse-db:5432/langfuse
LANGFUSE_DB_PASSWORD=langfuse
```
- **Purpose**: LLM observability data
- **Auto-init**: Schema created on first startup

### ChromaDB (Vector Memory)
```bash
CHROMA_URL=http://chromadb:8000
CHROMA_PORT=8200
```
- **Purpose**: Embeddings and semantic search
- **Version**: 0.6.3
- **Storage**: Volume `chroma-data`

---

## Authentication & Session Management

### Session Configuration
```bash
SESSION_SECRET=your-secret-key-here
```
- **Generate**: `openssl rand -base64 64 | tr -d '\n'`
- **⚠️ Critical**: Change in production
- **Usage**: Encrypts session cookies
- **Persistence**: Sessions survive restarts if set

### User Seeding (First Startup Only)
```bash
ADMIN_SEED_PASSWORD=initial-admin-password
RACHIT_SEED_PASSWORD=initial-user-password
```
- **Purpose**: Create seed users on first DB initialization
- **Applied**: Only if users don't already exist
- **Recommendation**: Set before first startup, then remove
- **Access**: Change via admin panel after login

### n8n Credentials
```bash
N8N_USER=admin
N8N_PASSWORD=changeme
N8N_OWNER_EMAIL=admin@local.dev
N8N_OWNER_PASSWORD=Changeme1!
N8N_API_KEY=your-api-key
```
- **Access**: http://localhost:5678
- **⚠️ Security**: Change default credentials
- **API**: Required for programmatic access

### Langfuse Credentials
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-local-dev
LANGFUSE_SECRET_KEY=sk-lf-local-dev
LANGFUSE_NEXTAUTH_SECRET=supersecret-nextauth
LANGFUSE_SALT=supersecret-salt
```
- **NextAuth**: Session management secret
- **Salt**: For password hashing
- **Production**: Generate strong random values

---

## Social Sign-On (SSO) — Optional

### Google OAuth2
```bash
SSO_GOOGLE_CLIENT_ID=your-client-id
SSO_GOOGLE_CLIENT_SECRET=your-client-secret
```
- **Setup**: https://console.cloud.google.com/
- **Redirect URI**: `http://localhost:3005/auth/sso/google/callback`

### GitHub OAuth2
```bash
SSO_GITHUB_CLIENT_ID=your-client-id
SSO_GITHUB_CLIENT_SECRET=your-client-secret
```
- **Setup**: https://github.com/settings/developers
- **Redirect URI**: `http://localhost:3005/auth/sso/github/callback`

### Microsoft/Entra ID
```bash
SSO_MICROSOFT_CLIENT_ID=your-client-id
SSO_MICROSOFT_CLIENT_SECRET=your-client-secret
```
- **Setup**: https://portal.azure.com/ (Entra ID)
- **Redirect URI**: `http://localhost:3005/auth/sso/microsoft/callback`

### SSO Base URL
```bash
SSO_BASE_URL=http://localhost:3005
```
- **Purpose**: Base URL for OAuth callbacks
- **Production**: Set to your domain
- **HTTPS**: Always use HTTPS in production

---

## External Integrations

### Brave Search API
```bash
BRAVE_API_KEY=your-api-key
```
- **Purpose**: Web search tool for agents
- **Get Key**: https://api.search.brave.com/
- **Used by**: "search_web" tool in agent toolkit

---

## Ports & Network

### Service Ports (Internal)
```bash
AGENT_PORT=8010           # Agent service
TOOLS_PORT=8011           # Tools service
UI_PORT=3005              # UI Console
N8N_PORT=5678             # n8n (internal)
N8N_PROXY_PORT=5679       # n8n proxy
OLLAMA_PORT=11436         # Ollama
GRAFANA_PORT=3013         # Grafana
PROMETHEUS_PORT=9090      # Prometheus
LANGFUSE_PORT=3012        # Langfuse
LOKI_PORT=3100            # Loki
OTEL_HTTP_PORT=4318       # OpenTelemetry HTTP
OTEL_GRPC_PORT=4317       # OpenTelemetry gRPC
DATASTORE_DB_PORT=5433    # PostgreSQL datastore
CHROMA_PORT=8200          # ChromaDB
```

### External URLs (Browser Accessible)
```bash
AGENT_EXTERNAL_URL=http://localhost:8010
N8N_EXTERNAL_URL=http://localhost:5678
N8N_PROXY_EXTERNAL_URL=http://localhost:5679
LANGFUSE_EXTERNAL_URL=http://localhost:3012
GRAFANA_EXTERNAL_URL=http://localhost:3013
```

---

## Common Configurations

### Development
```bash
LLM_PROVIDER=ollama
SESSION_SECRET=$(openssl rand -base64 64 | tr -d '\n')
SSO_BASE_URL=http://localhost:3005
N8N_SECURE_COOKIE=false
```

### Production
```bash
LLM_PROVIDER=azure-openai
SESSION_SECRET=<strong-random-value>
SSO_BASE_URL=https://your-domain.com
N8N_SECURE_COOKIE=true
LANGFUSE_CSP_ENFORCE_HTTPS=true
```

### Local Testing
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=neural-chat
DEBUG=true
```

---

## Security Best Practices

1. **Never commit secrets** to version control
2. **Generate strong SESSION_SECRET**: `openssl rand -base64 64 | tr -d '\n'`
3. **Change default passwords** before production
4. **Use environment variables** for all sensitive data
5. **Enable HTTPS** behind a reverse proxy in production
6. **Rotate API keys** regularly
7. **Monitor logs** for suspicious activity
8. **Update base images** monthly (see DOCKER-SECURITY.md)

---

## Troubleshooting

### "Service unavailable" errors
- Check `.env` has all required variables set
- Verify service URLs are accessible
- Run `docker compose logs <service-name>` to debug

### "LLM not responding"
- Verify `LLM_PROVIDER` and `OLLAMA_MODEL` are set correctly
- For Ollama: Check `OLLAMA_BASE_URL` and model is downloaded
- For Azure/OpenAI: Verify API key and endpoint are correct

### "Database connection failed"
- Check PostgreSQL is running: `docker compose ps datastore-db`
- Verify `DATASTORE_DB_PASSWORD` and `LANGFUSE_DB_PASSWORD`
- Run migrations if needed

### "SSO not working"
- Verify `SSO_<PROVIDER>_CLIENT_ID/SECRET` are correct
- Check redirect URIs match in provider settings
- Ensure `SSO_BASE_URL` matches your domain

---

## See Also

- [Docker Security Hardening](./DOCKER-SECURITY.md) — Image version management & CVE scanning
- [Architecture](./ARCHITECTURE.md) — System design and component interactions
- [README.md](../README.md) — Quick start guide
