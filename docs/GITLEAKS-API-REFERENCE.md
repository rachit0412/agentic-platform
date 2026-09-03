# Gitleaks API Reference

## Endpoint: POST /api/admin/secret-scan

Initiates a secret scanning operation using gitleaks CLI.

### Authentication
- **Required**: Admin role
- **Middleware**: `requireAdmin`
- **Session**: Active authenticated admin user

### Request

#### Headers
```
Content-Type: application/json
Cookie: agentic.sid=<session-id>
```

#### Body
```json
{
  "scanPath": "/app",
  "format": "json"
}
```

#### Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scanPath` | string | `/app` | Directory path to scan |
| `format` | string | `json` | Output format: `json`, `csv`, `sarif` |

### Response

#### Success (200 OK)
```json
{
  "success": true,
  "timestamp": "2026-09-03T10:30:00.000Z",
  "scanPath": "/app",
  "secretsDetected": false,
  "results": []
}
```

#### Success with Findings (200 OK)
```json
{
  "success": true,
  "timestamp": "2026-09-03T10:30:00.000Z",
  "scanPath": "/app",
  "secretsDetected": true,
  "results": [
    {
      "RuleID": "AWS API Key",
      "File": "services/agent/config.py",
      "StartLine": 42,
      "Match": "AKIA••••••••••••••••••",
      "Severity": "HIGH",
      "Secret": "AKIAIOSFODNN7EXAMPLE",
      "RuleTitle": "AWS Access Key"
    },
    {
      "RuleID": "GitHub Token",
      "File": ".env.example",
      "StartLine": 5,
      "Match": "ghp_••••••••••••••••••••",
      "Severity": "HIGH",
      "RuleTitle": "GitHub Personal Access Token"
    }
  ]
}
```

#### Error (500)
```json
{
  "error": "Secret scan failed",
  "details": "gitleaks command not found (development mode only)"
}
```

