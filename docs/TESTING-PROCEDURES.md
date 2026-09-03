# Agentic Platform - Testing Procedures

**Last Updated:** September 4, 2026  
**Version:** 1.0  
**Maintainer:** Development Team

---

## Overview

This document provides repeatable testing procedures for validating all features and functionality of the Agentic Platform, including recently fixed and improved features.

### Quick Test Checklist

- [ ] All 16 Docker services healthy
- [ ] Admin panel loads without errors
- [ ] Login page loads without errors
- [ ] Animations perform smoothly
- [ ] Audit logging functional
- [ ] Secret scanning operational
- [ ] Docker image management working
- [ ] Compliance settings accessible

---

## Part 1: Docker & Infrastructure

### 1.1 Service Health Check

**Procedure:**
```bash
# Check all containers running
docker compose ps

# Expected output: All 16 containers should be "Up" with status "healthy"
# Services: agent-service, tools-service, ui-console, ui-login, n8n, 
#           datastore-db, langfuse-db, chromadb, ollama, and more
```

**Test Steps:**
1. Run the command above
2. Verify all services show status: `Up X minutes (healthy)` or `Up X minutes`
3. Verify ports are correctly mapped (e.g., ui-console on 3005)

**Pass Criteria:** All 16 services running, no failed containers

**Related Docs:** [INSTALL.md](INSTALL.md)

### 1.2 Service Health Endpoints

**Procedure:**
```bash
# Test ui-console health
curl -s http://localhost:3005/health | jq .

# Expected: {"status":"healthy","service":"ui-console"}
```

**Pass Criteria:** Health endpoint returns 200 OK with status "healthy"

---

## Part 2: Authentication & Login

### 2.1 Login Page Load Test

**Procedure:**
1. Open browser to http://localhost:3005/login-app/
2. Wait 2 seconds for page load
3. Verify login form visible

**Expected Behavior:**
- Page loads quickly (< 2 seconds)
- No error messages
- Intro gate animation is **NOT** shown (disabled by default)
- Login form visible with username/password inputs
- "Sign in" button present
- "Remember me" checkbox visible

**Pass Criteria:** Login page fully accessible, form fields interactive

**Related Docs:** [AI-CAPABILITIES.md](AI-CAPABILITIES.md)

### 2.2 Remember Me Functionality

**Procedure:**
1. On login page, enter test credentials (e.g., admin / password)
2. Check "Remember me" checkbox
3. Close browser or clear session
4. Reopen http://localhost:3005/login-app/
5. Verify credentials pre-filled

**Pass Criteria:** Credentials persist in form after page reload

### 2.3 Forgot Password Modal

**Procedure:**
1. On login page, click "Forgot password?" link
2. Modal opens with email/username input
3. Can close modal without error

**Pass Criteria:** Modal opens/closes without errors

---

## Part 3: Animation Testing

### 3.1 Intro Gate Animation (Disabled by Default)

**Procedure:**
1. Clear all browser storage: `localStorage.clear()` in console
2. Navigate to http://localhost:3005/login-app/
3. Observe boot animation

**Expected Behavior:**
- Intro gate animation should **NOT** appear on first visit
- Login form should appear immediately
- Page load time: < 1 second

**Pass Criteria:** No gate animation shown, login form direct access

**Verification:**
```javascript
// In browser console:
localStorage.getItem('agentic_intro_gate_enabled')
// Should return: null or "false"
```

### 3.2 Sign-In Animation

**Procedure:**
1. On login page, enter valid credentials
2. Click "Sign in" button
3. Observe animation as screen fills
4. Total animation time

**Expected Animation Sequence:**
1. **Scan beam** (450ms) - Horizontal line sweeps top to bottom
2. **Glow trail** (450ms) - Soft shimmer follows scan beam
3. **Panel fly-out** (1000ms) - Screen splits into 4 quadrants flying outward
4. **Redirect** (1200ms) - Total time to dashboard

**Pass Criteria:** Animation smooth, redirect completes in < 1.2s

