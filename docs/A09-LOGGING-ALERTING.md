# A09:2025 - Security Logging and Alerting Failures

## Overview

Security logging and alerting failures prevent timely detection and response to attacks. This document details implementation of comprehensive security logging, monitoring, and alerting infrastructure.

## Vulnerabilities Addressed

- ❌ Insufficient logging (no audit trail)
- ❌ Missing security event detection
- ❌ No real-time alerting
- ❌ Lost log data (no retention)
- ❌ Insecure log storage
- ❌ No tamper detection
- ❌ Missing anomaly detection

## Implementation

### 1. Security Event Classification

**Status**: ✅ IMPLEMENTED

The `security_logging.py` module defines comprehensive event types:

#### Authentication Events
```python
from services.agent.agent.security_logging import (
    SecurityEventType,
    SecurityLogger,
    SeverityLevel
)

# Logged events include:
SecurityEventType.AUTH_LOGIN_SUCCESS
SecurityEventType.AUTH_LOGIN_FAILURE
SecurityEventType.AUTH_MFA_ATTEMPT
SecurityEventType.AUTH_SESSION_CREATED
SecurityEventType.AUTH_SESSION_EXPIRED
```

#### Authorization Events
```python
SecurityEventType.AUTHZ_DENIED              # Access denied
SecurityEventType.AUTHZ_ROLE_CHANGE         # Role modification
SecurityEventType.AUTHZ_PERMISSION_CHANGE   # Permission change
```

#### Vulnerability Events
```python
SecurityEventType.VULN_RATE_LIMIT_EXCEEDED
SecurityEventType.VULN_INJECTION_ATTEMPT
SecurityEventType.VULN_XSS_ATTEMPT
SecurityEventType.VULN_CSRF_ATTEMPT
```

#### Data & Administrative Events
```python
SecurityEventType.DATA_INTEGRITY_FAILURE
SecurityEventType.ADMIN_ACTION
SecurityEventType.ADMIN_CONFIG_CHANGE
SecurityEventType.COMPLIANCE_VIOLATION
```

### 2. Structured Logging Format

**Status**: ✅ IMPLEMENTED

All security events logged in JSON format for parsing and aggregation:

```json
{
  "timestamp": "2025-09-03T10:30:45.123456Z",
  "event_type": "AUTH_LOGIN_FAILURE",
  "severity": "MEDIUM",
  "user_id": "user-123",
  "ip_address": "192.168.1.100",
  "details": {
    "reason": "Invalid password",
    "attempt_count": 3
  },
  "context": {
    "user_agent": "Mozilla/5.0...",
    "method": "POST",
    "path": "/auth/login"
  }
}
```

### 3. Centralized Security Logger

**Status**: ✅ IMPLEMENTED

#### Usage
```python
logger = SecurityLogger(logger_name="security")

# Log authentication failure
logger.log_event(
    event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
    severity=SeverityLevel.MEDIUM,
    user_id="user-123",
    ip_address="192.168.1.100",
    details={"reason": "invalid_password", "attempt": 3},
    context={"method": "POST", "path": "/auth/login"}
)

# Log admin action
logger.log_event(
    event_type=SecurityEventType.ADMIN_ACTION,
    severity=SeverityLevel.HIGH,
    user_id="admin-001",
    details={"action": "user_role_change", "target": "user-456"},
    context={"timestamp": datetime.utcnow()}
)
```

#### Features
- JSON structured logging
- In-memory event buffer (10,000 events)
- Persistent file logging (`security-events.jsonl`)
- Thread-safe operations
- Alert trigger mechanism

### 4. Real-Time Anomaly Detection

**Status**: ✅ IMPLEMENTED

#### Automatic Pattern Detection
```python
# Detects suspicious patterns automatically
anomalies = logger.detect_anomalies()

# Returns:
[
    {
        "type": "BRUTE_FORCE_ATTEMPT",
        "severity": "HIGH",
        "ip_address": "192.168.1.100",
        "failed_attempts": 15,
        "timestamp": "2025-09-03T10:30:45Z"
    },
    {
        "type": "PRIVILEGE_ESCALATION_ATTEMPT",
        "severity": "HIGH",
        "user_id": "user-456",
        "failed_attempts": 25,
        "timestamp": "2025-09-03T10:31:00Z"
    },
    {
        "type": "OFF_HOURS_ADMIN_ACCESS",
        "severity": "MEDIUM",
        "user_id": "admin-001",
        "time": "2025-09-03T02:15:00Z",
        "action": "config_change"
    }
]
```

#### Patterns Detected
1. **Brute Force Attacks**: >5 failed logins in 15 minutes
2. **Privilege Escalation**: >10 authorization denials in 10 minutes
3. **Off-Hours Admin Access**: Admin actions between 10 PM - 6 AM
4. **Rapid Configuration Changes**: Multiple admin actions in short window

### 5. Tamper-Evident Audit Trail

**Status**: ✅ IMPLEMENTED

