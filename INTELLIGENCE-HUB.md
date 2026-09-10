# Intelligence Hub - Complete Guide

The Intelligence Hub is the central repository for all AI-driven intelligence, knowledge, and operational assets in the Agentic Platform.

## 📑 Sections Overview

### 1. **Prompts**
**Purpose**: Manage and version AI prompts across the platform

- Create, edit, and version system prompts
- Share prompts across agents
- Prompt templates and best practices
- Analytics on prompt performance

**Route**: `/prompts` | **Admin**: `/admin#prompts`

**API Endpoints**:
```bash
GET    /api/prompts              # List all prompts
POST   /api/prompts              # Create prompt
GET    /api/prompts/:id          # Get specific prompt
PUT    /api/prompts/:id          # Update prompt
DELETE /api/prompts/:id          # Delete prompt
POST   /api/prompts/validate     # Validate prompt syntax
POST   /api/prompts/generate     # Generate prompt with AI
```

---

### 2. **Tools**
**Purpose**: Catalog and manage all available tools/integrations

- Browse installed tools and their capabilities
- Tool documentation and usage examples
- Tool parameters and schemas
- Tool testing interface

**Route**: `/tools` | **Admin**: `/admin#tools`

**Tools Available**:
- Web Search
- URL Fetcher
- File Operations
- API Integrations
- Custom Extensions

---

### 3. **Documents**
**Purpose**: RAG (Retrieval Augmented Generation) document management

- Upload and ingest documents
- Manage document collections
- Search and retrieve document chunks
- Document versioning and tagging
- Integration with vector DB (ChromaDB)

**Route**: `/documents` | **Admin**: `/admin#documents`

**API Endpoints**:
```bash
GET    /api/documents             # List documents
POST   /api/documents/upload      # Upload document
POST   /api/documents/ingest      # Ingest/process document
POST   /api/documents/search      # Search documents
GET    /api/documents/stats       # Get collection stats
GET    /api/documents/collections # List document collections
DELETE /api/documents/:source     # Delete document
```

**Supported Formats**:
- PDF, DOCX, TXT
- JSON, CSV, JSONL
- Web URLs (fetch and ingest)
- Direct text input

---

### 4. **Workflows**
**Purpose**: Orchestrate multi-step AI processes via n8n

- Visual workflow builder (n8n UI)
- Pre-built workflow templates
- Workflow execution logs
- Trigger management (webhooks, schedules, events)

**Route**: `/workflows` | **Admin**: `/admin#workflows`

**Integration**: n8n at `http://localhost:5678`

**API Endpoints**:
```bash
GET  /api/n8n/workflows              # List workflows
POST /api/n8n/workflows/:id/activate # Activate workflow
POST /api/n8n/workflows/:id/deactivate
```

**Example Workflows**:
- `agent-workflow` - Multi-agent orchestration
- `web-research` - Automated research pipeline
- `rag-ingest` - Document ingestion pipeline
- `pipeline-with-discovery` - Dynamic tool discovery

---

### 5. **Evaluation**
**Purpose**: Assess and measure AI model and agent performance

- Evaluation frameworks and metrics
- A/B testing setup
- Performance dashboards
- Cost analysis
- Quality scoring

**Route**: `/evaluation` | **Admin**: `/admin#evaluation`

**Metrics Tracked**:
- Response quality
- Latency and throughput
- Token usage and cost
- Success/failure rates
- User satisfaction

---

### 6. **Guardrails**
**Purpose**: Safety, compliance, and constraint management

- Input validation rules
- Output filtering policies
- Compliance requirements
- Sensitive data handling
- Rate limiting and quotas

**Route**: `/guardrails` | **Admin**: `/admin#guardrails`

**API Endpoints**:
```bash
GET    /api/guardrails     # List guardrails
GET    /api/guardrails/:id # Get guardrail details
PUT    /api/guardrails/:id # Update guardrail
```

**Guardrail Types**:
- PII Detection and Masking
- Jailbreak Prevention
- Output Validation
- Rate Limiting
- Cost Control

---

### 7. **Marketplace**
**Purpose**: Discover and manage agent and tool extensions

- Community-contributed agents
- Third-party tool integrations
- Extension ratings and reviews
- Installation management

**Route**: `/marketplace` | **Admin**: `/admin#marketplace`

