# Network Architecture

Comprehensive documentation of the Agentic Platform's network topology, communication flows, security boundaries, and integration patterns.

## Network Topology Overview

```mermaid
graph TB
    subgraph "User Network"
        Browser["👤 User Browser<br/>localhost:3000<br/>localhost:5679<br/>localhost:3001"]
    end
    
    subgraph "Container Network (docker0)"
        subgraph "Entry Points"
            UIConsole["🖥️ UI Console<br/>Express.js<br/>:3000<br/>Port Mapping:<br/>3000→3000"]
            N8NProxy["🔀 n8n Proxy<br/>nginx<br/>:5679<br/>Port Mapping:<br/>5679→5679"]
            Grafana["📊 Grafana<br/>Dashboard<br/>:3001<br/>Port Mapping:<br/>3001→3001"]
        end
        
        subgraph "Core Services"
            AgentService["🧠 Agent Service<br/>FastAPI<br/>:8000<br/>Internal Only"]
            ToolsService["🛠️ Tools Service<br/>FastAPI<br/>:8001<br/>Internal Only"]
        end
        
        subgraph "Infrastructure Services"
            Ollama["🦙 Ollama<br/>:11434<br/>Internal Only"]
            ChromaDB["🔍 ChromaDB<br/>:8000<br/>Internal Only"]
            OTEL["📊 OTel Collector<br/>:4317<br/>Internal Only"]
            Prometheus["📊 Prometheus<br/>:9090<br/>Internal Only"]
            Loki["📝 Loki<br/>:3100<br/>Internal Only"]
            Langfuse["📈 Langfuse<br/>:3000<br/>Internal Only"]
            N8N["⚡ n8n<br/>:5678<br/>Internal Only"]
        end
        
        subgraph "Data Storage"
            SQLite["💾 SQLite<br/>agent-service<br/>tools-service<br/>n8n"]
            PostgreSQL["🐘 PostgreSQL<br/>:5432<br/>datastore-db<br/>langfuse-db"]
        end
        
        subgraph "Security Scanning"
            ClamAV["🛡️ ClamAV<br/>antivirus daemon<br/>libmagic"]
            GitLeaks["🔑 GitLeaks<br/>credential scanner"]
        end
        
        subgraph "MCPs"
            BraveSearchMCP["🔍 Brave Search MCP<br/>:3000+<br/>Tool Discovery"]
            OpenToolsMCP["🔧 Open Tools MCP<br/>:3001+<br/>Tool Discovery"]
        end
    end
    
    Browser -->|"HTTP :3000"| UIConsole
    Browser -->|"HTTP :5679"| N8NProxy
    Browser -->|"HTTP :3001"| Grafana
    
    UIConsole -->|"HTTP :8000<br/>agent-service"| AgentService
    UIConsole -->|"HTTP :8001<br/>tools-service"| ToolsService
    UIConsole -->|"HTTP :5678<br/>n8n proxy"| N8N
    
    AgentService -->|"HTTP :8000"| ChromaDB
    AgentService -->|"HTTP :11434"| Ollama
    AgentService -->|"HTTP :8001"| ToolsService
    AgentService -->|"HTTP :5678<br/>webhook"| N8N
    AgentService -->|"SQLite<br/>embedded"| SQLite
    
    ToolsService -->|"HTTP :11434"| Ollama
    ToolsService -->|"Direct call"| ClamAV
    ToolsService -->|"Shell exec"| GitLeaks
    ToolsService -->|"SQLite<br/>embedded"| SQLite
    ToolsService -->|"HTTP :3000+<br/>MCP"| BraveSearchMCP
    ToolsService -->|"HTTP :3001+<br/>MCP"| OpenToolsMCP
    
    AgentService -->|"gRPC :4317<br/>OTel"| OTEL
    ToolsService -->|"gRPC :4317<br/>OTel"| OTEL
    UIConsole -->|"HTTP push"| OTEL
    
    OTEL -->|"HTTP scrape"| Prometheus
    OTEL -->|"gRPC push"| Loki
    
    Prometheus -->|"Datasource"| Grafana
    Loki -->|"Datasource"| Grafana
    
    AgentService -->|"HTTP :3000<br/>Langfuse SDK"| Langfuse
    
    N8NProxy -->|"HTTP :5678"| N8N
    
    classDef entry fill:#F5E6FF,stroke:#7B1FA2
    classDef core fill:#E8F5E9,stroke:#43A047
    classDef infra fill:#FFF9E6,stroke:#F9A825
    classDef data fill:#DEECFF,stroke:#1976D2
    classDef security fill:#FFEBEE,stroke:#C62828
    classDef mcp fill:#E0F2F1,stroke:#00796B
    
    class UIConsole,N8NProxy,Grafana entry
    class AgentService,ToolsService core
    class Ollama,ChromaDB,OTEL,Prometheus,Loki,Langfuse,N8N infra
    class SQLite,PostgreSQL data
    class ClamAV,GitLeaks security
    class BraveSearchMCP,OpenToolsMCP mcp
```

