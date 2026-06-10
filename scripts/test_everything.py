"""
Complete platform test: MCP, A2A, Pipelines, n8n webhook, Agent orchestration.
Tests all features with correct API signatures.
"""

import json
import sys
import time

import requests

BASE = "http://localhost:8010"
N8N_PROXY = "http://localhost:5679"
ADMIN_CREDS = {"username": "admin", "password": "Admin@Platform2026!"}
RESULTS = {"pass": 0, "fail": 0, "skip": 0, "details": []}


def test(name, fn):
    try:
        ok, msg = fn()
        status = "PASS" if ok else "FAIL"
        if ok:
            RESULTS["pass"] += 1
        else:
            RESULTS["fail"] += 1
        RESULTS["details"].append((name, status, msg))
        print(f"  [{status}] {name}: {msg}")
    except Exception as e:
        RESULTS["fail"] += 1
        RESULTS["details"].append((name, "FAIL", str(e)))
        print(f"  [FAIL] {name}: {e}")


# Auth is header-based (x-user-id, x-user-role), set by the UI proxy
h = {
    "x-user-id": "admin",
    "x-user-role": "admin",
    "x-workspace-id": "default",
    "Content-Type": "application/json",
}

# =============== SERVICE HEALTH ===============
print("\n=== 1. SERVICE HEALTH ===")


def test_agent_health():
    r = requests.get(BASE + "/health", timeout=5)
    return r.status_code == 200, f"status={r.status_code}"


def test_tools_health():
    r = requests.get("http://localhost:8011/health", timeout=5)
    return r.status_code == 200, f"status={r.status_code}"


def test_n8n_health():
    r = requests.get(N8N_PROXY + "/healthz", timeout=5)
    return r.status_code == 200, f"status={r.status_code}"


test("Agent service health", test_agent_health)
test("Tools service health", test_tools_health)
test("n8n health", test_n8n_health)

# =============== AUTH ===============
print("\n=== 2. AUTHENTICATION ===")


def test_login():
    r = requests.post(BASE + "/auth/login", json=ADMIN_CREDS, timeout=10)
    if r.status_code == 200:
        user = r.json()
        return True, f"user={user.get('username')}, role={user.get('role')}"
    return False, f"{r.status_code}: {r.text[:100]}"


test("Admin login", test_login)

# =============== AGENTS CRUD ===============
print("\n=== 3. AGENTS CRUD ===")

test_agent_id = None


def test_create_agent():
    global test_agent_id
    r = requests.post(
        BASE + "/agents",
        headers=h,
        json={
            "name": "E2E Test Agent",
            "description": "Test agent for comprehensive testing",
            "model": "llama3",
            "system_prompt": "You are a helpful test assistant. Always respond briefly.",
            "scope": "global",
        },
        timeout=10,
    )
    if r.status_code in [200, 201]:
        test_agent_id = r.json().get("id")
        return True, f"id={test_agent_id}"
    return False, f"{r.status_code}: {r.text[:100]}"


def test_list_agents():
    r = requests.get(BASE + "/agents", headers=h, timeout=10)
    agents = r.json() if r.status_code == 200 else []
    return r.status_code == 200 and len(agents) > 0, f"count={len(agents)}"


def test_get_agent():
    if not test_agent_id:
        return False, "no agent created"
    r = requests.get(BASE + f"/agents/{test_agent_id}", headers=h, timeout=10)
    return r.status_code == 200, f"name={r.json().get('name', '?')}"


test("Create agent", test_create_agent)
test("List agents", test_list_agents)
test("Get agent", test_get_agent)

# =============== AGENT ORCHESTRATION (RUN) ===============
print("\n=== 4. AGENT ORCHESTRATION ===")


def test_agent_run():
    r = requests.post(
        BASE + "/run",
        headers=h,
        json={
            "prompt": "What is 2+2? Answer with just the number.",
            "sessionId": "e2e-test-session",
        },
        timeout=120,
    )
    if r.status_code == 200:
        resp = r.json()
        output = str(resp.get("output", resp.get("response", "")))
        return len(output) > 0, f"output={output[:100]}"
    return False, f"{r.status_code}: {r.text[:100]}"


test("Agent run (orchestration)", test_agent_run)

# =============== MCP SERVERS ===============
print("\n=== 5. MCP SERVERS ===")

mcp_server_id = None
mcp_tool_name = None


