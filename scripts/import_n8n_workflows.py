"""Import n8n workflows and activate the agent-workflow."""

import glob
import json
import os

import requests

N8N_URL = "http://localhost:5678"

# Login
r = requests.post(
    f"{N8N_URL}/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
    timeout=10,
)
cookies = r.cookies
print(f"Login: {r.status_code}")

if r.status_code != 200:
    print("Login failed, exiting")
    exit(1)

# Import workflows from n8n/workflows/
wf_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "n8n", "workflows")
wf_files = sorted(glob.glob(os.path.join(wf_dir, "*.json")))
print(f"\nFound {len(wf_files)} workflow files")

imported = []
for wf_file in wf_files:
    name = os.path.basename(wf_file)
    with open(wf_file) as f:
        wf_data = json.load(f)

    wf_name = wf_data.get("name", name)

    # Remove id so n8n assigns a new one
    payload = {k: v for k, v in wf_data.items() if k != "id"}

    r = requests.post(
        f"{N8N_URL}/rest/workflows",
        cookies=cookies,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if r.status_code in [200, 201]:
        result = r.json()
        wid = result.get("id", result.get("data", {}).get("id", "?"))
        print(f"  Imported: {wf_name} (id={wid})")
        imported.append({"id": wid, "name": wf_name, "data": result})
    else:
        print(f"  Failed: {wf_name} - {r.status_code} {r.text[:150]}")

# Activate the agent-workflow
print("\n=== Activating workflows ===")
for wf in imported:
    wid = wf["id"]
    wf_name = wf["name"]
    r = requests.patch(
        f"{N8N_URL}/rest/workflows/{wid}",
        cookies=cookies,
        json={"active": True},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if r.status_code == 200:
        print(f"  Activated: {wf_name} (id={wid})")
    else:
        print(f"  Activate failed: {wf_name} - {r.status_code} {r.text[:150]}")

# Verify
print("\n=== Current workflows ===")
r = requests.get(f"{N8N_URL}/rest/workflows", cookies=cookies, timeout=10)
if r.status_code == 200:
    wfs = r.json().get("data", r.json())
    if isinstance(wfs, list):
        for w in wfs:
            status = "ACTIVE" if w.get("active") else "inactive"
            print(f"  {w.get('name')} [{status}] (id={w.get('id')})")
    else:
        print(f"  Unexpected: {str(wfs)[:200]}")