#### Forbidden (403)
```json
{
  "error": "Admin access required"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Operation status |
| `timestamp` | string | ISO 8601 scan completion time |
| `scanPath` | string | Directory that was scanned |
| `secretsDetected` | boolean | Whether secrets were found |
| `results` | array | Array of secret findings (see below) |

### Finding Object

```json
{
  "RuleID": "string",
  "RuleTitle": "string",
  "File": "string",
  "StartLine": "number",
  "EndLine": "number",
  "Match": "string (obfuscated)",
  "Secret": "string (actual secret)",
  "Severity": "HIGH|MEDIUM|LOW",
  "Entropy": "number",
  "Author": "string",
  "Commit": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `RuleID` | string | Detection rule identifier |
| `RuleTitle` | string | Human-readable rule name |
| `File` | string | Relative path to file |
| `StartLine` | number | Line number where secret starts |
| `EndLine` | number | Line number where secret ends |
| `Match` | string | Obfuscated version (first 10 chars) |
| `Secret` | string | Full secret value (in dev only) |
| `Severity` | enum | HIGH, MEDIUM, or LOW |
| `Entropy` | number | Shannon entropy (0-8) |
| `Author` | string | Git commit author |
| `Commit` | string | Git commit hash |

---

## Examples

### Example 1: Scan Default Path
```bash
curl -X POST http://localhost:3005/api/admin/secret-scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanPath": "/app",
    "format": "json"
  }'
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2026-09-03T10:30:00.000Z",
  "scanPath": "/app",
  "secretsDetected": false,
  "results": []
}
```

### Example 2: Scan Specific Service with CSV
```bash
curl -X POST http://localhost:3005/api/admin/secret-scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanPath": "/app/services/agent",
    "format": "csv"
  }'
```

**Response (CSV format):**
```csv
RuleID,File,Line,Match,Severity
AWS API Key,config/prod.json,42,AKIA••••••••••••••••,HIGH
GitHub Token,scripts/deploy.sh,15,ghp_••••••••••••••••,HIGH
```

### Example 3: Scan with SARIF Output
```bash
curl -X POST http://localhost:3005/api/admin/secret-scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanPath": "/app",
    "format": "sarif"
  }'
```

**Response (SARIF format):**
```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "gitleaks",
          "informationUri": "https://github.com/gitleaks/gitleaks"
        }
      },
      "results": []
    }
  ]
}
```

### Example 4: Handle Scan Timeout
```bash
# Request times out after 60 seconds
curl -X POST http://localhost:3005/api/admin/secret-scan \
  -H "Content-Type: application/json" \
  --max-time 60 \
  -d '{
    "scanPath": "/app",
    "format": "json"
  }'
```

---

## Audit Logging

All secret scans are logged with:
```
[SECURITY] Admin initiated secret scan
{
  "path": "/app",
  "user": "admin@example.com",
  "ip": "192.168.1.100",
  "timestamp": "2026-09-03T10:30:00Z"
}

[SECURITY] Secret scan completed
{
  "user": "admin@example.com",
  "path": "/app",
  "secretsFound": true,
  "timestamp": "2026-09-03T10:31:30Z"
}
```

---

## Rate Limiting

- **No specific rate limit** for secret scans (admin action)
- **General admin API limit**: Subject to global rate limiter
- **Timeout**: 60 seconds per scan
- **Concurrent scans**: Sequential (one at a time)

---

## Error Handling

### Common Errors

```json
{
  "error": "Secret scan failed",
  "details": "gitleaks command not found"
}
```
**Cause**: gitleaks not installed  
**Solution**: Rebuild Docker image

```json
{
  "error": "Secret scan failed",
  "details": "Timeout waiting for scan to complete"
}
```
**Cause**: Scan took longer than 60 seconds  
**Solution**: Scan smaller directory

```json
{
  "error": "Admin access required"
}
```
**Cause**: User is not admin  
**Solution**: Login as admin user

---

## Implementation Details

### Code Location
- File: `services/ui-console/server.js`
- Line: ~2271
- Middleware: `requireAdmin`
- Method: `POST`

### Gitleaks Command
```bash
gitleaks detect --source "${scanPath}" --report-format ${format} --no-color
```

### Execution Environment
- **Container**: Node.js Alpine
- **User**: Default (non-root for security)
- **Working Directory**: `/app`
- **Timeout**: 60 seconds
- **Max Buffer**: 10MB

### Security Features
- ✅ Role-based access (requireAdmin)
- ✅ Audit logging
- ✅ Timeout protection
- ✅ Memory limits
- ✅ Error message sanitization
- ✅ No secret exposure in logs

---

## Frontend Integration

The admin panel calls this endpoint:

```javascript
const response = await fetch('/api/admin/secret-scan', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    scanPath: '/app', 
    format: 'json' 
  })
});

const result = await response.json();
displaySecretScanResults(result);
```

---

## Troubleshooting

### Test Endpoint
```bash
# Check if endpoint is accessible
curl -X OPTIONS http://localhost:3005/api/admin/secret-scan

# Check if admin user can access
curl -X POST http://localhost:3005/api/admin/secret-scan \
  -H "Content-Type: application/json" \
  -b "agentic.sid=<your-session-id>" \
  -d '{"scanPath": "/app", "format": "json"}'
```

### Debug Logging
Enable debug mode to see gitleaks command output:
```javascript
// In server.js, uncomment this line:
// console.log(`[DEBUG] Running: ${cmd}`);
```

---

## Future Enhancements

- [ ] Scheduled automatic scans
- [ ] Webhook notifications
- [ ] Custom rule support
- [ ] Integration with GitHub/GitLab
- [ ] Historical scan comparison
- [ ] SIEM integration
- [ ] Real-time scanning on commits

---

**API Version**: 1.0  
**Last Updated**: 2026-09-03  
**Status**: ✅ Production Ready
