"""Test all 35 tools — 29 proxy (tools-service) + 6 in-process (agent-service)."""

import json
import os

import httpx

TOOLS_BASE = os.environ.get("TOOLS_BASE", "http://localhost:8001")
AGENT_BASE = os.environ.get("AGENT_BASE", "http://localhost:8000")

tests = [
    ("math", "/tools/math", {"expression": "2+2"}),
    ("http_fetch", "/tools/http-fetch", {"url": "https://example.com"}),
    (
        "file_write",
        "/tools/file-write",
        {"filename": "test-run.txt", "content": "hello world"},
    ),
    ("file_read", "/tools/file-read", {"filename": "test-run.txt"}),
    ("file_list", "/tools/file-list", {"directory": ".", "pattern": "*"}),
    ("file_search_content", "/tools/file-search-content", {"query": "hello"}),
    ("datetime_tool", "/tools/datetime", {}),
    ("web_search", "/tools/web-search", {"query": "python programming"}),
    (
        "code_execute",
        "/tools/code-execute",
        {"language": "python", "code": "print(1+1)"},
    ),
    (
        "text_summarize",
        "/tools/text-summarize",
        {
            "text": "The quick brown fox jumps over the lazy dog. This is a longer test. Multiple sentences here."
        },
    ),
    (
        "text_transform",
        "/tools/text-transform",
        {"text": "hello world", "operation": "uppercase"},
    ),
    (
        "text_diff",
        "/tools/text-diff",
        {"text_a": "hello world", "text_b": "hello there"},
    ),
    (
        "text_extract",
        "/tools/text-extract",
        {"text": "email test@example.com phone 555-1234", "extract_type": "emails"},
    ),
    (
        "json_transform",
        "/tools/json-transform",
        {"data": '{"a":1,"b":2}', "operation": "keys"},
    ),
    ("csv_parse", "/tools/csv-parse", {"csv_text": "a,b\n1,2\n3,4"}),
    (
        "yaml_convert",
        "/tools/yaml-convert",
        {"content": '{"key":"value"}', "direction": "json_to_yaml"},
    ),
    ("base64_codec", "/tools/base64-codec", {"text": "hello", "operation": "encode"}),
    ("hash_generate", "/tools/hash-generate", {"text": "hello", "algorithm": "sha256"}),
    ("uuid_generate", "/tools/uuid-generate", {}),
    (
        "regex_match",
        "/tools/regex-match",
        {"text": "hello world 123", "pattern": "[0-9]+"},
    ),
    ("url_parse", "/tools/url-parse", {"url": "https://example.com/path?q=1"}),
    ("html_strip", "/tools/html-strip", {"html": "<p>Hello <b>World</b></p>"}),
    ("markdown_to_html", "/tools/markdown-to-html", {"markdown": "# Hello"}),
    ("webpage_extract", "/tools/webpage-extract", {"url": "https://example.com"}),
    ("dns_lookup", "/tools/dns-lookup", {"hostname": "google.com"}),
    (
        "json_schema_validate",
        "/tools/json-schema-validate",
        {
            "data": '{"name":"test"}',
            "schema_def": '{"type":"object","properties":{"name":{"type":"string"}}}',
        },
    ),
    ("cron_parse", "/tools/cron-parse", {"expression": "0 9 * * 1"}),
    (
        "jwt_decode",
        "/tools/jwt-decode",
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        },
    ),
    ("environment_info", "/tools/environment-info", {}),
]

results = []
for name, path, payload in tests:
    try:
        r = httpx.post(TOOLS_BASE + path, json=payload, timeout=15)
        status = "PASS" if r.status_code == 200 else "FAIL"
        detail = ""
        if r.status_code != 200:
            detail = r.text[:100]
        else:
            d = r.json()
            if d.get("note"):
                detail = "(fallback: DuckDuckGo)"
        results.append((name, status, r.status_code, detail))
    except Exception as e:
        results.append((name, "ERROR", 0, str(e)[:80]))

for name, status, code, detail in results:
    print(f"{name:<25} {status:<6} {code:<5} {detail}")

passes = sum(1 for _, s, _, _ in results if s == "PASS")
fails = sum(1 for _, s, _, _ in results if s != "PASS")
print(f"\nProxy Tools: {len(results)} | Pass: {passes} | Fail: {fails}")

# ── In-process tools (via agent /run endpoint) ──────────────────
print("\n--- In-process tools (via agent) ---")
in_process_tests = [
    ("vector_store", "Use vector_store to store text: test document for tool validation, with source: test-suite"),
    ("vector_search", "Use vector_search to find documents about tool validation with k=2"),
    ("advanced_search", "Use advanced_search to search for tool validation with mode hybrid and k=2"),
    ("delegate_to_agent", "Use delegate_to_agent to delegate task: say hello, to agent_id: default"),
    ("query_database", "Use query_database to list all tables using connection_string sqlite:///data/agent.db"),
    ("query_csv_data", "Use query_csv_data to count rows in file /tmp/test.csv"),
]

in_results = []
for name, prompt in in_process_tests:
    try:
        r = httpx.post(
            AGENT_BASE + "/run",
            json={"prompt": prompt, "workspace_id": "test-tools"},
            headers={"x-user-id": "admin", "x-user-role": "admin"},
            timeout=60,
        )
        resp = r.json().get("response", "")[:100]
        status = "PASS" if r.status_code == 200 else "FAIL"
        in_results.append((name, status, r.status_code, resp[:60]))
    except Exception as e:
        in_results.append((name, "ERROR", 0, str(e)[:60]))

for name, status, code, detail in in_results:
    print(f"{name:<25} {status:<6} {code:<5} {detail}")

ip_pass = sum(1 for _, s, _, _ in in_results if s == "PASS")
ip_fail = sum(1 for _, s, _, _ in in_results if s != "PASS")
print(f"\nIn-process Tools: {len(in_results)} | Pass: {ip_pass} | Fail: {ip_fail}")
print(f"\n{'='*50}")
print(f"TOTAL: {len(results) + len(in_results)} | Pass: {passes + ip_pass} | Fail: {fails + ip_fail}")
