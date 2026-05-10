const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3001;

// Service URLs (internal Docker network)
const AGENT_URL = process.env.AGENT_URL || "http://agent-service:8000";
const N8N_URL = process.env.N8N_URL || "http://n8n:5678";
const N8N_API_KEY = process.env.N8N_API_KEY || "";
const N8N_OWNER_EMAIL = process.env.N8N_OWNER_EMAIL || "";
const N8N_OWNER_PASSWORD = process.env.N8N_OWNER_PASSWORD || "";
const LANGFUSE_URL = process.env.LANGFUSE_URL || "http://langfuse:3000";
const GRAFANA_URL = process.env.GRAFANA_URL || "http://grafana:3000";
const CHROMA_URL = process.env.CHROMA_URL || "http://chromadb:8000";

// External URLs (browser-accessible)
const N8N_EXTERNAL = process.env.N8N_EXTERNAL_URL || "http://localhost:5678";
const N8N_PROXY_EXTERNAL = process.env.N8N_PROXY_EXTERNAL_URL || "http://localhost:5679";
const LANGFUSE_EXTERNAL = process.env.LANGFUSE_EXTERNAL_URL || "http://localhost:3002";
const GRAFANA_EXTERNAL = process.env.GRAFANA_EXTERNAL_URL || "http://localhost:3013";
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

