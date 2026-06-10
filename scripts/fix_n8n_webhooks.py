"""Fix n8n workflow activation - check and reactivate webhooks"""

import json
import sys

import requests

BASE = "http://localhost:5679"
s = requests.Session()
login = s.post(
    f"{BASE}/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
)
if login.status_code != 200:
    print(f"Login failed: {login.status_code}")
    sys.exit(1)

# Get all workflows
r = s.get(f"{BASE}/rest/workflows")
data = r.json()
wfs = data.get("data", data) if isinstance(data, dict) else data

print("=== ALL WORKFLOWS ===")
for w in wfs:
    wid = w["id"]
    name = w["name"]
    active = w.get("active", False)
    print(f"  {wid}  active={active}  {name}")

# Check active Agent Run Webhook
print("\n=== CHECKING AGENT RUN WEBHOOK ===")
active_webhooks = [w for w in wfs if w.get("active") and "Agent Run" in w["name"]]

for w in active_webhooks:
    wid = w["id"]
    print(f"\nWorkflow {wid}: {w['name']}")

    # Get full workflow
    r2 = s.get(f"{BASE}/rest/workflows/{wid}")
    full = r2.json()
    if isinstance(full, dict) and "data" in full:
        full = full["data"]

    nodes = full.get("nodes", [])
    print(f"  Nodes: {len(nodes)}")
    for n in nodes:
        ntype = n.get("type", "?")
        params = n.get("parameters", {})
        path = params.get("path", "")
        print(f"    type={ntype}  path={path}")

    # Try to deactivate and reactivate
    print(f"\n  Deactivating {wid}...")
    s.patch(f"{BASE}/rest/workflows/{wid}", json={"active": False})

    print(f"  Reactivating {wid}...")
    r3 = s.patch(f"{BASE}/rest/workflows/{wid}", json={"active": True})
    print(f"  Result: {r3.status_code} {r3.text[:200]}")

# Also try to fix and activate the OLD webhook workflow that has proper nodes
print("\n=== CHECKING OLD WEBHOOK WORKFLOWS ===")
inactive_webhooks = [w for w in wfs if not w.get("active") and "Agent Run" in w["name"]]
for w in inactive_webhooks:
    wid = w["id"]
    r2 = s.get(f"{BASE}/rest/workflows/{wid}")
    full = r2.json()
    if isinstance(full, dict) and "data" in full:
        full = full["data"]
    nodes = full.get("nodes", [])
    print(f"\n  Workflow {wid}: {w['name']}, nodes={len(nodes)}")
    for n in nodes:
        ntype = n.get("type", "?")
        path = n.get("parameters", {}).get("path", "")
        print(f"    type={ntype}  path={path}")

# Test the webhook
print("\n=== TESTING WEBHOOK ===")
try:
    r = requests.post(
        f"{BASE}/webhook/agent-run",
        json={"prompt": "test", "sessionId": "test"},
        timeout=10,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

try:
    r = requests.post(
        f"{BASE}/webhook-test/agent-run",
        json={"prompt": "test", "sessionId": "test"},
        timeout=10,
    )
    print(f"  Test webhook: {r.status_code} {r.text[:200]}")
except Exception as e:
    print(f"  Test webhook error: {e}")