**Performance Check:**
```bash
# Test animation timing
time curl -s -X POST http://localhost:3005/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

---

## Part 4: Admin Panel Tests

### 4.1 Admin Page Load

**Procedure:**
1. After login, navigate to http://localhost:3005/admin
2. Wait for page to load
3. Observe layout

**Expected Behavior:**
- Admin dashboard loads without errors
- No "500 Internal Server Error" message
- Navigation tabs visible:
  - Operations
  - Identity & Access
  - AI Platform
  - Data Platform
  - Infrastructure
  - Compliance & Ethics
- Page is responsive

**Pass Criteria:** Admin page fully loaded, no EJS errors in logs

**Verify Logs:**
```bash
# Check for EJS compilation errors
docker compose logs ui-console 2>&1 | grep -i "ejs\|error\|http"
# Should show no errors (or only normal request logs)
```

### 4.2 Configuration → System Config Tab

**Procedure:**
1. In admin panel, click "Configuration" tab
2. Click "System Config" subtab
3. Scroll to top section "UI/UX Settings"

**Expected Behavior:**
- UI/UX Settings card visible at top
- Intro gate toggle checkbox present
- Label: "🎬 Intro Gate Animation"
- Current state shown (Enabled/Disabled)
- Info box explaining functionality

**Pass Criteria:** All UI elements present and functional

### 4.3 Intro Gate Toggle Test

**Procedure:**

**Part A - Enable Gate:**
1. In UI/UX Settings, ensure toggle is OFF (Disabled)
2. Click toggle to ON
3. Verify message: "🎬 Intro gate animation enabled"
4. Verify localStorage updated:
   ```javascript
   localStorage.getItem('agentic_intro_gate_enabled')
   // Should return: "true"
   ```

**Part B - Disable Gate:**
1. Click toggle to OFF
2. Verify message: "⏭️ Intro gate animation disabled"
3. Verify localStorage updated:
   ```javascript
   localStorage.getItem('agentic_intro_gate_enabled')
   // Should return: "false"
   ```

**Part C - Cross-Session Persistence:**
1. Enable gate animation
2. Close browser completely
3. Reopen http://localhost:3005/
4. Gate animation should appear on next login (if accessing for first time)

**Pass Criteria:** Toggle works, localStorage persists, toast messages display

---

## Part 5: Compliance & Audit Logging

### 5.1 Audit Log Display Test

**Procedure:**
1. In admin panel, click "Compliance & Ethics" tab
2. Click "Compliance Audit" subtab
3. Scroll to "Audit Log" section

**Expected Behavior:**
- Audit log table visible
- Column headers: Timestamp, User, Action, Entity Type, Details
- Recent entries visible (if any)
- No errors in table rendering

**Pass Criteria:** Audit log table displays without errors

### 5.2 Audit Log Filtering

**Procedure:**
1. In Audit Log section, observe "Event Type" dropdown
2. Select different event types (if available)
3. Click "Filter"

**Expected Behavior:**
- Table updates with filtered results
- Export CSV button works
- No JavaScript errors

**Pass Criteria:** Filtering works, export accessible

---

## Part 6: Secret Scanning

### 6.1 Secret Scan UI Access

**Procedure:**
1. In admin panel, click "Compliance & Ethics" tab
2. Click "Secret Scan" subtab
3. Observe interface

**Expected Behavior:**
- Scan path input field visible
- Format selector (JSON/CSV/SARIF) visible
- "Run Scan" button present
- Previous scan results section (if any scans completed)

**Pass Criteria:** All UI elements present

### 6.2 Secret Scan Execution

**Procedure:**
1. In Secret Scan tab, enter scan path: `.`
2. Select format: JSON
3. Click "Run Scan"
4. Wait for results

**Expected Behavior:**
- Loading indicator shows
- Scan completes in < 60 seconds (backend timeout: 60s)
- Results table displays with columns:
  - Severity (badge with color)
  - What & Why (description)
  - Location (file + line)
  - Remediation (fix steps)
  - Matched Value (obfuscated)
  - Rule ID (reference)

**Pass Criteria:** Scan runs without errors, results display correctly

**Related Docs:** [GITLEAKS-SECURITY-SCANNING.md](GITLEAKS-SECURITY-SCANNING.md)

---

## Part 7: Docker Image Management

### 7.1 Docker Management Tab Access

**Procedure:**
1. In admin panel, click "Infrastructure" tab
2. Look for "Docker Image Management" section

**Expected Behavior:**
- Docker management UI loads
- No "Not Available" errors
- Security summary KPI cards visible:
  - Total Images
  - Critical Vulnerabilities
  - High Vulnerabilities
  - Healthy Images

**Pass Criteria:** Section loads without errors

### 7.2 Docker Images Table

**Procedure:**
1. In Docker management section, observe images table
2. Table should display Docker images with:
   - Image name
   - Tag
   - Size (MB)
   - Created date
   - Status
   - Scan button

**Expected Behavior:**
- Table populated (if Docker images exist)
- Scan buttons functional
- No loading errors

**Pass Criteria:** Table displays, scan buttons clickable

**Related Docs:** [DOCKER-SECURITY.md](DOCKER-SECURITY.md)

---

## Part 8: API Tests

### 8.1 Authentication API

**Procedure:**
```bash
# Test login endpoint
curl -X POST http://localhost:3005/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'
```

**Expected Response:**
- 200 OK with session cookie OR
- 401 Unauthorized with proper error message

**Pass Criteria:** API responds with appropriate status

### 8.2 Protected API Endpoints (Require Session)

**Procedure:**
```bash
# Without authentication - should fail
curl -s http://localhost:3005/api/admin/docker/images

