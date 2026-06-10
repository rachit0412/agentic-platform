"""Activate n8n workflows by updating them first to get a versionId."""

import json

import requests

N8N_URL = "http://localhost:5678"

# Login
r = requests.post(
    N8N_URL + "/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
    timeout=10,
)
cookies = r.cookies

# List workflows
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
wfs = r.json().get("data", [])
print("Workflows: " + str(len(wfs)))

for w in wfs:
    wid = w.get("id")
    wname = w.get("name")

    # Get full workflow
    r2 = requests.get(
        N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
    )
    full_wf = r2.json()

    # Update workflow (PUT) to get a versionId
    update_payload = {
        "name": full_wf.get("name"),
        "nodes": full_wf.get("nodes", []),
        "connections": full_wf.get("connections", {}),
        "settings": full_wf.get("settings", {}),
    }
    r3 = requests.put(
        N8N_URL + "/rest/workflows/" + str(wid),
        cookies=cookies,
        json=update_payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if r3.status_code == 200:
        updated = r3.json()
        version_id = updated.get("versionId")
        print("  " + wname + ": updated, versionId=" + str(version_id))

        if version_id:
            # Now activate
            r4 = requests.post(
                N8N_URL + "/rest/workflows/" + str(wid) + "/activate",
                cookies=cookies,
                json={"versionId": version_id},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if r4.status_code == 200:
                print("    ACTIVATED!")
            else:
                print(
                    "    Activate failed: " + str(r4.status_code) + " " + r4.text[:200]
                )
    else:
        print(
            "  "
            + wname
            + ": update failed "
            + str(r3.status_code)
            + " "
            + r3.text[:200]
        )

# Final status
print("\n=== Final Status ===")
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
for w in r.json().get("data", []):
    status = "ACTIVE" if w.get("active") else "inactive"
    print("  " + w.get("name", "?") + " [" + status + "]")
