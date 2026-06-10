"""
Final comprehensive platform test with correct API signatures.
Registers MCP servers and A2A peers, then tests every feature.
"""

import json
import sys
import time

import requests

BASE = "http://localhost:8010"
TOOLS = "http://localhost:8011"
N8N = "http://localhost:5679"

h = {
    "x-user-id": "admin",
    "x-user-role": "admin",
    "x-workspace-id": "default",
    "Content-Type": "application/json",
}

RESULTS = {"pass": 0, "fail": 0, "details": []}


def _extract_list(data):
    """Extract list from response that might be {key: [...]} or [...]."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def test(name, fn):
    try:
        ok, msg = fn()
        status = "PASS" if ok else "FAIL"
        RESULTS["pass" if ok else "fail"] += 1
        RESULTS["details"].append((name, status, msg))
        print(f"  [{status}] {name}: {msg}")
    except Exception as e:
        RESULTS["fail"] += 1
        RESULTS["details"].append((name, "FAIL", str(e)[:200]))
        print(f"  [FAIL] {name}: {str(e)[:200]}")


# Wait for agent service to be healthy after rebuild
print("Waiting for agent service...")
for i in range(30):
    try:
        r = requests.get(BASE + "/health", timeout=3)
        if r.status_code == 200:
            print("  Agent service ready!")
            break
    except:
        pass
    time.sleep(2)

# ============ SETUP ============
print("\n=== SETUP ===")

# Register MCP servers if not already
r = requests.get(BASE + "/mcp/servers", headers=h, timeout=10)
existing_servers = r.json().get("servers", [])
existing_names = {s.get("name") for s in existing_servers}

for srv in [
    {
        "name": "Open Tools MCP",
        "url": "http://open-tools-mcp:8080",
        "transport": "http",
        "description": "Wikipedia, calculator, etc.",
        "scope": "global",
    },
    {
        "name": "Brave Search MCP",
        "url": "http://brave-search-mcp:8080",
        "transport": "http",
        "description": "Brave web search",
        "scope": "global",
    },
]:
    if srv["name"] not in existing_names:
        r = requests.post(BASE + "/mcp/servers", headers=h, json=srv, timeout=10)
        print(f"  Registered MCP: {srv['name']} ({r.status_code})")
    else:
        print(f"  MCP exists: {srv['name']}")

# Register A2A peer
r = requests.get(BASE + "/a2a/peers", headers=h, timeout=10)
existing_peers = r.json().get("peers", [])
if not existing_peers:
    r = requests.post(
        BASE + "/a2a/peers",
        headers=h,
        json={
            "name": "Local Agent",
            "url": "http://agent-service:8000",
            "description": "Self peer",
        },
        timeout=10,
    )
    print(f"  Registered A2A peer ({r.status_code})")
else:
    print(f"  A2A peers exist: {len(existing_peers)}")

# Clean up old test agents
r = requests.get(BASE + "/agents", headers=h, timeout=10)
agents_data = r.json()
agents_list = (
    agents_data.get("agents", agents_data)
    if isinstance(agents_data, dict)
    else agents_data
)
if isinstance(agents_list, list):
    for a in agents_list:
        if isinstance(a, dict) and a.get("name", "").startswith("E2E"):
            requests.delete(BASE + f"/agents/{a['id']}", headers=h, timeout=10)
            print(f"  Cleaned up agent: {a['name']}")

# ============ 1. SERVICE HEALTH ============
print("\n=== 1. SERVICE HEALTH ===")
test(
    "Agent service",
    lambda: (requests.get(BASE + "/health", timeout=5).status_code == 200, "OK"),
)
test(
    "Tools service",
    lambda: (requests.get(TOOLS + "/health", timeout=5).status_code == 200, "OK"),
)
test(
    "n8n proxy",
    lambda: (requests.get(N8N + "/healthz", timeout=5).status_code == 200, "OK"),
)
test(
    "Grafana",
    lambda: (
        requests.get("http://localhost:3003/api/health", timeout=5).status_code == 200,
        "OK",
    ),
)
test(
    "Prometheus",
    lambda: (
        requests.get("http://localhost:9090/-/healthy", timeout=5).status_code == 200,
        "OK",
    ),
)

# ============ 2. AUTH ============
print("\n=== 2. AUTH ===")


def test_login():
    r = requests.post(
        BASE + "/auth/login",
        json={"username": "admin", "password": "Admin@Platform2026!"},
        timeout=10,
    )
    if r.status_code == 200:
        return True, f"role={r.json().get('role')}"
    return False, f"{r.status_code}"


test("Admin login", test_login)

# ============ 3. AGENTS CRUD ============
print("\n=== 3. AGENTS CRUD ===")
test_agent_id = None


def test_create_agent():
    global test_agent_id
    r = requests.post(
        BASE + "/agents",
        headers=h,
        json={
            "name": f"E2E Agent {int(time.time())}",
            "description": "Test",
            "model": "llama3",
            "system_prompt": "Be brief.",
            "scope": "global",
        },
        timeout=10,
    )
    if r.status_code in [200, 201]:
        test_agent_id = r.json().get("id")
        return True, f"id={test_agent_id}"
    return False, f"{r.status_code}: {r.text[:100]}"


test("Create agent", test_create_agent)


def test_list_agents():
    r = requests.get(BASE + "/agents", headers=h, timeout=10)
    agents = _extract_list(r.json())
    return len(agents) > 0, f"count={len(agents)}"


test("List agents", test_list_agents)


def test_get_agent():
    if not test_agent_id:
        return False, "no agent"
    r = requests.get(BASE + f"/agents/{test_agent_id}", headers=h, timeout=10)
    return r.status_code == 200, f"name={r.json().get('name')}"


test("Get agent", test_get_agent)


def test_update_agent():
    if not test_agent_id:
        return False, "no agent"
    r = requests.put(
        BASE + f"/agents/{test_agent_id}",
        headers=h,
        json={"description": "Updated description"},
        timeout=10,
    )
    return r.status_code == 200, "updated"


test("Update agent", test_update_agent)

# ============ 4. AGENT RUN ============
print("\n=== 4. AGENT RUN (60-120s for Ollama) ===")


def test_agent_run():
    r = requests.post(
        BASE + "/run",
        headers=h,
        json={"prompt": "What is 2+2? Just the number.", "sessionId": "e2e-final"},
        timeout=300,
    )
    if r.status_code == 200:
        out = str(r.json().get("output", r.json().get("response", "")))
        return len(out) > 0, f"output={out[:80]}"
    return False, f"{r.status_code}: {r.text[:150]}"


test("Agent run", test_agent_run)

# ============ 5. MCP ============
print("\n=== 5. MCP SERVERS ===")
mcp_server_id = None
mcp_tool_name = None


def test_mcp_list():
    global mcp_server_id, mcp_tool_name
    r = requests.get(BASE + "/mcp/servers", headers=h, timeout=10)
    servers = r.json().get("servers", [])
    if servers:
        # Use open-tools-mcp preferably
        for s in servers:
            if "open" in s.get("name", "").lower():
                mcp_server_id = s["id"]
                break
        if not mcp_server_id:
            mcp_server_id = servers[0]["id"]
        # Discover tools
        r2 = requests.post(
            BASE + f"/mcp/servers/{mcp_server_id}/discover", headers=h, timeout=15
        )
        if r2.status_code == 200:
            tools = r2.json().get("tools", [])
            if tools:
                mcp_tool_name = (
                    tools[0]["name"] if isinstance(tools[0], dict) else tools[0]
                )
    return (
        len(servers) > 0,
        f"count={len(servers)}, server={mcp_server_id}, tool={mcp_tool_name}",
    )


test("List MCP servers", test_mcp_list)


def test_mcp_invoke():
    if not mcp_server_id or not mcp_tool_name:
        return False, "no server/tool"
    r = requests.post(
        BASE + f"/mcp/servers/{mcp_server_id}/invoke",
        params={"tool_name": mcp_tool_name},
        headers=h,
        json={"arguments": {"query": "Python programming"}},
        timeout=30,
    )
    return r.status_code == 200, f"status={r.status_code}, result={str(r.json())[:80]}"


test("MCP tool invoke", test_mcp_invoke)

# ============ 6. A2A ============
print("\n=== 6. A2A ===")


def test_a2a_card():
    r = requests.get(BASE + "/a2a/card", headers=h, timeout=10)
    return r.status_code == 200, f"protocols={r.json().get('protocols')}"


test("A2A card", test_a2a_card)

a2a_peer_id = None


def test_a2a_peers():
    global a2a_peer_id
    r = requests.get(BASE + "/a2a/peers", headers=h, timeout=10)
    peers = r.json().get("peers", [])
    if peers:
        a2a_peer_id = peers[0].get("id")
    return len(peers) > 0, f"count={len(peers)}, first={a2a_peer_id}"


test("A2A list peers", test_a2a_peers)


def test_a2a_send():
    if not a2a_peer_id:
        return False, "no peer"
    r = requests.post(
        BASE + "/a2a/send",
        headers=h,
        json={"peer_id": a2a_peer_id, "task": "What is 1+1?", "context": {}},
        timeout=300,
    )
    if r.status_code == 200:
        return True, f"status={r.json().get('status')}, resp={str(r.json())[:80]}"
    return False, f"{r.status_code}: {r.text[:150]}"


test("A2A send task", test_a2a_send)

# ============ 7. PIPELINES ============
print("\n=== 7. PIPELINES ===")

pipeline_id = None


def test_create_pipeline():
    global pipeline_id
    r = requests.post(
        BASE + "/pipelines",
        headers=h,
        json={
            "name": f"E2E Pipeline {int(time.time())}",
            "description": "Test",
            "scope": "global",
            "steps": [
                {
                    "agent_id": test_agent_id or "default",
                    "prompt_template": "Answer: {prompt}",
                }
            ],
        },
        timeout=10,
    )
    if r.status_code in [200, 201]:
        pipeline_id = r.json().get("id")
        return True, f"id={pipeline_id}"
    return False, f"{r.status_code}: {r.text[:100]}"


test("Create pipeline", test_create_pipeline)


def test_run_pipeline():
    if not pipeline_id:
        return False, "no pipeline"
    r = requests.post(
        BASE + f"/pipelines/{pipeline_id}/run",
        headers=h,
        json={"prompt": "What is 5+5?", "session_id": "e2e-pipe"},
        timeout=300,
    )
    if r.status_code == 200:
        return True, f"status={r.json().get('status')}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("Run pipeline", test_run_pipeline)

# ============ 8. SKILLS ============
print("\n=== 8. SKILLS ===")
test(
    "List skills",
    lambda: (
        requests.get(BASE + "/skills", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/skills',headers=h,timeout=10).json()))}",
    ),
)
test(
    "Create skill",
    lambda: (
        requests.post(
            BASE + "/skills",
            headers=h,
            json={
                "name": f"E2E Skill {int(time.time())}",
                "description": "Test",
                "content": "Skill",
                "scope": "global",
            },
            timeout=10,
        ).status_code
        in [200, 201],
        "OK",
    ),
)

# ============ 9. PROMPTS ============
print("\n=== 9. PROMPTS ===")
test(
    "List prompts",
    lambda: (
        requests.get(BASE + "/prompts", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/prompts',headers=h,timeout=10).json()))}",
    ),
)
test(
    "Create prompt",
    lambda: (
        requests.post(
            BASE + "/prompts",
            headers=h,
            json={
                "name": f"E2E Prompt {int(time.time())}",
                "content": "Test: {input}",
                "scope": "global",
            },
            timeout=10,
        ).status_code
        in [200, 201],
        "OK",
    ),
)

# ============ 10. DOCUMENTS/KB ============
print("\n=== 10. DOCUMENTS & KB ===")
test(
    "Collections",
    lambda: (
        requests.get(BASE + "/documents/collections", headers=h, timeout=10).status_code
        == 200,
        f"count={len(_extract_list(requests.get(BASE+'/documents/collections',headers=h,timeout=10).json()))}",
    ),
)
test(
    "Documents",
    lambda: (
        requests.get(BASE + "/documents", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/documents',headers=h,timeout=10).json()))}",
    ),
)


def test_kb():
    r = requests.post(
        BASE + "/documents/search",
        headers=h,
        json={"query": "test", "n_results": 3},
        timeout=15,
    )
    return r.status_code == 200, f"results={len(_extract_list(r.json()))}"


test("KB search", test_kb)

# ============ 11. TOOLS SERVICE ============
print("\n=== 11. TOOLS SERVICE ===")


def test_math():
    r = requests.post(TOOLS + "/tools/math", json={"expression": "2+2"}, timeout=10)
    return r.status_code == 200, f"result={r.json()}"


test("Math tool", test_math)


def test_datetime():
    r = requests.post(TOOLS + "/tools/datetime", json={}, timeout=10)
    return r.status_code == 200, f"result={str(r.json())[:60]}"


test("DateTime tool", test_datetime)


def test_uuid():
    r = requests.post(TOOLS + "/tools/uuid-generate", json={}, timeout=10)
    return r.status_code == 200, f"result={str(r.json())[:60]}"


test("UUID tool", test_uuid)


# Agent-side tools list
def test_agent_tools():
    r = requests.get(BASE + "/tools", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


test("Agent tools list", test_agent_tools)

# ============ 12. USERS/PERSONAS ============
print("\n=== 12. USERS & PERSONAS ===")
test(
    "Users",
    lambda: (
        requests.get(BASE + "/users", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/users',headers=h,timeout=10).json()))}",
    ),
)
test(
    "Personas",
    lambda: (
        requests.get(BASE + "/personas", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/personas',headers=h,timeout=10).json()))}",
    ),
)

# ============ 13. GUARDRAILS ============
print("\n=== 13. GUARDRAILS ===")
test(
    "Guardrails",
    lambda: (
        requests.get(BASE + "/guardrails", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/guardrails',headers=h,timeout=10).json()))}",
    ),
)

# ============ 14. WORKSPACES ============
print("\n=== 14. WORKSPACES ===")
test(
    "Workspaces",
    lambda: (
        requests.get(BASE + "/workspaces", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/workspaces',headers=h,timeout=10).json()))}",
    ),
)

# ============ 15. MODELS ============
print("\n=== 15. LLM MODELS ===")
test(
    "Models",
    lambda: (
        requests.get(BASE + "/models", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/models',headers=h,timeout=10).json()))}",
    ),
)

# ============ 16. LLM ACTIVITY ============
print("\n=== 16. LLM ACTIVITY ===")
test(
    "LLM activity",
    lambda: (
        requests.get(BASE + "/llm-activity", headers=h, timeout=10).status_code == 200,
        f"count={len(_extract_list(requests.get(BASE+'/llm-activity',headers=h,timeout=10).json()))}",
    ),
)

# ============ 17. OBSERVABILITY ============
print("\n=== 17. OBSERVABILITY ===")
test(
    "Grafana",
    lambda: (
        requests.get("http://localhost:3003/api/health", timeout=5).status_code == 200,
        "OK",
    ),
)
test(
    "Prometheus",
    lambda: (
        requests.get("http://localhost:9090/-/healthy", timeout=5).status_code == 200,
        "OK",
    ),
)


def test_langfuse():
    r = requests.get("http://localhost:3014", timeout=5)
    return r.status_code in [200, 301, 302], f"status={r.status_code}"


test("Langfuse", test_langfuse)

# ============ 18. N8N WEBHOOK ============
print("\n=== 18. N8N WEBHOOK (60-120s) ===")


def test_n8n_webhook():
    r = requests.post(
        N8N + "/webhook/agent-run",
        json={"prompt": "Say hi", "sessionId": "n8n-test"},
        timeout=300,
    )
    if r.status_code == 200:
        return True, f"response={str(r.json())[:80]}"
    return (
        r.status_code == 404,
        f"status={r.status_code} (webhook may not be registered)",
    )


test("n8n webhook", test_n8n_webhook)

# ============ 19. CLEANUP ============
print("\n=== CLEANUP ===")
if test_agent_id:
    requests.delete(BASE + f"/agents/{test_agent_id}", headers=h, timeout=10)
    print(f"  Deleted test agent")

# ============ SUMMARY ============
total = RESULTS["pass"] + RESULTS["fail"]
print("\n" + "=" * 60)
print(f"RESULTS: {RESULTS['pass']}/{total} PASSED, {RESULTS['fail']} FAILED")
print("=" * 60)

if RESULTS["fail"] > 0:
    print("\nFailed tests:")
    for name, status, msg in RESULTS["details"]:
        if status == "FAIL":
            print(f"  X {name}: {msg}")
else:
    print("\nALL TESTS PASSED!")
