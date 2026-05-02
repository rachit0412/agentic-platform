/**
 * Unit tests for UI Console — routes, marketplace, health.
 */
const request = require("supertest");

// Stub fetch globally before requiring app
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
  })
);

const app = require("../../services/ui-console/server");
const marketplace = require("../../services/ui-console/marketplace");
const express = require("express");

// ── Health ─────────────────────────────────────────────

describe("GET /health", () => {
  it("returns healthy status", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("healthy");
    expect(res.body.service).toBe("ui-console");
  });
});

// ── Pages ──────────────────────────────────────────────

const pages = ["/", "/run-agent", "/documents", "/workflows", "/observability", "/marketplace", "/admin"];

pages.forEach((path) => {
  describe(`GET ${path}`, () => {
    it("returns 200 with HTML", async () => {
      const res = await request(app).get(path);
      expect(res.status).toBe(200);
      expect(res.headers["content-type"]).toMatch(/html/);
    });
  });
});

// ── Redirects ──────────────────────────────────────────

describe("GET /llm-activity", () => {
  it("redirects to /intelligence-hub", async () => {
    const res = await request(app).get("/llm-activity");
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe("/intelligence-hub");
  });
});

// ── API: health-check ──────────────────────────────────

describe("GET /api/health-check", () => {
  it("returns a services array", async () => {
    // fetch is mocked to return ok:true for all
    const res = await request(app).get("/api/health-check");
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.services)).toBe(true);
    expect(res.body.services.length).toBeGreaterThan(0);
  });
});

// ── API: agent-run proxy ───────────────────────────────

describe("POST /api/agent-run", () => {
  beforeEach(() => {
    global.fetch.mockReset();
  });

  it("proxies to agent service and returns response", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          response: "42",
          tools_used: ["math"],
          trace_id: "t-123",
        }),
    });

    const res = await request(app)
      .post("/api/agent-run")
      .send({ prompt: "What is 42?", sessionId: "s-1" });

    expect(res.status).toBe(200);
    expect(res.body.response).toBe("42");
  });

  it("returns 502 when agent is down", async () => {
    global.fetch.mockRejectedValueOnce(new Error("ECONNREFUSED"));

    const res = await request(app)
      .post("/api/agent-run")
      .send({ prompt: "hello" });

    expect(res.status).toBe(502);
    expect(res.body.error).toMatch(/unreachable/i);
  });
});

// ── API: traces proxy ──────────────────────────────────

describe("GET /api/traces", () => {
  it("returns empty traces when keys are not configured", async () => {
    // Keys default to pk-lf-local-dev / sk-lf-local-dev in test
    // The mock fetch returns empty
    global.fetch.mockReset();
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: [] }),
    });

    const res = await request(app).get("/api/traces");
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.traces)).toBe(true);
  });
});

// ── Marketplace API ────────────────────────────────────

describe("Marketplace", () => {
  const mktApp = express();
  mktApp.use(express.json());
  mktApp.use("/api/marketplace", marketplace);

  it("GET /api/marketplace/templates returns templates", async () => {
    const res = await request(mktApp).get("/api/marketplace/templates");
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.templates)).toBe(true);
    expect(res.body.templates.length).toBeGreaterThan(0);
  });

  it("GET /api/marketplace/templates/:id returns single template", async () => {
    const res = await request(mktApp).get("/api/marketplace/templates/wf-agent-run");
    expect(res.status).toBe(200);
    expect(res.body.id).toBe("wf-agent-run");
  });

  it("GET /api/marketplace/templates/:id returns 404 for unknown", async () => {
    const res = await request(mktApp).get("/api/marketplace/templates/nope");
    expect(res.status).toBe(404);
  });

  it("POST install / uninstall cycle", async () => {
    // Use a template that is NOT installed by default
    let res = await request(mktApp).post("/api/marketplace/templates/tool-web-search/install");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("installed");

    res = await request(mktApp).post("/api/marketplace/templates/tool-web-search/uninstall");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("uninstalled");
  });

  it("search filters templates", async () => {
    const res = await request(mktApp).get("/api/marketplace/templates?search=web");
    expect(res.status).toBe(200);
    expect(res.body.templates.length).toBeGreaterThan(0);
    expect(res.body.templates.every((t) => JSON.stringify(t).toLowerCase().includes("web"))).toBe(true);
  });

  it("type filter works", async () => {
    const res = await request(mktApp).get("/api/marketplace/templates?type=tool");
    expect(res.status).toBe(200);
    expect(res.body.templates.every((t) => t.type === "tool")).toBe(true);
  });
});

