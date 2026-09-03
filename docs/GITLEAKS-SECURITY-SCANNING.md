# 🔐 Gitleaks Secret Scanning Implementation

## Overview

Gitleaks is integrated into the Admin Panel as a **real-time secret detection tool** that scans your entire codebase for hardcoded credentials, API keys, tokens, passwords, and other sensitive data.

**Status**: ✅ Production Ready  
**Security Level**: Admin Only  
**Scan Time**: ~30-60 seconds (full repo)  
**Detection Patterns**: 100+ built-in rules  

---

## 🎯 What It Detects

Gitleaks automatically detects:

### 1. **Credentials & Authentication**
- API keys and tokens
- AWS credentials (Access Key ID, Secret Key)
- GitHub, GitLab, Bitbucket tokens
- Private SSH keys
- Database passwords
- OAuth tokens

### 2. **Cloud Secrets**
- Azure connection strings
- GCP service accounts
- AWS access keys
- Slack tokens
- SendGrid API keys
- Stripe API keys

### 3. **Sensitive Data**
- Private encryption keys
- Certificates and certificates with private keys
- Connection strings with passwords
- Hardcoded credentials in config files
- Firebase API keys
- Twilio auth tokens

### 4. **Code-Level Secrets**
- Plaintext passwords in source code
- Hardcoded database credentials
- API endpoints with embedded secrets
- JWT signing keys
- OAuth client secrets

---

## 📍 Access & Permissions

### Location in Admin Panel
```
Admin Plane
  └─ Compliance & Ethics
      └─ Secret Scanning
```

### Permission Requirements
- **Role**: Admin only
- **Session**: Active authenticated admin user
- **Audit Trail**: All scans logged with user, timestamp, IP

### Security Features
- ✅ Role-based access control (requireAdmin middleware)
- ✅ Scan audit logging (who, when, IP address)
- ✅ No secrets exposed in logs (only metadata)
- ✅ Timeout protection (60 seconds)
- ✅ Memory limits (10MB buffer)

---

## 🚀 How to Use

### Step 1: Navigate to Secret Scanning
1. Login as admin user
2. Go to **Admin Plane** (sidebar)
3. Click **Compliance & Ethics** section
4. Select **Secret Scanning** tab

### Step 2: Configure Scan
```
Scan Path:      /app (default) or custom path
Output Format:  JSON, CSV, or SARIF
```

**Common Scan Paths**:
- `/app` - Entire application (default)
- `/app/services` - All microservices
- `/app/services/agent` - Specific service
- `/app/scripts` - Scripts directory
- `/app/.git` - Git history (SLOW - 5+ minutes)

### Step 3: Run Scan
1. Click **🔍 Run Secret Scan**
2. Wait for progress indicator (30-60 seconds)
3. Results automatically display when complete

### Step 4: Review Results
Results show:
- **Summary Stats**: Total secrets, high severity count, scan timestamp
- **Results Table**: 
  - Type (secret type detected)
  - File (path to compromised file)
  - Line (line number where found)
  - Match (obfuscated secret snippet)
  - Rule (detection rule name)

### Step 5: Export Report
- Click **📥 Export Results** 
- Generates HTML report with:
  - Timestamp
  - Summary statistics
  - Detailed findings table
  - Color-coded severity levels

---

## 📊 Understanding Results

### Result Format

```
Type            │ RuleID
File            │ Path to file with secret
Line            │ Line number in file
Match           │ ••••••••... (obfuscated)
Rule            │ Rule Name (e.g., AWS Key)
```

### Severity Levels

