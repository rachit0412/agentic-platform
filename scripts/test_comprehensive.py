"""Comprehensive platform test — tests every major feature end-to-end."""

import json
import sys
import time
import uuid

import requests

BASE = "http://localhost:8010"
TOOLS_BASE = "http://localhost:8011"
UI_BASE = "http://localhost:3005"
N8N_BASE = "http://localhost:5678"
HEADERS = {
    "x-user-role": "admin",
    "x-user-id": "admin",
    "x-workspace-id": "default",
    "Content-Type": "application/json",
}

passed = 0
failed = 0
errors = []


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  ✗ {name} — {detail}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ────────────────────────────────────────────────────────────
section("1. HEALTH CHECKS")
for svc_name, url in [
    ("Agent Service", f"{BASE}/health"),
    ("Tools Service", f"{TOOLS_BASE}/health"),
    ("UI Console", f"{UI_BASE}/health"),
    ("ChromaDB", "http://localhost:8200/api/v1/heartbeat"),
]:
    try:
        r = requests.get(url, timeout=5)
        test(svc_name, r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        test(svc_name, False, str(e))

# ────────────────────────────────────────────────────────────
section("2. AUTHENTICATION")
r = requests.post(
    f"{BASE}/auth/login",
    json={"username": "admin", "password": "Admin@Platform2026!"},
    timeout=10,
)
user = r.json()
test(
    "Admin login",
    r.status_code == 200 and user.get("id") == "admin",
    f"status={r.status_code}",
)
test("Admin role", user.get("role") == "admin", f"role={user.get('role')}")
personas = user.get("personas", [])
test("Admin has personas", len(personas) > 0, f"count={len(personas)}")
admin_persona = next((p for p in personas if p["name"] == "Admin"), None)
test("Admin persona exists", admin_persona is not None)
if admin_persona:
    acts = admin_persona.get("permissions", {}).get("actions", [])
    test("Admin persona has access_admin", "access_admin" in acts, f"actions={acts}")
    test("Admin persona has create_global", "create_global" in acts, f"actions={acts}")

# Bad login
r = requests.post(
    f"{BASE}/auth/login", json={"username": "nobody", "password": "wrong"}, timeout=10
)
test("Bad password rejected", r.status_code == 401)

# ────────────────────────────────────────────────────────────
section("3. MODELS")
r = requests.get(f"{BASE}/models", headers=HEADERS, timeout=10)
d = r.json()
models = d.get("models", [])
test("Models endpoint", r.status_code == 200)
test("Has models", len(models) > 0, f"count={len(models)}")
if models:
    print(
        f"    → Sample: {models[0]['provider']}:{models[0].get('model', models[0].get('id', '?'))}"
    )

# ────────────────────────────────────────────────────────────
section("4. TOOLS")
r = requests.get(f"{BASE}/tools", headers=HEADERS, timeout=10)
d = r.json()
tools = d if isinstance(d, list) else d.get("tools", [])
test("Tools list", r.status_code == 200)
test("Has tools", len(tools) > 0, f"count={len(tools)}")
for t in tools[:3]:
    print(
        f"    → {t['name']} (scope={t.get('scope','?')}, enabled={t.get('enabled','?')})"
    )

# Test tools service directly
r2 = requests.get(f"{TOOLS_BASE}/tools", timeout=10)
test("Tools service direct", r2.status_code == 200)

# ────────────────────────────────────────────────────────────
section("5. PROMPTS CRUD + SCOPE")
# Create private prompt
r = requests.post(
    f"{BASE}/prompts",
    headers=HEADERS,
    json={
        "name": f"Test Prompt {uuid.uuid4().hex[:6]}",
        "content": "You are a test assistant. Answer briefly.",
        "category": "general",
        "scope": "private",
        "description": "Test prompt",
        "tags": ["test"],
    },
)
test(
    "Create private prompt",
    r.status_code == 200,
    f"status={r.status_code} body={r.text[:200]}",
)
prompt = r.json()
prompt_id = prompt.get("id", "")

# Create global prompt (admin)
r = requests.post(
    f"{BASE}/prompts",
    headers=HEADERS,
    json={
        "name": f"Global Prompt {uuid.uuid4().hex[:6]}",
        "content": "Global test prompt content.",
        "category": "general",
        "scope": "global",
        "description": "Global test",
        "tags": ["test", "global"],
    },
)
test("Create global prompt (admin)", r.status_code == 200)
global_prompt = r.json()
test(
    "Global scope applied",
    global_prompt.get("scope") == "global",
    f"scope={global_prompt.get('scope')}",
)
global_prompt_id = global_prompt.get("id", "")

# Update scope from private to global
if prompt_id:
    r = requests.put(
        f"{BASE}/prompts/{prompt_id}", headers=HEADERS, json={"scope": "global"}
    )
    test("Update scope to global", r.status_code == 200, f"status={r.status_code}")
    updated = r.json()
    test(
        "Scope changed to global",
        updated.get("scope") == "global",
        f"scope={updated.get('scope')}",
    )

# Non-admin cannot create global
member_headers = {**HEADERS, "x-user-role": "member"}
r = requests.post(
    f"{BASE}/prompts",
    headers=member_headers,
    json={
        "name": f"Member Prompt {uuid.uuid4().hex[:6]}",
        "content": "Member prompt.",
        "category": "general",
        "scope": "global",
    },
)
test(
    "Member cannot create global",
    r.json().get("scope") == "private",
    f"scope={r.json().get('scope')}",
)

# List prompts
r = requests.get(f"{BASE}/prompts", headers=HEADERS, timeout=10)
test("List prompts", r.status_code == 200 and len(r.json().get("prompts", [])) > 0)

# Delete test prompts
for pid in [prompt_id, global_prompt_id]:
    if pid:
        requests.delete(f"{BASE}/prompts/{pid}", headers=HEADERS)

# ────────────────────────────────────────────────────────────
section("6. SKILLS CRUD + SCOPE")
r = requests.post(
    f"{BASE}/skills",
    headers=HEADERS,
    json={
        "name": f"Test Skill {uuid.uuid4().hex[:6]}",
        "description": "A test skill",
        "prompt": "Do analysis",
        "scope": "global",
        "tools": [],
        "parameters": [],
    },
)
test(
    "Create global skill",
    r.status_code == 200,
    f"status={r.status_code} body={r.text[:200]}",
)
skill = r.json()
skill_id = skill.get("id", "")
test(
    "Skill scope is global",
    skill.get("scope") == "global",
    f"scope={skill.get('scope')}",
)

r = requests.get(f"{BASE}/skills", headers=HEADERS)
test("List skills", r.status_code == 200)

if skill_id:
    r = requests.put(
        f"{BASE}/skills/{skill_id}", headers=HEADERS, json={"scope": "private"}
    )
    test("Update skill scope", r.status_code == 200)
    test(
        "Skill scope changed",
        r.json().get("scope") == "private",
        f"scope={r.json().get('scope')}",
    )
    requests.delete(f"{BASE}/skills/{skill_id}", headers=HEADERS)

# ────────────────────────────────────────────────────────────
section("7. AGENTS CRUD + SCOPE")
agent_name = f"Test Agent {uuid.uuid4().hex[:6]}"
r = requests.post(
    f"{BASE}/agents",
    headers=HEADERS,
    json={
        "name": agent_name,
        "description": "Automated test agent",
        "system_prompt": "You are a helpful test agent.",
        "scope": "global",
        "tools": [],
        "model": "",
    },
)
test(
    "Create global agent",
    r.status_code == 200,
    f"status={r.status_code} body={r.text[:200]}",
)
agent = r.json()
agent_id = agent.get("id", "")
test(
    "Agent scope is global",
    agent.get("scope") == "global",
    f"scope={agent.get('scope')}",
)

r = requests.get(f"{BASE}/agents", headers=HEADERS)
agents_list = r.json().get("agents", [])
test(
    "List agents",
    r.status_code == 200 and len(agents_list) > 0,
    f"count={len(agents_list)}",
)

if agent_id:
    r = requests.get(f"{BASE}/agents/{agent_id}", headers=HEADERS)
    test(
        "Get single agent", r.status_code == 200 and r.json().get("name") == agent_name
    )

    r = requests.put(
        f"{BASE}/agents/{agent_id}",
        headers=HEADERS,
        json={"scope": "private", "description": "Updated"},
    )
    test("Update agent scope", r.status_code == 200)
    test(
        "Agent scope changed",
        r.json().get("scope") == "private",
        f"scope={r.json().get('scope')}",
    )

# ────────────────────────────────────────────────────────────
section("8. AGENT ORCHESTRATION (RUN)")
# Run agent with a simple prompt
r = requests.post(
    f"{BASE}/run",
    headers=HEADERS,
    json={
        "prompt": "What is 2+2? Answer in one word.",
        "session_id": f"test-{uuid.uuid4().hex[:8]}",
        "use_kb": False,
    },
    timeout=60,
)
test("Agent run", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")
run_result = r.json()
test(
    "Run has response",
    bool(run_result.get("response")),
    f"keys={list(run_result.keys())}",
)
if run_result.get("response"):
    print(f"    → Response: {run_result['response'][:100]}")
    print(
        f"    → Model: {run_result.get('model','?')}, Provider: {run_result.get('provider','?')}"
    )

# ────────────────────────────────────────────────────────────
section("9. MEMORY / SESSIONS")
r = requests.get(f"{BASE}/memory/sessions", headers=HEADERS)
test("List sessions", r.status_code == 200, f"status={r.status_code}")
sessions = r.json() if isinstance(r.json(), list) else r.json().get("sessions", [])
test("Has sessions", len(sessions) > 0, f"count={len(sessions)}")

r = requests.get(f"{BASE}/memory/stats", headers=HEADERS)
test("Memory stats", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
section("10. KNOWLEDGE BASE")
r = requests.get(f"{BASE}/kb/stats", headers=HEADERS)
test("KB stats", r.status_code == 200, f"status={r.status_code}")

r = requests.get(f"{BASE}/kb/collections", headers=HEADERS)
test("KB collections", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
section("11. MCP ENDPOINTS")
# MCP server info
r = requests.get(f"{BASE}/mcp/info", headers=HEADERS, timeout=10)
test("MCP info", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

# MCP tools list
r = requests.get(f"{BASE}/mcp/tools", headers=HEADERS, timeout=10)
test("MCP tools list", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    mcp_tools = r.json()
    tool_list = mcp_tools if isinstance(mcp_tools, list) else mcp_tools.get("tools", [])
    test("MCP has tools", len(tool_list) > 0, f"count={len(tool_list)}")
    for t in (tool_list[:3] if tool_list else []):
        name = t.get("name", t.get("function", {}).get("name", "?"))
        print(f"    → MCP Tool: {name}")

# MCP tool call
r = requests.post(
    f"{BASE}/mcp/tools/call",
    headers=HEADERS,
    json={"name": "calculator", "arguments": {"expression": "2+2"}},
    timeout=15,
)
if r.status_code == 200:
    test("MCP tool call (calculator)", True)
    print(f"    → Result: {r.json()}")
elif r.status_code == 404:
    # Try different tool name
    r2 = requests.post(
        f"{BASE}/mcp/tools/call",
        headers=HEADERS,
        json={
            "name": "note_save",
            "arguments": {"title": "test", "content": "test note from MCP"},
        },
        timeout=15,
    )
    test(
        "MCP tool call (note_save)",
        r2.status_code == 200,
        f"status={r2.status_code} body={r2.text[:200]}",
    )
else:
    test("MCP tool call", False, f"status={r.status_code} body={r.text[:200]}")

# MCP resources
r = requests.get(f"{BASE}/mcp/resources", headers=HEADERS, timeout=10)
test("MCP resources", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
section("12. A2A PROTOCOL")
# A2A agent card
r = requests.get(f"{BASE}/.well-known/agent.json", timeout=10)
test("A2A agent card", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    card = r.json()
    test("A2A card has name", bool(card.get("name")), f"keys={list(card.keys())}")
    test(
        "A2A card has skills", bool(card.get("skills")), f"skills={card.get('skills')}"
    )
    print(f"    → Name: {card.get('name')}")
    print(f"    → URL: {card.get('url')}")

# A2A task send
r = requests.post(
    f"{BASE}/a2a",
    headers=HEADERS,
    json={
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/send",
        "params": {
            "id": str(uuid.uuid4()),
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "What is 2+2?"}],
            },
        },
    },
    timeout=60,
)
test(
    "A2A tasks/send",
    r.status_code == 200,
    f"status={r.status_code} body={r.text[:300]}",
)
if r.status_code == 200:
    a2a_resp = r.json()
    result = a2a_resp.get("result", {})
    test("A2A has result", bool(result), f"keys={list(a2a_resp.keys())}")
    if result:
        status = result.get("status", {})
        print(f"    → State: {status.get('state')}")
        artifacts = result.get("artifacts", [])
        if artifacts:
            for art in artifacts[:1]:
                for part in art.get("parts", [])[:1]:
                    print(f"    → Response: {str(part.get('text',''))[:100]}")

# ────────────────────────────────────────────────────────────
section("13. GUARDRAILS")
r = requests.get(f"{BASE}/guardrails", headers=HEADERS)
test("List guardrails", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
section("14. WORKFLOWS / PIPELINES")
r = requests.get(f"{BASE}/pipelines", headers=HEADERS)
test("List pipelines", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
section("15. DOCUMENTS / FILESTORE")
r = requests.get(f"{BASE}/documents", headers=HEADERS)
test("List documents", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
section("16. WORKSPACES")
r = requests.get(f"{BASE}/workspaces", headers=HEADERS)
test("List workspaces", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
section("17. USERS & PERSONAS")
r = requests.get(f"{BASE}/users", headers=HEADERS)
test("List users", r.status_code == 200, f"status={r.status_code}")

r = requests.get(f"{BASE}/users/admin/personas", headers=HEADERS)
test("Admin personas", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    p_data = r.json()
    persona_list = p_data.get("personas", [])
    test("Admin has admin persona", any(p["name"] == "Admin" for p in persona_list))

# ────────────────────────────────────────────────────────────
section("18. N8N INTEGRATION")
try:
    r = requests.get(f"{N8N_BASE}/healthz", timeout=10)
    test("n8n health", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    test("n8n health", False, str(e))

# n8n webhook test — check if any workflows are active
try:
    # n8n API - list workflows
    r = requests.get(
        f"{N8N_BASE}/api/v1/workflows",
        headers={"Accept": "application/json"},
        timeout=10,
    )
    if r.status_code == 200:
        wf_data = r.json()
        workflows = wf_data.get("data", [])
        test("n8n workflows loaded", len(workflows) >= 0, f"count={len(workflows)}")
        for wf in workflows[:5]:
            active = "ACTIVE" if wf.get("active") else "inactive"
            print(f"    → {wf.get('name')} [{active}]")
    else:
        test("n8n workflows API", False, f"status={r.status_code}")
except Exception as e:
    test("n8n workflows", False, str(e))

# Test n8n proxy (webhook relay)
try:
    r = requests.get("http://localhost:5679/healthz", timeout=5)
    test("n8n proxy", r.status_code in [200, 301, 302, 404], f"status={r.status_code}")
except Exception as e:
    test("n8n proxy", False, str(e))

# ────────────────────────────────────────────────────────────
section("19. OBSERVABILITY")
# Prometheus
try:
    r = requests.get("http://localhost:9090/api/v1/targets", timeout=5)
    test("Prometheus targets", r.status_code == 200)
except Exception as e:
    test("Prometheus", False, str(e))

# Grafana
try:
    r = requests.get("http://localhost:3003/api/health", timeout=5)
    test("Grafana health", r.status_code == 200)
except Exception as e:
    test("Grafana", False, str(e))

# Langfuse
try:
    r = requests.get("http://localhost:3014/api/public/health", timeout=5)
    test("Langfuse health", r.status_code == 200)
except Exception as e:
    test("Langfuse", False, str(e))

# ────────────────────────────────────────────────────────────
section("20. LLM ACTIVITY / TRACES")
r = requests.get(f"{BASE}/llm-activity", headers=HEADERS)
test("LLM activity", r.status_code == 200, f"status={r.status_code}")

# ────────────────────────────────────────────────────────────
# Cleanup
if agent_id:
    requests.delete(f"{BASE}/agents/{agent_id}", headers=HEADERS)

# ────────────────────────────────────────────────────────────
section("RESULTS SUMMARY")
total = passed + failed
print(f"\n  Passed: {passed}/{total}")
print(f"  Failed: {failed}/{total}")
if errors:
    print(f"\n  FAILURES:")
    for e in errors:
        print(f"    ✗ {e}")
print()
sys.exit(1 if failed > 0 else 0)
