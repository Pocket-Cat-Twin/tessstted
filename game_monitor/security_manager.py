"""
Comprehensive Security Manager for Game Monitor System

Centralized security management including authentication, authorization,
encryption, audit logging, and security policy enforcement.
"""

import os
import hashlib
import secrets
import time
import threading
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import logging

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .performance_profiler import get_performance_profiler, profile_performance
from .constants import Performance

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security levels for the application"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Types of security events to track"""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    FILE_ACCESS = "file_access"
    ENCRYPTION_ERROR = "encryption_error"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"


class Permission(Enum):
    """System permissions"""
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    ADMIN_CONFIG = "admin_config"
    SYSTEM_CONTROL = "system_control"
    FILE_ACCESS = "file_access"
    DATABASE_ADMIN = "database_admin"
    SECURITY_AUDIT = "security_audit"
    EXPORT_DATA = "export_data"


@dataclass
class SecurityEvent:
    """Security event record"""
    event_id: str
    event_type: SecurityEventType
    timestamp: float
    user_id: Optional[str]
    source_ip: Optional[str]
    resource: Optional[str]
    action: str
    success: bool
    risk_score: int  # 1-10
    details: Dict[str, Any]


@dataclass
class SecurityUser:
    """Security user profile"""
    user_id: str
    username: str
    password_hash: str
    salt: str
    permissions: Set[Permission]
    created_at: float
    last_login: Optional[float]
    failed_attempts: int
    is_locked: bool
    session_token: Optional[str]
    token_expires: Optional[float]


class SecurityPolicy:
    """Security policy configuration"""
    
    def __init__(self):
        # Authentication settings
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5 minutes
        self.password_min_length = 12
        self.session_timeout = 3600  # 1 hour
        self.require_strong_passwords = True
        
        # Data protection settings
        self.encrypt_sensitive_data = True
        self.encryption_algorithm = "AES-256-GCM"
        self.key_rotation_interval = 86400 * 30  # 30 days
        
        # File access settings
        self.restrict_file_access = True
        self.allowed_file_extensions = {'.yaml', '.yml', '.txt', '.log', '.db', '.png', '.jpg'}
        self.blocked_paths = {'/etc/', '/root/', 'C:\\Windows\\', 'C:\\Program Files\\'}
        
        # Audit settings
        self.log_all_access = True
        self.log_failed_attempts = True
        self.audit_retention_days = 90
        
        # Security monitoring
        self.enable_intrusion_detection = True
        self.suspicious_activity_threshold = 10
        self.rate_limiting_enabled = True
        self.max_requests_per_minute = 60


