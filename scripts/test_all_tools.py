"""Test all 29 proxy tools against tools-service."""
import json
import httpx

BASE = "http://localhost:8001"

tests = [
    ("math", "/tools/math", {"expression": "2+2"}),
    ("http_fetch", "/tools/http-fetch", {"url": "https://httpbin.org/get"}),
    ("file_write", "/tools/file-write", {"filename": "test-run.txt", "content": "hello world"}),
    ("file_read", "/tools/file-read", {"filename": "test-run.txt"}),
    ("file_list", "/tools/file-list", {"directory": ".", "pattern": "*"}),
    ("file_search_content", "/tools/file-search-content", {"query": "hello"}),
    ("datetime_tool", "/tools/datetime", {}),
    ("web_search", "/tools/web-search", {"query": "python programming"}),
    ("code_execute", "/tools/code-execute", {"language": "python", "code": "print(1+1)"}),
    ("text_summarize", "/tools/text-summarize", {"text": "The quick brown fox jumps over the lazy dog. This is a longer test. Multiple sentences here."}),
    ("text_transform", "/tools/text-transform", {"text": "hello world", "operation": "uppercase"}),
    ("text_diff", "/tools/text-diff", {"text_a": "hello world", "text_b": "hello there"}),
    ("text_extract", "/tools/text-extract", {"text": "email test@example.com phone 555-1234", "extract_type": "emails"}),
    ("json_transform", "/tools/json-transform", {"data": '{"a":1,"b":2}', "operation": "keys"}),
    ("csv_parse", "/tools/csv-parse", {"csv_text": "a,b\n1,2\n3,4"}),
    ("yaml_convert", "/tools/yaml-convert", {"content": '{"key":"value"}', "direction": "json_to_yaml"}),
    ("base64_codec", "/tools/base64-codec", {"text": "hello", "operation": "encode"}),
    ("hash_generate", "/tools/hash-generate", {"text": "hello", "algorithm": "sha256"}),
    ("uuid_generate", "/tools/uuid-generate", {}),
    ("regex_match", "/tools/regex-match", {"text": "hello world 123", "pattern": "[0-9]+"}),
    ("url_parse", "/tools/url-parse", {"url": "https://example.com/path?q=1"}),
    ("html_strip", "/tools/html-strip", {"html": "<p>Hello <b>World</b></p>"}),
    ("markdown_to_html", "/tools/markdown-to-html", {"markdown": "# Hello"}),
    ("webpage_extract", "/tools/webpage-extract", {"url": "https://example.com"}),
    ("dns_lookup", "/tools/dns-lookup", {"hostname": "google.com"}),
    ("json_schema_validate", "/tools/json-schema-validate", {"data": '{"name":"test"}', "schema_def": '{"type":"object","properties":{"name":{"type":"string"}}}'}),
    ("cron_parse", "/tools/cron-parse", {"expression": "0 9 * * 1"}),
    ("jwt_decode", "/tools/jwt-decode", {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"}),
    ("environment_info", "/tools/environment-info", {}),
]

results = []
for name, path, payload in tests:
    try:
        r = httpx.post(BASE + path, json=payload, timeout=15)
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
print(f"\nTotal: {len(results)} | Pass: {passes} | Fail: {fails}")