# Expected response: {"error":"Not authenticated"}

# With session cookie - should succeed
curl -s -b "connect.sid=<session_id>" http://localhost:3005/api/admin/docker/images

# Expected response: {"images":[...], "count":X}
```

**Pass Criteria:** Authentication properly enforced

### 8.3 Audit Log API

**Procedure:**
```bash
# Test audit log endpoint (with auth)
curl -s -b "connect.sid=<session_id>" \
  "http://localhost:3005/api/audit-log?limit=10"

# Expected: JSON array with audit entries
```

**Pass Criteria:** Returns audit entries in JSON format

---

## Part 9: Data Persistence

### 9.1 localStorage Persistence

**Procedure:**
1. In browser console:
   ```javascript
   // Check intro gate setting
   localStorage.getItem('agentic_intro_gate_enabled')
   
   // Check if intro was shown
   localStorage.getItem('agentic_intro_shown')
   
   // Check remember-me data
   localStorage.getItem('agentic-remember')
   ```

**Expected Behavior:**
- Values persist across page reloads
- Settings match UI state in admin panel
- No undefined values

**Pass Criteria:** localStorage data persists correctly

### 9.2 Session Persistence

**Procedure:**
1. Login to platform
2. Navigate to different sections
3. Close browser tab (keep browser open)
4. Open new tab, navigate to http://localhost:3005/admin
5. Verify still logged in

**Expected Behavior:**
- Session maintained across tabs
- No re-authentication needed
- Admin access preserved

**Pass Criteria:** Session survives tab restart

### 9.3 Database Persistence

**Procedure:**
1. Perform action that creates audit entry (e.g., login)
2. Wait 5 seconds
3. Check audit log in admin panel
4. Restart container: `docker compose restart ui-console`
5. Re-login and check audit log again

**Expected Behavior:**
- Audit entries persist after container restart
- No data loss
- Historical entries still visible

**Pass Criteria:** Database persists across container restarts

---

## Part 10: Regression Testing

### 10.1 Critical Path Test

**Complete workflow:**
1. ✅ Load login page (no gate animation)
2. ✅ Enter credentials and sign in (animation plays)
3. ✅ See admin dashboard
4. ✅ Navigate to Compliance & Ethics
5. ✅ View audit log
6. ✅ Run secret scan
7. ✅ Check Docker images
8. ✅ Toggle intro gate in settings
9. ✅ Logout
10. ✅ Login again (observe gate animation if enabled)

**Pass Criteria:** All steps complete without errors

### 10.2 Browser Compatibility

**Test Browsers:**
- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

**Expected:** All functions work in each browser

---

## Part 11: Performance Testing

### 11.1 Page Load Time

**Procedure:**
```bash
# Measure login page load time
time curl -s http://localhost:3005/login-app/ > /dev/null

# Measure admin page load time (requires auth)
time curl -s -b "connect.sid=<session_id>" \
  http://localhost:3005/admin > /dev/null
```

**Expected:**
- Login page: < 2 seconds
- Admin page: < 3 seconds
- Network latency: < 100ms

**Pass Criteria:** Pages load within expected time

### 11.2 Animation Performance

**Procedure:**
1. Open DevTools (F12)
2. Go to Performance tab
3. Record sign-in animation
4. Play recording

**Expected:**
- Frame rate: 60 FPS (no stuttering)
- Animation duration: 1.2 seconds total
- No jank or frame drops

**Pass Criteria:** Smooth animation, consistent framerate

---

## Part 12: Error Handling

### 12.1 Invalid Login

**Procedure:**
1. Enter invalid username/password
2. Click "Sign in"
3. Observe error message

**Expected:**
- Clear error message displayed
- Login form remains accessible
- No page crash

**Pass Criteria:** Graceful error handling

### 12.2 API Error Handling

**Procedure:**
```bash
# Test with invalid session
curl -s -b "connect.sid=invalid" \
  http://localhost:3005/api/admin/docker/images