## Network Communication Flows

### Flow 1: User Query Execution

```mermaid
graph LR
    User["👤 User<br/>Browser"]
    UI["UI Console<br/>:3000"]
    Agent["Agent Service<br/>:8000"]
    LLM["Ollama<br/>:11434"]
    Vector["ChromaDB<br/>:8000"]
    Tools["Tools Service<br/>:8001"]
    OTel["OTel Collector<br/>:4317"]
    
    User -->|"POST /api/agents/:id/execute<br/>HTTP JSON"| UI
    UI -->|"POST /agents/:id/execute<br/>HTTP JSON"| Agent
    Agent -->|"Query Embedding<br/>HTTP JSON"| Vector
    Agent -->|"LLM Inference<br/>HTTP JSON"| LLM
    Agent -->|"Tool Invocation<br/>HTTP JSON"| Tools
    Tools -->|"Tool Result"| Agent
    Agent -->|"gRPC Span Export"| OTel
    Agent -->|"JSON Response"| UI
    UI -->|"HTML Render<br/>WebSocket Stream"| User
```

### Flow 2: File Upload & Scanning

```mermaid
graph TB
    User["👤 User<br/>Browser"]
    UI["UI Console<br/>:3000"]
    Auth["Session Auth<br/>Middleware"]
    Tools["Tools Service<br/>:8001"]
    ClamAV["ClamAV<br/>daemon"]
    GitLeaks["GitLeaks<br/>scanner"]
    DB["SQLite<br/>audit_log"]
    OTel["OTel Collector<br/>:4317"]
    
    User -->|"Form Upload<br/>multipart/form-data"| UI
    UI -->|"Auth Check<br/>Session Cookie"| Auth
    Auth -->|"✓ Valid"| UI
    UI -->|"POST /tools/scan-file<br/>Binary + Metadata"| Tools
    Tools -->|"Scan Request<br/>clamdscan"| ClamAV
    ClamAV -->|"Scan Result<br/>clean/threat"| Tools
    Tools -->|"Pattern Match<br/>Shell Exec"| GitLeaks
    GitLeaks -->|"Credential Found<br/>JSON"| Tools
    Tools -->|"INSERT audit_event<br/>SQL"| DB
    Tools -->|"Span Data<br/>gRPC"| OTel
    Tools -->|"JSON Response<br/>result + status"| UI
    UI -->|"Toast Notification<br/>HTML"| User
```

### Flow 3: Security Scanning Pipeline

```mermaid
graph TB
    Admin["👤 Admin<br/>Browser"]
    AdminUI["Admin Plane<br/>UI Console<br/>:3000"]
    Agent["Agent Service<br/>:8000"]
    Tools["Tools Service<br/>:8001"]
    
    subgraph "ClamAV Scan"
        ClamAV["ClamAV<br/>antivirus daemon"]
        LibMagic["libmagic<br/>file validator"]
    end
    
    subgraph "GitLeaks Scan"
        GitLeaks["GitLeaks<br/>scanner"]
        GitHistory["Git History<br/>Analyzer"]
    end
    
    subgraph "OWASP Assessment"
        OWASP["OWASP<br/>Checker<br/>10 items"]
    end
    
    DB["SQLite<br/>compliance_audit_log"]
    PDF["PDF Generator<br/>Scan Report"]
    
    Admin -->|"Click 'Run Scan'<br/>HTTP POST"| AdminUI
    AdminUI -->|"POST /run-scan<br/>JSON params"| Agent
    Agent -->|"Trigger Scans<br/>HTTP"| Tools
    
    Tools -->|"Upload Files<br/>Binary"| ClamAV
    ClamAV -->|"Detect Malware<br/>Result"| Tools
    Tools -->|"Check Magic Bytes<br/>File Type"| LibMagic
    LibMagic -->|"Type Validation"| Tools
    
    Tools -->|"Scan Credentials<br/>Target Path"| GitLeaks
    GitLeaks -->|"Pattern Matching<br/>Entropy Check"| GitHistory
    GitHistory -->|"Found Secrets<br/>List"| Tools
    
    Tools -->|"Check OWASP<br/>10 Items"| OWASP
    OWASP -->|"Risk Assessment<br/>Results"| Tools
    
    Tools -->|"Record Event<br/>SQL INSERT"| DB
    Tools -->|"Collect Results<br/>Data"| PDF
    PDF -->|"Generate Report<br/>PDF Blob"| AdminUI
    AdminUI -->|"Download File<br/>Blob URL"| Admin
```

