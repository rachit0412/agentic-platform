"""Check n8n webhook node version and fix if needed."""

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

# Get the Agent Run Webhook workflow
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
wfs = r.json().get("data", [])

for w in wfs:
    wid = w.get("id")
    wname = w.get("name")

    r2 = requests.get(
        N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
    )
    full = r2.json()
    nodes = full.get("nodes", [])

    print(wname + ":")
    for n in nodes:
        ntype = n.get("type", "?")
        nver = n.get("typeVersion", "?")
        nname = n.get("name", "?")
        print("  " + nname + ": type=" + str(ntype) + " v=" + str(nver))

# Check available node types
print("\nAvailable webhook types:")
r = requests.get(N8N_URL + "/rest/node-types", cookies=cookies, timeout=10)
if r.status_code == 200:
    types = r.json().get("data", [])
    for t in types:
        name = t.get("name", "")
        if "webhook" in name.lower() or "trigger" in name.lower():
            ver = t.get("version", "?")
            display = t.get("displayName", "")
            print("  " + name + " v" + str(ver) + " (" + display + ")")
else:
    print("  Failed: " + str(r.status_code))