#### Immutable Event Chain
```python
from services.agent.agent.security_logging import AuditTrail

audit_trail = AuditTrail(secret_key="your-secret-key")

# Add entry
entry = audit_trail.add_entry(
    action="UPDATE",
    actor_id="user-123",
    resource="user:456:role",
    changes={"from": "user", "to": "admin"}
)

# Entry includes:
{
    "sequence": 42,
    "timestamp": "2025-09-03T10:30:45Z",
    "action": "UPDATE",
    "actor_id": "user-123",
    "resource": "user:456:role",
    "changes": {"from": "user", "to": "admin"},
    "previous_hash": "abc123...",  # Chain integrity
    "integrity_hash": "def456..."   # HMAC-SHA256
}

# Verify integrity
is_valid, error = audit_trail.verify_integrity()
if not is_valid:
    print(f"Audit trail tampered: {error}")
```

#### Tampering Detection
- Each entry includes HMAC-SHA256 signature
- Chain validation ensures no entries deleted/modified
- Previous hash creates unbroken chain
- Constant-time comparison prevents timing attacks

### 6. Log Storage & Retention

**Status**: ✅ CONFIGURED

#### Storage Locations
```
security-events.jsonl          # Application logs (local)
/var/log/agentic-platform/     # System logs
loki:3100                       # Log aggregation
prometheus:9090                 # Metrics
```

#### Retention Policies
```yaml
# File-based logs (security-events.jsonl)
Retention: 365 days
Rotation: Daily (logs-2025-09-03.jsonl)
Compression: gzip (logs-2025-09-02.jsonl.gz)

# Loki (time-series logs)
Retention: 90 days
Retention Policy: Keep high-severity indefinitely

# Prometheus metrics
Retention: 15 days
Long-term storage: Archive to S3/GCS
```

#### Configuration (loki-config.yaml)
```yaml
retention_period: 90d  # Keep 90 days
retention_deletes_enabled: true

# Archive old logs
table_manager:
  retention_deletes_enabled: true
  retention_period: 2160h  # 90 days
```

### 7. Real-Time Alerting

**Status**: ✅ IMPLEMENTED

#### Alert Triggers
```python
# Register alert callbacks
def send_email_alert(event):
    send_email(
        to="security-team@example.com",
        subject=f"Security Alert: {event['event_type']}",
        body=json.dumps(event, indent=2)
    )

def send_slack_alert(event):
    notify_slack(
        channel="#security-alerts",
        message=f"🚨 {event['event_type']}: {event['details']}"
    )

logger.register_alert_callback(send_email_alert)
logger.register_alert_callback(send_slack_alert)

# Alerts automatically triggered for HIGH/CRITICAL events
```

#### Grafana Alerts
Configured in: `observability/grafana/dashboards/owasp-a09-security-monitoring.json`

**Alert Rules**:
1. **Brute Force Attack**: >5 failed logins in 15 minutes
2. **Rate Limiting Attack**: >50 rate limit violations in 5 minutes
3. **Critical Event**: Any CRITICAL severity event
4. **Data Integrity Failure**: Integrity check failure
5. **Unusual Admin Activity**: >20 admin actions in 1 hour

### 8. Integration with Monitoring Stack

**Status**: ✅ CONFIGURED

#### Loki (Log Aggregation)
```bash
# Query logs in Loki
{job="agentic-platform"} | json
{job="agentic-platform", severity="CRITICAL"}
{job="agentic-platform"} | error
```

#### Prometheus (Metrics)
```bash
# Security event metrics
security_events_total{event_type="AUTH_LOGIN_FAILURE"}
rate(security_events_total[5m])
increase(security_events_total{severity="CRITICAL"}[1h])
```

#### Grafana Dashboard
- File: `observability/grafana/dashboards/owasp-a09-security-monitoring.json`
- Real-time event timeline
- Failed login statistics
- Rate limit violations
- Authorization denial tracking
- Raw log viewer
- Admin action audit trail

### 9. Querying & Auditing

**Status**: ✅ IMPLEMENTED

#### Query Events
```python
# Get recent failures
failures = logger.get_events(
    event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
    minutes=60
)

# Get user audit trail
user_trail = logger.get_audit_trail(user_id="user-123")
for event in user_trail:
    print(f"{event['timestamp']}: {event['event_type']}")

# Get critical events
critical = logger.get_events(
    severity=SeverityLevel.CRITICAL,
    minutes=1440  # Last 24 hours
)
```

#### Generate Reports
```python
# Generate security report
report = {
    "period": "last_24h",
    "total_events": len(logger.event_buffer),
    "critical_events": len(logger.get_events(severity=SeverityLevel.CRITICAL)),
    "auth_failures": len(logger.get_events(event_type=SecurityEventType.AUTH_LOGIN_FAILURE)),
    "admin_actions": len(logger.get_events(event_type=SecurityEventType.ADMIN_ACTION)),
    "anomalies": logger.detect_anomalies()
}
```

## Configuration