## Service-to-Service Communication

### HTTP REST API Endpoints

| From | To | Endpoint | Method | Protocol | Port | Auth |
|------|----|----|--------|----------|------|------|
| UI Console | Agent Service | `/agents` | GET/POST | HTTP JSON | 8000 | Bearer token (future) |
| UI Console | Agent Service | `/agents/:id/execute` | POST | HTTP JSON | 8000 | Bearer token |
| UI Console | Tools Service | `/tools` | GET | HTTP JSON | 8001 | Bearer token |
| UI Console | Tools Service | `/tools/:name/execute` | POST | HTTP JSON | 8001 | Bearer token |
| Agent Service | Tools Service | `/tools/:name/execute` | POST | HTTP JSON | 8001 | Service-to-service |
| Agent Service | n8n | `/webhook/agent-trigger` | POST | HTTP JSON | 5678 | API key (env var) |
| Tools Service | ClamAV | `/scan` (internal) | N/A | libclamav C API | N/A | N/A |
| Tools Service | Ollama | `/api/embeddings` | POST | HTTP JSON | 11434 | None (internal) |
| Agent Service | Ollama | `/api/generate` | POST | HTTP JSON | 11434 | None (internal) |
| Agent Service | ChromaDB | `/api/v1/collections` | GET/POST | HTTP JSON | 8000 | None (internal) |
| MCP Servers | Tool Discovery | `/resources` | GET | HTTP JSON | Dynamic | API key |

### gRPC Telemetry Flows

| From | To | Endpoint | Data | Protocol | Port |
|------|----|----|------|----------|------|
| Agent Service | OTel Collector | `/opentelemetry.proto.collector.trace.v1.TraceService/Export` | Spans | gRPC | 4317 |
| Tools Service | OTel Collector | `/opentelemetry.proto.collector.trace.v1.TraceService/Export` | Spans | gRPC | 4317 |
| OTel Collector | Prometheus | `/metrics` | Time-series | HTTP (scrape) | 9090 |
| OTel Collector | Loki | `/loki/api/v1/push` | Logs | gRPC | 3100 |

### WebSocket Streams (Real-time)

| From | To | Endpoint | Use Case | Port |
|------|----|----|----------|------|
| Agent Service | UI Console | `/api/agents/:id/stream` | Agent execution streaming | 3000 |
| UI Console | Browser | `/stream` | SSE progress updates | 3000 |

## Network Security Boundaries

### Boundary 1: User → Platform (Perimeter)

```mermaid
graph LR
    User["👤 User<br/>External Network"]
    TLS["🔒 TLS 1.2+<br/>Encryption"]
    UIConsole["UI Console<br/>:3000"]
    AuthMiddleware["Auth Middleware<br/>Session Check"]
    CORS["CORS Policy<br/>localhost:* only"]
    RateLimit["Rate Limiter<br/>Token Bucket"]
    
    User -->|"HTTPS (future)"| TLS
    TLS -->|"Decrypted HTTP"| UIConsole
    UIConsole -->|"Check Session"| AuthMiddleware
    AuthMiddleware -->|"Validate Origin"| CORS
    CORS -->|"Check Rate Limit"| RateLimit
    RateLimit -->|"✓ Pass"| UIConsole
    RateLimit -->|"✗ Reject (429)"| User
    
    classDef user fill:#FFEBEE,stroke:#C62828
    classDef security fill:#FFEBEE,stroke:#C62828
    classDef service fill:#E8F5E9,stroke:#43A047
    
    class User user
    class TLS,AuthMiddleware,CORS,RateLimit security
    class UIConsole service
```