// ── API: DB Stats, Export, Import ──────────────────────
app.get("/api/db-stats", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/db-stats`); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/export", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/export`); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/import", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/import`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
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
app.post("/api/skills/enrich", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills/enrich`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body), signal: AbortSignal.timeout(30000) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/skills/decompose", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills/decompose`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body), signal: AbortSignal.timeout(120000) }); res.status(r.status).json(await r.json()); }
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
app.post("/api/prompts/validate", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts/validate`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body), signal: AbortSignal.timeout(30000) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/prompts/generate", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts/generate`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body), signal: AbortSignal.timeout(30000) }); res.status(r.status).json(await r.json()); }
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

  const abortController = new AbortController();

  // If the client disconnects (e.g. user clicks Stop), abort the upstream fetch
  res.on("close", () => {
    if (!res.writableFinished) abortController.abort();
  });

  try {
    const resp = await fetch(`${AGENT_URL}/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
      signal: abortController.signal,
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
    if (e.name === "AbortError") {
      // Client disconnected — normal stop
      res.end();
    } else {
      res.write(`event: error\ndata: ${JSON.stringify({error: e.message})}\n\n`);
      res.end();
    }
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

// ── API: Custom Tools CRUD (proxy to agent) ───────────
app.get("/api/custom-tools", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/custom-tools`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/custom-tools", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/custom-tools`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body), signal: AbortSignal.timeout(10000),
    });
    res.status(resp.status).json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/custom-tools/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/custom-tools/${req.params.id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body), signal: AbortSignal.timeout(10000),
    });
    res.status(resp.status).json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/custom-tools/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/custom-tools/${req.params.id}`, {
      method: "DELETE", signal: AbortSignal.timeout(5000),
    });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Documents / RAG (proxy to agent) ─────────────

// ── API: Guardrails (proxy to agent) ──────────────────
app.get("/api/guardrails", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/guardrails`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/guardrails/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/guardrails/${req.params.id}`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/guardrails/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/guardrails/${req.params.id}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Version History (proxy to agent) ─────────────
app.get("/api/versions/:entityType/:entityId", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/versions/${req.params.entityType}/${req.params.entityId}`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/versions/detail/:versionId", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/versions/detail/${req.params.versionId}`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/versions/:entityType/:entityId/rollback/:versionId", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/versions/${req.params.entityType}/${req.params.entityId}/rollback/${req.params.versionId}`, { method: "POST" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Audit Log (proxy to agent) ───────────────────
app.get("/api/audit-log", async (req, res) => {
  try {
    const params = new URLSearchParams();
    if (req.query.limit) params.set("limit", req.query.limit);
    if (req.query.entity_type) params.set("entity_type", req.query.entity_type);
    if (req.query.action) params.set("action", req.query.action);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const resp = await fetch(`${AGENT_URL}/audit-log${qs}`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── LLM Activity API proxy ───────────────────────────────────────────────
app.get("/api/llm-activity", async (req, res) => {
  try {
    const params = new URLSearchParams();
    if (req.query.limit) params.set("limit", req.query.limit);
    if (req.query.session_id) params.set("session_id", req.query.session_id);
    if (req.query.model) params.set("model", req.query.model);
    if (req.query.provider) params.set("provider", req.query.provider);
    if (req.query.since) params.set("since", req.query.since);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const resp = await fetch(`${AGENT_URL}/llm-activity${qs}`, { signal: AbortSignal.timeout(10000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.get("/api/llm-activity/summary", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/llm-activity/summary`, { signal: AbortSignal.timeout(10000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.get("/api/documents", async (req, res) => {
  try {
    const qs = req.query.collection ? `?collection=${encodeURIComponent(req.query.collection)}` : '';
    const resp = await fetch(`${AGENT_URL}/documents${qs}`, { signal: AbortSignal.timeout(5000) });
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

// ── Enterprise Document Management (staging) ──────────
app.post("/api/documents/upload", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/upload`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    if (!resp.ok) return res.status(resp.status).json(data);
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.post("/api/documents/connect", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/connect`, {
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

app.post("/api/documents/shortcut", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/shortcut`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    if (!resp.ok) return res.status(resp.status).json(data);
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.post("/api/documents/:id/index", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/${req.params.id}/index`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    if (!resp.ok) return res.status(resp.status).json(data);
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
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

app.get("/api/documents/collections", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/collections`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) {
    res.json({ collections: [], error: e.message });
  }
});

app.post("/api/documents/copy", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/copy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    res.json(await resp.json());
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

// ── API: Document Registry / Folders / Tags ───────────
app.get("/api/documents/registry", async (req, res) => {
  try {
    const params = new URLSearchParams();
    if (req.query.folder) params.append("folder", req.query.folder);
    if (req.query.agent_id) params.append("agent_id", req.query.agent_id);
    if (req.query.search) params.append("search", req.query.search);
    if (req.query.collection) params.append("collection", req.query.collection);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const resp = await fetch(`${AGENT_URL}/documents/registry${qs}`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ documents: [], error: e.message }); }
});
app.get("/api/documents/folders", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/folders`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ folders: [], error: e.message }); }
});
app.put("/api/documents/registry/:id/tags", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/registry/${req.params.id}/tags`, {
      method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body)
    });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/documents/registry/:id/folder", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/registry/${req.params.id}/folder`, {
      method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body)
    });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/documents/registry/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/documents/registry/${req.params.id}`, { method: "DELETE" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
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

// ── API: Tools Service Health ─────────────────────────
app.get("/api/tools-health", async (req, res) => {
  try {
    const resp = await fetch("http://tools-service:8001/health", { signal: AbortSignal.timeout(3000) });
    const data = await resp.json();
    res.json(data);
  } catch(e) { res.status(503).json({ status: "offline" }); }
});

// ── API: MCP Registry ─────────────────────────────────
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

// ── API: n8n helpers ──────────────────────────────────
let n8nSessionCookie = "";

function n8nHeaders() {
  const h = { Accept: "application/json" };
  if (N8N_API_KEY) h["X-N8N-API-KEY"] = N8N_API_KEY;
  if (n8nSessionCookie) h["Cookie"] = n8nSessionCookie;
  return h;
}

async function n8nLogin() {
  if (!N8N_OWNER_EMAIL || !N8N_OWNER_PASSWORD) return false;
  try {
    const resp = await fetch(`${N8N_URL}/rest/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ emailOrLdapLoginId: N8N_OWNER_EMAIL, password: N8N_OWNER_PASSWORD }),
      signal: AbortSignal.timeout(5000),
    });
    if (resp.ok) {
      const cookies = resp.headers.getSetCookie();
      if (cookies && cookies.length) {
        n8nSessionCookie = cookies.map(function(c) { return c.split(";")[0]; }).join("; ");
        console.log("[n8n] Session login successful");
        return true;
      }
    }
  } catch (e) { console.log("[n8n] Session login failed:", e.message); }
  return false;
}

