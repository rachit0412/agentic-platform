"""
API Connector — Pull data from REST API endpoints.

Supports GET/POST with custom headers and body.
Extracts text from JSON response using a dot-notation path.
"""

import logging
import json
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def pull_api(config: dict) -> list[dict]:
    """
    Fetch data from a REST API and convert response items into documents.
    Returns list of {"name": str, "content": str, "metadata": dict}
    """
    url = config["url"]
    method = config.get("method", "GET").upper()
    headers = _parse_json_field(config.get("headers", ""))
    body = _parse_json_field(config.get("body", ""))
    response_path = config.get("response_path", "")
    text_field = config["text_field"]
    name_field = config.get("name_field", "")

    response = _make_request(url, method, headers, body)

    # Navigate to the data array using dot-path
    data = response
    if response_path:
        for key in response_path.split("."):
            if isinstance(data, dict):
                data = data.get(key, [])
            elif isinstance(data, list) and key.isdigit():
                data = data[int(key)]
            else:
                data = []
                break

    # Normalize to list
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        data = [{"content": str(data)}]

    documents = []
    for i, item in enumerate(data):
        if isinstance(item, dict):
            content = str(item.get(text_field, ""))
            name = str(item.get(name_field, "")) if name_field else f"item_{i+1}"
        else:
            content = str(item)
            name = f"item_{i+1}"

        if not content.strip():
            continue

        documents.append({
            "name": name,
            "content": content,
            "metadata": {"source_url": url, "index": i},
        })

    logger.info(f"API connector pulled {len(documents)} documents from {url}")
    return documents


def test_connection(config: dict) -> dict:
    """Test API connectivity with a HEAD or small GET."""
    try:
        url = config["url"]
        method = config.get("method", "GET").upper()
        headers = _parse_json_field(config.get("headers", ""))

        with httpx.Client(timeout=10, follow_redirects=True) as client:
            if method == "GET":
                r = client.head(url, headers=headers)
            else:
                r = client.options(url, headers=headers)

        if r.status_code < 400:
            return {"ok": True, "message": f"API reachable: HTTP {r.status_code}"}
        else:
            return {"ok": False, "message": f"API returned HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _make_request(url: str, method: str, headers: dict, body: Optional[dict]) -> any:
    """Execute the HTTP request and return parsed JSON."""
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        if method == "POST":
            r = client.post(url, headers=headers, json=body)
        else:
            r = client.get(url, headers=headers)

    r.raise_for_status()
    return r.json()


def _parse_json_field(value: str) -> dict:
    """Parse a JSON string field, return empty dict if invalid."""
    if not value or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
