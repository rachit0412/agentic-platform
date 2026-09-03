"""
A09:2025 - Security Logging and Alerting Failures
Comprehensive Security Event Logging & Monitoring

Provides:
- Security event classification and logging
- Real-time alerting on suspicious activities
- Audit trail with tamper detection
- Integration with Loki/Grafana monitoring
- SIEM compatibility (Splunk, ELK)
"""

import json
import logging
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from enum import Enum
from functools import wraps
import threading
from collections import deque


class SecurityEventType(Enum):
    """Classification of security-relevant events."""
    
    # Authentication events
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"
    AUTH_MFA_ATTEMPT = "AUTH_MFA_ATTEMPT"
    AUTH_MFA_FAILURE = "AUTH_MFA_FAILURE"
    AUTH_SESSION_CREATED = "AUTH_SESSION_CREATED"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_SESSION_INVALIDATED = "AUTH_SESSION_INVALIDATED"
    
    # Authorization events
    AUTHZ_DENIED = "AUTHZ_DENIED"
    AUTHZ_ROLE_CHANGE = "AUTHZ_ROLE_CHANGE"
    AUTHZ_PERMISSION_CHANGE = "AUTHZ_PERMISSION_CHANGE"
    
    # Vulnerability events
    VULN_RATE_LIMIT_EXCEEDED = "VULN_RATE_LIMIT_EXCEEDED"
    VULN_INJECTION_ATTEMPT = "VULN_INJECTION_ATTEMPT"
    VULN_XSS_ATTEMPT = "VULN_XSS_ATTEMPT"
    VULN_CSRF_ATTEMPT = "VULN_CSRF_ATTEMPT"
    VULN_XXE_ATTEMPT = "VULN_XXE_ATTEMPT"
    
    # Data events
    DATA_INTEGRITY_FAILURE = "DATA_INTEGRITY_FAILURE"
    DATA_ENCRYPTION_FAILURE = "DATA_ENCRYPTION_FAILURE"
    DATA_EXFILTRATION_ATTEMPT = "DATA_EXFILTRATION_ATTEMPT"
    
    # Administrative events
    ADMIN_ACTION = "ADMIN_ACTION"
    ADMIN_CONFIG_CHANGE = "ADMIN_CONFIG_CHANGE"
    ADMIN_ACCESS_GRANTED = "ADMIN_ACCESS_GRANTED"
    ADMIN_ACCESS_REVOKED = "ADMIN_ACCESS_REVOKED"
    
    # System events
    SYSTEM_ERROR = "SYSTEM_ERROR"
    SYSTEM_WARNING = "SYSTEM_WARNING"
    SYSTEM_HEALTH_DEGRADED = "SYSTEM_HEALTH_DEGRADED"
    
    # Compliance events
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    COMPLIANCE_CHECK_PASSED = "COMPLIANCE_CHECK_PASSED"


class SeverityLevel(Enum):
    """Event severity levels following CVSS scale."""
    
    CRITICAL = 5  # CVSS > 9.0: Immediate action required
    HIGH = 4      # CVSS 7.0-8.9: Address within 24 hours
    MEDIUM = 3    # CVSS 4.0-6.9: Address within 1 week
    LOW = 2       # CVSS 0.1-3.9: Monitor and plan fix
    INFO = 1      # Informational only


