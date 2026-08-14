const express = require("express");
const fs = require("fs");
const path = require("path");

const router = express.Router();

// ── Template catalog ───────────────────────────────────
const TEMPLATES = [
  {
    id: "wf-agent-run",
    type: "n8n-workflow",
    name: "Agent Run Webhook",
    description: "POST webhook that calls agent-service and returns the response with traceId.",
    file: "agent-workflow.json",
    installed: true,
  },
  {
    id: "wf-scheduled-report",
    type: "n8n-workflow",
    name: "Scheduled Report",
    description: "Cron-triggered workflow that asks the agent for a daily summary and saves to file.",
    file: "scheduled-report.json",
    installed: false,
  },
  {
    id: "tool-web-search",
    type: "tool",
    name: "Web Search Tool",
    description: "DuckDuckGo-based web search tool endpoint for the agent.",
    file: null,
    installed: false,
  },
  {
    id: "agent-rag",
    type: "agent-template",
    name: "RAG Agent",
    description: "Retrieval-augmented generation agent template using ChromaDB vector store.",
    file: null,
    installed: false,
  },
  {
    id: "tool-code-exec",
    type: "tool",
    name: "Code Execution Tool",
    description: "Sandboxed Python code execution tool for the agent.",
    file: null,
    installed: false,
  },
];

// Track installed state in memory (persists within container lifecycle)
const installedSet = new Set(TEMPLATES.filter((t) => t.installed).map((t) => t.id));

router.get("/templates", (req, res) => {
  const { type, search } = req.query;
  let results = TEMPLATES.map((t) => ({
    ...t,
    installed: installedSet.has(t.id),
  }));

  if (type) {
    results = results.filter((t) => t.type === type);
  }
  if (search) {
    const q = search.toLowerCase();
    results = results.filter(
      (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
    );
  }

  res.json({ templates: results });
});

router.get("/templates/:id", (req, res) => {
  const tmpl = TEMPLATES.find((t) => t.id === req.params.id);
  if (!tmpl) return res.status(404).json({ error: "Template not found" });
  res.json({ ...tmpl, installed: installedSet.has(tmpl.id) });
});

router.post("/templates/:id/install", (req, res) => {
  const tmpl = TEMPLATES.find((t) => t.id === req.params.id);
  if (!tmpl) return res.status(404).json({ error: "Template not found" });

  if (installedSet.has(tmpl.id)) {
    return res.json({ status: "already_installed", template: tmpl.id });
  }

  // For n8n workflows, copy the JSON to /workflows if file exists
  if (tmpl.type === "n8n-workflow" && tmpl.file) {
    const src = path.join("/workflows", tmpl.file);
    if (fs.existsSync(src)) {
      // Already available as a mounted file
      installedSet.add(tmpl.id);
      return res.json({
        status: "installed",
        template: tmpl.id,
        instructions: `Workflow file ${tmpl.file} is available. Import it via n8n UI or API.`,
      });
    }
  }

  // Mark as installed (simulated for non-file templates)
  installedSet.add(tmpl.id);
  res.json({ status: "installed", template: tmpl.id });
});

router.post("/templates/:id/uninstall", (req, res) => {
  const tmpl = TEMPLATES.find((t) => t.id === req.params.id);
  if (!tmpl) return res.status(404).json({ error: "Template not found" });
  installedSet.delete(tmpl.id);
  res.json({ status: "uninstalled", template: tmpl.id });
});

module.exports = router;