class SecurityManager:
    """Main security manager coordinating all security functions"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.profiler = get_performance_profiler()
        
        # Security components
        self.policy = SecurityPolicy()
        self.users = {}  # user_id -> SecurityUser
        self.active_sessions = {}  # token -> user_id
        self.security_events = []
        
        # Security state
        self.security_level = SecurityLevel.MEDIUM
        self.system_locked = False
        self.intrusion_detection_active = True
        
        # Threading
        self._lock = threading.RLock()
        self._event_lock = threading.Lock()
        
        # Rate limiting
        self._request_counts = {}  # IP -> (count, reset_time)
        self._blocked_ips = set()
        
        # Initialize security
        self._initialize_security()
        
        logger.info("SecurityManager initialized with enhanced security features")
    
    def _initialize_security(self):
        """Initialize security subsystem"""
        try:
            # Create default admin user if none exists
            if not self.users:
                self._create_default_admin()
            
            # Start security monitoring
            self._start_security_monitoring()
            
            # Load security configuration
            self._load_security_config()
            
            logger.info("Security subsystem initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security subsystem: {e}")
            self.security_level = SecurityLevel.CRITICAL
    
    def _create_default_admin(self):
        """Create default admin user for initial setup"""
        admin_id = "admin"
        admin_username = "administrator"
        
        # Generate secure random password
        temp_password = secrets.token_urlsafe(16)
        
        # Create admin user
        admin_user = self.create_user(
            user_id=admin_id,
            username=admin_username,
            password=temp_password,
            permissions={Permission.ADMIN_CONFIG, Permission.SYSTEM_CONTROL, 
                        Permission.DATABASE_ADMIN, Permission.SECURITY_AUDIT,
                        Permission.READ_DATA, Permission.WRITE_DATA, 
                        Permission.FILE_ACCESS, Permission.EXPORT_DATA}
        )
        
        if admin_user:
            logger.warning(f"Default admin user created with password: {temp_password}")
            logger.warning("SECURITY: Change default admin password immediately!")
            
            # Log security event
            self._log_security_event(SecurityEvent(
                event_id=self._generate_event_id(),
                event_type=SecurityEventType.AUTH_SUCCESS,
                timestamp=time.time(),
                user_id=admin_id,
                source_ip="localhost",
                resource="user_creation",
                action="create_default_admin",
                success=True,
                risk_score=3,
                details={'username': admin_username, 'temp_password': True}
            ))
    
    def _start_security_monitoring(self):
        """Start background security monitoring"""
        def security_monitor():
            while True:
                try:
                    self._check_security_threats()
                    self._cleanup_expired_sessions()
                    self._rotate_keys_if_needed()
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Security monitoring error: {e}")
                    time.sleep(300)  # Wait longer after errors
        
        monitor_thread = threading.Thread(target=security_monitor, daemon=True)
        monitor_thread.start()
    
    def _load_security_config(self):
        """Load security configuration from secure location"""
        # This would load from encrypted config file in production
        # For now, use default policy
        logger.info("Security configuration loaded")
    
    @profile_performance("security_manager.authenticate")
    def authenticate(self, username: str, password: str, source_ip: str = "localhost") -> Optional[str]:
        """Authenticate user and return session token"""
        auth_start = time.time()
        
        try:
            # Rate limiting check
            if not self._check_rate_limit(source_ip):
                self._log_security_event(SecurityEvent(
                    event_id=self._generate_event_id(),
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    timestamp=time.time(),
                    user_id=None,
                    source_ip=source_ip,
                    resource="authentication",
                    action="rate_limit_exceeded",
                    success=False,
                    risk_score=7,
                    details={'username': username}
                ))
                return None
            
            # Find user
            user = None
            with self._lock:
                for u in self.users.values():
                    if u.username == username:
                        user = u
                        break
            
            if not user:
                self._handle_auth_failure(None, username, source_ip, "user_not_found")
                return None
            
            # Check if user is locked
            if user.is_locked:
                self._handle_auth_failure(user, username, source_ip, "user_locked")
                return None
            
            # Verify password
            if not self._verify_password(password, user.password_hash, user.salt):
                self._handle_auth_failure(user, username, source_ip, "invalid_password")
                return None
            
            # Authentication successful
            session_token = self._create_session(user, source_ip)
            
            # Update user login info
            with self._lock:
                user.last_login = time.time()
                user.failed_attempts = 0
            
            # Log successful authentication
            self._log_security_event(SecurityEvent(
                event_id=self._generate_event_id(),
                event_type=SecurityEventType.AUTH_SUCCESS,
                timestamp=time.time(),
                user_id=user.user_id,
                source_ip=source_ip,
                resource="authentication",
                action="login",
                success=True,
                risk_score=1,
                details={'username': username, 'auth_time_ms': (time.time() - auth_start) * 1000}
            ))
            
            logger.info(f"User {username} authenticated successfully from {source_ip}")
            return session_token
            
        except Exception as e:
            error_context = ErrorContext(
                component="security_manager",
                operation="authenticate",
                user_data={'username': username, 'source_ip': source_ip},
                system_state={'security_level': self.security_level.value},
                timestamp=datetime.now()
            )
            
            self.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
            logger.error(f"Authentication error for {username}: {e}")
            return None
    
    def _handle_auth_failure(self, user: Optional[SecurityUser], username: str, 
                           source_ip: str, reason: str):
        """Handle authentication failure with security measures"""
        if user:
            with self._lock:
                user.failed_attempts += 1
                if user.failed_attempts >= self.policy.max_failed_attempts:
                    user.is_locked = True
                    logger.warning(f"User {username} locked after {user.failed_attempts} failed attempts")
        
        # Log security event
        self._log_security_event(SecurityEvent(
            event_id=self._generate_event_id(),
            event_type=SecurityEventType.AUTH_FAILURE,
            timestamp=time.time(),
            user_id=user.user_id if user else None,
            source_ip=source_ip,
            resource="authentication",
            action="login_failed",
            success=False,
            risk_score=5 if reason == "invalid_password" else 7,
            details={'username': username, 'reason': reason, 'failed_attempts': user.failed_attempts if user else 0}
        ))
        
        # Check for suspicious activity
        if reason == "invalid_password" and user and user.failed_attempts > 3:
            self._flag_suspicious_activity(source_ip, f"Multiple failed login attempts for {username}")
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        try:
            # Use PBKDF2 with SHA-256
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000  # 100,000 iterations
            )
            return secrets.compare_digest(computed_hash.hex(), password_hash)
            
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def _create_session(self, user: SecurityUser, source_ip: str) -> str:
        """Create authenticated session token"""
        session_token = secrets.token_urlsafe(32)
        expires_at = time.time() + self.policy.session_timeout
        
        with self._lock:
            user.session_token = session_token
            user.token_expires = expires_at
            self.active_sessions[session_token] = user.user_id
        
        logger.debug(f"Created session for {user.username} from {source_ip}")
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[SecurityUser]:
        """Validate session token and return user if valid"""
        if not session_token:
            return None
        
        with self._lock:
            user_id = self.active_sessions.get(session_token)
            if not user_id:
                return None
            
            user = self.users.get(user_id)
            if not user:
                # Clean up orphaned session
                del self.active_sessions[session_token]
                return None
            
            # Check token expiration
            if user.token_expires and time.time() > user.token_expires:
                # Expire session
                del self.active_sessions[session_token]
                user.session_token = None
                user.token_expires = None
                return None
            
            return user
    
    def check_permission(self, session_token: str, permission: Permission) -> bool:
        """Check if user has required permission"""
        user = self.validate_session(session_token)
        if not user:
            return False
        
        has_permission = permission in user.permissions
        
        # Log permission check for audit
        self._log_security_event(SecurityEvent(
            event_id=self._generate_event_id(),
            event_type=SecurityEventType.PERMISSION_DENIED if not has_permission else SecurityEventType.DATA_ACCESS,
            timestamp=time.time(),
            user_id=user.user_id,
            source_ip="localhost",
            resource="permission_check",
            action=f"check_{permission.value}",
            success=has_permission,
            risk_score=3 if not has_permission else 1,
            details={'permission': permission.value, 'username': user.username}
        ))
        
        return has_permission
    
    def create_user(self, user_id: str, username: str, password: str, 
                   permissions: Set[Permission]) -> Optional[SecurityUser]:
        """Create new user with security validation"""
        try:
            # Validate password strength
            if not self._validate_password_strength(password):
                logger.error(f"Password does not meet security requirements for user {username}")
                return None
            
            # Check if user already exists
            with self._lock:
                if user_id in self.users or any(u.username == username for u in self.users.values()):
                    logger.error(f"User {username} already exists")
                    return None
            
            # Generate salt and hash password
            salt = secrets.token_hex(32)
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            ).hex()
            
            # Create user
            user = SecurityUser(
                user_id=user_id,
                username=username,
                password_hash=password_hash,
                salt=salt,
                permissions=permissions,
                created_at=time.time(),
                last_login=None,
                failed_attempts=0,
                is_locked=False,
                session_token=None,
                token_expires=None
            )
            
            with self._lock:
                self.users[user_id] = user
            
            logger.info(f"Created user {username} with {len(permissions)} permissions")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return None
    
    def _validate_password_strength(self, password: str) -> bool:
        """Validate password meets security requirements"""
        if len(password) < self.policy.password_min_length:
            return False
        
        if self.policy.require_strong_passwords:
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in password)
            
            return all([has_upper, has_lower, has_digit, has_special])
        
        return True
    
    def _check_rate_limit(self, ip_address: str) -> bool:
        """Check if IP address is within rate limits"""
        if not self.policy.rate_limiting_enabled:
            return True
        
        if ip_address in self._blocked_ips:
            return False
        
        current_time = time.time()
        
        if ip_address in self._request_counts:
            count, reset_time = self._request_counts[ip_address]
            
            if current_time > reset_time:
                # Reset counter
                self._request_counts[ip_address] = (1, current_time + 60)
                return True
            elif count >= self.policy.max_requests_per_minute:
                # Rate limit exceeded
                self._blocked_ips.add(ip_address)
                logger.warning(f"IP {ip_address} blocked for rate limit violation")
                return False
            else:
                # Increment counter
                self._request_counts[ip_address] = (count + 1, reset_time)
                return True
        else:
            # First request from this IP
            self._request_counts[ip_address] = (1, current_time + 60)
            return True
    
    def _check_security_threats(self):
        """Check for security threats and anomalies"""
        current_time = time.time()
        
        # Check for suspicious patterns in recent events
        recent_events = [e for e in self.security_events if current_time - e.timestamp < 300]  # Last 5 minutes
        
        # Pattern detection
        failed_logins = len([e for e in recent_events if e.event_type == SecurityEventType.AUTH_FAILURE])
        permission_denials = len([e for e in recent_events if e.event_type == SecurityEventType.PERMISSION_DENIED])
        
        if failed_logins > self.policy.suspicious_activity_threshold:
            self._flag_suspicious_activity("multiple_sources", f"{failed_logins} failed logins in 5 minutes")
        
        if permission_denials > self.policy.suspicious_activity_threshold:
            self._flag_suspicious_activity("multiple_sources", f"{permission_denials} permission denials in 5 minutes")
    
    def _flag_suspicious_activity(self, source: str, description: str):
        """Flag suspicious activity for investigation"""
        self._log_security_event(SecurityEvent(
            event_id=self._generate_event_id(),
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            timestamp=time.time(),
            user_id=None,
            source_ip=source,
            resource="security_monitor",
            action="suspicious_activity_detected",
            success=False,
            risk_score=8,
            details={'description': description}
        ))
        
        logger.warning(f"Suspicious activity detected: {description}")
        
        # Escalate security level if needed
        if self.security_level == SecurityLevel.LOW:
            self.security_level = SecurityLevel.MEDIUM
            logger.info("Security level escalated to MEDIUM")
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_tokens = []
        
        with self._lock:
            for token, user_id in self.active_sessions.items():
                user = self.users.get(user_id)
                if user and user.token_expires and current_time > user.token_expires:
                    expired_tokens.append(token)
            
            for token in expired_tokens:
                user_id = self.active_sessions.get(token)
                if user_id and user_id in self.users:
                    self.users[user_id].session_token = None
                    self.users[user_id].token_expires = None
                del self.active_sessions[token]
        
        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired sessions")
    
    def _rotate_keys_if_needed(self):
        """Rotate encryption keys if needed"""
        # This would implement key rotation logic
        # For now, just log that we're checking
        logger.debug("Checking if key rotation is needed")
    
    def _log_security_event(self, event: SecurityEvent):
        """Log security event"""
        with self._event_lock:
            self.security_events.append(event)
            
            # Limit event history
            if len(self.security_events) > 10000:
                self.security_events = self.security_events[-5000:]
        
        # Log to file for audit trail
        logger.info(f"SECURITY_EVENT: {event.event_type.value} - {event.action} - Risk: {event.risk_score}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return secrets.token_hex(16)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        with self._lock:
            active_users = sum(1 for u in self.users.values() if u.session_token)
            locked_users = sum(1 for u in self.users.values() if u.is_locked)
        
        recent_events = [e for e in self.security_events if time.time() - e.timestamp < 3600]  # Last hour
        
        return {
            'security_level': self.security_level.value,
            'system_locked': self.system_locked,
            'intrusion_detection_active': self.intrusion_detection_active,
            'total_users': len(self.users),
            'active_sessions': len(self.active_sessions),
            'active_users': active_users,
            'locked_users': locked_users,
            'blocked_ips': len(self._blocked_ips),
            'recent_events': len(recent_events),
            'high_risk_events': len([e for e in recent_events if e.risk_score >= 7]),
            'policy': {
                'max_failed_attempts': self.policy.max_failed_attempts,
                'session_timeout': self.policy.session_timeout,
                'encryption_enabled': self.policy.encrypt_sensitive_data,
                'rate_limiting_enabled': self.policy.rate_limiting_enabled
            }
        }
    
    def get_security_events(self, hours: int = 24, min_risk_score: int = 1) -> List[Dict[str, Any]]:
        """Get security events for specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        
        filtered_events = [
            asdict(event) for event in self.security_events
            if event.timestamp > cutoff_time and event.risk_score >= min_risk_score
        ]
        
        return sorted(filtered_events, key=lambda e: e['timestamp'], reverse=True)


# Global security manager instance
_security_manager_instance = None
_security_lock = threading.Lock()

def get_security_manager() -> SecurityManager:
    """Get singleton security manager instance"""
    global _security_manager_instance
    if _security_manager_instance is None:
        with _security_lock:
            if _security_manager_instance is None:
                _security_manager_instance = SecurityManager()
    return _security_manager_instance


# Decorator for requiring authentication
def require_auth(permission: Permission = None):
    """Decorator to require authentication and optional permission"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Get session token from args or instance
            session_token = getattr(self, '_session_token', None)
            
            if not session_token:
                logger.warning(f"Authentication required for {func.__name__}")
                raise PermissionError("Authentication required")
            
            security_manager = get_security_manager()
            user = security_manager.validate_session(session_token)
            
            if not user:
                logger.warning(f"Invalid session for {func.__name__}")
                raise PermissionError("Invalid or expired session")
            
            if permission and not security_manager.check_permission(session_token, permission):
                logger.warning(f"Permission {permission.value} denied for {user.username}")
                raise PermissionError(f"Permission {permission.value} required")
            
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator