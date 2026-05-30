"""Comprehensive workspace + RBAC test suite."""
import requests
import json
import sys

BASE = "http://localhost:8010"
PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — {detail}")


print("=" * 60)
print("WORKSPACE + RBAC COMPREHENSIVE TEST SUITE")
print("=" * 60)

# ── 1. Workspace Management ───────────────────────────────
print("\n── 1. Workspace Management ──")

r = requests.get(f"{BASE}/workspaces")
ws_list = r.json()
test("List workspaces returns array", isinstance(ws_list, list))
test("Default workspace exists", any(w["id"] == "default" for w in ws_list))

# Create workspaces
eng = requests.post(f"{BASE}/workspaces", json={"name": "Test-Eng", "description": "Engineering"}).json()
test("Create workspace returns id", "id" in eng, str(eng))

res = requests.post(f"{BASE}/workspaces", json={"name": "Test-Research", "description": "Research"}).json()
test("Create workspace 2", "id" in res, str(res))

ENG_ID = eng["id"]
RES_ID = res["id"]

# Update workspace
upd = requests.put(f"{BASE}/workspaces/{ENG_ID}", json={"description": "Updated eng"}).json()
test("Update workspace", upd.get("description") == "Updated eng")

# Members
m = requests.post(f"{BASE}/workspaces/{ENG_ID}/members", json={"user_id": "bob", "role": "member"}).json()
test("Add member", m.get("user_id") == "bob")

members = requests.get(f"{BASE}/workspaces/{ENG_ID}/members").json()
test("List members", len(members) >= 2)

rm = requests.delete(f"{BASE}/workspaces/{ENG_ID}/members/bob").json()
test("Remove member", rm.get("removed") == True)

# ── 2. Scope-aware Skill CRUD ─────────────────────────────
print("\n── 2. Scope-aware Skills ──")

# Create global skill
gs = requests.post(f"{BASE}/skills",
    json={"name": "TestGlobalSkill", "description": "Global", "scope": "global"},
    headers={"x-workspace-id": "default", "x-user-role": "admin"}).json()
test("Create global skill", gs.get("scope") == "global", str(gs.get("scope")))

# Create workspace-scoped skill in Engineering
es = requests.post(f"{BASE}/skills",
    json={"name": "TestEngSkill", "description": "Eng only", "scope": "workspace"},
    headers={"x-workspace-id": ENG_ID, "x-user-role": "member"}).json()
test("Create eng skill", es.get("scope") == "workspace" and es.get("workspace_id") == ENG_ID)

# Create workspace-scoped skill in Research
rs = requests.post(f"{BASE}/skills",
    json={"name": "TestResSkill", "description": "Res only", "scope": "workspace"},
    headers={"x-workspace-id": RES_ID, "x-user-role": "member"}).json()
test("Create research skill", rs.get("scope") == "workspace" and rs.get("workspace_id") == RES_ID)

# List from Engineering: should see Global + Eng, NOT Research
eng_skills = requests.get(f"{BASE}/skills", headers={"x-workspace-id": ENG_ID}).json().get("skills", [])
eng_names = [s["name"] for s in eng_skills]
test("Eng sees global skill", "TestGlobalSkill" in eng_names)
test("Eng sees own skill", "TestEngSkill" in eng_names)
test("Eng does NOT see research skill", "TestResSkill" not in eng_names)

# List from Research: should see Global + Research, NOT Engineering
res_skills = requests.get(f"{BASE}/skills", headers={"x-workspace-id": RES_ID}).json().get("skills", [])
res_names = [s["name"] for s in res_skills]
test("Research sees global skill", "TestGlobalSkill" in res_names)
test("Research sees own skill", "TestResSkill" in res_names)
test("Research does NOT see eng skill", "TestEngSkill" not in res_names)

# ── 3. Scope-aware Agent CRUD ─────────────────────────────
print("\n── 3. Scope-aware Agents ──")

ga = requests.post(f"{BASE}/agents",
    json={"name": "GlobalBot", "description": "Global agent", "scope": "global"},
    headers={"x-workspace-id": "default", "x-user-role": "admin"}).json()
test("Create global agent", ga.get("scope") == "global")

ea = requests.post(f"{BASE}/agents",
    json={"name": "EngBot", "description": "Eng agent", "scope": "workspace"},
    headers={"x-workspace-id": ENG_ID}).json()
test("Create eng agent", ea.get("scope") == "workspace" and ea.get("workspace_id") == ENG_ID)

ra = requests.post(f"{BASE}/agents",
    json={"name": "ResBot", "description": "Res agent", "scope": "workspace"},
    headers={"x-workspace-id": RES_ID}).json()
test("Create research agent", ra.get("scope") == "workspace")

eng_agents = [a["name"] for a in requests.get(f"{BASE}/agents", headers={"x-workspace-id": ENG_ID}).json().get("agents", [])]
test("Eng sees global agent", "GlobalBot" in eng_agents)
test("Eng sees own agent", "EngBot" in eng_agents)
test("Eng does NOT see research agent", "ResBot" not in eng_agents)

res_agents = [a["name"] for a in requests.get(f"{BASE}/agents", headers={"x-workspace-id": RES_ID}).json().get("agents", [])]
test("Research sees global agent", "GlobalBot" in res_agents)
test("Research sees own agent", "ResBot" in res_agents)
test("Research does NOT see eng agent", "EngBot" not in res_agents)

# ── 4. Scope-aware MCP Servers ────────────────────────────
print("\n── 4. Scope-aware MCP Servers ──")

gm = requests.post(f"{BASE}/mcp/servers",
    json={"name": "GlobalMCP", "url": "http://test:8080", "transport": "http", "scope": "global"},
    headers={"x-workspace-id": "default", "x-user-role": "admin"}).json()
test("Create global MCP", gm.get("scope") == "global")

em = requests.post(f"{BASE}/mcp/servers",
    json={"name": "EngMCP", "url": "http://eng-mcp:8080", "transport": "http", "scope": "workspace"},
    headers={"x-workspace-id": ENG_ID}).json()
test("Create eng MCP", em.get("scope") == "workspace")

eng_mcps = [m["name"] for m in requests.get(f"{BASE}/mcp/servers", headers={"x-workspace-id": ENG_ID}).json().get("servers", [])]
test("Eng sees global MCPs", "GlobalMCP" in eng_mcps)
test("Eng sees own MCP", "EngMCP" in eng_mcps)

res_mcps = [m["name"] for m in requests.get(f"{BASE}/mcp/servers", headers={"x-workspace-id": RES_ID}).json().get("servers", [])]
test("Research sees global MCPs", "GlobalMCP" in res_mcps)
test("Research does NOT see eng MCP", "EngMCP" not in res_mcps)

# ── 5. Scope-aware Prompts ────────────────────────────────
print("\n── 5. Scope-aware Prompts ──")

gp = requests.post(f"{BASE}/prompts",
    json={"name": "GlobalPrompt", "content": "Test prompt", "scope": "global"},
    headers={"x-workspace-id": "default", "x-user-role": "admin"}).json()
test("Create global prompt", gp.get("scope") == "global")

ep = requests.post(f"{BASE}/prompts",
    json={"name": "EngPrompt", "content": "Eng prompt", "scope": "workspace"},
    headers={"x-workspace-id": ENG_ID}).json()
test("Create eng prompt", ep.get("scope") == "workspace")

eng_prompts = [p["name"] for p in requests.get(f"{BASE}/prompts", headers={"x-workspace-id": ENG_ID}).json().get("prompts", [])]
test("Eng sees global prompt", "GlobalPrompt" in eng_prompts)
test("Eng sees own prompt", "EngPrompt" in eng_prompts)

res_prompts = [p["name"] for p in requests.get(f"{BASE}/prompts", headers={"x-workspace-id": RES_ID}).json().get("prompts", [])]
test("Research sees global prompt", "GlobalPrompt" in res_prompts)
test("Research does NOT see eng prompt", "EngPrompt" not in res_prompts)

