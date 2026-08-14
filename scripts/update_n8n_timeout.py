"""Update n8n Agent Run Webhook workflow - increase timeout to 300s"""

import json

import requests

BASE = "http://localhost:5679"
s = requests.Session()
s.post(
    f"{BASE}/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
)

# Get workflow
r = s.get(f"{BASE}/rest/workflows/8nJ6K4pZ3wUOrGR6")
wf = r.json().get("data", r.json())

# Update HTTP Request node timeout
for n in wf.get("nodes", []):
    if n.get("type") == "n8n-nodes-base.httpRequest":
        n["parameters"]["options"]["timeout"] = 300000  # 300 seconds
        print(f"Updated timeout to 300s for {n['name']}")

# Deactivate first
s.patch(f"{BASE}/rest/workflows/8nJ6K4pZ3wUOrGR6", json={"active": False})

# Update workflow
r = s.put(
    f"{BASE}/rest/workflows/8nJ6K4pZ3wUOrGR6",
    json={
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {}),
    },
)
print(f"Update: {r.status_code}")

# Reactivate
r = s.patch(f"{BASE}/rest/workflows/8nJ6K4pZ3wUOrGR6", json={"active": True})
print(f"Activate: {r.status_code}")
print("Done!")
