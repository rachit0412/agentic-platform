import json
import uuid

import requests

h = {"x-user-role": "admin", "x-user-id": "admin", "Content-Type": "application/json"}
base = "http://localhost:8010"

passed = 0
failed = 0
errors = []


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK: {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  FAIL: {name} -- {detail}")


# ── MCP Tool Invocation ──
print("=== MCP TOOL INVOKE ===")

# Invoke via MCP discover
r = requests.get(f"{base}/mcp/servers", headers=h, timeout=10)
servers = r.json().get("servers", [])
test("MCP servers list", len(servers) >= 2, f"count={len(servers)}")

# Discover open-tools MCP
ot_server = next((s for s in servers if "open" in s.get("name", "").lower()), None)
if ot_server:
    sid = ot_server["id"]
    r = requests.post(f"{base}/mcp/servers/{sid}/discover", headers=h, timeout=15)
    discover = r.json()
    mcp_tools = discover.get("tools", [])
    test("Open Tools MCP discover", len(mcp_tools) > 0, f"tools={len(mcp_tools)}")
    tool_names = [t["name"] for t in mcp_tools]
    print(f"    Available: {tool_names}")

    # Invoke a tool
    r = requests.post(
        f"{base}/mcp/servers/{sid}/invoke",
        headers=h,
        json={
            "tool": "wikipedia_search",
            "arguments": {"query": "Python programming language"},
        },
        timeout=30,
    )
    test(
        "MCP invoke wikipedia_search",
        r.status_code == 200,
        f"status={r.status_code} body={r.text[:200]}",
    )
    if r.status_code == 200:
        result = r.json()
        print(f"    Result keys: {list(result.keys())}")
        content = result.get("content", result.get("result", str(result)))
        print(f"    Content preview: {str(content)[:150]}")

# Discover brave-search MCP
bs_server = next((s for s in servers if "brave" in s.get("name", "").lower()), None)
if bs_server:
    sid = bs_server["id"]
    r = requests.post(f"{base}/mcp/servers/{sid}/discover", headers=h, timeout=15)
    discover = r.json()
    test("Brave Search MCP discover", r.status_code == 200)
    mcp_tools = discover.get("tools", [])
    if mcp_tools:
        print(f"    Tools: {[t['name'] for t in mcp_tools]}")

# ── A2A Protocol ──
print("\n=== A2A PROTOCOL ===")
r = requests.get(f"{base}/a2a/card", headers=h, timeout=10)
card = r.json()
test("A2A card", r.status_code == 200 and card.get("name"))
print(f"    Card: name={card.get('name')}, version={card.get('version')}")
print(f"    Capabilities: {card.get('capabilities', {})}")

# A2A send (to self or test)
r = requests.post(
    f"{base}/a2a/send",
    headers=h,
    json={"peer_id": "", "message": "What is 2 plus 2? Answer with just the number."},
    timeout=60,
)
test(
    "A2A send (local)",
    r.status_code == 200,
    f"status={r.status_code} body={r.text[:300]}",
)
if r.status_code == 200:
    print(f"    Response: {str(r.json())[:200]}")

# A2A peer management
r = requests.post(
    f"{base}/a2a/peers",
    headers=h,
    json={
        "name": "Test Peer",
        "url": "http://localhost:8010",
        "description": "Self-reference for testing",
    },
    timeout=10,
)
test(
    "A2A add peer",
    r.status_code == 200 or r.status_code == 201,
    f"status={r.status_code} body={r.text[:200]}",
)
if r.status_code in [200, 201]:
    peer = r.json()
    peer_id = peer.get("id", peer.get("peer_id", ""))
    print(f"    Peer ID: {peer_id}")

    # Ping peer
    if peer_id:
        r = requests.post(f"{base}/a2a/peers/{peer_id}/ping", headers=h, timeout=10)
        test("A2A ping peer", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            print(f"    Ping: {r.json()}")

        # Send to peer
        r = requests.post(
            f"{base}/a2a/send",
            headers=h,
            json={"peer_id": peer_id, "message": "Hello from A2A test"},
            timeout=60,
        )
        test(
            "A2A send to peer",
            r.status_code == 200,
            f"status={r.status_code} body={r.text[:200]}",
        )
        if r.status_code == 200:
            print(f"    Response: {str(r.json())[:200]}")

        # Cleanup
        requests.delete(f"{base}/a2a/peers/{peer_id}", headers=h, timeout=10)

# ── N8N Integration ──
print("\n=== N8N INTEGRATION ===")
# N8N agents endpoint
r = requests.get(f"{base}/n8n/agents", headers=h, timeout=10)
test("N8N agents", r.status_code == 200)
n8n_agents = r.json().get("agents", [])
print(f"    Agents: {len(n8n_agents)}")
for a in n8n_agents[:3]:
    print(f"      - {a.get('name')}: {a.get('run_url','?')}")

# Test agent run via n8n webhook proxy
# n8n-proxy is at port 5679 and proxies to agent-service
r = requests.post(
    "http://localhost:5679/webhook/agent-run",
    headers=h,
    json={
        "prompt": "What is 3+3? Answer with just the number.",
        "session_id": f"n8n-test-{uuid.uuid4().hex[:6]}",
    },
    timeout=60,
)
test(
    "N8N proxy agent-run",
    r.status_code == 200,
    f"status={r.status_code} body={r.text[:200]}",
)
if r.status_code == 200:
    print(f"    Response: {str(r.json())[:200]}")

# ── Pipelines ──
print("\n=== PIPELINES ===")
# Create a simple pipeline
r = requests.post(
    f"{base}/pipelines",
    headers=h,
    json={
        "name": f"Test Pipeline {uuid.uuid4().hex[:6]}",
        "description": "Automated test pipeline",
        "steps": [{"name": "step1", "prompt": "What is AI?", "agent_id": ""}],
    },
)
test(
    "Create pipeline",
    r.status_code == 200,
    f"status={r.status_code} body={r.text[:200]}",
)
if r.status_code == 200:
    pipeline = r.json()
    pid = pipeline.get("id", "")
    print(f"    Pipeline ID: {pid}")

    # Run pipeline
    if pid:
        r = requests.post(f"{base}/pipelines/{pid}/run", headers=h, json={}, timeout=90)
        test(
            "Run pipeline",
            r.status_code == 200,
            f"status={r.status_code} body={r.text[:300]}",
        )
        if r.status_code == 200:
            print(f"    Run result: {str(r.json())[:200]}")

        # List runs
        r = requests.get(f"{base}/pipelines/{pid}/runs", headers=h, timeout=10)
        test("Pipeline runs", r.status_code == 200)

        # Cleanup
        requests.delete(f"{base}/pipelines/{pid}", headers=h)

# ── Agent with Tools ──
print("\n=== AGENT WITH TOOLS ===")
r = requests.post(
    f"{base}/agents",
    headers=h,
    json={
        "name": f"Math Agent {uuid.uuid4().hex[:6]}",
        "description": "Agent that uses math tool",
        "system_prompt": "You are a math assistant. Use the math tool for calculations.",
        "scope": "global",
        "tools": ["math"],
        "model": "",
    },
)
test("Create agent with tools", r.status_code == 200, f"status={r.status_code}")
agent = r.json()
aid = agent.get("id", "")

if aid:
    # Run with tool use
    r = requests.post(
        f"{base}/run",
        headers=h,
        json={
            "prompt": "Calculate 15 * 23 using the math tool",
            "agent_id": aid,
            "session_id": f"tool-test-{uuid.uuid4().hex[:6]}",
            "use_kb": False,
        },
        timeout=60,
    )
    test("Agent run with tools", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        result = r.json()
        print(f"    Response: {result.get('response', '?')[:150]}")
        print(f"    Tools used: {result.get('tools_used', [])}")

    requests.delete(f"{base}/agents/{aid}", headers=h)

# ── Summary ──
print(f"\n{'='*50}")
print(f"  PASSED: {passed}")
print(f"  FAILED: {failed}")
if errors:
    print(f"  ERRORS:")
    for e in errors:
        print(f"    - {e}")
