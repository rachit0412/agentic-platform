"""Delete all n8n workflows and re-import from JSON files."""

import glob
import json
import os

import requests

N8N_URL = "http://localhost:5678"
WF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "n8n", "workflows"
)

# Login
r = requests.post(
    N8N_URL + "/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
    timeout=10,
)
cookies = r.cookies
print("Login: " + str(r.status_code))

# Delete all existing workflows
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
wfs = r.json().get("data", [])
for w in wfs:
    wid = w.get("id")
    wname = w.get("name")
    r2 = requests.delete(
        N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
    )
    print("Deleted: " + wname + " -> " + str(r2.status_code))

# Re-import each workflow JSON
for fn in sorted(os.listdir(WF_DIR)):
    if not fn.endswith(".json"):
        continue
    fp = os.path.join(WF_DIR, fn)
    with open(fp) as f:
        wf_data = json.load(f)

    wf_name = wf_data.get("name", fn)
    nodes = wf_data.get("nodes", [])
    connections = wf_data.get("connections", {})

    print("\nImporting " + wf_name + " (" + str(len(nodes)) + " nodes)")
    for n in nodes:
        print("  Node: " + n.get("name", "?") + " type=" + n.get("type", "?"))

    # Build proper import payload (exclude id to let n8n assign one)
    payload = {
        "name": wf_name,
        "nodes": nodes,
        "connections": connections,
        "settings": wf_data.get("settings", {}),
        "active": False,
    }
    if "tags" in wf_data:
        payload["tags"] = wf_data["tags"]

    r3 = requests.post(
        N8N_URL + "/rest/workflows",
        cookies=cookies,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if r3.status_code in [200, 201]:
        result = r3.json()
        if isinstance(result, dict) and "data" in result:
            result = result["data"]
        new_id = result.get("id", "?")
        new_nodes = result.get("nodes", [])
        version = result.get("versionId", None)
        print(
            "  Imported: id="
            + str(new_id)
            + ", nodes="
            + str(len(new_nodes))
            + ", version="
            + str(version)
        )

        # Try to activate if it has trigger nodes
        has_trigger = any(
            "webhook" in n.get("type", "").lower()
            or "trigger" in n.get("type", "").lower()
            or "schedule" in n.get("type", "").lower()
            or "cron" in n.get("type", "").lower()
            for n in nodes
        )

        if has_trigger and version:
            r4 = requests.post(
                N8N_URL + "/rest/workflows/" + str(new_id) + "/activate",
                cookies=cookies,
                json={"versionId": version},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if r4.status_code == 200:
                print("  ACTIVATED!")
            else:
                print("  Activation: " + str(r4.status_code) + " " + r4.text[:150])
    else:
        print("  Failed: " + str(r3.status_code) + " " + r3.text[:300])

# Final status
print("\n=== Final Status ===")
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
for w in r.json().get("data", []):
    status = "ACTIVE" if w.get("active") else "inactive"
    n_nodes = len(w.get("nodes", []))
    print("  " + w.get("name", "?") + " [" + status + "] nodes=" + str(n_nodes))