# ── 6. Scope-aware Custom Tools ───────────────────────────
print("\n── 6. Scope-aware Custom Tools ──")

gt = requests.post(f"{BASE}/custom-tools",
    json={"name": "GlobalTool", "description": "Global tool", "endpoint": "http://test", "scope": "global"},
    headers={"x-workspace-id": "default", "x-user-role": "admin"}).json()
test("Create global custom tool", gt.get("scope") == "global")

et = requests.post(f"{BASE}/custom-tools",
    json={"name": "EngTool", "description": "Eng tool", "endpoint": "http://eng", "scope": "workspace"},
    headers={"x-workspace-id": ENG_ID}).json()
test("Create eng custom tool", et.get("scope") == "workspace")

eng_tools = [t["name"] for t in requests.get(f"{BASE}/custom-tools", headers={"x-workspace-id": ENG_ID}).json().get("tools", [])]
test("Eng sees global tool", "GlobalTool" in eng_tools)
test("Eng sees own tool", "EngTool" in eng_tools)

res_tools = [t["name"] for t in requests.get(f"{BASE}/custom-tools", headers={"x-workspace-id": RES_ID}).json().get("tools", [])]
test("Research sees global tool", "GlobalTool" in res_tools)
test("Research does NOT see eng tool", "EngTool" not in res_tools)

# ── 7. RBAC: Non-admin cannot create global ───────────────
print("\n── 7. RBAC Enforcement ──")

non_admin_skill = requests.post(f"{BASE}/skills",
    json={"name": "ShouldBeWorkspace", "description": "Member tries global", "scope": "global"},
    headers={"x-workspace-id": ENG_ID, "x-user-role": "member"}).json()
test("Member requesting global gets workspace", non_admin_skill.get("scope") == "workspace",
     f"Got scope={non_admin_skill.get('scope')}")

admin_skill = requests.post(f"{BASE}/skills",
    json={"name": "ShouldBeGlobal", "description": "Admin creates global", "scope": "global"},
    headers={"x-workspace-id": "default", "x-user-role": "admin"}).json()
test("Admin requesting global gets global", admin_skill.get("scope") == "global",
     f"Got scope={admin_skill.get('scope')}")

# ── 8. Backward Compatibility ─────────────────────────────
print("\n── 8. Backward Compatibility ──")

# No headers = default workspace, admin role (backward compat)
no_header_agents = requests.get(f"{BASE}/agents").json().get("agents", [])
test("No headers returns agents (backward compat)", len(no_header_agents) > 0)

# Default agent still accessible
default_agent = requests.get(f"{BASE}/agents/default").json()
test("Default agent still accessible", default_agent.get("name") == "Assistant")

# ── 9. Workspace deletion ────────────────────────────────
print("\n── 9. Workspace Deletion ──")

cant_del = requests.delete(f"{BASE}/workspaces/default").json()
test("Cannot delete default workspace", cant_del.get("error") is not None or cant_del.get("deleted") == False)

# ── Summary ──────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 60)

# Cleanup: delete test workspaces and resources
for sid in [gs.get("id"), es.get("id"), rs.get("id"), non_admin_skill.get("id"), admin_skill.get("id")]:
    if sid: requests.delete(f"{BASE}/skills/{sid}")
for aid in [ga.get("id"), ea.get("id"), ra.get("id")]:
    if aid: requests.delete(f"{BASE}/agents/{aid}")
for mid in [gm.get("id"), em.get("id")]:
    if mid: requests.delete(f"{BASE}/mcp/servers/{mid}")
for pid in [gp.get("id"), ep.get("id")]:
    if pid: requests.delete(f"{BASE}/prompts/{pid}")
for tid in [gt.get("id"), et.get("id")]:
    if tid: requests.delete(f"{BASE}/custom-tools/{tid}")
for wid in [ENG_ID, RES_ID]:
    requests.delete(f"{BASE}/workspaces/{wid}")

if FAIL > 0:
    sys.exit(1)