def test_list_mcp():
    global mcp_server_id, mcp_tool_name
    r = requests.get(BASE + "/mcp/servers", headers=h, timeout=10)
    if r.status_code == 200:
        servers = r.json()
        if servers:
            mcp_server_id = servers[0].get("id")
            tools = servers[0].get("tools", [])
            if tools:
                mcp_tool_name = (
                    tools[0].get("name") if isinstance(tools[0], dict) else tools[0]
                )
        return True, f"count={len(servers)}, first_id={mcp_server_id}"
    return False, f"{r.status_code}"


def test_mcp_invoke():
    if not mcp_server_id or not mcp_tool_name:
        return False, "no MCP server/tool available"
    # tool_name is a QUERY parameter, arguments in body
    r = requests.post(
        BASE + f"/mcp/servers/{mcp_server_id}/invoke",
        params={"tool_name": mcp_tool_name},
        headers=h,
        json={"arguments": {"query": "test"}},
        timeout=30,
    )
    if r.status_code == 200:
        return True, f"response={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("List MCP servers", test_list_mcp)
test("MCP tool invoke", test_mcp_invoke)

# =============== A2A ===============
print("\n=== 6. A2A (Agent-to-Agent) ===")


def test_a2a_card():
    r = requests.get(BASE + "/a2a/card", headers=h, timeout=10)
    return r.status_code == 200, f"keys={list(r.json().keys())[:5]}"


def test_a2a_peers():
    r = requests.get(BASE + "/a2a/peers", headers=h, timeout=10)
    return (
        r.status_code == 200,
        f"count={len(r.json()) if isinstance(r.json(), list) else '?'}",
    )


def test_a2a_send():
    r = requests.post(
        BASE + "/a2a/send",
        headers=h,
        json={"peer_id": "self", "task": "What is 1+1?", "context": {}},
        timeout=30,
    )
    if r.status_code == 200:
        return True, f"response={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("A2A card", test_a2a_card)
test("A2A peers", test_a2a_peers)
test("A2A send task", test_a2a_send)

# =============== PIPELINES ===============
print("\n=== 7. PIPELINES ===")

pipeline_id = None


def test_list_pipelines():
    global pipeline_id
    r = requests.get(BASE + "/pipelines", headers=h, timeout=10)
    if r.status_code == 200:
        pipes = r.json()
        if pipes:
            pipeline_id = pipes[0].get("id")
        return True, f"count={len(pipes)}"
    return False, f"{r.status_code}"


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


def test_run_pipeline():
    if not pipeline_id:
        return False, "no pipeline"
    r = requests.post(
        BASE + f"/pipelines/{pipeline_id}/run",
        headers=h,
        json={
            "prompt": "What is the capital of France?",
            "session_id": "e2e-pipeline-test",
        },
        timeout=120,
    )
    if r.status_code == 200:
        return True, f"result={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("List pipelines", test_list_pipelines)
test("Create pipeline", test_create_pipeline)
test("Run pipeline", test_run_pipeline)

# =============== SKILLS CRUD ===============
print("\n=== 8. SKILLS ===")


