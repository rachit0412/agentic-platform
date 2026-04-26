const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3001;

// Service URLs (internal Docker network)
const AGENT_URL = process.env.AGENT_URL || "http://agent-service:8000";
const N8N_URL = process.env.N8N_URL || "http://n8n:5678";
const LANGFUSE_URL = process.env.LANGFUSE_URL || "http://langfuse:3000";
const GRAFANA_URL = process.env.GRAFANA_URL || "http://grafana:3000";
const CHROMA_URL = process.env.CHROMA_URL || "http://chromadb:8000";

// External URLs (browser-accessible)
const N8N_EXTERNAL = process.env.N8N_EXTERNAL_URL || "http://localhost:5678";
const LANGFUSE_EXTERNAL = process.env.LANGFUSE_EXTERNAL_URL || "http://localhost:3002";
const GRAFANA_EXTERNAL = process.env.GRAFANA_EXTERNAL_URL || "http://localhost:3003";
const AGENT_EXTERNAL = process.env.AGENT_EXTERNAL_URL || "http://localhost:8010";

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// ── Health ──────────────────────────────────────────────
app.get("/health", (req, res) => {
  res.json({ status: "healthy", service: "ui-console" });
});

// ── API: Service health checks ─────────────────────────
app.get("/api/health-check", async (req, res) => {
  const services = [
    { name: "agent-service", url: `${AGENT_URL}/health` },
    { name: "tools-service", url: "http://tools-service:8001/health" },
    { name: "n8n", url: `${N8N_URL}/healthz` },
    { name: "ollama", url: "http://ollama:11434/api/tags" },
    { name: "chromadb", url: `${CHROMA_URL}/api/v2/heartbeat` },
  ];

  const results = await Promise.all(
    services.map(async (svc) => {
      try {
        const resp = await fetch(svc.url, { signal: AbortSignal.timeout(5000) });
        return { name: svc.name, status: resp.ok ? "healthy" : "unhealthy", code: resp.status };
      } catch (e) {
        return { name: svc.name, status: "unreachable", error: e.message };
      }
    })
  );
  res.json({ services: results });
});

// ── API: Skills CRUD proxy ─────────────────────────────
app.get("/api/skills", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills`); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/skills", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/skills/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills/${req.params.id}`); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/skills/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills/${req.params.id}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/skills/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills/${req.params.id}`, { method: "DELETE" }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Prompts CRUD proxy ────────────────────────────
app.get("/api/prompts", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts`); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/prompts", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/prompts/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts/${req.params.id}`); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/prompts/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts/${req.params.id}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/prompts/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts/${req.params.id}`, { method: "DELETE" }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Agents CRUD proxy ─────────────────────────────
app.get("/api/agents", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/agents`); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/agents", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/agents`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/agents/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/agents/${req.params.id}`); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/agents/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/agents/${req.params.id}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/agents/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/agents/${req.params.id}`, { method: "DELETE" }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Proxy to agent /run ───────────────────────────
app.post("/api/agent-run", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: "Agent service unreachable", detail: e.message });
  }
});

