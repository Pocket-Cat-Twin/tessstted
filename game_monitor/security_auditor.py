"""
Security Audit and Compliance System for Game Monitor

Comprehensive security event logging, compliance monitoring,
and forensic analysis capabilities for security incidents.
"""

import os
import json
import time
import threading
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import logging
import gzip
import shutil

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .performance_profiler import get_performance_profiler, profile_performance
from .encryption_manager import get_encryption_manager

logger = get_logger(__name__)


class ComplianceStandard(Enum):
    """Supported compliance standards"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    CUSTOM = "custom"


class AuditLevel(Enum):
    """Audit logging levels"""
    MINIMAL = "minimal"          # Critical events only
    STANDARD = "standard"        # Standard security events
    DETAILED = "detailed"        # All security-relevant events
    FORENSIC = "forensic"        # Everything for forensic analysis


@dataclass
class SecurityAuditEvent:
    """Comprehensive security audit event"""
    event_id: str
    timestamp: float
    event_type: str
    severity: str
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: str
    source_process: Optional[str]
    resource: str
    action: str
    outcome: str  # SUCCESS, FAILURE, DENIED
    risk_score: int
    details: Dict[str, Any]
    compliance_tags: Set[str]
    file_hash: Optional[str]
    signature: Optional[str]


@dataclass
class ComplianceRule:
    """Compliance monitoring rule"""
    rule_id: str
    standard: ComplianceStandard
    description: str
    event_pattern: Dict[str, Any]
    severity_threshold: str
    retention_days: int
    notification_required: bool
    auto_response: Optional[str]


class SecurityAuditor:
    """Advanced security audit and compliance monitoring system"""
    
    def __init__(self, audit_dir: str = "logs/security_audit"):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        self.error_handler = get_error_handler()
        self.profiler = get_performance_profiler()
        self.encryption_manager = get_encryption_manager()
        
        # Audit configuration
        self.audit_level = AuditLevel.STANDARD
        self.encrypt_audit_logs = True
        self.compress_old_logs = True
        self.retention_days = 2555  # 7 years default retention
        
        # Compliance rules
        self.compliance_rules = {}
        self.active_standards = {ComplianceStandard.ISO_27001}
        
        # Event storage and processing
        self.audit_events = []
        self.event_buffer_size = 1000
        self.current_log_file = None
        self.log_rotation_size = 10 * 1024 * 1024  # 10MB
        
        # Threading for async processing
        self._audit_lock = threading.Lock()
        self._processing_thread = None
        self._stop_processing = threading.Event()
        
        # Forensic capabilities
        self.forensic_mode = False
        self.integrity_checking = True
        self.chain_of_custody = {}
        
        # Statistics
        self.audit_stats = {
            'events_logged': 0,
            'compliance_violations': 0,
            'high_severity_events': 0,
            'files_created': 0,
            'total_size_bytes': 0,
            'integrity_checks_passed': 0,
            'integrity_checks_failed': 0
        }
        
        # Initialize audit system
        self._initialize_audit_system()
        
        logger.info(f"SecurityAuditor initialized with {self.audit_level.value} logging level")
    
    def _initialize_audit_system(self):
        """Initialize the audit system"""
        try:
            # Load compliance rules
            self._load_compliance_rules()
            
            # Start processing thread
            self._start_audit_processing()
            
            # Create initial log file
            self._rotate_log_file()
            
            # Log audit system initialization
            self.log_security_event(
                event_type="SYSTEM_EVENT",
                severity="INFO",
                user_id="system",
                resource="security_auditor",
                action="initialize",
                outcome="SUCCESS",
                details={'audit_level': self.audit_level.value, 'retention_days': self.retention_days}
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize audit system: {e}")
    
    def _load_compliance_rules(self):
        """Load compliance monitoring rules"""
        # ISO 27001 rules
        self.compliance_rules['iso27001_access_control'] = ComplianceRule(
            rule_id='iso27001_access_control',
            standard=ComplianceStandard.ISO_27001,
            description='Monitor access control violations',
            event_pattern={'event_type': 'PERMISSION_DENIED'},
            severity_threshold='MEDIUM',
            retention_days=2555,  # 7 years
            notification_required=True,
            auto_response='log_and_alert'
        )
        
        self.compliance_rules['iso27001_authentication'] = ComplianceRule(
            rule_id='iso27001_authentication',
            standard=ComplianceStandard.ISO_27001,
            description='Monitor authentication events',
            event_pattern={'event_type': 'AUTH_FAILURE'},
            severity_threshold='HIGH',
            retention_days=2555,
            notification_required=True,
            auto_response='count_and_block'
        )
        
        # GDPR rules (if applicable)
        self.compliance_rules['gdpr_data_access'] = ComplianceRule(
            rule_id='gdpr_data_access',
            standard=ComplianceStandard.GDPR,
            description='Monitor personal data access',
            event_pattern={'event_type': 'DATA_ACCESS', 'resource': 'personal_data'},
            severity_threshold='LOW',
            retention_days=2190,  # 6 years
            notification_required=False,
            auto_response=None
        )
        
        logger.info(f"Loaded {len(self.compliance_rules)} compliance rules")
    
    def _start_audit_processing(self):
        """Start background audit processing thread"""
        def audit_processor():
            while not self._stop_processing.wait(5):  # Process every 5 seconds
                try:
                    self._process_audit_queue()
                    self._check_compliance_violations()
                    self._perform_integrity_checks()
                    
                except Exception as e:
                    logger.error(f"Audit processing error: {e}")
                    time.sleep(30)  # Wait longer after errors
        
        self._processing_thread = threading.Thread(target=audit_processor, daemon=True)
        self._processing_thread.start()
    
    @profile_performance("security_auditor.log_security_event")
    def log_security_event(self, event_type: str, severity: str, user_id: Optional[str],
                         resource: str, action: str, outcome: str,
                         session_id: Optional[str] = None, source_ip: str = "localhost",
                         details: Optional[Dict[str, Any]] = None, risk_score: int = 1) -> str:
        """Log a security event with comprehensive audit trail"""
        try:
            # Generate unique event ID
            event_id = self._generate_event_id()
            
            # Determine compliance tags
            compliance_tags = self._determine_compliance_tags(event_type, severity, details or {})
            
            # Create audit event
            audit_event = SecurityAuditEvent(
                event_id=event_id,
                timestamp=time.time(),
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                source_ip=source_ip,
                source_process=os.getpid(),
                resource=resource,
                action=action,
                outcome=outcome,
                risk_score=risk_score,
                details=details or {},
                compliance_tags=compliance_tags,
                file_hash=None,  # Will be set during persistence
                signature=None   # Will be set during persistence
            )
            
            # Add to processing queue
            with self._audit_lock:
                self.audit_events.append(audit_event)
                self.audit_stats['events_logged'] += 1
                
                if severity in ['HIGH', 'CRITICAL']:
                    self.audit_stats['high_severity_events'] += 1
            
            # For high-severity events, process immediately
            if severity in ['HIGH', 'CRITICAL'] or self.forensic_mode:
                self._persist_audit_event(audit_event)
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            return ""
    
    def _generate_event_id(self) -> str:
        """Generate cryptographically secure event ID"""
        import secrets
        return f"AUD_{int(time.time())}_{secrets.token_hex(8)}"
    
    def _determine_compliance_tags(self, event_type: str, severity: str, details: Dict[str, Any]) -> Set[str]:
        """Determine which compliance standards apply to this event"""
        tags = set()
        
        for rule_id, rule in self.compliance_rules.items():
            if self._matches_compliance_pattern(event_type, severity, details, rule):
                tags.add(rule.standard.value)
        
        return tags
    
    def _matches_compliance_pattern(self, event_type: str, severity: str, 
                                  details: Dict[str, Any], rule: ComplianceRule) -> bool:
        """Check if event matches compliance rule pattern"""
        pattern = rule.event_pattern
        
        # Check event type
        if 'event_type' in pattern and event_type != pattern['event_type']:
            return False
        
        # Check severity threshold
        severity_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if severity_levels.index(severity) < severity_levels.index(rule.severity_threshold):
            return False
        
        # Check other pattern criteria
        for key, value in pattern.items():
            if key == 'event_type':
                continue
            if key not in details or details[key] != value:
                return False
        
        return True
    
    def _process_audit_queue(self):
        """Process queued audit events"""
        events_to_process = []
        
        with self._audit_lock:
            if len(self.audit_events) >= self.event_buffer_size or len(self.audit_events) > 0:
                events_to_process = self.audit_events.copy()
                self.audit_events.clear()
        
        for event in events_to_process:
            self._persist_audit_event(event)
    
    def _persist_audit_event(self, event: SecurityAuditEvent):
        """Persist audit event to secure storage"""
        try:
            # Generate file hash for integrity
            event_json = json.dumps(asdict(event), sort_keys=True)
            event.file_hash = hashlib.sha256(event_json.encode()).hexdigest()
            
            # Sign event if encryption is available
            if self.encryption_manager and self.integrity_checking:
                event.signature = self._sign_audit_event(event)
            
            # Write to current log file
            self._write_to_log_file(event)
            
            # Check if log rotation is needed
            if self._should_rotate_log():
                self._rotate_log_file()
            
        except Exception as e:
            logger.error(f"Failed to persist audit event {event.event_id}: {e}")
    
    def _sign_audit_event(self, event: SecurityAuditEvent) -> Optional[str]:
        """Create cryptographic signature for audit event"""
        try:
            if not self.encryption_manager:
                return None
            
            # Create signature payload
            payload = {
                'event_id': event.event_id,
                'timestamp': event.timestamp,
                'file_hash': event.file_hash,
                'user_id': event.user_id,
                'action': event.action
            }
            
            # Encrypt the payload as signature
            encrypted = self.encryption_manager.encrypt_data(
                json.dumps(payload, sort_keys=True), 
                "asymmetric_default_private"
            )
            
            return encrypted.ciphertext if encrypted else None
            
        except Exception as e:
            logger.warning(f"Failed to sign audit event: {e}")
            return None
    
    def _write_to_log_file(self, event: SecurityAuditEvent):
        """Write audit event to current log file"""
        if not self.current_log_file:
            self._rotate_log_file()
        
        try:
            event_data = asdict(event)
            event_data['compliance_tags'] = list(event_data['compliance_tags'])  # Convert set to list
            
            log_line = json.dumps(event_data) + '\n'
            
            if self.encrypt_audit_logs and self.encryption_manager:
                # Encrypt log line
                encrypted = self.encryption_manager.encrypt_data(log_line, "config_encryption")
                if encrypted:
                    log_line = json.dumps(asdict(encrypted)) + '\n'
            
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
                f.flush()  # Ensure immediate write for audit integrity
            
        except Exception as e:
            logger.error(f"Failed to write to audit log file: {e}")
    
    def _should_rotate_log(self) -> bool:
        """Check if log file should be rotated"""
        if not self.current_log_file or not os.path.exists(self.current_log_file):
            return True
        
        try:
            file_size = os.path.getsize(self.current_log_file)
            return file_size >= self.log_rotation_size
        except Exception:
            return True
    
    def _rotate_log_file(self):
        """Rotate to a new log file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"security_audit_{timestamp}.log"
            
            if self.encrypt_audit_logs:
                log_filename += ".enc"
            
            self.current_log_file = self.audit_dir / log_filename
            
            # Create new log file with initial entry
            initial_event = {
                'event_type': 'LOG_ROTATION',
                'timestamp': time.time(),
                'message': f'New audit log file created: {log_filename}',
                'previous_file': str(self.current_log_file) if hasattr(self, 'current_log_file') else None
            }
            
            with open(self.current_log_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(initial_event) + '\n')
            
            self.audit_stats['files_created'] += 1
            logger.info(f"Created new audit log file: {log_filename}")
            
            # Compress old log files if configured
            if self.compress_old_logs:
                self._compress_old_logs()
            
        except Exception as e:
            logger.error(f"Failed to rotate audit log file: {e}")
    
    def _compress_old_logs(self):
        """Compress old audit log files"""
        try:
            # Find log files older than 1 day
            cutoff_time = time.time() - 86400
            
            for log_file in self.audit_dir.glob("security_audit_*.log"):
                if log_file != self.current_log_file:
                    stat = log_file.stat()
                    if stat.st_mtime < cutoff_time:
                        # Compress the file
                        compressed_file = log_file.with_suffix('.log.gz')
                        
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(compressed_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Remove original file
                        log_file.unlink()
                        logger.debug(f"Compressed audit log: {log_file.name}")
            
        except Exception as e:
            logger.warning(f"Failed to compress old audit logs: {e}")
    
    def _check_compliance_violations(self):
        """Check for compliance violations in recent events"""
        try:
            # This would implement complex compliance checking
            # For now, we'll do basic pattern matching
            
            recent_events = [e for e in self.audit_events if time.time() - e.timestamp < 300]  # Last 5 minutes
            
            for rule in self.compliance_rules.values():
                violations = [e for e in recent_events 
                            if self._matches_compliance_pattern(e.event_type, e.severity, e.details, rule)]
                
                if violations and rule.notification_required:
                    self._handle_compliance_violation(rule, violations)
            
        except Exception as e:
            logger.error(f"Compliance checking failed: {e}")
    
    def _handle_compliance_violation(self, rule: ComplianceRule, violations: List[SecurityAuditEvent]):
        """Handle detected compliance violation"""
        self.audit_stats['compliance_violations'] += len(violations)
        
        # Log compliance violation
        self.log_security_event(
            event_type="COMPLIANCE_VIOLATION",
            severity="HIGH",
            user_id="system",
            resource="compliance_monitor",
            action="violation_detected",
            outcome="DETECTED",
            details={
                'rule_id': rule.rule_id,
                'standard': rule.standard.value,
                'violation_count': len(violations),
                'description': rule.description
            },
            risk_score=8
        )
        
        logger.warning(f"Compliance violation detected: {rule.description} ({len(violations)} events)")
    
    def _perform_integrity_checks(self):
        """Perform integrity checks on audit logs"""
        try:
            # Check current log file integrity
            if self.current_log_file and os.path.exists(self.current_log_file):
                if self._verify_log_file_integrity(self.current_log_file):
                    self.audit_stats['integrity_checks_passed'] += 1
                else:
                    self.audit_stats['integrity_checks_failed'] += 1
                    logger.error(f"Integrity check failed for {self.current_log_file}")
            
        except Exception as e:
            logger.error(f"Integrity checking failed: {e}")
    
    def _verify_log_file_integrity(self, log_file: Path) -> bool:
        """Verify integrity of an audit log file"""
        try:
            # This would implement comprehensive integrity checking
            # For now, just check if file is readable and valid JSON lines
            
            with open(log_file, 'r', encoding='utf-8') as f:
                line_count = 0
                for line in f:
                    if line.strip():
                        json.loads(line)  # Validate JSON format
                        line_count += 1
                
                return line_count > 0
            
        except Exception as e:
            logger.warning(f"Integrity check failed for {log_file}: {e}")
            return False
    
    def search_audit_events(self, start_time: Optional[float] = None, end_time: Optional[float] = None,
                          event_type: Optional[str] = None, user_id: Optional[str] = None,
                          severity: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Search audit events with filtering"""
        try:
            matching_events = []
            
            # Search in current memory buffer
            for event in self.audit_events:
                if self._matches_search_criteria(event, start_time, end_time, event_type, user_id, severity):
                    matching_events.append(asdict(event))
                    if len(matching_events) >= limit:
                        break
            
            # If we need more results, search log files
            if len(matching_events) < limit:
                file_events = self._search_log_files(start_time, end_time, event_type, user_id, severity, 
                                                   limit - len(matching_events))
                matching_events.extend(file_events)
            
            return sorted(matching_events, key=lambda e: e['timestamp'], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"Audit event search failed: {e}")
            return []
    
    def _matches_search_criteria(self, event: SecurityAuditEvent, start_time: Optional[float],
                               end_time: Optional[float], event_type: Optional[str],
                               user_id: Optional[str], severity: Optional[str]) -> bool:
        """Check if event matches search criteria"""
        if start_time and event.timestamp < start_time:
            return False
        if end_time and event.timestamp > end_time:
            return False
        if event_type and event.event_type != event_type:
            return False
        if user_id and event.user_id != user_id:
            return False
        if severity and event.severity != severity:
            return False
        
        return True
    
    def _search_log_files(self, start_time: Optional[float], end_time: Optional[float],
                        event_type: Optional[str], user_id: Optional[str], 
                        severity: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Search historical log files"""
        matching_events = []
        
        try:
            # Get all log files sorted by modification time (newest first)
            log_files = sorted(
                self.audit_dir.glob("security_audit_*.log*"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            for log_file in log_files:
                if len(matching_events) >= limit:
                    break
                
                try:
                    file_events = self._read_log_file_events(log_file, start_time, end_time, 
                                                           event_type, user_id, severity, 
                                                           limit - len(matching_events))
                    matching_events.extend(file_events)
                    
                except Exception as e:
                    logger.warning(f"Failed to read audit log file {log_file}: {e}")
                    continue
            
            return matching_events
            
        except Exception as e:
            logger.error(f"Log file search failed: {e}")
            return []
    
    def _read_log_file_events(self, log_file: Path, start_time: Optional[float],
                            end_time: Optional[float], event_type: Optional[str],
                            user_id: Optional[str], severity: Optional[str],
                            limit: int) -> List[Dict[str, Any]]:
        """Read events from a specific log file"""
        events = []
        
        try:
            # Handle compressed files
            if log_file.suffix == '.gz':
                opener = gzip.open
            else:
                opener = open
            
            with opener(log_file, 'rt', encoding='utf-8') as f:
                for line in f:
                    if len(events) >= limit:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event_data = json.loads(line)
                        
                        # Skip log rotation entries
                        if event_data.get('event_type') == 'LOG_ROTATION':
                            continue
                        
                        # If encrypted, decrypt first
                        if self.encrypt_audit_logs and 'algorithm' in event_data:
                            # This is an encrypted event
                            decrypted_data = self._decrypt_audit_event(event_data)
                            if decrypted_data:
                                event_data = decrypted_data
                            else:
                                continue
                        
                        # Check search criteria
                        if self._matches_event_data_criteria(event_data, start_time, end_time, 
                                                           event_type, user_id, severity):
                            events.append(event_data)
                    
                    except json.JSONDecodeError:
                        continue  # Skip malformed lines
            
            return events
            
        except Exception as e:
            logger.warning(f"Failed to read events from {log_file}: {e}")
            return []
    
    def _decrypt_audit_event(self, encrypted_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Decrypt an encrypted audit event"""
        try:
            if not self.encryption_manager:
                return None
            
            from .encryption_manager import EncryptedData
            encrypted_event = EncryptedData(**encrypted_data)
            
            decrypted_bytes = self.encryption_manager.decrypt_data(encrypted_event)
            if decrypted_bytes:
                return json.loads(decrypted_bytes.decode('utf-8'))
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to decrypt audit event: {e}")
            return None
    
    def _matches_event_data_criteria(self, event_data: Dict[str, Any], start_time: Optional[float],
                                   end_time: Optional[float], event_type: Optional[str],
                                   user_id: Optional[str], severity: Optional[str]) -> bool:
        """Check if event data matches search criteria"""
        timestamp = event_data.get('timestamp', 0)
        
        if start_time and timestamp < start_time:
            return False
        if end_time and timestamp > end_time:
            return False
        if event_type and event_data.get('event_type') != event_type:
            return False
        if user_id and event_data.get('user_id') != user_id:
            return False
        if severity and event_data.get('severity') != severity:
            return False
        
        return True
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive audit system statistics"""
        try:
            total_log_size = sum(f.stat().st_size for f in self.audit_dir.glob("*") if f.is_file())
            log_file_count = len(list(self.audit_dir.glob("security_audit_*.log*")))
            
            return {
                'audit_level': self.audit_level.value,
                'encryption_enabled': self.encrypt_audit_logs,
                'compression_enabled': self.compress_old_logs,
                'retention_days': self.retention_days,
                'current_log_file': str(self.current_log_file) if self.current_log_file else None,
                'total_log_files': log_file_count,
                'total_log_size_mb': total_log_size / (1024 * 1024),
                'events_in_buffer': len(self.audit_events),
                'compliance_standards': [std.value for std in self.active_standards],
                'statistics': self.audit_stats.copy()
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {'error': str(e)}
    
    def cleanup_old_logs(self, days_to_keep: int = None):
        """Clean up audit logs older than specified days"""
        try:
            cleanup_days = days_to_keep or self.retention_days
            cutoff_time = time.time() - (cleanup_days * 86400)
            
            removed_count = 0
            removed_size = 0
            
            for log_file in self.audit_dir.glob("security_audit_*.log*"):
                if log_file != self.current_log_file:
                    stat = log_file.stat()
                    if stat.st_mtime < cutoff_time:
                        removed_size += stat.st_size
                        log_file.unlink()
                        removed_count += 1
            
            # Log cleanup activity
            self.log_security_event(
                event_type="MAINTENANCE",
                severity="INFO",
                user_id="system",
                resource="audit_logs",
                action="cleanup_old_logs",
                outcome="SUCCESS",
                details={
                    'files_removed': removed_count,
                    'size_freed_mb': removed_size / (1024 * 1024),
                    'retention_days': cleanup_days
                }
            )
            
            logger.info(f"Cleaned up {removed_count} old audit log files ({removed_size / (1024 * 1024):.1f}MB)")
            
        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
    
    def shutdown(self):
        """Gracefully shutdown audit system"""
        try:
            # Stop processing thread
            self._stop_processing.set()
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=10)
            
            # Process any remaining events
            self._process_audit_queue()
            
            # Log shutdown
            self.log_security_event(
                event_type="SYSTEM_EVENT",
                severity="INFO",
                user_id="system",
                resource="security_auditor",
                action="shutdown",
                outcome="SUCCESS",
                details={'events_processed': self.audit_stats['events_logged']}
            )
            
            logger.info("SecurityAuditor shutdown completed")
            
        except Exception as e:
            logger.error(f"Audit system shutdown error: {e}")


# Global security auditor instance
_security_auditor_instance = None
_auditor_lock = threading.Lock()

def get_security_auditor() -> SecurityAuditor:
    """Get singleton security auditor instance"""
    global _security_auditor_instance
    if _security_auditor_instance is None:
        with _auditor_lock:
            if _security_auditor_instance is None:
                _security_auditor_instance = SecurityAuditor()
    return _security_auditor_instance


# Convenience function for external use
def audit_security_event(event_type: str, severity: str, user_id: Optional[str],
                        resource: str, action: str, outcome: str, **kwargs) -> str:
    """Convenience function to log security event"""
    auditor = get_security_auditor()
    return auditor.log_security_event(event_type, severity, user_id, resource, action, outcome, **kwargs)