**Controls**:
- Session cookie (HttpOnly, SameSite=Strict)
- CORS whitelist (localhost only for dev)
- Rate limiting (5 auth attempts per 5 minutes per IP)
- CSRF token validation on state-changing operations
- Input validation (type checking, size limits)

### Boundary 2: Platform → External APIs (Egress)

```mermaid
graph LR
    Agent["Agent Service<br/>:8000"]
    ToolsService["Tools Service<br/>:8001"]
    
    subgraph "External APIs (Optional)"
        AzureOpenAI["Azure OpenAI<br/>LLM API"]
        OpenAI["OpenAI<br/>API"]
        BraveSearch["Brave Search<br/>API"]
    end
    
    subgraph "Egress Security"
        URLWhitelist["URL Whitelist<br/>http_fetch tool"]
        SSRFProtection["SSRF Protection<br/>Blocked IPs:<br/>127.0.0.1<br/>169.254.x.x<br/>10.0.0.0/8"]
        ProxyConfig["HTTP Proxy<br/>config (corporate)"]
    end
    
    Agent -->|"Check URL"| URLWhitelist
    Agent -->|"Validate Host"| SSRFProtection
    ToolsService -->|"Set proxy"| ProxyConfig
    
    URLWhitelist -->|"✓ Allowed"| AzureOpenAI
    URLWhitelist -->|"✓ Allowed"| OpenAI
    URLWhitelist -->|"✓ Allowed"| BraveSearch
    
    classDef external fill:#FFF9E6,stroke:#F9A825
    classDef security fill:#FFEBEE,stroke:#C62828
    
    class AzureOpenAI,OpenAI,BraveSearch external
    class URLWhitelist,SSRFProtection,ProxyConfig security
```

**Controls**:
- URL whitelist for HTTP fetch tool
- SSRF protection (blocks private IPs)
- Proxy configuration for corporate networks
- TLS certificate validation
- API key rotation (env vars)

### Boundary 3: Internal Network (Container Bridge)

```mermaid
graph TB
    subgraph "Exposed Ports (localhost)"
        UIConsole["UI :3000"]
        N8NProxy["n8n :5679"]
        Grafana["Grafana :3001"]
    end
    
    subgraph "Internal Only (Docker bridge)"
        AgentService["Agent :8000"]
        ToolsService["Tools :8001"]
        Ollama["Ollama :11434"]
        ChromaDB["ChromaDB :8000"]
        N8N["n8n :5678"]
        OTel["OTel :4317"]
        PostgreSQL["PostgreSQL :5432"]
    end
    
    subgraph "Internal Communication Rules"
        DNS["Docker DNS<br/>service discovery"]
        NoTLS["No TLS needed<br/>Docker bridge isolated"]
        NoAuth["No auth<br/>internal traffic"]
    end
    
    UIConsole -.->|"via docker dns"| AgentService
    UIConsole -.->|"via docker dns"| ToolsService
    AgentService -.->|"via docker dns"| Ollama
    ToolsService -.->|"via docker dns"| N8N
    
    DNS --> NoTLS
    DNS --> NoAuth
    
    classDef exposed fill:#F5E6FF,stroke:#7B1FA2
    classDef internal fill:#DEECFF,stroke:#1976D2
    classDef rule fill:#E0F2F1,stroke:#00796B
    
    class UIConsole,N8NProxy,Grafana exposed
    class AgentService,ToolsService,Ollama,ChromaDB,N8N,OTel,PostgreSQL internal
    class DNS,NoTLS,NoAuth rule
```

**Key Properties**:
- All internal services use Docker bridge network isolation
- DNS service discovery by container name
- No TLS certificates needed (Docker bridge is private)
- No authentication between internal services (network isolation provides security)
- External access only through three exposed entry points

## Port Mapping & Exposure

