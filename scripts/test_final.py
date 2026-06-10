"""
Register MCP servers, seed test data, and run complete platform tests.
Fixes: MCP not listed, A2A peer not found, pipeline empty.
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


# ============ STEP 1: Register MCP servers ============
print("\n=== SETUP: Register MCP Servers ===")

# Register open-tools-mcp
r = requests.get(BASE + "/mcp/servers", headers=h, timeout=10)
existing = r.json().get("servers", [])
existing_names = {s.get("name") for s in existing}

mcp_servers_to_register = [
    {
        "name": "Open Tools MCP",
        "url": "http://open-tools-mcp:8080",
        "transport": "http",
        "description": "Free tools: Wikipedia, calculator, date/time, weather",
        "scope": "global",
    },
    {
        "name": "Brave Search MCP",
        "url": "http://brave-search-mcp:8080",
        "transport": "http",
        "description": "Brave web search (requires API key)",
        "scope": "global",
    },
]

for srv in mcp_servers_to_register:
    if srv["name"] not in existing_names:
        r = requests.post(BASE + "/mcp/servers", headers=h, json=srv, timeout=10)
        if r.status_code in [200, 201]:
            sid = r.json().get("id", "?")
            print(f"  Registered: {srv['name']} (id={sid})")
        else:
            print(f"  Failed to register {srv['name']}: {r.status_code} {r.text[:100]}")
    else:
        print(f"  Already exists: {srv['name']}")

# ============ STEP 2: Register A2A self peer ============
print("\n=== SETUP: Register A2A Self Peer ===")

r = requests.get(BASE + "/a2a/peers", headers=h, timeout=10)
peers = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
peer_names = [p.get("name", "") for p in peers]

if not any("self" in n.lower() or "local" in n.lower() for n in peer_names):
    r = requests.post(
        BASE + "/a2a/peers",
        headers=h,
        json={
            "name": "Local Agent",
            "url": "http://agent-service:8000",
            "description": "Self-referencing local agent peer",
        },
        timeout=10,
    )
    if r.status_code in [200, 201]:
        peer_id = r.json().get("id", "?")
        print(f"  Registered self peer: id={peer_id}")
    else:
        print(f"  Failed: {r.status_code} {r.text[:200]}")
else:
    print(f"  Already registered")

# ============ SERVICE HEALTH ============
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

# ============ AUTH ============
print("\n=== 2. AUTHENTICATION ===")


def test_login():
    r = requests.post(
        BASE + "/auth/login",
        json={"username": "admin", "password": "Admin@Platform2026!"},
        timeout=10,
    )
    if r.status_code == 200:
        user = r.json()
        return True, f"user={user.get('username')}, role={user.get('role')}"
    return False, f"{r.status_code}: {r.text[:100]}"


test("Admin login", test_login)

# ============ AGENTS CRUD ============
print("\n=== 3. AGENTS CRUD ===")

test_agent_id = None


def test_create_agent():
    global test_agent_id
    r = requests.post(
        BASE + "/agents",
        headers=h,
        json={
            "name": "E2E Test Agent",
            "description": "Comprehensive test agent",
            "model": "llama3",
            "system_prompt": "You are a helpful assistant. Be very brief.",
            "scope": "global",
        },
        timeout=10,
    )
    if r.status_code in [200, 201]:
        test_agent_id = r.json().get("id")
        return True, f"id={test_agent_id}"
    return False, f"{r.status_code}: {r.text[:100]}"


test("Create agent", test_create_agent)
test(
    "List agents",
    lambda: (
        len(requests.get(BASE + "/agents", headers=h, timeout=10).json()) > 0,
        f"count={len(requests.get(BASE+'/agents',headers=h,timeout=10).json())}",
    ),
)
test(
    "Get agent",
    lambda: (
        test_agent_id
        and requests.get(
            BASE + f"/agents/{test_agent_id}", headers=h, timeout=10
        ).status_code
        == 200,
        f"found" if test_agent_id else "skipped",
    ),
)

# ============ AGENT RUN ============
print("\n=== 4. AGENT ORCHESTRATION (may take 60-120s) ===")


def test_agent_run():
    r = requests.post(
        BASE + "/run",
        headers=h,
        json={"prompt": "What is 2+2? Just the number.", "sessionId": "e2e-run-test"},
        timeout=300,
    )  # 5 min timeout for slow Ollama
    if r.status_code == 200:
        resp = r.json()
        out = str(resp.get("output", resp.get("response", "")))
        return len(out) > 0, f"output={out[:80]}"
    return False, f"{r.status_code}: {r.text[:150]}"


test("Agent run", test_agent_run)

# ============ MCP ============
print("\n=== 5. MCP SERVERS ===")

mcp_server_id = None
mcp_tool_name = None


def test_mcp_list():
    global mcp_server_id, mcp_tool_name
    r = requests.get(BASE + "/mcp/servers", headers=h, timeout=10)
    if r.status_code == 200:
        servers = r.json().get(
            "servers", r.json() if isinstance(r.json(), list) else []
        )
        if servers:
            mcp_server_id = servers[0].get("id")
            # Try to discover tools
            r2 = requests.post(
                BASE + f"/mcp/servers/{mcp_server_id}/discover", headers=h, timeout=15
            )
            if r2.status_code == 200:
                tools = r2.json().get("tools", [])
                if tools:
                    mcp_tool_name = (
                        tools[0].get("name") if isinstance(tools[0], dict) else tools[0]
                    )
        return len(servers) > 0, f"count={len(servers)}, tool={mcp_tool_name}"
    return False, f"{r.status_code}"


def test_mcp_invoke():
    if not mcp_server_id or not mcp_tool_name:
        return False, f"no server/tool (sid={mcp_server_id}, tool={mcp_tool_name})"
    r = requests.post(
        BASE + f"/mcp/servers/{mcp_server_id}/invoke",
        params={"tool_name": mcp_tool_name},
        headers=h,
        json={"arguments": {"query": "Python programming"}},
        timeout=30,
    )
    if r.status_code == 200:
        return True, f"result={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("List MCP servers", test_mcp_list)
test("MCP tool invoke", test_mcp_invoke)

# ============ A2A ============
print("\n=== 6. A2A ===")

test(
    "A2A card",
    lambda: (
        requests.get(BASE + "/a2a/card", headers=h, timeout=10).status_code == 200,
        f"keys={list(requests.get(BASE+'/a2a/card',headers=h,timeout=10).json().keys())[:5]}",
    ),
)

a2a_peer_id = None


def test_a2a_peers():
    global a2a_peer_id
    r = requests.get(BASE + "/a2a/peers", headers=h, timeout=10)
    if r.status_code == 200:
        peers = r.json() if isinstance(r.json(), list) else []
        if peers:
            a2a_peer_id = peers[0].get("id")
        return True, f"count={len(peers)}, first={a2a_peer_id}"
    return False, f"{r.status_code}"


test("A2A list peers", test_a2a_peers)


def test_a2a_send():
    if not a2a_peer_id:
        return False, "no peer registered"
    r = requests.post(
        BASE + "/a2a/send",
        headers=h,
        json={"peer_id": a2a_peer_id, "task": "What is 1+1?", "context": {}},
        timeout=300,
    )
    if r.status_code == 200:
        return True, f"result={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("A2A send task", test_a2a_send)

# ============ PIPELINES ============
print("\n=== 7. PIPELINES ===")

pipeline_id = None


def test_create_pipeline():
    global pipeline_id
    r = requests.post(
        BASE + "/pipelines",
        headers=h,
        json={
            "name": "E2E Test Pipeline",
            "description": "Test pipeline",
            "steps": [
                {
                    "agent_id": test_agent_id or "default",
                    "prompt_template": "Answer: {prompt}",
                }
            ],
            "scope": "global",
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
        json={"prompt": "What is 3+3?", "session_id": "e2e-pipe"},
        timeout=300,
    )
    if r.status_code == 200:
        return True, f"result={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("Run pipeline", test_run_pipeline)

# ============ SKILLS ============
print("\n=== 8. SKILLS ===")

test(
    "List skills",
    lambda: (
        requests.get(BASE + "/skills", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/skills',headers=h,timeout=10).json())}",
    ),
)
test(
    "Create skill",
    lambda: (
        requests.post(
            BASE + "/skills",
            headers=h,
            json={
                "name": "E2E Skill",
                "description": "Test",
                "content": "Test skill",
                "scope": "global",
            },
            timeout=10,
        ).status_code
        in [200, 201],
        "created",
    ),
)

# ============ PROMPTS ============
print("\n=== 9. PROMPTS ===")

test(
    "List prompts",
    lambda: (
        requests.get(BASE + "/prompts", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/prompts',headers=h,timeout=10).json())}",
    ),
)
test(
    "Create prompt",
    lambda: (
        requests.post(
            BASE + "/prompts",
            headers=h,
            json={"name": "E2E Prompt", "content": "Test: {input}", "scope": "global"},
            timeout=10,
        ).status_code
        in [200, 201],
        "created",
    ),
)

# ============ DOCUMENTS/KB ============
print("\n=== 10. DOCUMENTS & KB ===")

test(
    "Collections",
    lambda: (
        requests.get(BASE + "/collections", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/collections',headers=h,timeout=10).json())}",
    ),
)
test(
    "Documents",
    lambda: (
        requests.get(BASE + "/documents", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/documents',headers=h,timeout=10).json())}",
    ),
)
test(
    "KB query",
    lambda: (
        requests.post(
            BASE + "/kb/query",
            headers=h,
            json={"query": "test", "n_results": 3},
            timeout=15,
        ).status_code
        == 200,
        "queried",
    ),
)

# ============ TOOLS ============
print("\n=== 11. TOOLS ===")

test(
    "List tools",
    lambda: (
        requests.get(BASE + "/tools", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/tools',headers=h,timeout=10).json())}",
    ),
)
test(
    "Calculator tool",
    lambda: (
        requests.post(
            TOOLS + "/tools/calculator", json={"expression": "2+2"}, timeout=10
        ).status_code
        == 200,
        f"result={requests.post(TOOLS+'/tools/calculator',json={'expression':'2+2'},timeout=10).json()}",
    ),
)

# ============ USERS/PERSONAS ============
print("\n=== 12. USERS & PERSONAS ===")

test(
    "List users",
    lambda: (
        requests.get(BASE + "/users", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/users',headers=h,timeout=10).json())}",
    ),
)
test(
    "List personas",
    lambda: (
        requests.get(BASE + "/personas", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/personas',headers=h,timeout=10).json())}",
    ),
)

# ============ GUARDRAILS ============
print("\n=== 13. GUARDRAILS ===")

test(
    "List guardrails",
    lambda: (
        requests.get(BASE + "/guardrails", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/guardrails',headers=h,timeout=10).json())}",
    ),
)

# ============ WORKSPACES ============
print("\n=== 14. WORKSPACES ===")

test(
    "List workspaces",
    lambda: (
        requests.get(BASE + "/workspaces", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/workspaces',headers=h,timeout=10).json())}",
    ),
)

# ============ MODELS ============
print("\n=== 15. LLM MODELS ===")

test(
    "List models",
    lambda: (
        requests.get(BASE + "/models", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/models',headers=h,timeout=10).json())}",
    ),
)

# ============ LLM ACTIVITY ============
print("\n=== 16. LLM ACTIVITY ===")

test(
    "LLM activity",
    lambda: (
        requests.get(BASE + "/llm-activity", headers=h, timeout=10).status_code == 200,
        f"count={len(requests.get(BASE+'/llm-activity',headers=h,timeout=10).json())}",
    ),
)

# ============ N8N WEBHOOK ============
print("\n=== 17. N8N WEBHOOK (may take 60-120s) ===")


def test_n8n_webhook():
    r = requests.post(
        N8N + "/webhook/agent-run",
        json={"prompt": "Say hello briefly", "sessionId": "n8n-e2e"},
        timeout=300,
    )
    if r.status_code == 200:
        return True, f"response={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("n8n webhook (agent-run)", test_n8n_webhook)

# ============ CLEANUP ============
print("\n=== 18. CLEANUP ===")

if test_agent_id:
    r = requests.delete(BASE + f"/agents/{test_agent_id}", headers=h, timeout=10)
    print(f"  Deleted test agent: {r.status_code}")

# ============ SUMMARY ============
print("\n" + "=" * 60)
print(
    f"RESULTS: {RESULTS['pass']} PASSED, {RESULTS['fail']} FAILED out of {RESULTS['pass']+RESULTS['fail']} tests"
)
print("=" * 60)

if RESULTS["fail"] > 0:
    print("\nFailed tests:")
    for name, status, msg in RESULTS["details"]:
        if status == "FAIL":
            print(f"  X {name}: {msg}")

print(
    "\nAll passed:"
    if RESULTS["fail"] == 0
    else f"\n{RESULTS['fail']} test(s) need attention."
)