// ── API: SSE Proxy to agent /run/stream ───────────────
app.post("/api/agent-run/stream", async (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();
  try {
    const resp = await fetch(`${AGENT_URL}/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(120000),
    });
    if (!resp.ok) {
      res.write(`event: error\ndata: ${JSON.stringify({error: "Agent returned " + resp.status})}\n\n`);
      res.end();
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(decoder.decode(value, { stream: true }));
    }
    res.end();
  } catch (e) {
    res.write(`event: error\ndata: ${JSON.stringify({error: e.message})}\n\n`);
    res.end();
  }
});

// ── API: Langfuse traces proxy ─────────────────────────
app.get("/api/traces", async (req, res) => {
  const publicKey = process.env.LANGFUSE_PUBLIC_KEY || "";
  const secretKey = process.env.LANGFUSE_SECRET_KEY || "";
  if (!publicKey || !secretKey) {
    return res.json({ traces: [], error: "Langfuse keys not configured" });
  }
  try {
    const auth = Buffer.from(`${publicKey}:${secretKey}`).toString("base64");
    const resp = await fetch(`${LANGFUSE_URL}/api/public/traces?limit=20`, {
      headers: { Authorization: `Basic ${auth}` },
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) {
      return res.json({ traces: [], error: `Langfuse returned ${resp.status}` });
    }
    const data = await resp.json();
    res.json({ traces: data.data || [] });
  } catch (e) {
    res.json({ traces: [], error: e.message });
  }
});

// ── API: Marketplace ───────────────────────────────────
const marketplace = require("./marketplace");
app.use("/api/marketplace", marketplace);

// ── API: Trace detail (Langfuse) ──────────────────────
app.get("/api/traces/:traceId", async (req, res) => {
  const publicKey = process.env.LANGFUSE_PUBLIC_KEY || "";
  const secretKey = process.env.LANGFUSE_SECRET_KEY || "";
  if (!publicKey || !secretKey) {
    return res.json({ trace: null, error: "Langfuse keys not configured" });
  }
  try {
    const auth = Buffer.from(`${publicKey}:${secretKey}`).toString("base64");
    const [traceResp, obsResp] = await Promise.all([
      fetch(`${LANGFUSE_URL}/api/public/traces/${req.params.traceId}`, {
        headers: { Authorization: `Basic ${auth}` },
        signal: AbortSignal.timeout(5000),
      }),
      fetch(`${LANGFUSE_URL}/api/public/observations?traceId=${req.params.traceId}&limit=50`, {
        headers: { Authorization: `Basic ${auth}` },
        signal: AbortSignal.timeout(5000),
      }),
    ]);
    const trace = traceResp.ok ? await traceResp.json() : {};
    const obs = obsResp.ok ? await obsResp.json() : {};
    res.json({ trace, observations: obs.data || [] });
  } catch (e) {
    res.json({ trace: null, observations: [], error: e.message });
  }
});

// ── API: Sessions (proxy to agent) ────────────────────
app.get("/api/sessions", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/sessions`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ sessions: [], error: e.message });
  }
});

app.get("/api/sessions/:id/history", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/sessions/${req.params.id}/history`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ messages: [], error: e.message });
  }
});

app.delete("/api/sessions/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/sessions/${req.params.id}`, { method: "DELETE" });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.get("/api/sessions/:id/summary", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/sessions/${req.params.id}/summary`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ summary: null, error: e.message });
  }
});

// ── API: Memory stats ─────────────────────────────────
app.get("/api/memory/stats", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/memory/stats`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ memory: {}, knowledge_base: {}, error: e.message });
  }
});

// ── API: Models (proxy to agent) ──────────────────────
app.get("/api/models", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/models`, { signal: AbortSignal.timeout(10000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ models: [], error: e.message });
  }
});

app.post("/api/models/switch", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/models/switch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(10000),
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ── API: Tools (proxy to agent) ───────────────────────
app.get("/api/tools", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/tools`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ tools: [], error: e.message });
  }
});

// ── API: Documents / RAG (proxy to agent) ─────────────
app.get("/api/documents", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ documents: [], error: e.message });
  }
});

app.get("/api/documents/stats", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/stats`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ total_chunks: 0, unique_documents: 0, error: e.message });
  }
});

app.post("/api/documents/ingest", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.post("/api/documents/search", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ results: [], error: e.message });
  }
});

app.delete("/api/documents/:source", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/${encodeURIComponent(req.params.source)}`, {
      method: "DELETE",
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.post("/api/documents/fetch-url", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/fetch-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(15000),
    });
    const data = await resp.json();
    if (!resp.ok) return res.status(resp.status).json(data);
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

// ── API: A2A Protocol ─────────────────────────────────
// A2A peers CRUD
app.get("/api/a2a/peers", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/a2a/peers`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ peers: [], error: e.message }); }
});
app.post("/api/a2a/peers", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/a2a/peers`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/a2a/peers/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/a2a/peers/${req.params.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/a2a/peers/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/a2a/peers/${req.params.id}`, { method: "DELETE" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/a2a/peers/:id/ping", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/a2a/peers/${req.params.id}/ping`, { method: "POST" });
    res.json(await resp.json());
  } catch (e) { res.json({ status: "error", error: e.message }); }
});
app.post("/api/a2a/send", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/a2a/send`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/a2a/card", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/a2a/card`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ error: e.message }); }
});