// ── API: sessions proxy ────────────────────────────────

describe("GET /api/sessions", () => {
  beforeEach(() => global.fetch.mockReset());

  it("returns sessions from agent service", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ sessions: ["s-1", "s-2"] }),
    });
    const res = await request(app).get("/api/sessions");
    expect(res.status).toBe(200);
    expect(res.body.sessions).toBeDefined();
  });

  it("returns empty on error", async () => {
    global.fetch.mockRejectedValueOnce(new Error("down"));
    const res = await request(app).get("/api/sessions");
    expect(res.status).toBe(200);
    expect(res.body.sessions).toEqual([]);
  });
});

// ── API: models proxy ──────────────────────────────────

describe("GET /api/models", () => {
  beforeEach(() => global.fetch.mockReset());

  it("returns models from agent", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ models: [{ name: "llama3" }], current_model: "llama3" }),
    });
    const res = await request(app).get("/api/models");
    expect(res.status).toBe(200);
    expect(res.body.models).toBeDefined();
  });
});

// ── API: tools proxy ───────────────────────────────────

describe("GET /api/tools", () => {
  beforeEach(() => global.fetch.mockReset());

  it("returns tools from agent", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ tools: [{ name: "math" }] }),
    });
    const res = await request(app).get("/api/tools");
    expect(res.status).toBe(200);
    expect(res.body.tools).toBeDefined();
  });
});

// ── API: documents proxy ───────────────────────────────

describe("Documents API", () => {
  beforeEach(() => global.fetch.mockReset());

  it("GET /api/documents returns docs", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ documents: ["doc1.txt"] }),
    });
    const res = await request(app).get("/api/documents");
    expect(res.status).toBe(200);
    expect(res.body.documents).toBeDefined();
  });

  it("GET /api/documents/stats returns stats", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ total_chunks: 10, unique_documents: 2 }),
    });
    const res = await request(app).get("/api/documents/stats");
    expect(res.status).toBe(200);
    expect(res.body.total_chunks).toBeDefined();
  });

  it("POST /api/documents/ingest proxies to agent", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: "ingested", chunks: 5 }),
    });
    const res = await request(app)
      .post("/api/documents/ingest")
      .send({ text: "Hello world", source: "test.txt" });
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ingested");
  });

  it("POST /api/documents/search proxies to agent", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ results: [{ content: "Hello", score: 0.9 }] }),
    });
    const res = await request(app)
      .post("/api/documents/search")
      .send({ query: "hello", k: 3 });
    expect(res.status).toBe(200);
    expect(res.body.results).toBeDefined();
  });
});

// ── API: n8n workflows proxy ───────────────────────────

describe("GET /api/n8n/workflows", () => {
  beforeEach(() => global.fetch.mockReset());

  it("returns workflows from n8n", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: [{ id: 1, name: "Test", active: true }] }),
    });
    const res = await request(app).get("/api/n8n/workflows");
    expect(res.status).toBe(200);
    expect(res.body.workflows).toBeDefined();
  });

  it("handles n8n being down", async () => {
    global.fetch.mockRejectedValueOnce(new Error("down"));
    const res = await request(app).get("/api/n8n/workflows");
    expect(res.status).toBe(200);
    expect(res.body.workflows).toEqual([]);
  });
});
