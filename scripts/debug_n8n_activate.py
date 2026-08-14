"""Debug n8n workflow activation."""

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

for w in wfs[:1]:
    wid = w.get("id")
    wname = w.get("name")
    print("Attempting to activate: " + wname + " (id=" + str(wid) + ")")

    # Get full workflow
    r2 = requests.get(
        N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
    )
    full_wf = r2.json()
    print("  Current active state: " + str(full_wf.get("active")))

    # Try PATCH with active: true
    r3 = requests.patch(
        N8N_URL + "/rest/workflows/" + str(wid),
        cookies=cookies,
        json={"active": True},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    print("  PATCH response: " + str(r3.status_code))
    resp_data = r3.json()
    print("  Active after PATCH: " + str(resp_data.get("active")))
    print("  Response keys: " + str(list(resp_data.keys())))

    # Try the activate endpoint if PATCH doesn't work
    r4 = requests.post(
        N8N_URL + "/rest/workflows/" + str(wid) + "/activate",
        cookies=cookies,
        timeout=10,
    )
    print("  POST /activate: " + str(r4.status_code) + " " + r4.text[:200])

    # Verify
    r5 = requests.get(
        N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
    )
    print("  Final active: " + str(r5.json().get("active")))
