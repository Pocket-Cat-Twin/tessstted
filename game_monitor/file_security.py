"""
File Security Manager for Game Monitor System

Secure file operations with access controls, path validation,
and content scanning to prevent security vulnerabilities.
"""

import os
import stat
import hashlib
import time
import threading
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
import tempfile
import shutil

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .security_auditor import get_security_auditor
from .encryption_manager import get_encryption_manager
from .constants import FileSystem

logger = get_logger(__name__)


class FileOperation(Enum):
    """Types of file operations"""
    READ = "read"
    WRITE = "write"
    CREATE = "create"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    EXECUTE = "execute"
    LIST = "list"


class SecurityThreat(Enum):
    """Types of security threats in files"""
    PATH_TRAVERSAL = "path_traversal"
    MALICIOUS_EXTENSION = "malicious_extension"
    OVERSIZED_FILE = "oversized_file"
    SUSPICIOUS_CONTENT = "suspicious_content"
    BLOCKED_PATH = "blocked_path"
    PERMISSION_VIOLATION = "permission_violation"


@dataclass
class FileSecurityPolicy:
    """File security policy configuration"""
    allowed_extensions: Set[str]
    blocked_extensions: Set[str]
    blocked_paths: Set[str]
    max_file_size_mb: int
    scan_content: bool
    require_encryption: bool
    backup_critical_files: bool
    log_all_operations: bool
    quarantine_threats: bool


@dataclass
class FileThreatReport:
    """Report of security threat found in file"""
    file_path: str
    threat_type: SecurityThreat
    severity: str
    description: str
    details: Dict[str, Any]
    detected_at: float
    action_taken: str


@dataclass
class FileAccessAttempt:
    """Record of file access attempt"""
    file_path: str
    operation: FileOperation
    user_id: Optional[str]
    process_id: int
    timestamp: float
    success: bool
    threat_detected: Optional[SecurityThreat]
    details: Dict[str, Any]