| Container | Internal Port | Host Port | Exposed | Purpose |
|-----------|---------------|-----------|---------|---------|
| ui-console | 3000 | 3000 | ✅ Yes | User dashboard |
| n8n-proxy | 5679 | 5679 | ✅ Yes | Workflow UI proxy |
| grafana | 3001 | 3001 | ✅ Yes | Monitoring dashboard |
| agent-service | 8000 | — | ❌ No | Internal API |
| tools-service | 8001 | — | ❌ No | Internal API |
| ollama | 11434 | — | ❌ No | Internal LLM |
| chromadb | 8000 | — | ❌ No | Internal vector DB |
| datastore-db | 5432 | — | ❌ No | Internal PostgreSQL |
| langfuse-db | 5432 | — | ❌ No | Internal PostgreSQL |
| n8n | 5678 | — | ❌ No | Internal workflow |
| otel-collector | 4317 | — | ❌ No | Internal telemetry |
| prometheus | 9090 | — | ❌ No | Internal metrics |
| loki | 3100 | — | ❌ No | Internal logs |
| langfuse | 3000 | — | ❌ No | Internal tracing |

## DNS & Service Discovery

### Docker Compose Service Names

All services available by container name on Docker bridge network:

```
agent-service:8000
tools-service:8001
ollama:11434
chromadb:8000
ui-console:3000
n8n:5678
n8n-proxy:5679
prometheus:9090
grafana:3001
loki:3100
otel-collector:4317
langfuse:3000
datastore-db:5432
langfuse-db:5432
```

### Resolution Examples

```
Agent Service connecting to Ollama:
  http://ollama:11434/api/generate

Tools Service connecting to n8n:
  http://n8n:5678/webhook/agent-trigger

ChromaDB collection from Agent:
  http://chromadb:8000/api/v1/collections
```

## Firewall Rules (docker-compose networking)

| Source | Destination | Port | Protocol | Allowed |
|--------|-------------|------|----------|---------|
| ui-console | agent-service | 8000 | HTTP | ✅ |
| ui-console | tools-service | 8001 | HTTP | ✅ |
| ui-console | n8n | 5678 | HTTP | ✅ |
| agent-service | tools-service | 8001 | HTTP | ✅ |
| agent-service | ollama | 11434 | HTTP | ✅ |
| agent-service | chromadb | 8000 | HTTP | ✅ |
| tools-service | ollama | 11434 | HTTP | ✅ |
| tools-service | n8n | 5678 | HTTP | ✅ |
| All → otel-collector | 4317 | gRPC | ✅ |
| All → postgres (if needed) | 5432 | TCP | ✅ |
| External | ui-console:3000 | 3000 | HTTP | ✅ |
| External | n8n-proxy:5679 | 5679 | HTTP | ✅ |
| External | grafana:3001 | 3001 | HTTP | ✅ |
| External | agent-service:8000 | 8000 | HTTP | ❌ |
| External | tools-service:8001 | 8001 | HTTP | ❌ |
| External | Internal Services | Any | Any | ❌ |

## Traffic Shaping & Load Characteristics

### Request Rate Profiles

```
Peak Load Scenario (10 concurrent agents):
- Agent execution requests: 10 req/s
- Tool execution calls: 50 req/s (5 tools per agent)
- LLM inference requests: 10 req/s
- Vector search queries: 15 req/s
- Total network throughput: ~5 MB/s (with streaming responses)
- Typical response latency: 2-5s (LLM time dominates)
```

### Data Flow Volumes

| Operation | Data Size | Frequency | Direction |
|-----------|-----------|-----------|-----------|
| Agent execution request | 50-500 KB | Per user query | Client → Platform |
| LLM streaming response | 100-1000 KB | Per LLM call | Platform → Client |
| Document ingestion | 1-100 MB | Per upload | Client → Platform |
| Vector embeddings | 50-500 KB | Per document chunk | ChromaDB ↔ Ollama |
| Telemetry spans | 1-5 KB | Per operation | Services → OTel |
| Audit log events | 1-2 KB | Per event | Services → SQLite |

## Scaling Implications

### Current Bottlenecks (Single-Node)

1. **SQLite single-writer** — concurrent tool execution queues behind write lock
2. **Ollama inference latency** — LLM generation time dominates request latency
3. **ChromaDB memory** — large knowledge bases may exceed container RAM
4. **Network latency** — HTTP overhead on container bridge (vs in-process)

### Multi-Node Scaling (Future ADR)

- PostgreSQL migration for concurrent writes
- Agent-service horizontal scaling behind reverse proxy
- Tools-service horizontal scaling (stateless)
- ChromaDB clustering or pgvector replacement
- Redis for distributed caching
- mTLS service mesh (Istio/Linkerd) for service-to-service auth