```

**Expected:**
- 401 Unauthorized response
- Clear error message
- No server crash

**Pass Criteria:** Proper HTTP status and error messages

### 12.3 Network Error Handling

**Procedure:**
1. Stop ui-console service: `docker compose stop ui-console`
2. Try to access http://localhost:3005/
3. Observe behavior

**Expected:**
- Connection refused or timeout error
- Browser shows appropriate error
- No white screen

**Pass Criteria:** Graceful error display

**Recovery:**
```bash
# Restart service
docker compose up -d ui-console
```

---

## Automated Testing

### Setup Continuous Testing

**Create test script:** `scripts/test_platform.sh`

```bash
#!/bin/bash
set -e

echo "=== Agentic Platform Test Suite ==="

# 1. Check services
echo -e "\n[1/4] Checking Docker services..."
docker compose ps | grep healthy > /dev/null || exit 1

# 2. Check health endpoints
echo "[2/4] Checking health endpoints..."
curl -f -s http://localhost:3005/health > /dev/null || exit 1

# 3. Check login page
echo "[3/4] Checking login page..."
curl -f -s http://localhost:3005/login-app/ | grep -q "Agentic Platform" || exit 1

# 4. Check for errors
echo "[4/4] Checking logs for errors..."
docker compose logs ui-console 2>&1 | grep -i "error" | grep -v "404" > /dev/null && exit 1

echo -e "\n✅ All tests passed!"
```

**Run tests:**
```bash
chmod +x scripts/test_platform.sh
./scripts/test_platform.sh
```

---

## Test Report Template

**Create file:** `TEST-REPORT-DATE.md`

```markdown
# Test Report - [DATE]

**Environment:** Docker Compose | **Tester:** [NAME] | **Duration:** [X minutes]

## Summary
- Total Tests: X
- Passed: X
- Failed: X
- Warnings: X

## Test Results

### Infrastructure
- [ ] All services healthy
- [ ] Database connectivity
- [ ] Logs clean

### Features
- [ ] Login page loads
- [ ] Admin panel accessible
- [ ] Animations smooth
- [ ] Audit log functional
- [ ] Secret scan working
- [ ] Docker management operational

### Regressions
- [ ] No new errors
- [ ] Performance acceptable
- [ ] UI fully responsive

## Issues Found
(List any bugs or concerns)

## Recommendations
(Any improvements or fixes needed)

**Tested:** [Date/Time]  
**Status:** ✅ PASS / ⚠️ NEEDS WORK / ❌ FAILED
```

---

## Quick Reference

### Common Commands

```bash
# Full system restart
docker compose down && docker compose up -d

# View real-time logs
docker compose logs -f ui-console

# Run specific test
./scripts/test_platform.sh

# Clear browser storage (JavaScript console)
localStorage.clear(); sessionStorage.clear()

# Check admin panel access
curl -s http://localhost:3005/admin | head -50

# View animation settings
curl -s http://localhost:3005/api/admin/ui-settings
```

### Debugging

```bash
# Check for EJS errors
docker compose logs ui-console | grep -i ejs

# Check for auth errors
docker compose logs ui-console | grep -i "auth\|session"

# Check for animation issues
# Open browser DevTools → Console (should show no errors)

# Check localStorage (browser console)
console.log(localStorage)
```

---

## Checklist for New Releases

Before deploying to production:

- [ ] All automated tests pass
- [ ] Manual testing completed per this guide
- [ ] No new errors in logs
- [ ] Admin panel fully functional
- [ ] All animations smooth
- [ ] Documentation updated
- [ ] Git commits clean
- [ ] No breaking changes to APIs

---

## Support & Escalation

**If tests fail:**
1. Check [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)
2. Review relevant feature documentation
3. Check Docker logs: `docker compose logs`
4. Verify all services healthy: `docker compose ps`
5. Restart if needed: `docker compose restart ui-console`
6. Escalate to development team if issue persists

---

**End of Testing Procedures**
