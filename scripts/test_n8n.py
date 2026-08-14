import json

import requests

# Login first
r = requests.post(
    "http://localhost:5678/rest/login",
    json={"emailOrLdapLoginId": "admin@local.dev", "password": "Changeme1!"},
    timeout=10,
)
cookies = r.cookies
print(f"n8n login: {r.status_code}")

# Use REST API with session cookie
r2 = requests.get("http://localhost:5678/rest/workflows", cookies=cookies, timeout=10)
print(f"REST workflows: {r2.status_code}")
if r2.status_code == 200:
    data = r2.json()
    wfs = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(wfs, list):
        print(f"Count: {len(wfs)}")
        for w in wfs[:10]:
            name = w.get("name", "?")
            wid = w.get("id")
            active = w.get("active")
            print(f"  - {name} (id={wid}, active={active})")
    else:
        print(f"Data: {str(data)[:300]}")
else:
    print(r2.text[:300])

# Check if agent-workflow has a webhook trigger
if r2.status_code == 200 and isinstance(wfs, list):
    for w in wfs:
        name = w.get("name", "")
        if "agent" in name.lower():
            # Get full workflow details
            wid = w.get("id")
            r3 = requests.get(
                f"http://localhost:5678/rest/workflows/{wid}",
                cookies=cookies,
                timeout=10,
            )
            if r3.status_code == 200:
                wf = r3.json()
                nodes = wf.get("nodes", wf.get("data", {}).get("nodes", []))
                print(f"\n  Workflow '{name}' nodes:")
                for n in nodes[:10]:
                    ntype = n.get("type", "?")
                    nname = n.get("name", "?")
                    print(f"    Node: {nname} ({ntype})")

# Try to create an API key
print("\n=== Generating n8n API Key ===")
r4 = requests.post(
    "http://localhost:5678/rest/api-keys",
    cookies=cookies,
    json={"label": "agentic-platform"},
    timeout=10,
)
print(f"Create API key: {r4.status_code}")
if r4.status_code in [200, 201]:
    key_data = r4.json()
    api_key = key_data.get("apiKey", key_data.get("data", {}).get("apiKey", ""))
    print(
        f"API Key: {api_key[:20]}..." if api_key else f"Response: {str(key_data)[:200]}"
    )
else:
    print(f"Response: {r4.text[:200]}")
