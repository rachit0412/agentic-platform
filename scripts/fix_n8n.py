"""Fix n8n workflow tags format and re-import + activate."""

import json
import os

import requests

WF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "n8n", "workflows")
N8N_URL = "http://localhost:5678"

# Fix tags format
for fn in os.listdir(WF_DIR):
    if not fn.endswith(".json"):
        continue
    fp = os.path.join(WF_DIR, fn)
    with open(fp) as f:
        data = json.load(f)
    tags = data.get("tags", [])
    if tags and isinstance(tags[0], dict):
        data["tags"] = [
            t.get("name", str(t)) if isinstance(t, dict) else t for t in tags
        ]
        with open(fp, "w") as f:
            json.dump(data, f, indent=2)
        print("Fixed tags in " + fn + ": " + str(data["tags"]))

# Login
r = requests.post(
    N8N_URL + "/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
    timeout=10,
)
cookies = r.cookies
if r.status_code != 200:
    print("Login failed")
    exit(1)

# Get existing workflows
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
existing = r.json().get("data", []) if r.status_code == 200 else []
existing_names = {w.get("name") for w in existing}

# Import missing workflows
for fn in sorted(os.listdir(WF_DIR)):
    if not fn.endswith(".json"):
        continue
    fp = os.path.join(WF_DIR, fn)
    with open(fp) as f:
        wf_data = json.load(f)
    wf_name = wf_data.get("name", fn)
    if wf_name in existing_names:
        print("Already exists: " + wf_name)
        continue
    payload = {k: v for k, v in wf_data.items() if k != "id"}
    r = requests.post(
        N8N_URL + "/rest/workflows",
        cookies=cookies,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code in [200, 201]:
        result = r.json()
        wid = result.get("id", "?")
        print("Imported: " + wf_name + " (id=" + str(wid) + ")")
    else:
        print("Failed: " + wf_name + " - " + str(r.status_code) + " " + r.text[:200])

# Re-list and activate ALL
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
all_wfs = r.json().get("data", []) if r.status_code == 200 else []

for w in all_wfs:
    wid = w.get("id")
    wname = w.get("name")
    if not w.get("active"):
        r = requests.patch(
            N8N_URL + "/rest/workflows/" + str(wid),
            cookies=cookies,
            json={"active": True},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        status = (
            "ACTIVATED"
            if r.status_code == 200
            else "FAILED " + str(r.status_code) + " " + r.text[:100]
        )
        print("  " + wname + ": " + status)
    else:
        print("  " + wname + ": already active")

# Final list
print("\n=== Final Workflow Status ===")
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
for w in r.json().get("data", []):
    status = "ACTIVE" if w.get("active") else "inactive"
    print("  " + w.get("name", "?") + " [" + status + "]")
