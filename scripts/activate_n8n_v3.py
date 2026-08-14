"""Activate n8n workflows using PATCH to update and get versionId."""

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

    # PATCH to update and get a versionId - send nodes and connections
    patch_payload = {
        "nodes": full_wf.get("nodes", []),
        "connections": full_wf.get("connections", {}),
    }
    r3 = requests.patch(
        N8N_URL + "/rest/workflows/" + str(wid),
        cookies=cookies,
        json=patch_payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if r3.status_code == 200:
        updated_data = r3.json()
        # Check nested data structure
        if "data" in updated_data and isinstance(updated_data["data"], dict):
            updated = updated_data["data"]
        else:
            updated = updated_data
        version_id = updated.get("versionId")
        print("  " + wname + ": patched, versionId=" + str(version_id))

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
            # Try activate anyway
            r4 = requests.post(
                N8N_URL + "/rest/workflows/" + str(wid) + "/activate",
                cookies=cookies,
                json={},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            print(
                "    Activate (no version): "
                + str(r4.status_code)
                + " "
                + r4.text[:150]
            )
    else:
        print(
            "  " + wname + ": patch failed " + str(r3.status_code) + " " + r3.text[:200]
        )

# Final status
print("\n=== Final Status ===")
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
for w in r.json().get("data", []):
    status = "ACTIVE" if w.get("active") else "inactive"
    print("  " + w.get("name", "?") + " [" + status + "]")