// ── API: MCP Protocol ─────────────────────────────────
// MCP servers CRUD
app.get("/api/mcp/servers", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ servers: [], error: e.message }); }
});
app.post("/api/mcp/servers", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/mcp/servers/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/mcp/servers/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}`, { method: "DELETE" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/mcp/servers/:id/discover", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/discover`, { method: "POST" });
    res.json(await resp.json());
  } catch (e) { res.json({ status: "error", error: e.message }); }
});
app.post("/api/mcp/servers/:id/invoke", async (req, res) => {
  try {
    const qs = req.query.tool_name ? `?tool_name=${encodeURIComponent(req.query.tool_name)}` : '';
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/invoke${qs}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: n8n Workflows ────────────────────────────────
app.get("/api/n8n/workflows", async (req, res) => {
  try {
    const resp = await fetch(`${N8N_URL}/api/v1/workflows`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) {
      return res.json({ workflows: [], error: `n8n returned ${resp.status}` });
    }
    const data = await resp.json();
    res.json({ workflows: data.data || [] });
  } catch (e) {
    res.json({ workflows: [], error: e.message });
  }
});

// ── API: Observability stack health ───────────────────
app.get("/api/observability/health", async (req, res) => {
  const checks = [
    { name: "prometheus", url: "http://prometheus:9090/-/healthy" },
    { name: "grafana", url: `${GRAFANA_URL}/api/health` },
    { name: "loki", url: "http://loki:3100/ready" },
    { name: "otel-collector", url: "http://otel-collector:13133/" },
  ];
  const results = await Promise.all(
    checks.map(async (svc) => {
      try {
        const resp = await fetch(svc.url, { signal: AbortSignal.timeout(5000) });
        return { name: svc.name, status: resp.ok ? "healthy" : "unhealthy", code: resp.status };
      } catch (e) {
        return { name: svc.name, status: "unreachable", error: e.message };
      }
    })
  );
  res.json({ services: results });
});

// ── API: Prometheus query proxy ───────────────────────
app.get("/api/observability/prometheus/query", async (req, res) => {
  try {
    const query = req.query.query || "up";
    const resp = await fetch(`http://prometheus:9090/api/v1/query?query=${encodeURIComponent(query)}`, {
      signal: AbortSignal.timeout(5000),
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ status: "error", error: e.message });
  }
});

// ── API: Prometheus targets ───────────────────────────
app.get("/api/observability/prometheus/targets", async (req, res) => {
  try {
    const resp = await fetch("http://prometheus:9090/api/v1/targets", {
      signal: AbortSignal.timeout(5000),
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.json({ status: "error", error: e.message });
  }
});

// ── API: ChromaDB stats ───────────────────────────────
app.get("/api/chromadb/stats", async (req, res) => {
  try {
    const resp = await fetch(`${CHROMA_URL}/api/v2/heartbeat`, { signal: AbortSignal.timeout(5000) });
    const heartbeat = await resp.json();
    res.json({ status: "connected", heartbeat });
  } catch (e) {
    res.json({ status: "unreachable", error: e.message });
  }
});

// ── Pages ──────────────────────────────────────────────
const externalUrls = {
  n8n: N8N_EXTERNAL,
  langfuse: LANGFUSE_EXTERNAL,
  grafana: GRAFANA_EXTERNAL,
  agent: AGENT_EXTERNAL,
};

app.get("/", (req, res) => res.render("overview", { urls: externalUrls }));
app.get("/run-agent", (req, res) => res.render("run-agent", { urls: externalUrls }));
app.get("/documents", (req, res) => res.render("documents", { urls: externalUrls }));
app.get("/workflows", (req, res) => res.render("workflows", { urls: externalUrls }));
app.get("/skills", (req, res) => res.render("skills", { urls: externalUrls }));
app.get("/prompts", (req, res) => res.render("prompts", { urls: externalUrls }));
app.get("/agents", (req, res) => res.render("agents", { urls: externalUrls }));
app.get("/a2a", (req, res) => res.render("a2a", { urls: externalUrls }));
app.get("/mcp", (req, res) => res.render("mcp", { urls: externalUrls }));
app.get("/llm-activity", (req, res) => res.render("llm-activity", { urls: externalUrls }));
app.get("/traceability", (req, res) => res.render("traceability", { urls: externalUrls }));
app.get("/evaluation", (req, res) => res.render("evaluation", { urls: externalUrls }));
app.get("/observability", (req, res) => res.render("observability", { urls: externalUrls }));
app.get("/marketplace", (req, res) => res.render("marketplace", { urls: externalUrls }));
app.get("/admin", (req, res) => res.render("admin", { urls: externalUrls }));

app.listen(PORT, () => {
  console.log(`UI Console listening on :${PORT}`);
});

module.exports = app;
