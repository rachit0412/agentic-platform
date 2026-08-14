"""Delete inactive duplicate n8n workflows."""

import requests

N8N_URL = "http://localhost:5678"

# Login
r = requests.post(
    N8N_URL + "/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
    timeout=10,
)
cookies = r.cookies

# Get all workflows
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
wfs = r.json().get("data", [])

# Delete inactive ones
for w in wfs:
    if not w.get("active"):
        wid = w.get("id")
        wname = w.get("name")
        # Try DELETE
        r2 = requests.delete(
            N8N_URL + "/rest/workflows/" + str(wid), cookies=cookies, timeout=10
        )
        print("Delete " + wname + " (" + str(wid) + "): " + str(r2.status_code))

# Final status
print("\n=== Final Status ===")
r = requests.get(N8N_URL + "/rest/workflows", cookies=cookies, timeout=10)
for w in r.json().get("data", []):
    status = "ACTIVE" if w.get("active") else "inactive"
    print("  " + w.get("name", "?") + " [" + status + "]")