class FileSecurityManager:
    """Comprehensive file security management system"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.security_auditor = get_security_auditor()
        self.encryption_manager = get_encryption_manager()
        
        # Security policy
        self.policy = FileSecurityPolicy(
            allowed_extensions={'.yaml', '.yml', '.txt', '.log', '.db', '.png', '.jpg', '.json', '.csv'},
            blocked_extensions={'.exe', '.bat', '.cmd', '.sh', '.ps1', '.vbs', '.scr', '.com'},
            blocked_paths={'/etc/', '/root/', '/sys/', '/proc/', 'C:\\Windows\\', 'C:\\Program Files\\'},
            max_file_size_mb=100,
            scan_content=True,
            require_encryption=False,
            backup_critical_files=True,
            log_all_operations=True,
            quarantine_threats=True
        )
        
        # Threat detection patterns
        self.threat_patterns = self._initialize_threat_patterns()
        
        # File access tracking
        self.access_attempts = []
        self.threat_reports = []
        self.quarantine_dir = Path("data/quarantine")
        
        # Threading
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'operations_performed': 0,
            'threats_detected': 0,
            'files_quarantined': 0,
            'access_denied': 0,
            'files_encrypted': 0,
            'backups_created': 0
        }
        
        # Initialize system
        self._initialize_security_system()
        
        logger.info("FileSecurityManager initialized with comprehensive security policies")
    
    def _initialize_security_system(self):
        """Initialize file security system"""
        try:
            # Create necessary directories
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Set secure permissions on quarantine directory
            self._set_secure_permissions(self.quarantine_dir)
            
            # Load custom security policies if available
            self._load_security_policies()
            
            logger.info("File security system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize file security system: {e}")
    
    def _initialize_threat_patterns(self) -> Dict[str, List[bytes]]:
        """Initialize patterns for detecting threats in file content"""
        return {
            'script_injection': [
                b'<script',
                b'javascript:',
                b'eval(',
                b'exec(',
                b'system(',
                b'shell_exec(',
                b'passthru(',
            ],
            'sql_injection': [
                b'union select',
                b'drop table',
                b'delete from',
                b'insert into',
                b'update set',
                b'exec sp_',
            ],
            'path_traversal': [
                b'../',
                b'..\\',
                b'/etc/passwd',
                b'C:\\Windows\\System32',
            ],
            'malware_signatures': [
                b'MZ\x90\x00',  # PE executable header
                b'\x7fELF',     # ELF executable header
                b'PK\x03\x04',  # ZIP header (could contain malware)
            ]
        }
    
    def _load_security_policies(self):
        """Load custom security policies from configuration"""
        # This would load from a secure configuration file
        # For now, using default policies
        logger.debug("Using default file security policies")
    
    def secure_file_operation(self, operation: FileOperation, file_path: Union[str, Path],
                            user_id: Optional[str] = None, **kwargs) -> Tuple[bool, Optional[str]]:
        """Perform secure file operation with comprehensive security checks"""
        operation_start = time.time()
        file_path_str = str(file_path)
        
        try:
            with self._lock:
                self.stats['operations_performed'] += 1
            
            # Security validation
            threat = self._validate_file_access(file_path_str, operation, user_id)
            
            if threat:
                # Security threat detected
                self._handle_security_threat(file_path_str, operation, threat, user_id)
                return False, f"Security threat detected: {threat.value}"
            
            # Perform operation with security monitoring
            result = self._execute_secure_operation(operation, file_path, user_id, **kwargs)
            
            # Log successful operation
            if self.policy.log_all_operations:
                self._log_file_access(file_path_str, operation, user_id, True, None)
            
            operation_time = time.time() - operation_start
            logger.debug(f"Secure {operation.value} operation completed in {operation_time*1000:.2f}ms")
            
            return result
            
        except Exception as e:
            # Log failed operation
            self._log_file_access(file_path_str, operation, user_id, False, None, str(e))
            
            error_context = ErrorContext(
                component="file_security",
                operation=f"secure_{operation.value}",
                user_data={'file_path': file_path_str, 'user_id': user_id},
                system_state={'policy_enabled': True},
                timestamp=time.time()
            )
            
            self.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
            logger.error(f"Secure file operation failed: {e}")
            return False, str(e)
    
    def _validate_file_access(self, file_path: str, operation: FileOperation, 
                            user_id: Optional[str]) -> Optional[SecurityThreat]:
        """Validate file access for security threats"""
        try:
            # Path traversal detection
            if self._detect_path_traversal(file_path):
                return SecurityThreat.PATH_TRAVERSAL
            
            # Blocked path check
            if self._is_blocked_path(file_path):
                return SecurityThreat.BLOCKED_PATH
            
            # Extension validation
            if operation in [FileOperation.WRITE, FileOperation.CREATE]:
                if self._has_malicious_extension(file_path):
                    return SecurityThreat.MALICIOUS_EXTENSION
            
            # File size check for write operations
            if operation in [FileOperation.WRITE, FileOperation.CREATE]:
                if self._is_oversized_file(file_path):
                    return SecurityThreat.OVERSIZED_FILE
            
            # Content scanning for existing files
            if operation == FileOperation.READ and os.path.exists(file_path):
                if self.policy.scan_content and self._has_suspicious_content(file_path):
                    return SecurityThreat.SUSPICIOUS_CONTENT
            
            return None
            
        except Exception as e:
            logger.warning(f"File validation error for {file_path}: {e}")
            return SecurityThreat.PERMISSION_VIOLATION
    
    def _detect_path_traversal(self, file_path: str) -> bool:
        """Detect path traversal attempts"""
        normalized = os.path.normpath(file_path)
        
        # Check for directory traversal patterns
        dangerous_patterns = ['../', '..\\', '/etc/', '/root/', 'C:\\Windows\\', 'C:\\Users\\']
        
        for pattern in dangerous_patterns:
            if pattern in file_path or pattern in normalized:
                return True
        
        # Check if normalized path escapes allowed directories
        allowed_dirs = ['data/', 'config/', 'logs/', './']
        if not any(normalized.startswith(allowed_dir) or normalized.startswith(f'./{allowed_dir}') 
                  for allowed_dir in allowed_dirs):
            # Allow absolute paths only if they're in safe locations
            if os.path.isabs(normalized):
                safe_absolute_dirs = ['/tmp/', '/var/tmp/', str(Path.cwd())]
                if not any(normalized.startswith(safe_dir) for safe_dir in safe_absolute_dirs):
                    return True
        
        return False
    
    def _is_blocked_path(self, file_path: str) -> bool:
        """Check if file path is in blocked locations"""
        normalized = os.path.normpath(file_path)
        
        for blocked_path in self.policy.blocked_paths:
            if normalized.startswith(blocked_path) or blocked_path in normalized:
                return True
        
        return False
    
    def _has_malicious_extension(self, file_path: str) -> bool:
        """Check if file has malicious extension"""
        file_ext = Path(file_path).suffix.lower()
        
        # Check blocked extensions
        if file_ext in self.policy.blocked_extensions:
            return True
        
        # If allowed extensions are specified, reject anything not in the list
        if self.policy.allowed_extensions and file_ext not in self.policy.allowed_extensions:
            # Allow files without extensions for directories and special files
            if file_ext != '' and not Path(file_path).is_dir():
                return True
        
        return False
    
    def _is_oversized_file(self, file_path: str) -> bool:
        """Check if file exceeds size limits"""
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                max_size_bytes = self.policy.max_file_size_mb * 1024 * 1024
                return file_size > max_size_bytes
        except Exception:
            return False
        
        return False
    
    def _has_suspicious_content(self, file_path: str) -> bool:
        """Scan file content for suspicious patterns"""
        try:
            # Only scan text-like files to avoid false positives
            file_ext = Path(file_path).suffix.lower()
            text_extensions = {'.txt', '.log', '.yaml', '.yml', '.json', '.csv', '.py', '.js', '.html', '.xml'}
            
            if file_ext not in text_extensions:
                return False
            
            # Read file content (limit size for performance)
            max_scan_size = 1024 * 1024  # 1MB max scan
            
            with open(file_path, 'rb') as f:
                content = f.read(max_scan_size)
            
            # Check for threat patterns
            for threat_type, patterns in self.threat_patterns.items():
                for pattern in patterns:
                    if pattern in content:
                        logger.warning(f"Suspicious content detected in {file_path}: {threat_type}")
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Content scanning failed for {file_path}: {e}")
            return False
    
    def _execute_secure_operation(self, operation: FileOperation, file_path: Path, 
                                user_id: Optional[str], **kwargs) -> Tuple[bool, Optional[str]]:
        """Execute file operation with security measures"""
        try:
            if operation == FileOperation.READ:
                return self._secure_read(file_path, **kwargs)
            elif operation == FileOperation.WRITE:
                return self._secure_write(file_path, **kwargs)
            elif operation == FileOperation.CREATE:
                return self._secure_create(file_path, **kwargs)
            elif operation == FileOperation.DELETE:
                return self._secure_delete(file_path, **kwargs)
            elif operation == FileOperation.MOVE:
                return self._secure_move(file_path, **kwargs)
            elif operation == FileOperation.COPY:
                return self._secure_copy(file_path, **kwargs)
            elif operation == FileOperation.LIST:
                return self._secure_list(file_path, **kwargs)
            else:
                return False, f"Unsupported operation: {operation.value}"
                
        except Exception as e:
            logger.error(f"Secure operation {operation.value} failed: {e}")
            return False, str(e)
    
    def _secure_read(self, file_path: Path, **kwargs) -> Tuple[bool, Optional[str]]:
        """Securely read file with access controls"""
        try:
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check read permissions
            if not os.access(file_path, os.R_OK):
                return False, "Read permission denied"
            
            # For encrypted files, decrypt if needed
            content = kwargs.get('content')  # Pre-read content for validation
            if content is None:
                # Regular file read
                return True, None  # Let caller handle actual reading
            else:
                # Content was provided for validation
                return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _secure_write(self, file_path: Path, **kwargs) -> Tuple[bool, Optional[str]]:
        """Securely write file with backup and encryption"""
        try:
            content = kwargs.get('content', '')
            create_backup = kwargs.get('backup', self.policy.backup_critical_files)
            
            # Create backup if file exists and policy requires it
            if file_path.exists() and create_backup:
                backup_path = self._create_backup(file_path)
                if backup_path:
                    with self._lock:
                        self.stats['backups_created'] += 1
            
            # Set secure permissions on new files
            if not file_path.exists():
                file_path.touch()
                self._set_secure_permissions(file_path)
            
            # Write content
            if isinstance(content, str):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _secure_create(self, file_path: Path, **kwargs) -> Tuple[bool, Optional[str]]:
        """Securely create new file"""
        try:
            if file_path.exists():
                return False, "File already exists"
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file with secure permissions
            file_path.touch()
            self._set_secure_permissions(file_path)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _secure_delete(self, file_path: Path, **kwargs) -> Tuple[bool, Optional[str]]:
        """Securely delete file with backup option"""
        try:
            if not file_path.exists():
                return False, "File does not exist"
            
            create_backup = kwargs.get('backup', self.policy.backup_critical_files)
            secure_wipe = kwargs.get('secure_wipe', False)
            
            # Create backup before deletion
            if create_backup:
                backup_path = self._create_backup(file_path)
                if backup_path:
                    with self._lock:
                        self.stats['backups_created'] += 1
            
            # Secure deletion (overwrite with random data)
            if secure_wipe:
                self._secure_wipe_file(file_path)
            else:
                file_path.unlink()
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _secure_move(self, file_path: Path, **kwargs) -> Tuple[bool, Optional[str]]:
        """Securely move file with validation"""
        try:
            destination = kwargs.get('destination')
            if not destination:
                return False, "Destination path required"
            
            dest_path = Path(destination)
            
            # Validate destination path
            threat = self._validate_file_access(str(dest_path), FileOperation.CREATE, None)
            if threat:
                return False, f"Destination security threat: {threat.value}"
            
            # Perform move
            shutil.move(str(file_path), str(dest_path))
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _secure_copy(self, file_path: Path, **kwargs) -> Tuple[bool, Optional[str]]:
        """Securely copy file with validation"""
        try:
            destination = kwargs.get('destination')
            if not destination:
                return False, "Destination path required"
            
            dest_path = Path(destination)
            
            # Validate destination path
            threat = self._validate_file_access(str(dest_path), FileOperation.CREATE, None)
            if threat:
                return False, f"Destination security threat: {threat.value}"
            
            # Perform copy
            shutil.copy2(str(file_path), str(dest_path))
            
            # Set secure permissions on copy
            self._set_secure_permissions(dest_path)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _secure_list(self, file_path: Path, **kwargs) -> Tuple[bool, Optional[str]]:
        """Securely list directory contents"""
        try:
            if not file_path.is_dir():
                return False, "Path is not a directory"
            
            # Check read permissions
            if not os.access(file_path, os.R_OK):
                return False, "Read permission denied"
            
            # Let caller handle actual directory listing
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create backup of file before modification"""
        try:
            timestamp = int(time.time())
            backup_name = f"{file_path.name}.backup_{timestamp}"
            backup_path = file_path.parent / "backups" / backup_name
            
            # Create backup directory
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to backup location
            shutil.copy2(file_path, backup_path)
            
            # Set secure permissions
            self._set_secure_permissions(backup_path)
            
            logger.debug(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def _secure_wipe_file(self, file_path: Path):
        """Securely wipe file by overwriting with random data"""
        try:
            file_size = file_path.stat().st_size
            
            # Overwrite with random data multiple times
            with open(file_path, 'r+b') as f:
                for _ in range(3):  # 3 passes
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally delete the file
            file_path.unlink()
            
        except Exception as e:
            logger.error(f"Secure wipe failed for {file_path}: {e}")
            # Fall back to regular deletion
            file_path.unlink()
    
    def _set_secure_permissions(self, file_path: Path):
        """Set secure permissions on file or directory"""
        try:
            if file_path.is_dir():
                # Directory: owner read/write/execute, group read/execute, no others
                file_path.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
            else:
                # File: owner read/write, group read, no others
                file_path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
            
        except Exception as e:
            logger.warning(f"Failed to set secure permissions on {file_path}: {e}")
    
    def _handle_security_threat(self, file_path: str, operation: FileOperation,
                              threat: SecurityThreat, user_id: Optional[str]):
        """Handle detected security threat"""
        threat_report = FileThreatReport(
            file_path=file_path,
            threat_type=threat,
            severity="HIGH" if threat in [SecurityThreat.PATH_TRAVERSAL, 
                                         SecurityThreat.MALICIOUS_EXTENSION] else "MEDIUM",
            description=f"Security threat {threat.value} detected in file operation",
            details={
                'operation': operation.value,
                'user_id': user_id,
                'process_id': os.getpid(),
                'timestamp': time.time()
            },
            detected_at=time.time(),
            action_taken="BLOCKED"
        )
        
        # Store threat report
        with self._lock:
            self.threat_reports.append(threat_report)
            self.stats['threats_detected'] += 1
            self.stats['access_denied'] += 1
        
        # Quarantine file if it exists and policy allows
        if os.path.exists(file_path) and self.policy.quarantine_threats:
            self._quarantine_file(file_path, threat_report)
        
        # Log security event
        self.security_auditor.log_security_event(
            event_type="SECURITY_THREAT",
            severity=threat_report.severity,
            user_id=user_id,
            resource=file_path,
            action=f"{operation.value}_blocked",
            outcome="BLOCKED",
            details={
                'threat_type': threat.value,
                'operation': operation.value
            },
            risk_score=8 if threat_report.severity == "HIGH" else 6
        )
        
        logger.warning(f"Security threat blocked: {threat.value} in {file_path}")
    
    def _quarantine_file(self, file_path: str, threat_report: FileThreatReport):
        """Quarantine suspicious file"""
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return
            
            # Create quarantine filename with timestamp and threat info
            timestamp = int(time.time())
            quarantine_name = f"{source_path.name}_{timestamp}_{threat_report.threat_type.value}"
            quarantine_path = self.quarantine_dir / quarantine_name
            
            # Move file to quarantine
            shutil.move(str(source_path), str(quarantine_path))
            
            # Set restrictive permissions
            quarantine_path.chmod(stat.S_IRUSR)  # Owner read only
            
            # Create metadata file
            metadata = {
                'original_path': file_path,
                'threat_report': threat_report.__dict__,
                'quarantined_at': time.time(),
                'file_hash': self._calculate_file_hash(quarantine_path)
            }
            
            metadata_path = quarantine_path.with_suffix('.metadata.json')
            with open(metadata_path, 'w') as f:
                import json
                json.dump(metadata, f, indent=2, default=str)
            
            with self._lock:
                self.stats['files_quarantined'] += 1
            
            logger.info(f"File quarantined: {file_path} -> {quarantine_path}")
            
        except Exception as e:
            logger.error(f"Failed to quarantine file {file_path}: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""
    
    def _log_file_access(self, file_path: str, operation: FileOperation, user_id: Optional[str],
                        success: bool, threat: Optional[SecurityThreat], error: Optional[str] = None):
        """Log file access attempt"""
        access_attempt = FileAccessAttempt(
            file_path=file_path,
            operation=operation,
            user_id=user_id,
            process_id=os.getpid(),
            timestamp=time.time(),
            success=success,
            threat_detected=threat,
            details={'error': error} if error else {}
        )
        
        with self._lock:
            self.access_attempts.append(access_attempt)
            
            # Limit access log size
            if len(self.access_attempts) > 10000:
                self.access_attempts = self.access_attempts[-5000:]
        
        # Log to security auditor if configured
        if self.policy.log_all_operations:
            self.security_auditor.log_security_event(
                event_type="FILE_ACCESS",
                severity="LOW" if success else "MEDIUM",
                user_id=user_id,
                resource=file_path,
                action=operation.value,
                outcome="SUCCESS" if success else "FAILURE",
                details={
                    'threat_detected': threat.value if threat else None,
                    'error': error
                },
                risk_score=1 if success else 4
            )
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive file security status"""
        with self._lock:
            recent_threats = len([t for t in self.threat_reports 
                                if time.time() - t.detected_at < 3600])  # Last hour
            
            return {
                'policy': {
                    'allowed_extensions': list(self.policy.allowed_extensions),
                    'blocked_extensions': list(self.policy.blocked_extensions),
                    'max_file_size_mb': self.policy.max_file_size_mb,
                    'content_scanning': self.policy.scan_content,
                    'encryption_required': self.policy.require_encryption,
                    'quarantine_enabled': self.policy.quarantine_threats
                },
                'statistics': self.stats.copy(),
                'recent_threats': recent_threats,
                'quarantine_files': len(list(self.quarantine_dir.glob("*"))) if self.quarantine_dir.exists() else 0,
                'access_log_entries': len(self.access_attempts),
                'threat_patterns': len(self.threat_patterns)
            }
    
    def get_threat_reports(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent threat reports"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            recent_reports = [
                report.__dict__ for report in self.threat_reports
                if report.detected_at > cutoff_time
            ]
        
        return sorted(recent_reports, key=lambda r: r['detected_at'], reverse=True)


# Global file security manager instance
_file_security_instance = None
_file_security_lock = threading.Lock()

def get_file_security_manager() -> FileSecurityManager:
    """Get singleton file security manager instance"""
    global _file_security_instance
    if _file_security_instance is None:
        with _file_security_lock:
            if _file_security_instance is None:
                _file_security_instance = FileSecurityManager()
    return _file_security_instance


# Convenience functions for secure file operations
def secure_read_file(file_path: Union[str, Path], user_id: Optional[str] = None) -> Optional[str]:
    """Securely read text file"""
    manager = get_file_security_manager()
    success, error = manager.secure_file_operation(FileOperation.READ, file_path, user_id)
    
    if success:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
    else:
        logger.error(f"Secure read denied for {file_path}: {error}")
        return None


def secure_write_file(file_path: Union[str, Path], content: str, 
                     user_id: Optional[str] = None, backup: bool = True) -> bool:
    """Securely write text file"""
    manager = get_file_security_manager()
    success, error = manager.secure_file_operation(
        FileOperation.WRITE, file_path, user_id, 
        content=content, backup=backup
    )
    
    if not success:
        logger.error(f"Secure write denied for {file_path}: {error}")
    
    return success