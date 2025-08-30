"""
Error Tracking and Recovery System for Game Monitor
Comprehensive error classification, correlation, and recovery strategies.
"""

import threading
import time
import json
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import traceback
import hashlib

from .advanced_logger import get_logger, ErrorSeverity


class ErrorCategory(Enum):
    """Error categories for classification"""
    SYSTEM = "system"           # System-level errors (file system, memory, etc.)
    NETWORK = "network"         # Network-related errors  
    DATABASE = "database"       # Database operation errors
    OCR = "ocr"                # OCR processing errors
    VALIDATION = "validation"   # Data validation errors
    USER_INPUT = "user_input"   # User input validation errors
    PERMISSION = "permission"   # Permission/access errors
    RESOURCE = "resource"       # Resource exhaustion errors
    EXTERNAL = "external"       # External dependency errors
    UNKNOWN = "unknown"         # Unclassified errors


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"                    # Simple retry
    RETRY_WITH_BACKOFF = "backoff"     # Retry with exponential backoff
    FALLBACK = "fallback"              # Use fallback method
    SKIP = "skip"                      # Skip operation and continue
    RESTART_COMPONENT = "restart"      # Restart component
    USER_INTERVENTION = "user"         # Require user intervention
    CIRCUIT_BREAKER = "circuit"        # Circuit breaker pattern
    NONE = "none"                      # No automatic recovery


@dataclass
class ErrorSignature:
    """Unique signature for error classification"""
    error_type: str
    component: str
    operation: str
    error_message_hash: str
    
    def __hash__(self):
        return hash((self.error_type, self.component, self.operation, self.error_message_hash))


@dataclass
class ErrorOccurrence:
    """Single error occurrence with context"""
    timestamp: datetime
    trace_id: str
    component: str
    operation: str
    error_type: str
    error_message: str
    stack_trace: str
    context: Dict[str, Any]
    severity: ErrorSeverity
    category: ErrorCategory
    recovery_attempted: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_successful: bool = False
    user_impact: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        if self.recovery_strategy:
            data['recovery_strategy'] = self.recovery_strategy.value
        return data


@dataclass
class ErrorPattern:
    """Pattern for recurring errors"""
    signature: ErrorSignature
    occurrences: List[ErrorOccurrence]
    first_seen: datetime
    last_seen: datetime
    total_count: int
    frequency: float  # occurrences per hour
    severity: ErrorSeverity
    category: ErrorCategory
    suggested_recovery: RecoveryStrategy
    
    def update_stats(self):
        """Update pattern statistics"""
        if not self.occurrences:
            return
        
        self.total_count = len(self.occurrences)
        self.last_seen = max(occ.timestamp for occ in self.occurrences)
        
        # Calculate frequency (last 24 hours)
        recent_threshold = datetime.now() - timedelta(hours=24)
        recent_occurrences = [occ for occ in self.occurrences if occ.timestamp >= recent_threshold]
        self.frequency = len(recent_occurrences) / 24.0