class SecurityLogger:
    """Central logging system for security events."""
    
    def __init__(self, logger_name: str = "security", max_buffer: int = 10000):
        """Initialize security logger.
        
        Args:
            logger_name: Logger name for Python logging
            max_buffer: Maximum in-memory buffer size for events
        """
        self.logger = logging.getLogger(logger_name)
        self.event_buffer = deque(maxlen=max_buffer)
        self.alert_callbacks: List[callable] = []
        self.lock = threading.RLock()
        
        # Setup JSON formatter for structured logging
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers for structured JSON output."""
        # Console handler with JSON format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(message)s'  # Already JSON from our formatters
        ))
        self.logger.addHandler(console_handler)
        
        # File handler for persistence
        try:
            file_handler = logging.FileHandler('security-events.jsonl')
            file_handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(file_handler)
        except Exception as e:
            logging.warning(f"Could not setup file handler: {e}")
        
        self.logger.setLevel(logging.DEBUG)
    
    def log_event(self, 
                  event_type: SecurityEventType,
                  severity: SeverityLevel,
                  user_id: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Log a security event.
        
        Args:
            event_type: Type of security event
            severity: Severity level
            user_id: User ID associated with event
            ip_address: IP address (for network-based events)
            details: Event-specific details
            context: Additional context (request, response, etc.)
            
        Returns:
            Event record that was logged
        """
        event_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "severity": severity.name,
            "user_id": user_id or "unknown",
            "ip_address": ip_address or "unknown",
            "details": details or {},
            "context": context or {},
        }
        
        with self.lock:
            # Add to buffer
            self.event_buffer.append(event_record)
            
            # Log to application logger
            self.logger.log(
                self._severity_to_log_level(severity),
                json.dumps(event_record)
            )
            
            # Trigger alerts for critical events
            if severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                self._trigger_alerts(event_record)
        
        return event_record
    
    def _severity_to_log_level(self, severity: SeverityLevel) -> int:
        """Convert severity level to Python logging level."""
        mapping = {
            SeverityLevel.CRITICAL: logging.CRITICAL,
            SeverityLevel.HIGH: logging.ERROR,
            SeverityLevel.MEDIUM: logging.WARNING,
            SeverityLevel.LOW: logging.INFO,
            SeverityLevel.INFO: logging.DEBUG,
        }
        return mapping.get(severity, logging.INFO)
    
    def _trigger_alerts(self, event_record: Dict[str, Any]):
        """Trigger alert callbacks for high-severity events."""
        for callback in self.alert_callbacks:
            try:
                callback(event_record)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def register_alert_callback(self, callback: callable):
        """Register callback for alert notifications.
        
        Callback signature: callback(event_record: Dict) -> None
        """
        self.alert_callbacks.append(callback)
    
    def get_events(self, 
                   event_type: Optional[SecurityEventType] = None,
                   severity: Optional[SeverityLevel] = None,
                   user_id: Optional[str] = None,
                   minutes: int = 60) -> List[Dict[str, Any]]:
        """Query logged events with optional filters.
        
        Args:
            event_type: Filter by event type
            severity: Filter by severity level
            user_id: Filter by user ID
            minutes: Look back this many minutes
            
        Returns:
            List of matching events
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        results = []
        
        with self.lock:
            for event in self.event_buffer:
                # Parse timestamp
                try:
                    event_time = datetime.fromisoformat(event['timestamp'])
                    if event_time < cutoff:
                        continue
                except:
                    pass
                
                # Apply filters
                if event_type and event['event_type'] != event_type.value:
                    continue
                if severity and event['severity'] != severity.name:
                    continue
                if user_id and event['user_id'] != user_id:
                    continue
                
                results.append(event)
        
        return results
    
    def get_audit_trail(self, user_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for a user."""
        return self.get_events(user_id=user_id, minutes=10080)  # 7 days
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in logs.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Pattern 1: Multiple failed login attempts from same IP
        failed_logins = self.get_events(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            minutes=15
        )
        
        ip_counts = {}
        for event in failed_logins:
            ip = event.get('ip_address')
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        for ip, count in ip_counts.items():
            if count > 5:
                anomalies.append({
                    "type": "BRUTE_FORCE_ATTEMPT",
                    "severity": "HIGH",
                    "ip_address": ip,
                    "failed_attempts": count,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Pattern 2: Rapid authorization failures
        authz_failures = self.get_events(
            event_type=SecurityEventType.AUTHZ_DENIED,
            minutes=10
        )
        
        user_counts = {}
        for event in authz_failures:
            user = event.get('user_id')
            user_counts[user] = user_counts.get(user, 0) + 1
        
        for user, count in user_counts.items():
            if count > 10:
                anomalies.append({
                    "type": "PRIVILEGE_ESCALATION_ATTEMPT",
                    "severity": "HIGH",
                    "user_id": user,
                    "failed_attempts": count,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Pattern 3: Unusual times of access (off-hours)
        admin_actions = self.get_events(
            event_type=SecurityEventType.ADMIN_ACTION,
            minutes=1440  # Last 24 hours
        )
        
        for event in admin_actions:
            try:
                event_time = datetime.fromisoformat(event['timestamp'])
                hour = event_time.hour
                if hour < 6 or hour > 22:  # Off-hours: 10 PM - 6 AM
                    anomalies.append({
                        "type": "OFF_HOURS_ADMIN_ACCESS",
                        "severity": "MEDIUM",
                        "user_id": event.get('user_id'),
                        "time": event['timestamp'],
                        "action": event.get('details', {}).get('action')
                    })
            except:
                pass
        
        return anomalies


class AuditTrail:
    """Tamper-evident audit trail for compliance."""
    
    def __init__(self, secret_key: str):
        """Initialize audit trail with tampering detection.
        
        Args:
            secret_key: Secret key for integrity verification
        """
        self.secret_key = secret_key.encode()
        self.entries: List[Dict[str, Any]] = []
    
    def add_entry(self, 
                  action: str,
                  actor_id: str,
                  resource: str,
                  changes: Dict[str, Any]) -> Dict[str, Any]:
        """Add tamper-evident entry to audit trail.
        
        Args:
            action: Action performed (CREATE, UPDATE, DELETE, etc.)
            actor_id: User who performed action
            resource: Resource affected
            changes: Changes made
            
        Returns:
            Entry record with integrity hash
        """
        previous_hash = self.entries[-1].get('integrity_hash') if self.entries else ""
        
        entry = {
            "sequence": len(self.entries) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "actor_id": actor_id,
            "resource": resource,
            "changes": changes,
            "previous_hash": previous_hash,
        }
        
        # Calculate integrity hash (includes previous hash for tampering detection)
        entry_json = json.dumps(entry, sort_keys=True)
        integrity_hash = hmac.new(
            self.secret_key,
            entry_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        entry['integrity_hash'] = integrity_hash
        self.entries.append(entry)
        
        return entry
    
    def verify_integrity(self) -> tuple[bool, Optional[str]]:
        """Verify audit trail has not been tampered with.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        for i, entry in enumerate(self.entries):
            # Verify current entry
            stored_hash = entry.get('integrity_hash')
            
            entry_copy = dict(entry)
            del entry_copy['integrity_hash']
            entry_json = json.dumps(entry_copy, sort_keys=True)
            
            computed_hash = hmac.new(
                self.secret_key,
                entry_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(stored_hash, computed_hash):
                return (False, f"Entry {i} integrity check failed")
            
            # Verify chain integrity
            if i > 0:
                previous_hash = entry.get('previous_hash')
                actual_previous = self.entries[i-1].get('integrity_hash')
                if previous_hash != actual_previous:
                    return (False, f"Entry {i} chain broken (entry {i-1} was modified)")
        
        return (True, None)
    
    def get_entries(self, 
                   actor_id: Optional[str] = None,
                   action: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query audit trail with filters.
        
        Args:
            actor_id: Filter by actor
            action: Filter by action
            
        Returns:
            Matching entries
        """
        results = []
        for entry in self.entries:
            if actor_id and entry['actor_id'] != actor_id:
                continue
            if action and entry['action'] != action:
                continue
            results.append(entry)
        return results


# ──────────────────────────────────────────────────────────────────────────
# Decorators for Auto-Logging
# ──────────────────────────────────────────────────────────────────────────

def log_security_event(event_type: SecurityEventType,
                       severity: SeverityLevel):
    """Decorator to automatically log security events.
    
    Usage:
        @log_security_event(
            SecurityEventType.AUTH_LOGIN_SUCCESS,
            SeverityLevel.INFO
        )
        async def login_endpoint(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            result = await func(request, *args, **kwargs)
            
            # Log the event
            user_id = getattr(request.state, 'user_id', None)
            ip_address = request.client.host if request.client else None
            
            # Assume module-level logger is available
            logger = logging.getLogger('security')
            logger.log(
                logging.WARNING if severity == SeverityLevel.HIGH else logging.INFO,
                json.dumps({
                    "event": event_type.value,
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            
            return result
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────────────────────
# Export public API
# ──────────────────────────────────────────────────────────────────────────

__all__ = [
    'SecurityLogger',
    'SecurityEventType',
    'SeverityLevel',
    'AuditTrail',
    'log_security_event',
]