- **🔴 HIGH**: Critical secrets (passwords, tokens, keys)
  - Action: Rotate immediately, commit message to rewrite history
  - Background: Red highlight (#EF4444)

- **🟡 MEDIUM**: Potentially sensitive (hostnames, usernames)
  - Action: Review and assess risk
  - Background: Yellow highlight (#FBB036)

- **🟢 LOW**: Informational patterns
  - Action: Review if needed
  - Background: No highlight

### Example Results

```
AWS Key Found
  File: services/agent/config.py
  Line: 42
  Match: AKIA••••••••••••••••
  Rule: AWS API Key
  
GitHub Token Found
  File: .env.example
  Line: 5
  Match: ghp_••••••••••••••••••••
  Rule: GitHub Personal Access Token
```

---

## 🔧 Output Formats

### JSON (Recommended)
```json
{
  "Description": "Gitleaks scan results",
  "StartTime": "2026-09-03T10:30:00Z",
  "Findings": [
    {
      "RuleID": "AWS API Key",
      "RuleTitle": "AWS Access Key",
      "File": "config/prod.json",
      "Match": "AKIA...",
      "StartLine": 42,
      "Severity": "HIGH"
    }
  ]
}
```

### CSV
```csv
RuleID,File,Line,Match,Severity
AWS API Key,config/prod.json,42,AKIA...,HIGH
GitHub Token,scripts/deploy.sh,15,ghp_...,HIGH
```

### SARIF (Security Analysis Result Format)
Standard format for security tools, integrates with GitHub Security and other SIEM tools.

---

## 🎛️ Advanced Configuration

### Backend Endpoint

**URL**: `POST /api/admin/secret-scan`  
**Auth**: Admin only (requireAdmin middleware)  
**Timeout**: 60 seconds  
**Buffer**: 10MB

### Request
```bash
curl -X POST http://localhost:3005/api/admin/secret-scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanPath": "/app",
    "format": "json"
  }'
```

### Response
```json
{
  "success": true,
  "timestamp": "2026-09-03T10:30:00.000Z",
  "scanPath": "/app",
  "secretsDetected": true,
  "results": [
    {
      "RuleID": "AWS API Key",
      "File": "config/prod.json",
      "StartLine": 42,
      "Match": "AKIA...",
      "Severity": "HIGH"
    }
  ]
}
```

### Environment Variables

No additional env vars needed (gitleaks works out of the box after Docker install).

Optional tuning:
```bash
# Timeout (seconds)
GITLEAKS_TIMEOUT=120

# Max file size to scan (MB)
GITLEAKS_MAX_FILE_SIZE=100
```

---

## 🛡️ Security Best Practices

### 1. **Run Regularly**
- Schedule weekly automated scans
- Run before each production deployment
- Run after any credentials rotation

### 2. **Immediate Action on High Severity**
- Rotate any compromised secrets immediately
- Update all references to the secret
- Rewrite git history if in repository
  ```bash
  git filter-repo --invert-paths --path <file>
  ```

### 3. **Implement Pre-commit Hooks**
```bash
# Install gitleaks hook
cd /your/repo
gitleaks protect --install pre-commit

# Now every commit is automatically scanned
git commit -m "your message"  # Fails if secrets detected
```

### 4. **Exclude False Positives**
Create `.gitleaksignore` file:
```
# Example test credentials (safe for testing)
test-api-key-12345
```

### 5. **Never Commit Secrets**
Use environment variables or secret management:
```bash
# ❌ DON'T DO THIS
API_KEY = "sk-1234567890"

# ✅ DO THIS
API_KEY = os.getenv('API_KEY')
```

---

## 🔍 Running Scans Manually

### Command Line
```bash
# Scan entire repo
gitleaks detect --source .

# Scan specific directory
gitleaks detect --source ./services/agent

# JSON output
gitleaks detect --source . --report-format json

# Save to file
gitleaks detect --source . --report-path ./report.json

# Scan git history
gitleaks detect --source . --verbose

# Scan with custom rules
gitleaks detect --source . --config ./custom-rules.toml
```

### Exit Codes
- `0`: No secrets found ✅
- `1`: Secrets found ⚠️
- `2`: Error occurred ❌

---

## 📋 Docker Integration

### Installation
Gitleaks is automatically installed in the UI Console Dockerfile:

```dockerfile
FROM node:20.11.1-alpine
RUN apk add --no-cache gitleaks git
```

### Verify Installation
```bash
docker exec ui-console gitleaks --version
```

---

## 📊 Audit Logging

All secret scans are logged for compliance:

```javascript
[SECURITY] Admin initiated secret scan
{
  "path": "/app",
  "user": "admin@company.com",
  "ip": "192.168.1.100",
  "timestamp": "2026-09-03T10:30:00Z"
}

[SECURITY] Secret scan completed
{
  "user": "admin@company.com",
  "path": "/app",
  "secretsFound": true,
  "timestamp": "2026-09-03T10:31:30Z"
}
```

---

## 🐛 Troubleshooting

### Gitleaks Not Found
```
Error: gitleaks command not found
```
**Solution**: Rebuild Docker image
```bash
docker-compose build ui-console
docker-compose up -d ui-console
```

### Scan Timeout
```
Error: Command timed out after 60 seconds
```
**Solution**: 
- Scan smaller directory instead of full `/app`
- Exclude `.git` directory
- Increase timeout in code (up to 120 seconds max)

### Too Many Results
```
1,000+ secrets found - unusual
```
**Solution**: Check for:
- Accidentally committed `.env` files
- Test credentials in source code
- Mock/fixture data files

### False Positives
```
Detected: "password123" (but it's just a test string)
```
**Solution**:
- Add to `.gitleaksignore`
- Use custom rules
- Review and mark as reviewed in results

---

## 🎓 Real-World Examples

### Example 1: Found AWS Key
```
Type:   AWS API Key
File:   services/agent/config.py
Line:   42
Match:  AKIA••••••••••••••••••
Rule:   AWS Access Key

Action:
1. Rotate AWS access key immediately
2. Rewrite git history to remove it
3. Update all references
4. Check AWS console for unauthorized access
```

### Example 2: Found GitHub Token
```
Type:   GitHub Token
File:   .env.example
Line:   5
Match:  ghp_••••••••••••••••••••
Rule:   GitHub Personal Access Token

Action:
1. Revoke token in GitHub settings
2. Generate new token
3. Update deployment scripts
4. Commit .env.example with new token
```

### Example 3: Found Database Password
```
Type:   Database Password
File:   docker-compose.yml
Line:   15
Match:  postgres://user:pass••••••••
Rule:   Connection String with Credentials

Action:
1. Use environment variables instead
2. Update docker-compose.yml to use ${DB_PASSWORD}
3. Set DB_PASSWORD in .env (git ignored)
4. Rewrite history to remove hardcoded password
```

---

## 📈 Metrics & Reporting

### Dashboard Stats
```
Secrets Found:      42
High Severity:      12
Medium Severity:    18
Low Severity:       12
Last Scan:          Today 10:30 AM
Scan Path:          /app
```

### Export Reports
Click **📥 Export Results** to generate:
- HTML report with findings
- Timestamp and scan metadata
- Color-coded severity levels
- Shareable with security team

### Integration with SIEM
Use SARIF format to integrate with:
- GitHub Security
- GitLab Security Dashboard
- Azure DevOps
- Snyk
- Checkmarx

---

## 🔐 Compliance Mapping

### OWASP Top 10:2025
- **A02**: Security Misconfiguration (detects hardcoded secrets)
- **A04**: Cryptographic Failures (detects exposed keys)
- **A07**: Authentication Failures (detects password exposure)

### Regulatory Compliance
- **PCI DSS**: Requirement 8.2 (password management)
- **HIPAA**: Technical safeguards (access controls)
- **SOC 2**: Logical access controls
- **ISO 27001**: Asset management (information classification)

### Framework Alignment
- ✅ NIST Cybersecurity Framework (ID.BE-1)
- ✅ CIS Controls (v8: Control 3)
- ✅ SLSA Framework (Supply chain security)

---

## 📚 Additional Resources

### Official Documentation
- Gitleaks GitHub: https://github.com/gitleaks/gitleaks
- Gitleaks Docs: https://gitleaks.io/

### Configuration
- Custom Rules: https://gitleaks.io/configuration/
- Pre-commit Integration: https://gitleaks.io/integrate-gitleaks/

### Training
- Secret Management Best Practices
- Secure Coding Training
- Incident Response Procedures

---

## 🎯 Next Steps

### Immediate (This Week)
- [ ] Review initial scan results
- [ ] Rotate any high-severity secrets found
- [ ] Rewrite git history if needed

### Short Term (This Month)
- [ ] Run weekly automated scans
- [ ] Setup pre-commit gitleaks hooks
- [ ] Document secret rotation procedures
- [ ] Train team on secret management

### Long Term (Q4 2026)
- [ ] Integrate with SIEM platform
- [ ] Setup automated alerts for CRITICAL findings
- [ ] Implement Hardware Security Module (HSM)
- [ ] Complete PCI DSS compliance

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review Gitleaks documentation
3. Contact security team
4. Submit bug report to GitHub

---

**Version**: 1.0  
**Last Updated**: 2026-09-03  
**Status**: ✅ Production Ready  
**Maintained By**: Security Team