class ErrorTracker:
    """Comprehensive error tracking and recovery system"""
    
    def __init__(self):
        self.logger = get_logger('error_tracker')
        
        # Error storage
        self._errors = deque(maxlen=10000)  # Keep last 10K errors
        self._error_patterns = {}  # signature -> ErrorPattern
        self._lock = threading.RLock()
        
        # Circuit breaker states
        self._circuit_breakers = defaultdict(lambda: {
            'state': 'closed',  # closed, open, half-open
            'failure_count': 0,
            'last_failure': None,
            'next_attempt': None
        })
        
        # Recovery strategies configuration
        self._recovery_strategies = self._init_recovery_strategies()
        
        # Error classification rules
        self._classification_rules = self._init_classification_rules()
        
        # Monitoring thread
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
    
    def _init_recovery_strategies(self) -> Dict[ErrorCategory, Dict[str, Any]]:
        """Initialize recovery strategies for different error categories"""
        return {
            ErrorCategory.NETWORK: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'max_retries': 3,
                'backoff_factor': 2.0,
                'circuit_breaker_threshold': 5
            },
            ErrorCategory.DATABASE: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'max_retries': 2,
                'backoff_factor': 1.5,
                'circuit_breaker_threshold': 3
            },
            ErrorCategory.OCR: {
                'primary': RecoveryStrategy.FALLBACK,
                'max_retries': 1,
                'fallback_method': 'use_cached_result'
            },
            ErrorCategory.VALIDATION: {
                'primary': RecoveryStrategy.SKIP,
                'log_level': 'warning'
            },
            ErrorCategory.USER_INPUT: {
                'primary': RecoveryStrategy.USER_INTERVENTION,
                'show_dialog': True
            },
            ErrorCategory.PERMISSION: {
                'primary': RecoveryStrategy.USER_INTERVENTION,
                'escalate': True
            },
            ErrorCategory.RESOURCE: {
                'primary': RecoveryStrategy.CIRCUIT_BREAKER,
                'circuit_breaker_threshold': 2,
                'cooldown_minutes': 5
            },
            ErrorCategory.EXTERNAL: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'max_retries': 2,
                'circuit_breaker_threshold': 4
            }
        }
    
    def _init_classification_rules(self) -> List[Dict[str, Any]]:
        """Initialize error classification rules"""
        return [
            # Database errors
            {
                'pattern': ['sqlite3', 'database', 'connection'],
                'category': ErrorCategory.DATABASE,
                'severity': ErrorSeverity.HIGH
            },
            {
                'pattern': ['database is locked', 'database disk image is malformed'],
                'category': ErrorCategory.DATABASE,
                'severity': ErrorSeverity.CRITICAL
            },
            
            # Network errors
            {
                'pattern': ['connection', 'timeout', 'network', 'socket'],
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.MEDIUM
            },
            
            # OCR errors
            {
                'pattern': ['tesseract', 'ocr', 'image processing'],
                'category': ErrorCategory.OCR,
                'severity': ErrorSeverity.MEDIUM
            },
            
            # File system errors
            {
                'pattern': ['permission denied', 'access denied'],
                'category': ErrorCategory.PERMISSION,
                'severity': ErrorSeverity.HIGH
            },
            {
                'pattern': ['no space left', 'disk full', 'out of memory'],
                'category': ErrorCategory.RESOURCE,
                'severity': ErrorSeverity.CRITICAL
            },
            
            # Validation errors
            {
                'pattern': ['validation', 'invalid', 'format'],
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.LOW
            }
        ]
    
    def _classify_error(self, error_type: str, error_message: str, 
                       component: str) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error based on type, message, and component"""
        error_text = f"{error_type} {error_message} {component}".lower()
        
        for rule in self._classification_rules:
            if any(pattern.lower() in error_text for pattern in rule['pattern']):
                return rule['category'], rule['severity']
        
        # Default classification
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def _create_error_signature(self, error_type: str, component: str, 
                               operation: str, error_message: str) -> ErrorSignature:
        """Create unique error signature for pattern matching"""
        # Create hash of normalized error message
        normalized_message = error_message.lower()
        # Remove variable parts (numbers, paths, etc.)
        import re
        normalized_message = re.sub(r'\d+', 'N', normalized_message)
        normalized_message = re.sub(r'/[^\s]+', '/PATH', normalized_message)
        
        message_hash = hashlib.md5(normalized_message.encode()).hexdigest()[:8]
        
        return ErrorSignature(
            error_type=error_type,
            component=component,
            operation=operation,
            error_message_hash=message_hash
        )
    
    def record_error(self, component: str, operation: str, error: Exception,
                    context: Optional[Dict[str, Any]] = None,
                    trace_id: Optional[str] = None) -> str:
        """Record error occurrence with full context"""
        
        # Create error occurrence
        occurrence = ErrorOccurrence(
            timestamp=datetime.now(),
            trace_id=trace_id or 'unknown',
            component=component,
            operation=operation,
            error_type=error.__class__.__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {},
            severity=ErrorSeverity.MEDIUM,  # Will be updated by classification
            category=ErrorCategory.UNKNOWN  # Will be updated by classification
        )
        
        # Classify error
        occurrence.category, occurrence.severity = self._classify_error(
            occurrence.error_type, occurrence.error_message, component
        )
        
        # Assess user impact
        occurrence.user_impact = self._assess_user_impact(occurrence)
        
        with self._lock:
            # Add to error storage
            self._errors.append(occurrence)
            
            # Update error patterns
            signature = self._create_error_signature(
                occurrence.error_type, component, operation, occurrence.error_message
            )
            
            if signature not in self._error_patterns:
                self._error_patterns[signature] = ErrorPattern(
                    signature=signature,
                    occurrences=[],
                    first_seen=occurrence.timestamp,
                    last_seen=occurrence.timestamp,
                    total_count=0,
                    frequency=0.0,
                    severity=occurrence.severity,
                    category=occurrence.category,
                    suggested_recovery=self._get_suggested_recovery(occurrence.category)
                )
            
            pattern = self._error_patterns[signature]
            pattern.occurrences.append(occurrence)
            pattern.update_stats()
            
            # Update severity if this occurrence is more severe
            if occurrence.severity.value > pattern.severity.value:
                pattern.severity = occurrence.severity
        
        # Log the error
        self.logger.error(
            f"Error in {component}.{operation}: {error}",
            error=error,
            extra_data={
                'component': component,
                'operation': operation,
                'category': occurrence.category.value,
                'severity': occurrence.severity.value,
                'user_impact': occurrence.user_impact,
                'context': context
            }
        )
        
        # Trigger recovery if appropriate
        recovery_id = self._attempt_recovery(occurrence)
        
        return recovery_id or 'no_recovery'
    
    def _assess_user_impact(self, occurrence: ErrorOccurrence) -> str:
        """Assess the impact of error on user experience"""
        if occurrence.severity == ErrorSeverity.CRITICAL:
            return "high"
        elif occurrence.severity == ErrorSeverity.HIGH:
            return "medium"
        elif occurrence.category in [ErrorCategory.VALIDATION, ErrorCategory.OCR]:
            return "low"
        else:
            return "medium"
    
    def _get_suggested_recovery(self, category: ErrorCategory) -> RecoveryStrategy:
        """Get suggested recovery strategy for error category"""
        return self._recovery_strategies.get(category, {}).get(
            'primary', RecoveryStrategy.NONE
        )
    
    def _attempt_recovery(self, occurrence: ErrorOccurrence) -> Optional[str]:
        """Attempt automatic recovery based on error type and history"""
        strategy = self._get_suggested_recovery(occurrence.category)
        
        if strategy == RecoveryStrategy.NONE:
            return None
        
        # Check circuit breaker
        if self._is_circuit_open(occurrence.component, occurrence.operation):
            self.logger.warning(
                f"Circuit breaker open for {occurrence.component}.{occurrence.operation}, skipping recovery"
            )
            return None
        
        recovery_id = f"recovery_{int(time.time())}"
        
        self.logger.info(
            f"Attempting recovery for {occurrence.component}.{occurrence.operation}",
            extra_data={
                'recovery_id': recovery_id,
                'strategy': strategy.value,
                'error_type': occurrence.error_type
            }
        )
        
        # Mark recovery as attempted
        occurrence.recovery_attempted = True
        occurrence.recovery_strategy = strategy
        
        return recovery_id
    
    def _is_circuit_open(self, component: str, operation: str) -> bool:
        """Check if circuit breaker is open for component/operation"""
        key = f"{component}.{operation}"
        breaker = self._circuit_breakers[key]
        
        if breaker['state'] == 'open':
            # Check if we should try half-open
            if (breaker['next_attempt'] and 
                datetime.now() >= breaker['next_attempt']):
                breaker['state'] = 'half-open'
                return False
            return True
        
        return False
    
    def record_recovery_result(self, recovery_id: str, successful: bool,
                             details: Optional[Dict[str, Any]] = None):
        """Record the result of a recovery attempt"""
        self.logger.info(
            f"Recovery {recovery_id} {'successful' if successful else 'failed'}",
            extra_data={
                'recovery_id': recovery_id,
                'successful': successful,
                'details': details or {}
            }
        )
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for specified time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [err for err in self._errors if err.timestamp >= cutoff]
            
            stats = {
                'total_errors': len(recent_errors),
                'by_category': defaultdict(int),
                'by_severity': defaultdict(int),
                'by_component': defaultdict(int),
                'top_patterns': [],
                'recovery_success_rate': 0.0
            }
            
            # Count by categories
            for error in recent_errors:
                stats['by_category'][error.category.value] += 1
                stats['by_severity'][error.severity.value] += 1
                stats['by_component'][error.component] += 1
            
            # Get top error patterns
            pattern_counts = []
            for pattern in self._error_patterns.values():
                recent_count = len([occ for occ in pattern.occurrences 
                                 if occ.timestamp >= cutoff])
                if recent_count > 0:
                    pattern_counts.append((pattern, recent_count))
            
            pattern_counts.sort(key=lambda x: x[1], reverse=True)
            stats['top_patterns'] = [
                {
                    'error_type': pattern.signature.error_type,
                    'component': pattern.signature.component,
                    'count': count,
                    'severity': pattern.severity.value,
                    'category': pattern.category.value
                }
                for pattern, count in pattern_counts[:10]
            ]
            
            # Calculate recovery success rate
            recovery_attempts = [err for err in recent_errors if err.recovery_attempted]
            if recovery_attempts:
                successful_recoveries = [err for err in recovery_attempts if err.recovery_successful]
                stats['recovery_success_rate'] = len(successful_recoveries) / len(recovery_attempts)
        
        return dict(stats)
    
    def get_critical_errors(self, hours: int = 1) -> List[ErrorOccurrence]:
        """Get critical errors from recent time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                err for err in self._errors 
                if err.timestamp >= cutoff and err.severity == ErrorSeverity.CRITICAL
            ]
    
    def _monitoring_loop(self):
        """Background monitoring loop for error patterns and alerts"""
        while self._monitoring_active:
            try:
                # Check for error pattern anomalies
                self._check_error_patterns()
                
                # Update circuit breaker states
                self._update_circuit_breakers()
                
                # Cleanup old errors (keep last 7 days)
                self._cleanup_old_errors()
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                # Don't let monitoring loop crash
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def _check_error_patterns(self):
        """Check for concerning error patterns"""
        current_time = datetime.now()
        
        with self._lock:
            for pattern in self._error_patterns.values():
                # Check for error spikes (more than 5 errors in last 10 minutes)
                recent_threshold = current_time - timedelta(minutes=10)
                recent_occurrences = [
                    occ for occ in pattern.occurrences 
                    if occ.timestamp >= recent_threshold
                ]
                
                if len(recent_occurrences) >= 5:
                    self.logger.critical(
                        f"Error spike detected: {pattern.signature.error_type} "
                        f"in {pattern.signature.component} ({len(recent_occurrences)} in 10 min)",
                        extra_data={
                            'pattern': pattern.signature.__dict__,
                            'recent_count': len(recent_occurrences),
                            'severity': pattern.severity.value
                        }
                    )
    
    def _update_circuit_breakers(self):
        """Update circuit breaker states based on recent errors"""
        current_time = datetime.now()
        
        for key, breaker in self._circuit_breakers.items():
            # Auto-close circuit breakers after cooldown period
            if (breaker['state'] == 'open' and 
                breaker['next_attempt'] and
                current_time >= breaker['next_attempt']):
                breaker['state'] = 'half-open'
                breaker['failure_count'] = 0
    
    def _cleanup_old_errors(self):
        """Clean up old error records"""
        cutoff = datetime.now() - timedelta(days=7)
        
        with self._lock:
            # Clean up error patterns
            for signature in list(self._error_patterns.keys()):
                pattern = self._error_patterns[signature]
                pattern.occurrences = [
                    occ for occ in pattern.occurrences 
                    if occ.timestamp >= cutoff
                ]
                
                # Remove pattern if no recent occurrences
                if not pattern.occurrences:
                    del self._error_patterns[signature]
                else:
                    pattern.update_stats()
    
    def shutdown(self):
        """Shutdown error tracker"""
        self._monitoring_active = False
        if self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)