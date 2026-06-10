import json
import uuid

import requests

h = {"x-user-role": "admin", "x-user-id": "admin", "Content-Type": "application/json"}
base = "http://localhost:8010"

print("=== SESSIONS ===")
r = requests.get(f"{base}/sessions", headers=h, timeout=10)
data = r.json()
count = len(data) if isinstance(data, list) else len(data.get("sessions", []))
print(f"  /sessions: {r.status_code}, count={count}")

print("\n=== DOCUMENTS/KB ===")
for ep in ["/documents", "/documents/stats", "/documents/collections"]:
    r = requests.get(f"{base}{ep}", headers=h, timeout=10)
    print(f"  {ep}: {r.status_code} {str(r.json())[:150]}")

print("\n=== MCP ===")
r = requests.get(f"{base}/mcp/servers", headers=h, timeout=10)
result = r.json()
servers = result.get("servers", result) if isinstance(result, dict) else result
print(
    f"  /mcp/servers: {r.status_code}, count={len(servers) if isinstance(servers, list) else 'N/A'}"
)
if isinstance(servers, list):
    for s in servers[:5]:
        nm = s.get("name", "?")
        tp = s.get("type", "?")
        st = s.get("status", "?")
        print(f"    - {nm} ({tp}): {st}")

print("\n=== A2A ===")
r = requests.get(f"{base}/a2a/card", headers=h, timeout=10)
print(f"  /a2a/card: {r.status_code}")
if r.status_code == 200:
    card = r.json()
    print(f"    name={card.get('name')}")
    print(f"    skills={card.get('skills')}")

r = requests.get(f"{base}/a2a/peers", headers=h, timeout=10)
print(f"  /a2a/peers: {r.status_code}")
peers = r.json() if r.status_code == 200 else {}
peer_list = peers.get("peers", peers) if isinstance(peers, dict) else peers
print(f"    count={len(peer_list) if isinstance(peer_list, list) else 'N/A'}")

print("\n=== N8N ===")
r = requests.get(f"{base}/n8n/agents", headers=h, timeout=10)
print(f"  /n8n/agents: {r.status_code} {str(r.json())[:200]}")

print("\n=== TOOLS SERVICE (8011) ===")
r = requests.get("http://localhost:8011/openapi.json", timeout=5)
if r.status_code == 200:
    paths = list(r.json().get("paths", {}).keys())
    print(f"  Routes: {paths}")
else:
    print(f"  openapi: {r.status_code}")

# MCP discover
if isinstance(servers, list) and len(servers) > 0:
    sid = servers[0].get("id", "")
    if sid:
        print(f"\n=== MCP DISCOVER: {sid} ===")
        r = requests.post(f"{base}/mcp/servers/{sid}/discover", headers=h, timeout=15)
        print(f"  discover: {r.status_code} {str(r.json())[:300]}")