def test_list_skills():
    r = requests.get(BASE + "/skills", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


def test_create_skill():
    r = requests.post(
        BASE + "/skills",
        headers=h,
        json={
            "name": "E2E Test Skill",
            "description": "Test skill",
            "content": "You are skilled at testing.",
            "scope": "global",
        },
        timeout=10,
    )
    return r.status_code in [200, 201], f"{r.status_code}"


test("List skills", test_list_skills)
test("Create skill", test_create_skill)

# =============== PROMPTS CRUD ===============
print("\n=== 9. PROMPTS ===")


def test_list_prompts():
    r = requests.get(BASE + "/prompts", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


def test_create_prompt():
    r = requests.post(
        BASE + "/prompts",
        headers=h,
        json={
            "name": "E2E Test Prompt",
            "content": "Test prompt template: {input}",
            "scope": "global",
        },
        timeout=10,
    )
    return r.status_code in [200, 201], f"{r.status_code}"


test("List prompts", test_list_prompts)
test("Create prompt", test_create_prompt)

# =============== DOCUMENTS/KB ===============
print("\n=== 10. DOCUMENTS & KB ===")


def test_collections():
    r = requests.get(BASE + "/collections", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


def test_documents():
    r = requests.get(BASE + "/documents", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


def test_kb_query():
    r = requests.post(
        BASE + "/kb/query",
        headers=h,
        json={"query": "test", "n_results": 3},
        timeout=15,
    )
    if r.status_code == 200:
        return True, f"results={str(r.json())[:100]}"
    return False, f"{r.status_code}"


test("List collections", test_collections)
test("List documents", test_documents)
test("KB query", test_kb_query)

# =============== TOOLS ===============
print("\n=== 11. TOOLS ===")


def test_list_tools():
    r = requests.get(BASE + "/tools", headers=h, timeout=10)
    if r.status_code == 200:
        tools = r.json()
        return True, f"count={len(tools)}"
    return False, f"{r.status_code}"


def test_tool_call():
    r = requests.post(
        "http://localhost:8011/tools/calculator", json={"expression": "2+2"}, timeout=10
    )
    if r.status_code == 200:
        return True, f"result={str(r.json())[:80]}"
    return False, f"{r.status_code}: {r.text[:100]}"


test("List tools", test_list_tools)
test("Tool direct call (calculator)", test_tool_call)

# =============== USERS & PERSONAS ===============
print("\n=== 12. USERS & PERSONAS ===")


def test_users():
    r = requests.get(BASE + "/users", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


def test_personas():
    r = requests.get(BASE + "/personas", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


test("List users", test_users)
test("List personas", test_personas)

# =============== GUARDRAILS ===============
print("\n=== 13. GUARDRAILS ===")


def test_guardrails():
    r = requests.get(BASE + "/guardrails", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


test("List guardrails", test_guardrails)

# =============== WORKSPACES ===============
print("\n=== 14. WORKSPACES ===")


def test_workspaces():
    r = requests.get(BASE + "/workspaces", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


test("List workspaces", test_workspaces)

# =============== LLM MODELS ===============
print("\n=== 15. LLM MODELS ===")


def test_models():
    r = requests.get(BASE + "/models", headers=h, timeout=10)
    if r.status_code == 200:
        models = r.json()
        return True, f"count={len(models)}"
    return False, f"{r.status_code}"


test("List models", test_models)

# =============== OBSERVABILITY ===============
print("\n=== 16. OBSERVABILITY ===")


def test_grafana():
    r = requests.get("http://localhost:3003/api/health", timeout=5)
    return r.status_code == 200, "healthy"


def test_prometheus():
    r = requests.get("http://localhost:9090/-/healthy", timeout=5)
    return r.status_code == 200, "healthy"


def test_langfuse():
    r = requests.get("http://localhost:3014", timeout=5)
    return r.status_code == 200, "reachable"


test("Grafana health", test_grafana)
test("Prometheus health", test_prometheus)
test("Langfuse reachable", test_langfuse)

# =============== N8N WEBHOOK ===============
print("\n=== 17. N8N WEBHOOK INTEGRATION ===")


def test_n8n_webhook():
    # Test the Agent Run Webhook workflow
    r = requests.post(
        N8N_PROXY + "/webhook/agent-run",
        json={"prompt": "Say hello", "sessionId": "n8n-test"},
        timeout=120,
    )
    if r.status_code == 200:
        return True, f"response={str(r.json())[:100]}"
    return False, f"{r.status_code}: {r.text[:200]}"


test("n8n webhook (agent-run)", test_n8n_webhook)

# =============== LLM ACTIVITY ===============
print("\n=== 18. LLM ACTIVITY ===")


def test_llm_activity():
    r = requests.get(BASE + "/llm-activity", headers=h, timeout=10)
    return r.status_code == 200, f"count={len(r.json())}"


test("LLM activity log", test_llm_activity)

# =============== CLEANUP ===============
print("\n=== 19. CLEANUP ===")


def test_delete_agent():
    if not test_agent_id:
        return True, "skipped"
    r = requests.delete(BASE + f"/agents/{test_agent_id}", headers=h, timeout=10)
    return r.status_code in [200, 204], f"{r.status_code}"


test("Delete test agent", test_delete_agent)

# =============== SUMMARY ===============
print("\n" + "=" * 60)
print(f"RESULTS: {RESULTS['pass']} PASSED, {RESULTS['fail']} FAILED")
print("=" * 60)

if RESULTS["fail"] > 0:
    print("\nFailed tests:")
    for name, status, msg in RESULTS["details"]:
        if status == "FAIL":
            print(f"  - {name}: {msg}")
