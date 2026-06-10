"""Fix n8n activation - need to include versionId."""

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

    # Get full workflow with versionId
    r2 = requests.get(
        N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
    )
    full_wf = r2.json()
    version_id = full_wf.get("versionId")
    active = full_wf.get("active", False)

    print(
        "  " + wname + " (version=" + str(version_id) + ", active=" + str(active) + ")"
    )

    if not active:
        # Activate with versionId
        r3 = requests.post(
            N8N_URL + "/rest/workflows/" + str(wid) + "/activate",
            cookies=cookies,
            json={"versionId": version_id},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print("    Activate: " + str(r3.status_code) + " " + r3.text[:200])

        # Verify
        r4 = requests.get(
            N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
        )
        print("    Final active: " + str(r4.json().get("active")))
