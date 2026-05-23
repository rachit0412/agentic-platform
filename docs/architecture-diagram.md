# Architecture Diagram

```mermaid
flowchart TD
    User([👤 User]) --> UI[🖥️ UI Console<br/>Express.js :3000]
    UI --> Agent[🧠 Agent Service<br/>FastAPI + LangGraph :8010]

    Agent --> Guards{Guardrails}
    Guards -->|Pass| RAG
    Guards -->|Block| UI

    Agent --> RAG[📚 RAG Pipeline]
    RAG --> Chroma[(ChromaDB :8200)]
    RAG --> LlamaIdx[LlamaIndex<br/>Advanced Retrieval]

    Agent --> LLM{🤖 LLM Layer}
    LLM --> Ollama[Ollama<br/>Local Models]
    LLM --> AzureOAI[Azure OpenAI]
    LLM --> OpenAI[OpenAI]
    LLM --> Foundry[Azure AI Foundry]

    Agent --> Tools[🔧 Tools Service<br/>FastAPI :8011]
    Tools --> BuiltIn[33 Tool Endpoints]

    Agent --> MCP[MCP Servers<br/>External + Managed Tools]
    Agent -->|Docker SDK| ManagedMCP[🔗 Managed MCP<br/>Config / Code Containers]
    Agent --> A2A[A2A Peers<br/>Agent Delegation]
    Agent --> N8N[⚡ n8n<br/>Workflows :5678]

    Agent --> Data[(💾 SQLite + PostgreSQL)]

    Agent -.-> OTel[📡 OTel Collector]
    Agent -.-> Langfuse[Langfuse :3012]
    OTel -.-> Prom[Prometheus :9090]
    OTel -.-> Loki[Loki :3100]
    Prom -.-> Grafana[📊 Grafana :3013]
    Loki -.-> Grafana

    classDef frontend fill:#e3f2fd,stroke:#1976d2,color:#0d47a1
    classDef agent fill:#fff3e0,stroke:#f57c00,color:#e65100
    classDef llm fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c
    classDef data fill:#e8f5e9,stroke:#388e3c,color:#1b5e20
    classDef obs fill:#e0f2f1,stroke:#00796b,color:#004d40
    classDef tools fill:#fce4ec,stroke:#c62828,color:#b71c1c

    class UI frontend
    class Agent agent
    class LLM,Ollama,AzureOAI,OpenAI,Foundry llm
    class Data,Chroma data
    class OTel,Langfuse,Prom,Loki,Grafana obs
    class Tools,BuiltIn,MCP,ManagedMCP tools
```

## Layer Summary

| Layer         | Components                                | Purpose                        |
| ------------- | ----------------------------------------- | ------------------------------ |
| Frontend      | Express.js + EJS (25 pages)               | Dashboard & API proxy          |
| Orchestrator  | FastAPI + LangGraph                       | ReAct loop, routing, state     |
| LLM           | Ollama, Azure OpenAI, OpenAI, Foundry     | Multi-provider inference       |
| RAG           | ChromaDB + LlamaIndex                     | Retrieval-augmented generation |
| Tools         | tools-service, MCP (external + managed), A2A, n8n | Tool execution & automation    |
| Data          | SQLite + PostgreSQL                       | Config, memory, documents      |
| Observability | OTel, Prometheus, Grafana, Loki, Langfuse | Metrics, logs, LLM traces      |