### Environment Variables
```bash
# Security logging
SECURITY_LOG_LEVEL=DEBUG
SECURITY_LOG_FILE=security-events.jsonl
SECURITY_EVENT_BUFFER_SIZE=10000

# Alerting
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_TO=security-team@example.com
ALERT_SLACK_ENABLED=false
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Loki integration
LOKI_URL=http://loki:3100
LOKI_RETENTION_DAYS=90

# Grafana
GRAFANA_URL=http://localhost:3000
GRAFANA_ADMIN_PASSWORD=<secure-password>
```

### FastAPI Integration
```python
from fastapi import FastAPI, Request
from services.agent.agent.security_logging import SecurityLogger, SecurityEventType, SeverityLevel

app = FastAPI()
logger = SecurityLogger("security")

@app.post("/auth/login")
async def login(request: Request, credentials: dict):
    try:
        user = authenticate(credentials)
        
        # Log successful login
        logger.log_event(
            event_type=SecurityEventType.AUTH_LOGIN_SUCCESS,
            severity=SeverityLevel.INFO,
            user_id=user.id,
            ip_address=request.client.host
        )
        
        return {"token": create_token(user)}
    except InvalidCredentials:
        # Log failed login
        logger.log_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SeverityLevel.MEDIUM,
            ip_address=request.client.host,
            details={"reason": "invalid_credentials"}
        )
        raise
```

## Running & Testing

### Test Security Logger
```bash
# Start logger and test events
python -c "
from services.agent.agent.security_logging import SecurityLogger, SecurityEventType, SeverityLevel

logger = SecurityLogger()

# Log test events
logger.log_event(
    SecurityEventType.AUTH_LOGIN_FAILURE,
    SeverityLevel.HIGH,
    user_id='test-user',
    ip_address='192.168.1.1',
    details={'attempt': 1}
)

# Query events
failures = logger.get_events(event_type=SecurityEventType.AUTH_LOGIN_FAILURE)
print(f'Failed logins: {len(failures)}')

# Detect anomalies
anomalies = logger.detect_anomalies()
print(f'Anomalies found: {len(anomalies)}')
"
```

### View Logs in Docker
```bash
# Tail security logs
docker exec -it ui-console tail -f security-events.jsonl

# Filter for critical events
docker exec -it ui-console grep "CRITICAL" security-events.jsonl | jq .

# Search Loki
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="agentic-platform"} | severity="CRITICAL"' \
  | jq .
```

### Access Grafana Dashboard
```bash
# Dashboard
http://localhost:3000
Username: admin
Password: $GRAFANA_ADMIN_PASSWORD

# Navigate to: Dashboards > Browse > "OWASP A09 Security Monitoring"
```

## Compliance & Standards

### Standards Compliance
- ✅ **OWASP A09:2025**: Security Logging and Alerting Failures
- ✅ **NIST SP 800-53**: Audit and Accountability (AU)
- ✅ **PCI DSS**: Requirement 10 (Logging and Monitoring)
- ✅ **ISO 27001**: A.12.4 (Logging)
- ✅ **GDPR**: Audit trail for data access

### Log Content Compliance
- ✅ No sensitive data logged (passwords, PII)
- ✅ Timestamps for all events
- ✅ User identification
- ✅ Action identification
- ✅ Resource identification
- ✅ Outcome (success/failure)

## Troubleshooting

### Logs Not Appearing
```bash
# Check if security logger is initialized
ps aux | grep "python.*security"

# Check file permissions
ls -la security-events.jsonl

# Verify Loki is running
docker ps | grep loki

# Check Loki logs
docker logs loki 2>&1 | grep -i error
```

### High Volume of Events
```python
# Adjust buffer size
logger = SecurityLogger(max_buffer=50000)

# Implement filtering to reduce noise
# Only log severity >= MEDIUM
if event.severity >= SeverityLevel.MEDIUM:
    logger.log_event(...)
```

### Alerts Not Triggering
```bash
# Check Grafana alert configuration
# Admin > Alerting > Alert Rules

# Test alert manually
curl -X POST http://localhost:3000/api/alerts/test \
  -H "Content-Type: application/json" \
  -d '{"alert": "test-alert"}'

# Check Grafana logs
docker logs grafana | grep -i alert
```

## Future Enhancements

### Phase 2 (Next Quarter)
- [ ] Real-time SIEM integration (Splunk, ELK)
- [ ] Machine learning anomaly detection
- [ ] Automated incident response
- [ ] Log encryption at rest
- [ ] Tamper-proof audit vault

### Phase 3 (Later)
- [ ] Blockchain-based audit trail
- [ ] Federated security logging
- [ ] Advanced threat intelligence
- [ ] Predictive security analytics
- [ ] Autonomous response automation

## References

- **OWASP A09:2025**: https://owasp.org/Top10/A09_2025-Security_Logging_and_Monitoring_Failures/
- **NIST Logging**: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5
- **Grafana Alerting**: https://grafana.com/docs/grafana/latest/alerting/
- **Loki**: https://grafana.com/oss/loki/

---

**Last Updated**: 2025-09-03  
**Version**: 1.0.0  
**Maintained By**: Security Operations Team