async function n8nAutoSetup() {
  if (!N8N_OWNER_EMAIL || !N8N_OWNER_PASSWORD) {
    console.log("[n8n] No N8N_OWNER_EMAIL/PASSWORD set — API stats will be unavailable until n8n owner is configured");
    return;
  }
  // Check if owner is already set up by trying to login
  if (await n8nLogin()) return;
  // Owner not yet created — try auto-provisioning via setup endpoint
  try {
    const name = N8N_OWNER_EMAIL.split("@")[0] || "Admin";
    const resp = await fetch(`${N8N_URL}/rest/owner/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: N8N_OWNER_EMAIL,
        firstName: name.charAt(0).toUpperCase() + name.slice(1),
        lastName: "User",
        password: N8N_OWNER_PASSWORD,
      }),
      signal: AbortSignal.timeout(10000),
    });
    if (resp.ok) {
      console.log("[n8n] Owner auto-provisioned:", N8N_OWNER_EMAIL);
      const cookies = resp.headers.getSetCookie();
      if (cookies && cookies.length) {
        n8nSessionCookie = cookies.map(function(c) { return c.split(";")[0]; }).join("; ");
      }
    } else {
      const txt = await resp.text().catch(function() { return ""; });
      console.log("[n8n] Owner setup returned", resp.status, "— complete setup manually at the n8n UI");
    }
  } catch (e) { console.log("[n8n] Auto-setup failed:", e.message, "— complete setup manually at the n8n UI"); }
}

// Auto-setup on startup (non-blocking, delayed to let n8n fully start)
setTimeout(function() { n8nAutoSetup(); }, 5000);

async function n8nFetchWithAuth(url, options) {
  options = options || {};
  options.headers = Object.assign({}, n8nHeaders(), options.headers || {});
  options.signal = options.signal || AbortSignal.timeout(5000);
  let resp = await fetch(url, options);
  // If 401, try re-login then retry once
  if (resp.status === 401 && (N8N_OWNER_EMAIL || N8N_API_KEY)) {
    await n8nLogin();
    options.headers = Object.assign({}, n8nHeaders(), options.headers || {});
    resp = await fetch(url, options);
  }
  return resp;
}

// ── API: n8n Workflows ────────────────────────────────
app.get("/api/n8n/workflows", async (req, res) => {
  try {
    // Try public API first, then internal REST API
    let resp = await n8nFetchWithAuth(`${N8N_URL}/api/v1/workflows`);
    if (resp.status === 401) {
      resp = await n8nFetchWithAuth(`${N8N_URL}/rest/workflows`);
    }
    if (!resp.ok) {
      return res.json({ workflows: [], error: `n8n returned ${resp.status}` });
    }
    const data = await resp.json();
    res.json({ workflows: data.data || [] });
  } catch (e) {
    res.json({ workflows: [], error: e.message });
  }
});

// ── API: n8n Workflow activate/deactivate ─────────────
app.post("/api/n8n/workflows/:id/activate", async (req, res) => {
  try {
    const resp = await n8nFetchWithAuth(`${N8N_URL}/api/v1/workflows/${req.params.id}/activate`, {
      method: "POST",
    });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/n8n/workflows/:id/deactivate", async (req, res) => {
  try {
    const resp = await n8nFetchWithAuth(`${N8N_URL}/api/v1/workflows/${req.params.id}/deactivate`, {
      method: "POST",
    });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: n8n Executions ───────────────────────────────
app.get("/api/n8n/executions", async (req, res) => {
  try {
    const limit = req.query.limit || 10;
    let resp = await n8nFetchWithAuth(`${N8N_URL}/api/v1/executions?limit=${limit}`);
    if (resp.status === 401) {
      resp = await n8nFetchWithAuth(`${N8N_URL}/rest/executions?limit=${limit}`);
    }
    if (!resp.ok) return res.json({ executions: [], error: `n8n returned ${resp.status}` });
    const data = await resp.json();
    const raw = data.data || [];
    const executions = Array.isArray(raw) ? raw : (raw.results || []);
    res.json({ executions });
  } catch (e) {
    res.json({ executions: [], error: e.message });
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

// ── API: Prometheus range query ───────────────────────
app.get("/api/observability/prometheus/query_range", async (req, res) => {
  try {
    const query = req.query.query || "up";
    const start = req.query.start || Math.floor(Date.now() / 1000) - 1800;
    const end = req.query.end || Math.floor(Date.now() / 1000);
    const step = req.query.step || "30";
    const url = `http://prometheus:9090/api/v1/query_range?query=${encodeURIComponent(query)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&step=${encodeURIComponent(step)}`;
    const resp = await fetch(url, { signal: AbortSignal.timeout(10000) });
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

// ── API: Data Connectors ──────────────────────────────
app.get("/api/connectors/catalog", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors/catalog`);
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.get("/api/connectors", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors`);
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.post("/api/connectors", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    if (!resp.ok) return res.status(resp.status).json(data);
    res.json(data);
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.put("/api/connectors/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors/${req.params.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    if (!resp.ok) return res.status(resp.status).json(data);
    res.json(data);
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.delete("/api/connectors/:id", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors/${req.params.id}`, { method: "DELETE" });
    const data = await resp.json();
    res.json(data);
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.post("/api/connectors/test", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.post("/api/connectors/:id/sync", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors/${req.params.id}/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    if (!resp.ok) return res.status(resp.status).json(data);
    res.json(data);
  } catch (e) { res.status(502).json({ error: e.message }); }
});

app.get("/api/connectors/:id/jobs", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/connectors/${req.params.id}/jobs`);
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
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
  n8nProxy: N8N_PROXY_EXTERNAL,
  langfuse: LANGFUSE_EXTERNAL,
  grafana: GRAFANA_EXTERNAL,
  agent: AGENT_EXTERNAL,
};

app.get("/", (req, res) => res.render("overview", { urls: externalUrls }));
app.get("/run-agent", (req, res) => res.render("run-agent", { urls: externalUrls }));
app.get("/agent-builder", (req, res) => res.render("agent-builder", { urls: externalUrls }));
app.get("/ai-studio", (req, res) => res.render("ai-studio", { urls: externalUrls }));
app.get("/documents", (req, res) => res.render("documents", { urls: externalUrls }));
app.get("/workflows", (req, res) => res.render("workflows", { urls: externalUrls }));
app.get("/skills", (req, res) => res.render("skills", { urls: externalUrls }));
app.get("/prompts", (req, res) => res.render("prompts", { urls: externalUrls }));
app.get("/agents", (req, res) => res.render("agents", { urls: externalUrls }));
app.get("/tools", (req, res) => res.render("tools", { urls: externalUrls }));
app.get("/guardrails", (req, res) => res.render("guardrails", { urls: externalUrls }));
app.get("/a2a", (req, res) => res.render("a2a", { urls: externalUrls }));
app.get("/mcp", (req, res) => res.render("mcp", { urls: externalUrls }));
app.get("/rest", (req, res) => res.render("rest", { urls: externalUrls }));
app.get("/intelligence-hub", (req, res) => res.render("intelligence-hub", { urls: externalUrls }));
app.get("/agent-hub", (req, res) => res.render("agent-hub", { urls: externalUrls }));
app.get("/data-ingestion", (req, res) => res.render("data-ingestion", { urls: externalUrls }));
app.get("/llm-activity", (req, res) => res.render("llm-activity", { urls: externalUrls }));
app.get("/traceability", (req, res) => res.render("traceability", { urls: externalUrls }));
app.get("/evaluation", (req, res) => res.render("evaluation", { urls: externalUrls }));
app.get("/observability", (req, res) => res.render("observability", { urls: externalUrls }));
app.get("/marketplace", (req, res) => res.render("marketplace", { urls: externalUrls }));
app.get("/admin", (req, res) => res.render("admin", { urls: externalUrls }));
app.get("/docs", (req, res) => res.render("docs", { urls: externalUrls }));
app.get("/docs/architecture-diagram", (req, res) => {
  res.sendFile(path.join(__dirname, "docs-static", "architecture-diagram.html"));
});

app.listen(PORT, () => {
  console.log(`UI Console listening on :${PORT}`);
});

module.exports = app;
