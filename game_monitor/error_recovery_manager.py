#!/usr/bin/env python3

import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from collections import defaultdict, deque
import json
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ErrorCategory(Enum):
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    OCR = "ocr"
    VALIDATION = "validation"
    HOTKEY = "hotkey"
    GUI = "gui"
    PERFORMANCE = "performance"
    SECURITY = "security"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    RESTART_COMPONENT = "restart_component"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ESCALATE = "escalate"
    IGNORE = "ignore"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class ErrorRecord:
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    component: str = ""
    operation: str = ""
    error_type: str = ""
    message: str = ""
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    max_retries: int = 3
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)


@dataclass
class RecoveryRule:
    name: str
    category: ErrorCategory
    error_patterns: List[str]
    strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    timeout: float = 30.0
    fallback_action: Optional[Callable] = None
    escalation_threshold: int = 5
    enabled: bool = True


@dataclass
class ComponentHealth:
    component: str
    status: str = "healthy"
    error_count: int = 0
    last_error: Optional[datetime] = None
    consecutive_errors: int = 0
    recovery_count: int = 0
    uptime_start: datetime = field(default_factory=datetime.now)


class ErrorRecoveryManager:
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.error_records: Dict[str, ErrorRecord] = {}
        self.recovery_rules: Dict[str, RecoveryRule] = {}
        self.component_health: Dict[str, ComponentHealth] = {}
        self.error_history: deque = deque(maxlen=1000)
        self.recovery_callbacks: Dict[str, Callable] = {}
        self.escalation_callbacks: Dict[str, Callable] = {}
        
        # Statistics
        self.error_stats = defaultdict(int)
        self.recovery_stats = defaultdict(int)
        self.component_stats = defaultdict(lambda: defaultdict(int))
        
        # Configuration
        self.max_error_history = 1000
        self.cleanup_interval = 3600  # 1 hour
        self.health_check_interval = 60  # 1 minute
        
        # Threading
        self.cleanup_thread = None
        self.health_monitor_thread = None
        self.running = False
        
        self._setup_default_rules()
        self._initialized = True
    
    def _setup_default_rules(self):
        default_rules = [
            # Database errors
            RecoveryRule(
                name="database_connection_error",
                category=ErrorCategory.DATABASE,
                error_patterns=["connection", "database", "sqlite"],
                strategy=RecoveryStrategy.RETRY,
                max_retries=5,
                retry_delay=2.0,
                backoff_multiplier=1.5
            ),
            
            # Network errors
            RecoveryRule(
                name="network_timeout",
                category=ErrorCategory.NETWORK,
                error_patterns=["timeout", "network", "connection refused"],
                strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                retry_delay=1.0
            ),
            
            # OCR errors
            RecoveryRule(
                name="ocr_processing_error",
                category=ErrorCategory.OCR,
                error_patterns=["tesseract", "ocr", "image processing"],
                strategy=RecoveryStrategy.FALLBACK,
                max_retries=2,
                retry_delay=0.5
            ),
            
            # Performance errors
            RecoveryRule(
                name="performance_degradation",
                category=ErrorCategory.PERFORMANCE,
                error_patterns=["timeout", "slow", "performance"],
                strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                max_retries=1
            ),
            
            # Critical system errors
            RecoveryRule(
                name="critical_system_error",
                category=ErrorCategory.SYSTEM,
                error_patterns=["memory", "system", "critical"],
                strategy=RecoveryStrategy.RESTART_COMPONENT,
                max_retries=1,
                escalation_threshold=1
            )
        ]
        
        for rule in default_rules:
            self.add_recovery_rule(rule)
    
    def start(self):
        with self._lock:
            if self.running:
                return
                
            self.running = True
            
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True,
                name="ErrorRecoveryCleanup"
            )
            self.cleanup_thread.start()
            
            # Start health monitor
            self.health_monitor_thread = threading.Thread(
                target=self._health_monitor_worker,
                daemon=True,
                name="ComponentHealthMonitor"
            )
            self.health_monitor_thread.start()
            
            logger.info("Error Recovery Manager started")
    
    def stop(self):
        with self._lock:
            self.running = False
            logger.info("Error Recovery Manager stopped")
    
    def record_error(self, 
                    component: str,
                    operation: str,
                    error: Exception,
                    category: ErrorCategory = ErrorCategory.UNKNOWN,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None) -> str:
        """Record an error and return the error ID"""
        
        error_record = ErrorRecord(
            category=category,
            severity=severity,
            component=component,
            operation=operation,
            error_type=type(error).__name__,
            message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {}
        )
        
        # Determine recovery strategy
        recovery_rule = self._find_recovery_rule(error_record)
        if recovery_rule:
            error_record.recovery_strategy = recovery_rule.strategy
            error_record.max_retries = recovery_rule.max_retries
        
        # Store error record
        with self._lock:
            self.error_records[error_record.error_id] = error_record
            self.error_history.append(error_record)
            
            # Update statistics
            self.error_stats[category.value] += 1
            self.error_stats[severity.value] += 1
            self.component_stats[component]["errors"] += 1
            
            # Update component health
            self._update_component_health(component, error_record)
        
        logger.error(f"Error recorded [{error_record.error_id}]: {component}.{operation} - {error}")
        
        return error_record.error_id
    
    def attempt_recovery(self, error_id: str) -> bool:
        """Attempt to recover from an error"""
        
        with self._lock:
            if error_id not in self.error_records:
                logger.warning(f"Error record not found: {error_id}")
                return False
            
            error_record = self.error_records[error_id]
            
            if error_record.resolved:
                return True
            
            if error_record.recovery_attempts >= error_record.max_retries:
                logger.warning(f"Max recovery attempts exceeded for error {error_id}")
                self._escalate_error(error_record)
                return False
            
            error_record.recovery_attempts += 1
            
        # Find recovery rule
        recovery_rule = self._find_recovery_rule(error_record)
        if not recovery_rule:
            logger.warning(f"No recovery rule found for error {error_id}")
            return False
        
        try:
            success = self._execute_recovery_strategy(error_record, recovery_rule)
            
            with self._lock:
                if success:
                    error_record.resolved = True
                    error_record.resolution_time = datetime.now()
                    self.recovery_stats[recovery_rule.strategy.value] += 1
                    self.component_stats[error_record.component]["recoveries"] += 1
                    
                    logger.info(f"Successfully recovered from error {error_id} using {recovery_rule.strategy.value}")
                else:
                    logger.warning(f"Recovery attempt failed for error {error_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during recovery attempt for {error_id}: {e}")
            return False
    
    def _execute_recovery_strategy(self, error_record: ErrorRecord, rule: RecoveryRule) -> bool:
        """Execute the recovery strategy"""
        
        strategy = error_record.recovery_strategy
        
        if strategy == RecoveryStrategy.RETRY:
            return self._retry_recovery(error_record, rule)
        elif strategy == RecoveryStrategy.FALLBACK:
            return self._fallback_recovery(error_record, rule)
        elif strategy == RecoveryStrategy.RESTART_COMPONENT:
            return self._restart_component_recovery(error_record, rule)
        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return self._graceful_degradation_recovery(error_record, rule)
        elif strategy == RecoveryStrategy.ESCALATE:
            return self._escalate_error(error_record)
        elif strategy == RecoveryStrategy.IGNORE:
            return True
        else:
            logger.warning(f"Unknown recovery strategy: {strategy}")
            return False
    
    def _retry_recovery(self, error_record: ErrorRecord, rule: RecoveryRule) -> bool:
        """Implement retry recovery strategy"""
        
        component = error_record.component
        if component in self.recovery_callbacks:
            try:
                # Calculate delay with exponential backoff
                delay = rule.retry_delay * (rule.backoff_multiplier ** (error_record.recovery_attempts - 1))
                time.sleep(min(delay, 30.0))  # Max 30 seconds delay
                
                # Attempt recovery callback
                return self.recovery_callbacks[component](error_record)
            except Exception as e:
                logger.error(f"Retry callback failed for {component}: {e}")
                return False
        
        # Default retry logic - just mark as resolved if no callback
        logger.info(f"No retry callback for {component}, marking as resolved")
        return True
    
    def _fallback_recovery(self, error_record: ErrorRecord, rule: RecoveryRule) -> bool:
        """Implement fallback recovery strategy"""
        
        if rule.fallback_action:
            try:
                return rule.fallback_action(error_record)
            except Exception as e:
                logger.error(f"Fallback action failed: {e}")
                return False
        
        # Default fallback - graceful degradation
        logger.info(f"Using default fallback for {error_record.component}")
        return True
    
    def _restart_component_recovery(self, error_record: ErrorRecord, rule: RecoveryRule) -> bool:
        """Implement component restart recovery strategy"""
        
        component = error_record.component
        logger.info(f"Attempting to restart component: {component}")
        
        # Call restart callback if available
        restart_callback = self.recovery_callbacks.get(f"{component}_restart")
        if restart_callback:
            try:
                return restart_callback(error_record)
            except Exception as e:
                logger.error(f"Component restart failed for {component}: {e}")
                return False
        
        # Default restart logic
        logger.warning(f"No restart callback for {component}")
        return False
    
    def _graceful_degradation_recovery(self, error_record: ErrorRecord, rule: RecoveryRule) -> bool:
        """Implement graceful degradation recovery strategy"""
        
        component = error_record.component
        logger.info(f"Applying graceful degradation for: {component}")
        
        # Mark component as degraded
        with self._lock:
            if component in self.component_health:
                self.component_health[component].status = "degraded"
        
        return True
    
    def _escalate_error(self, error_record: ErrorRecord) -> bool:
        """Escalate error to higher level handler"""
        
        component = error_record.component
        logger.warning(f"Escalating error for component: {component}")
        
        # Call escalation callback if available
        escalation_callback = self.escalation_callbacks.get(component)
        if escalation_callback:
            try:
                escalation_callback(error_record)
            except Exception as e:
                logger.error(f"Escalation callback failed for {component}: {e}")
        
        # Mark component as failed
        with self._lock:
            if component in self.component_health:
                self.component_health[component].status = "failed"
        
        return False
    
    def _find_recovery_rule(self, error_record: ErrorRecord) -> Optional[RecoveryRule]:
        """Find matching recovery rule for error"""
        
        for rule in self.recovery_rules.values():
            if not rule.enabled:
                continue
                
            if rule.category != error_record.category:
                continue
            
            # Check if error message matches patterns
            error_text = f"{error_record.message} {error_record.error_type}".lower()
            for pattern in rule.error_patterns:
                if pattern.lower() in error_text:
                    return rule
        
        return None
    
    def _update_component_health(self, component: str, error_record: ErrorRecord):
        """Update component health status"""
        
        if component not in self.component_health:
            self.component_health[component] = ComponentHealth(component=component)
        
        health = self.component_health[component]
        health.error_count += 1
        health.last_error = error_record.timestamp
        health.consecutive_errors += 1
        
        # Determine health status
        if error_record.severity == ErrorSeverity.CRITICAL:
            health.status = "critical"
        elif health.consecutive_errors > 5:
            health.status = "unhealthy"
        elif health.consecutive_errors > 2:
            health.status = "degraded"
    
    def register_recovery_callback(self, component: str, callback: Callable):
        """Register recovery callback for component"""
        self.recovery_callbacks[component] = callback
    
    def register_escalation_callback(self, component: str, callback: Callable):
        """Register escalation callback for component"""
        self.escalation_callbacks[component] = callback
    
    def add_recovery_rule(self, rule: RecoveryRule):
        """Add recovery rule"""
        self.recovery_rules[rule.name] = rule
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self._lock:
            return {
                "total_errors": len(self.error_records),
                "error_by_category": dict(self.error_stats),
                "recovery_by_strategy": dict(self.recovery_stats),
                "component_stats": dict(self.component_stats),
                "resolved_errors": len([r for r in self.error_records.values() if r.resolved]),
                "pending_errors": len([r for r in self.error_records.values() if not r.resolved])
            }
    
    def get_component_health_status(self) -> Dict[str, ComponentHealth]:
        """Get component health status"""
        with self._lock:
            return self.component_health.copy()
    
    def get_recent_errors(self, limit: int = 10) -> List[ErrorRecord]:
        """Get recent errors"""
        with self._lock:
            return list(self.error_history)[-limit:]
    
    def clear_resolved_errors(self, older_than_hours: int = 24):
        """Clear resolved errors older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        with self._lock:
            resolved_ids = []
            for error_id, record in self.error_records.items():
                if record.resolved and record.resolution_time and record.resolution_time < cutoff_time:
                    resolved_ids.append(error_id)
            
            for error_id in resolved_ids:
                del self.error_records[error_id]
            
            logger.info(f"Cleared {len(resolved_ids)} resolved errors")
    
    def _cleanup_worker(self):
        """Background cleanup worker"""
        while self.running:
            try:
                time.sleep(self.cleanup_interval)
                self.clear_resolved_errors()
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
    
    def _health_monitor_worker(self):
        """Background health monitor worker"""
        while self.running:
            try:
                time.sleep(self.health_check_interval)
                self._check_component_health()
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
    
    def _check_component_health(self):
        """Check and update component health"""
        current_time = datetime.now()
        
        with self._lock:
            for component, health in self.component_health.items():
                # Reset consecutive errors if no recent errors
                if health.last_error and (current_time - health.last_error).total_seconds() > 300:  # 5 minutes
                    if health.consecutive_errors > 0:
                        health.consecutive_errors = 0
                        health.status = "healthy"
                        health.recovery_count += 1


# Singleton instance
error_recovery_manager = ErrorRecoveryManager()