**Features**:
- Advanced search and filtering
- Dependency resolution
- Version management
- One-click installation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UI Console (Web)                         │
│        /admin#prompts|tools|documents|workflows...          │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Prompts │     │  Tools  │     │Documents│
    │  API    │     │  API    │     │   API   │
    └────┬────┘     └────┬────┘     └────┬────┘
         │               │               │
         │               │               │
    ┌────┴───────────────┴───────────────┴────┐
    │                                         │
    │     Agent Service (FastAPI)             │
    │  - Prompt management                    │
    │  - Tool orchestration                   │
    │  - Document processing                  │
    │  - Guardrail enforcement                │
    │  - Evaluation metrics                   │
    │                                         │
    └────┬────────┬─────────┬────────┬────────┘
         │        │         │        │
    ┌────▼─┐ ┌───▼──┐ ┌───▼──┐ ┌──▼────┐
    │ n8n  │ │Ollama│ │ChromaDB│ │Postgres
    │      │ │(LLM) │ │(Vector) │ │(Meta)
    └──────┘ └──────┘ └────────┘ └───────┘
```

---

## 🚀 Getting Started

### Access Intelligence Hub

1. **Via Admin Panel** (Recommended)
   ```
   http://localhost:3005/admin
   → Click "Intelligence Hub" section
   → Choose tab: Prompts, Tools, Documents, etc.
   ```

2. **Direct URLs**
   ```
   Prompts:      http://localhost:3005/prompts
   Tools:        http://localhost:3005/tools
   Documents:    http://localhost:3005/documents
   Workflows:    http://localhost:3005/workflows
   Evaluation:   http://localhost:3005/evaluation
   Guardrails:   http://localhost:3005/guardrails
   Marketplace:  http://localhost:3005/marketplace
   ```

### Common Workflows

#### Create and Deploy a Prompt
```bash
1. Navigate to /prompts
2. Click "Create Prompt"
3. Define:
   - Name and description
   - System message
   - Input/output schema
   - Version tags
4. Test prompt with AI
5. Deploy to agents
```

#### Ingest Documents for RAG
```bash
1. Navigate to /documents
2. Click "Upload"
3. Select document(s) or paste URL
4. Choose collection and settings
5. Click "Ingest"
6. Monitor processing status
```

#### Create AI Workflow
```bash
1. Navigate to /workflows
2. Click "Create New Workflow"
3. Opens n8n workflow editor
4. Add nodes: Trigger → Process → Output
5. Configure each node
6. Test workflow
7. Activate and set trigger
```

---

## 🔌 Dependencies

| Service | Purpose | Port | Status |
|---------|---------|------|--------|
| **agent-service** | Core APIs | 8000 | ✅ Required |
| **n8n** | Workflow Orchestration | 5678 | ✅ Required |
| **ollama** | LLM Runtime | 11434 | ✅ Required |
| **chromadb** | Vector Database | 8200 | ✅ Required |
| **postgres** | Metadata Store | 5432 | ✅ Required |

### Start All Services
```bash
docker-compose up -d

# Verify all healthy
docker-compose ps
```

---

## 📊 Observability

Monitor Intelligence Hub operations:

- **Metrics**: Prometheus (`:9090`) - Request rates, latencies, errors
- **Logs**: Loki (`:3100`) - Structured logging from all services
- **Traces**: Jaeger (`:16686`) - End-to-end request tracing
- **Dashboards**: Grafana (`:3003`) - Pre-built Intelligence Hub dashboards

**Access**: http://localhost:3005/admin → Observability section

---

## 🔒 Security & Compliance

All Intelligence Hub operations enforce:

- **Authentication**: Token-based access control
- **Authorization**: Role-based permissions (see Personas in admin)
- **Guardrails**: Automatic compliance checks on all inputs/outputs
- **Audit Logging**: Full request/response logging
- **Data Privacy**: PII detection and masking

---

## 🆘 Troubleshooting

### "Cannot access Prompts/Tools/Documents"
```bash
# Check agent-service is healthy
curl http://localhost:8010/health

# Check API connectivity
curl http://localhost:3005/api/prompts
```

### "Document ingestion failed"
```bash
# Check ChromaDB is running
docker-compose ps | grep chromadb

# Check disk space
df -h
```

### "Workflow not executing"
```bash
# Check n8n is healthy
curl http://localhost:5678/healthz

# View n8n logs
docker-compose logs n8n --tail=50
```

---

## 📚 Related Documentation

- [AI Studio](./AI-STUDIO-SETUP.md) - UI Generation
- [Architecture](./docs/ARCHITECTURE.md) - System design
- [API Reference](./docs/API-REFERENCE.md) - All endpoints
- [Observability](./INTELLIGENCE-HUB.md#observability) - Monitoring
- [Guardrails](./docs/SECURITY-CONTROLS-INTEGRATION.md) - Safety controls

---

## 🎯 Next Steps

1. ✅ Explore each Intelligence Hub section
2. ✅ Create your first prompt
3. ✅ Upload sample documents
4. ✅ Build a workflow
5. ✅ Monitor via Grafana dashboards
6. ✅ Set up guardrails for your use case

**Questions?** Check the [Admin Panel → Docs](http://localhost:3005/admin#docs) section.
