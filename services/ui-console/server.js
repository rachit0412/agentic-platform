const express = require("express");
const path = require("path");
const session = require("express-session");

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

// ── Session Management ─────────────────────────────────
const crypto = require("crypto");
const sessionSecret = process.env.SESSION_SECRET || crypto.randomBytes(64).toString("hex");
if (!process.env.SESSION_SECRET) {
  console.warn("[SECURITY] SESSION_SECRET not set — using ephemeral random secret. Sessions will NOT survive restarts. Set SESSION_SECRET in .env for production.");
}
app.use(session({
  secret: sessionSecret,
  resave: false,
  saveUninitialized: false,
  name: "agentic.sid",
  cookie: {
    httpOnly: true,
    secure: false,      // set true behind HTTPS reverse proxy
    maxAge: 24 * 60 * 60 * 1000,  // 24 hours
    sameSite: "lax",
  },
}));

// ── Auth Routes (before auth middleware) ────────────────
app.get("/login", (req, res) => {
  if (req.session && req.session.user) return res.redirect("/");
  res.redirect("/login-app/");
});

app.post("/auth/login", async (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) {
    return res.status(400).json({ error: "Username and password are required" });
  }
  try {
    const r = await fetch(`${AGENT_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await r.json();
    if (r.ok && data.id) {
      // Load user personas
      let personas = [];
      try {
        const pr = await fetch(`${AGENT_URL}/users/${data.id}/personas`);
        const pd = await pr.json();
        personas = pd.personas || [];
      } catch (_) {}
      data.personas = personas;
      data.active_persona = personas.length > 0 ? personas[0] : null;
      // Regenerate session to prevent fixation and guarantee a fresh cookie
      return req.session.regenerate((err) => {
        if (err) return res.status(500).json({ error: "Session error" });
        req.session.user = data;
        return req.session.save((err) => {
          if (err) return res.status(500).json({ error: "Session save failed" });
          return res.json(data);
        });
      });
    }
    return res.status(r.status).json(data);
  } catch (e) {
    return res.status(502).json({ error: "Auth service unavailable" });
  }
});

// ── Auth proxy routes (register, forgot-password, reset) ─
async function proxyToAgent(req, res, endpoint) {
  try {
    const r = await fetch(`${AGENT_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await r.json();
    return res.status(r.status).json(data);
  } catch (e) {
    return res.status(502).json({ error: "Agent service unavailable" });
  }
}
app.post("/auth/register", (req, res) => proxyToAgent(req, res, "/auth/register"));
app.post("/auth/forgot-password", (req, res) => proxyToAgent(req, res, "/auth/forgot-password"));
app.post("/auth/reset-password", (req, res) => proxyToAgent(req, res, "/auth/reset-password"));
app.post("/auth/verify-email", (req, res) => proxyToAgent(req, res, "/auth/verify-email"));
app.post("/auth/resend-code", (req, res) => proxyToAgent(req, res, "/auth/resend-code"));

app.post("/auth/logout", (req, res) => {
  req.session.destroy(() => {
    res.clearCookie("agentic.sid");
    res.json({ ok: true });
  });
});

app.get("/auth/logout", (req, res) => {
  req.session.destroy(() => {
    res.clearCookie("agentic.sid");
    res.redirect("/login");
  });
});

// ── Auth Middleware (protects all routes below) ────────
function requireAuth(req, res, next) {
  // Allow health endpoint without auth
  if (req.path === "/health") return next();
  if (!req.session || !req.session.user) {
    if (req.path.startsWith("/api/")) {
      return res.status(401).json({ error: "Not authenticated" });
    }
    return res.redirect("/login");
  }
  next();
}
app.use(requireAuth);

// ── Change password (for logged-in user) ───────────────
app.post("/api/change-password", async (req, res) => {
  const userId = req.session.user.id;
  const { current_password, new_password } = req.body;
  if (!current_password || !new_password) {
    return res.status(400).json({ error: "Current and new password are required" });
  }
  try {
    // Verify current password first
    const authR = await fetch(`${AGENT_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: req.session.user.username, password: current_password }),
    });
    if (!authR.ok) {
      return res.status(401).json({ error: "Current password is incorrect" });
    }
    // Now update to new password
    const r = await fetch(`${AGENT_URL}/users/${userId}`, {
      method: "PUT",
      headers: { ...wsHeaders(req), "Content-Type": "application/json" },
      body: JSON.stringify({ password: new_password }),
    });
    const data = await r.json();
    return res.status(r.status).json(data);
  } catch (e) {
    return res.status(502).json({ error: "Service unavailable" });
  }
});

// ── User profile (get current user) ────────────────────
app.get("/api/me", (req, res) => {
  res.json(req.session.user);
});

// ── Update profile (display name) ──────────────────────
app.post("/api/update-profile", async (req, res) => {
  const userId = req.session.user.id;
  try {
    const r = await fetch(`${AGENT_URL}/users/${userId}`, {
      method: "PUT",
      headers: { ...wsHeaders(req), "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: req.body.display_name }),
    });
    const data = await r.json();
    if (r.ok && data.display_name) {
      req.session.user.display_name = data.display_name;
    }
    return res.status(r.status).json(data);
  } catch (e) {
    return res.status(502).json({ error: "Service unavailable" });
  }
});

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

// ── Workspace header forwarding helper ─────────────────
function wsHeaders(req, extra) {
  const h = { ...extra };
  const user = req.session && req.session.user;
  // Use session user context for content isolation
  h['x-user-id'] = (user && user.username) || req.headers['x-user-id'] || 'system';
  h['x-user-role'] = (user && user.role) || req.headers['x-user-role'] || 'admin';
  h['x-workspace-id'] = 'default';
  return h;
}

// ── API: Workspaces CRUD ───────────────────────────────
app.get("/api/workspaces", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/workspaces`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/workspaces", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/workspaces`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/workspaces/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/workspaces/${req.params.id}`, { method: "PUT", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/workspaces/:id", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/workspaces/${req.params.id}`, { method: "DELETE", headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/workspaces/:id/members", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/workspaces/${req.params.id}/members`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/workspaces/:id/members", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/workspaces/${req.params.id}/members`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/workspaces/:id/members/:userId", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/workspaces/${req.params.id}/members/${req.params.userId}`, { method: "DELETE", headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: User Management (admin-only) ──────────────────
function requireAdmin(req, res, next) {
  const user = req.session && req.session.user;
  if (!user || user.role !== "admin") {
    return res.status(403).json({ error: "Admin access required" });
  }
  next();
}

app.get("/api/users", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/users/:id", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users/${req.params.id}`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/users", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/users/:id", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users/${req.params.id}`, { method: "PUT", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/users/:id", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users/${req.params.id}`, { method: "DELETE", headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/users/:id/verify", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users/${req.params.id}/verify`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Persona Management (admin-only for CRUD) ──────
app.get("/api/personas", requireAuth, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/personas`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/personas/:id", requireAuth, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/personas/${req.params.id}`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/personas", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/personas`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/personas/:id", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/personas/${req.params.id}`, { method: "PUT", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/personas/:id", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/personas/${req.params.id}`, { method: "DELETE", headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
// User persona assignments (admin-only)
app.get("/api/users/:id/personas", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users/${req.params.id}/personas`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/users/:id/personas", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users/${req.params.id}/personas`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/users/:id/personas/:pid", requireAdmin, async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/users/${req.params.id}/personas/${req.params.pid}`, { method: "DELETE", headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Switch active persona (self-service) ──────────
app.post("/api/switch-persona", requireAuth, async (req, res) => {
  const { persona_id } = req.body || {};
  if (!persona_id) return res.status(400).json({ error: "persona_id is required" });
  // Fetch user's assigned personas to validate
  try {
    const r = await fetch(`${AGENT_URL}/users/${req.session.user.id}/personas`, { headers: wsHeaders(req) });
    const data = await r.json();
    const personas = data.personas || [];
    const match = personas.find(p => p.id === persona_id);
    if (!match) return res.status(403).json({ error: "Persona not assigned to you" });
    req.session.user.active_persona = match;
    res.json({ success: true, active_persona: match });
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Get my personas (self-service) ────────────────
app.get("/api/my-personas", requireAuth, async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/users/${req.session.user.id}/personas`, { headers: wsHeaders(req) });
    const data = await r.json();
    res.json({ personas: data.personas || [], active_persona: req.session.user.active_persona || null });
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Current session info ──────────────────────────
app.get("/api/auth/me", (req, res) => {
  res.json(req.session.user || { error: "Not authenticated" });
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
  try { const qs = req.query.created_by ? `?created_by=${encodeURIComponent(req.query.created_by)}` : ''; const r = await fetch(`${AGENT_URL}/skills${qs}`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/skills", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.json(await r.json()); }
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
// ── Skill files proxy (upload streams raw body) ────────
app.post("/api/skills/:id/files", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/skills/${req.params.id}/files`, {
      method: "POST",
      headers: { "content-type": req.headers["content-type"] },
      body: req,
      duplex: "half",
    });
    res.status(r.status).json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/skills/:id/files", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills/${req.params.id}/files`); res.status(r.status).json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/skills/:id/files/:category/:filename", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/skills/${req.params.id}/files/${req.params.category}/${req.params.filename}`);
    if (!r.ok) return res.status(r.status).json(await r.json());
    const ct = r.headers.get("content-type") || "application/octet-stream";
    res.setHeader("content-type", ct);
    const arrayBuf = await r.arrayBuffer();
    res.send(Buffer.from(arrayBuf));
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/skills/:id/files/:category/:filename", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/skills/${req.params.id}/files/${req.params.category}/${req.params.filename}`, { method: "DELETE" }); res.status(r.status).json(await r.json()); }
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
  try { const qs = req.query.created_by ? `?created_by=${encodeURIComponent(req.query.created_by)}` : ''; const r = await fetch(`${AGENT_URL}/prompts${qs}`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/prompts", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/prompts`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.json(await r.json()); }
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
  try { const qs = req.query.created_by ? `?created_by=${encodeURIComponent(req.query.created_by)}` : ''; const r = await fetch(`${AGENT_URL}/agents${qs}`, { headers: wsHeaders(req) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/agents", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/agents`, { method: "POST", headers: wsHeaders(req, {"Content-Type":"application/json"}), body: JSON.stringify(req.body) }); res.json(await r.json()); }
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
    const qs = req.query.created_by ? `?created_by=${encodeURIComponent(req.query.created_by)}` : '';
    const resp = await fetch(`${AGENT_URL}/custom-tools${qs}`, { headers: wsHeaders(req), signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/custom-tools", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/custom-tools`, {
      method: "POST", headers: wsHeaders(req, { "Content-Type": "application/json" }),
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
app.get("/api/global-constraints", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/global-constraints`); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/global-constraints", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/global-constraints`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) }); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});
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
    const resp = await fetch(`${AGENT_URL}/mcp/servers`, { headers: wsHeaders(req), signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ servers: [], error: e.message }); }
});
app.post("/api/mcp/servers", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers`, { method: "POST", headers: wsHeaders(req, { "Content-Type": "application/json" }), body: JSON.stringify(req.body) });
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

// Managed MCP servers — create, provision, lifecycle
app.post("/api/mcp/servers/managed/config", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/managed/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body), signal: AbortSignal.timeout(15000) });
    res.status(resp.status).json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/mcp/servers/managed/code", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/managed/code`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req.body), signal: AbortSignal.timeout(15000) });
    res.status(resp.status).json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/mcp/servers/:id/provision", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/provision`, { method: "POST", signal: AbortSignal.timeout(30000) });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/mcp/servers/:id/container/stop", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/container/stop`, { method: "POST" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/mcp/servers/:id/container/start", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/container/start`, { method: "POST" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.post("/api/mcp/servers/:id/container/restart", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/container/restart`, { method: "POST" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.delete("/api/mcp/servers/:id/container", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/container`, { method: "DELETE" });
    res.json(await resp.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.get("/api/mcp/servers/:id/container/logs", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/container/logs`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ logs: "", error: e.message }); }
});
app.get("/api/mcp/servers/:id/container/status", async (req, res) => {
  try {
    const resp = await fetch(`${AGENT_URL}/mcp/servers/${req.params.id}/container/status`, { signal: AbortSignal.timeout(5000) });
    res.json(await resp.json());
  } catch (e) { res.json({ status: "unknown", error: e.message }); }
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

// ── API: Admin – Full service health (all 10 services) ─
app.get("/api/admin/services/health", async (req, res) => {
  const services = [
    { name: "agent-service", url: `${AGENT_URL}/health`, type: "core" },
    { name: "tools-service", url: "http://tools-service:8001/health", type: "core" },
    { name: "chromadb", url: `${CHROMA_URL}/api/v2/heartbeat`, type: "core" },
    { name: "ollama", url: "http://ollama:11434/api/tags", type: "core" },
    { name: "n8n", url: `${N8N_URL}/healthz`, type: "integration" },
    { name: "langfuse", url: `${LANGFUSE_URL}/api/public/health`, type: "observability" },
    { name: "prometheus", url: "http://prometheus:9090/-/healthy", type: "observability" },
    { name: "grafana", url: `${GRAFANA_URL}/api/health`, type: "observability" },
    { name: "loki", url: "http://loki:3100/ready", type: "observability" },
    { name: "otel-collector", url: "http://otel-collector:13133/", type: "observability" },
  ];
  const results = await Promise.all(
    services.map(async (svc) => {
      const start = Date.now();
      try {
        const resp = await fetch(svc.url, { signal: AbortSignal.timeout(5000) });
        return { name: svc.name, type: svc.type, status: resp.ok ? "healthy" : "unhealthy", code: resp.status, latency: Date.now() - start };
      } catch (e) {
        return { name: svc.name, type: svc.type, status: "unreachable", error: e.message, latency: Date.now() - start };
      }
    })
  );
  const healthy = results.filter(r => r.status === "healthy").length;
  res.json({ services: results, summary: { total: results.length, healthy, unhealthy: results.length - healthy, timestamp: new Date().toISOString() } });
});

// ── API: Admin – Prometheus metrics for services ──────
app.get("/api/admin/metrics", async (req, res) => {
  const queries = {
    cpu: 'rate(process_cpu_seconds_total[5m])',
    memory: 'process_resident_memory_bytes',
    http_rate: 'rate(http_requests_total[5m])',
    http_errors: 'rate(http_requests_total{status=~"5.."}[5m])',
    up: 'up',
  };
  const results = {};
  for (const [key, query] of Object.entries(queries)) {
    try {
      const resp = await fetch(`http://prometheus:9090/api/v1/query?query=${encodeURIComponent(query)}`, { signal: AbortSignal.timeout(5000) });
      const data = await resp.json();
      results[key] = data.data?.result || [];
    } catch (e) {
      results[key] = [];
    }
  }
  res.json(results);
});

// ── API: Admin – LLM usage summary ───────────────────
app.get("/api/admin/llm-summary", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/llm-activity/summary`);
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Admin – Memory/platform stats ───────────────
app.get("/api/admin/memory-stats", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/memory/stats`);
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Admin – Global constraints ──────────────────
app.get("/api/admin/global-constraints", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/global-constraints`);
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/admin/global-constraints", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/global-constraints`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) });
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Admin – Best practices ──────────────────────
app.get("/api/admin/security-considerations", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/security-considerations`); res.json(await r.json()); }
  catch (e) { res.json({ error: e.message }); }
});
app.put("/api/admin/security-considerations", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/security-considerations`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) });
    res.json(await r.json());
  } catch (e) { res.json({ error: e.message }); }
});
app.get("/api/security-considerations", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/security-considerations`); res.json(await r.json()); }
  catch (e) { res.json({ error: e.message }); }
});

app.get("/api/admin/best-practices", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/best-practices`);
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
app.put("/api/admin/best-practices", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/best-practices`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(req.body) });
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});
// ── Also expose on non-admin path for skills page ────
app.get("/api/best-practices", async (req, res) => {
  try { const r = await fetch(`${AGENT_URL}/best-practices`); res.json(await r.json()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Admin – ChromaDB collections detail ─────────
app.get("/api/admin/chromadb/collections", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/documents/collections`);
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Admin – Document stats ──────────────────────
app.get("/api/admin/documents/stats", async (req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/documents/stats`);
    res.json(await r.json());
  } catch (e) { res.status(502).json({ error: e.message }); }
});

// ── API: Admin – n8n workflow list ───────────────────
app.get("/api/admin/n8n/workflows", async (req, res) => {
  try {
    const headers = {};
    if (N8N_API_KEY) headers["X-N8N-API-KEY"] = N8N_API_KEY;
    const resp = await fetch(`${N8N_URL}/api/v1/workflows`, { headers, signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    res.json(data);
  } catch (e) { res.json({ data: [], error: e.message }); }
});

// ── API: Admin – Platform overview counts ────────────
app.get("/api/admin/overview", async (req, res) => {
  const counts = {};
  const endpoints = [
    { key: "agents", url: `${AGENT_URL}/agents` },
    { key: "skills", url: `${AGENT_URL}/skills` },
    { key: "prompts", url: `${AGENT_URL}/prompts` },
    { key: "tools", url: `${AGENT_URL}/tools` },
    { key: "custom_tools", url: `${AGENT_URL}/custom-tools` },
    { key: "sessions", url: `${AGENT_URL}/sessions` },
    { key: "guardrails", url: `${AGENT_URL}/guardrails` },
    { key: "a2a_peers", url: `${AGENT_URL}/a2a/peers` },
    { key: "mcp_servers", url: `${AGENT_URL}/mcp/servers` },
    { key: "connectors", url: `${AGENT_URL}/connectors` },
  ];
  await Promise.all(endpoints.map(async (ep) => {
    try {
      const r = await fetch(ep.url, { signal: AbortSignal.timeout(5000) });
      const d = await r.json();
      if (Array.isArray(d)) { counts[ep.key] = d.length; }
      else {
        const arr = Object.values(d).find(v => Array.isArray(v));
        counts[ep.key] = arr ? arr.length : 0;
      }
    } catch { counts[ep.key] = 0; }
  }));
  res.json(counts);
});

// ── Pages ──────────────────────────────────────────────
const externalUrls = {
  n8n: N8N_EXTERNAL,
  n8nProxy: N8N_PROXY_EXTERNAL,
  langfuse: LANGFUSE_EXTERNAL,
  grafana: GRAFANA_EXTERNAL,
  agent: AGENT_EXTERNAL,
};

// Helper: render with user context
function renderPage(view) {
  return (req, res) => {
    res.render(view, { urls: externalUrls, user: req.session.user || {} });
  };
}

app.get("/", renderPage("overview"));
app.get("/run-agent", renderPage("run-agent"));
app.get("/agent-builder", renderPage("agent-builder"));
app.get("/ai-studio", renderPage("ai-studio"));
app.get("/documents", renderPage("documents"));
app.get("/workflows", renderPage("workflows"));
app.get("/skills", renderPage("skills"));
app.get("/prompts", renderPage("prompts"));
app.get("/agents", renderPage("agents"));
app.get("/tools", renderPage("tools"));
app.get("/guardrails", renderPage("guardrails"));
app.get("/a2a", renderPage("a2a"));
app.get("/mcp", renderPage("mcp"));
app.get("/rest", renderPage("rest"));
app.get("/intelligence-hub", renderPage("intelligence-hub"));
app.get("/agent-hub", renderPage("agent-hub"));
app.get("/data-ingestion", renderPage("data-ingestion"));
app.get("/llm-activity", renderPage("llm-activity"));
app.get("/traceability", renderPage("traceability"));
app.get("/evaluation", renderPage("evaluation"));
app.get("/observability", renderPage("observability"));
app.get("/marketplace", renderPage("marketplace"));
app.get("/admin", (req, res) => {
  const user = req.session.user || {};
  if (user.role !== "admin") return res.redirect("/");
  res.render("admin", { urls: externalUrls, user });
});
app.get("/docs", renderPage("docs"));
app.get("/docs/architecture-diagram", (req, res) => {
  res.sendFile(path.join(__dirname, "docs-static", "architecture-diagram.html"));
});

app.listen(PORT, () => {
  console.log(`UI Console listening on :${PORT}`);
});

module.exports = app;
