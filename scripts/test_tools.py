#!/usr/bin/env python3
"""Test every tool in tools-service and report results."""

import json
import sys

import httpx

BASE = "http://localhost:8001"

TESTS = [
    ("math", "/tools/math", {"expression": "2+2*3"}),
    ("http_fetch", "/tools/http-fetch", {"url": "https://httpbin.org/get"}),
    (
        "file_write",
        "/tools/file-write",
        {"filename": "tool-test.txt", "content": "hello from tool test"},
    ),
    ("file_read", "/tools/file-read", {"filename": "tool-test.txt"}),
    ("file_list", "/tools/file-list", {"directory": "", "pattern": "*"}),
    (
        "file_search_content",
        "/tools/file-search-content",
        {"query": "hello", "pattern": "*", "max_results": 5},
    ),
    ("datetime_tool", "/tools/datetime", {}),
    (
        "web_search",
        "/tools/web-search",
        {"query": "python programming", "max_results": 3},
    ),
    (
        "code_execute",
        "/tools/code-execute",
        {"code": "print(1+1)", "language": "python"},
    ),
    (
        "text_summarize",
        "/tools/text-summarize",
        {
            "text": "The quick brown fox jumps over the lazy dog. The dog barked loudly. The fox ran away quickly.",
            "max_sentences": 2,
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
        {"text_a": "hello\nworld", "text_b": "hello\nearth", "context_lines": 1},
    ),
    (
        "text_extract",
        "/tools/text-extract",
        {
            "text": "Email me at test@example.com or visit https://example.com",
            "extract_type": "emails",
        },
    ),
    (
        "json_transform",
        "/tools/json-transform",
        {"data": '{"b":2,"a":1}', "operation": "sort_keys"},
    ),
    (
        "csv_parse",
        "/tools/csv-parse",
        {"csv_text": "name,age\nAlice,30\nBob,25", "operation": "to_json"},
    ),
    (
        "yaml_convert",
        "/tools/yaml-convert",
        {"content": "name: test\nvalue: 42", "direction": "yaml_to_json"},
    ),
    (
        "base64_codec",
        "/tools/base64-codec",
        {"text": "hello world", "operation": "encode"},
    ),
    ("hash_generate", "/tools/hash-generate", {"text": "hello", "algorithm": "sha256"}),
    ("uuid_generate", "/tools/uuid-generate", {"count": 1}),
    (
        "regex_match",
        "/tools/regex-match",
        {
            "text": "my email is test@example.com",
            "pattern": r"[\w.]+@[\w.]+",
            "flags": "",
        },
    ),
    (
        "url_parse",
        "/tools/url-parse",
        {"url": "https://example.com:8080/path?q=1&r=2#section"},
    ),
    (
        "html_strip",
        "/tools/html-strip",
        {"html": "<h1>Hello</h1><p>World</p>", "keep_links": False},
    ),
    (
        "markdown_to_html",
        "/tools/markdown-to-html",
        {"markdown": "# Hello\n\n**bold** text"},
    ),
    (
        "webpage_extract",
        "/tools/webpage-extract",
        {"url": "https://httpbin.org/html", "max_length": 500},
    ),
    ("dns_lookup", "/tools/dns-lookup", {"hostname": "example.com"}),
    (
        "json_schema_validate",
        "/tools/json-schema-validate",
        {
            "data": '{"name":"test","age":25}',
            "schema_def": '{"type":"object","properties":{"name":{"type":"string"},"age":{"type":"integer"}},"required":["name"]}',
        },
    ),
    ("cron_parse", "/tools/cron-parse", {"expression": "0 9 * * 1-5"}),
    (
        "jwt_decode",
        "/tools/jwt-decode",
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        },
    ),
    ("environment_info", "/tools/environment-info", {}),
]


def main():
    results = []
    client = httpx.Client(timeout=30.0)

    for name, endpoint, payload in TESTS:
        try:
            resp = client.post(f"{BASE}{endpoint}", json=payload)
            status = resp.status_code
            body = resp.text[:300]
            ok = 200 <= status < 300
            err = None if ok else body
            if ok:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and "error" in data:
                        ok = False
                        err = data["error"]
                except Exception:
                    pass
        except Exception as e:
            status = 0
            ok = False
            err = str(e)
            body = ""

        icon = "PASS" if ok else "FAIL"
        results.append({"name": name, "ok": ok, "status": status, "error": err})
        print(f"  [{icon}] {name:25s}  HTTP {status}  {err or ''}")

    passed = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])
    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed, {len(results)} total")
    print(f"{'='*60}")

    if failed:
        print("\nFailed tools:")
        for r in results:
            if not r["ok"]:
                print(f"  - {r['name']}: {r['error']}")

    # Output JSON for programmatic use
    with open("tool-test-results.json", "w") as f:
        json.dump(results, f, indent=2)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
