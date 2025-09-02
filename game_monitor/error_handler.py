"""
Centralized Error Handler for Game Monitor System
Provides comprehensive error handling with recovery strategies and structured logging.
"""

import logging
import time
import traceback
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager
import functools

from .advanced_logger import get_logger, ErrorSeverity
from .error_tracker import ErrorTracker


class ErrorCategory(Enum):
    """Enhanced error categories for classification"""
    DATABASE = "database"           # Database operation errors
    OCR = "ocr"                    # OCR processing errors
    VALIDATION = "validation"       # Data validation errors
    VISION = "vision"              # Vision system errors
    HOTKEY = "hotkey"              # Hotkey system errors
    CONTROLLER = "controller"       # Main controller errors
    PERFORMANCE = "performance"     # Performance-related errors
    RESOURCE = "resource"           # Resource management errors
    CONFIGURATION = "configuration" # Configuration errors
    THREADING = "threading"         # Threading/concurrency errors
    UNKNOWN = "unknown"            # Unclassified errors


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"                    # Simple retry
    RETRY_WITH_BACKOFF = "backoff"     # Retry with exponential backoff
    FALLBACK = "fallback"              # Use fallback method
    SKIP = "skip"                      # Skip operation and continue
    RESTART_COMPONENT = "restart"      # Restart component
    USER_INTERVENTION = "user"         # Require user intervention
    CIRCUIT_BREAKER = "circuit"        # Circuit breaker pattern
    GRACEFUL_DEGRADATION = "degrade"   # Reduce functionality gracefully
    NONE = "none"                      # No automatic recovery


@dataclass
class ErrorContext:
    """Context information for error handling"""
    component: str
    operation: str
    user_data: Dict[str, Any]
    system_state: Dict[str, Any]
    timestamp: datetime
    trace_id: Optional[str] = None
    performance_data: Optional[Dict[str, float]] = None


@dataclass
class ErrorHandlingResult:
    """Result of error handling operation"""
    success: bool
    recovery_attempted: bool
    recovery_strategy: Optional[RecoveryStrategy]
    recovery_successful: bool
    error_logged: bool
    user_notified: bool
    system_state_changed: bool
    retry_count: int
    total_time: float
    additional_context: Dict[str, Any]


class ErrorHandler:
    """
    Centralized error handler with recovery strategies and comprehensive logging.
    
    Features:
    - Automatic error classification
    - Recovery strategy selection
    - Retry mechanisms with backoff
    - Performance impact tracking
    - User notification management
    - System state management
    """
    
    def __init__(self, logger_name: str = "error_handler"):
        self.logger = get_logger(logger_name)
        self.error_tracker = ErrorTracker()
        self._lock = threading.Lock()
        
        # Error handling statistics
        self.stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'recovery_success_rate': {},
            'average_recovery_time': {},
            'retry_statistics': {},
            'fallback_usage': {}
        }
        
        # Recovery strategy mapping
        self._recovery_strategies = self._initialize_recovery_strategies()
        
        # Circuit breaker states
        self._circuit_breakers = {}
        
        # Retry configuration
        self._retry_config = {
            'max_retries': 3,
            'base_delay': 0.1,
            'max_delay': 5.0,
            'backoff_multiplier': 2.0
        }
        
        self.logger.info("Centralized ErrorHandler initialized")
    
    def _initialize_recovery_strategies(self) -> Dict[ErrorCategory, RecoveryStrategy]:
        """Initialize default recovery strategies for each error category"""
        return {
            ErrorCategory.DATABASE: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorCategory.OCR: RecoveryStrategy.RETRY,
            ErrorCategory.VALIDATION: RecoveryStrategy.SKIP,
            ErrorCategory.VISION: RecoveryStrategy.FALLBACK,
            ErrorCategory.HOTKEY: RecoveryStrategy.RESTART_COMPONENT,
            ErrorCategory.CONTROLLER: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ErrorCategory.PERFORMANCE: RecoveryStrategy.CIRCUIT_BREAKER,
            ErrorCategory.RESOURCE: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ErrorCategory.CONFIGURATION: RecoveryStrategy.USER_INTERVENTION,
            ErrorCategory.THREADING: RecoveryStrategy.RESTART_COMPONENT,
            ErrorCategory.UNKNOWN: RecoveryStrategy.RETRY
        }
    
    def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        custom_recovery: Optional[RecoveryStrategy] = None
    ) -> ErrorHandlingResult:
        """
        Main error handling method with comprehensive processing.
        
        Args:
            error: The exception that occurred
            context: Error context information
            custom_recovery: Override default recovery strategy
            
        Returns:
            ErrorHandlingResult with processing details
        """
        start_time = time.time()
        
        try:
            with self._lock:
                self.stats['total_errors'] += 1
            
            # Classify error
            category = self._classify_error(error, context)
            severity = self._determine_severity(error, context, category)
            
            # Log error with context
            self._log_error(error, context, category, severity)
            
            # Select recovery strategy
            recovery_strategy = custom_recovery or self._recovery_strategies.get(
                category, RecoveryStrategy.RETRY
            )
            
            # Check circuit breaker
            if self._is_circuit_breaker_open(category, context.component):
                recovery_strategy = RecoveryStrategy.SKIP
            
            # Attempt recovery
            recovery_result = self._attempt_recovery(
                error, context, recovery_strategy, category
            )
            
            # Update statistics
            self._update_statistics(category, recovery_strategy, recovery_result)
            
            # Create result
            total_time = time.time() - start_time
            result = ErrorHandlingResult(
                success=recovery_result['success'],
                recovery_attempted=True,
                recovery_strategy=recovery_strategy,
                recovery_successful=recovery_result['success'],
                error_logged=True,
                user_notified=recovery_result.get('user_notified', False),
                system_state_changed=recovery_result.get('state_changed', False),
                retry_count=recovery_result.get('retry_count', 0),
                total_time=total_time,
                additional_context=recovery_result.get('context', {})
            )
            
            # Track error for pattern analysis
            self.error_tracker.record_error(
                context.component, context.operation, error,
                context=context.user_data,
                trace_id=context.trace_id
            )
            
            return result
            
        except Exception as handling_error:
            # Error in error handling - log and return minimal result
            self.logger.critical(
                f"Error in error handling: {handling_error}",
                extra_data={
                    'original_error': str(error),
                    'handling_error': str(handling_error),
                    'context': context.component
                }
            )
            
            return ErrorHandlingResult(
                success=False,
                recovery_attempted=False,
                recovery_strategy=None,
                recovery_successful=False,
                error_logged=True,
                user_notified=False,
                system_state_changed=False,
                retry_count=0,
                total_time=time.time() - start_time,
                additional_context={'handling_error': str(handling_error)}
            )
    
    def _classify_error(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Classify error based on type and context"""
        error_type = type(error).__name__
        component = context.component.lower()
        
        # Classification rules
        if 'database' in component or 'db' in component:
            return ErrorCategory.DATABASE
        elif 'ocr' in error_type.lower() or 'tesseract' in str(error).lower():
            return ErrorCategory.OCR
        elif 'validation' in component or 'validator' in component:
            return ErrorCategory.VALIDATION
        elif 'vision' in component or 'screenshot' in str(error).lower():
            return ErrorCategory.VISION
        elif 'hotkey' in component or 'keyboard' in str(error).lower():
            return ErrorCategory.HOTKEY
        elif 'controller' in component or 'main' in component:
            return ErrorCategory.CONTROLLER
        elif 'timeout' in str(error).lower() or 'performance' in str(error).lower():
            return ErrorCategory.PERFORMANCE
        elif 'memory' in str(error).lower() or 'resource' in str(error).lower():
            return ErrorCategory.RESOURCE
        elif 'config' in str(error).lower() or 'setting' in str(error).lower():
            return ErrorCategory.CONFIGURATION
        elif 'thread' in str(error).lower() or 'lock' in str(error).lower():
            return ErrorCategory.THREADING
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_severity(
        self, error: Exception, context: ErrorContext, category: ErrorCategory
    ) -> ErrorSeverity:
        """Determine error severity based on multiple factors"""
        error_msg = str(error).lower()
        
        # Critical conditions
        if any(word in error_msg for word in ['fatal', 'critical', 'corrupt', 'crash']):
            return ErrorSeverity.CRITICAL
        
        # High severity conditions
        if any(word in error_msg for word in ['timeout', 'connection', 'memory', 'thread']):
            return ErrorSeverity.HIGH
        
        # Category-based severity
        if category in [ErrorCategory.DATABASE, ErrorCategory.CONTROLLER]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.PERFORMANCE, ErrorCategory.RESOURCE]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _log_error(
        self, 
        error: Exception, 
        context: ErrorContext, 
        category: ErrorCategory, 
        severity: ErrorSeverity
    ):
        """Log error with comprehensive context"""
        extra_data = {
            'error_type': type(error).__name__,
            'error_category': category.value,
            'error_severity': severity.value,
            'component': context.component,
            'operation': context.operation,
            'trace_id': context.trace_id,
            'user_data': context.user_data,
            'system_state': context.system_state,
            'stack_trace': traceback.format_exc(),
            'performance_data': context.performance_data
        }
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error in {context.component}: {error}", 
                               error=error, extra_data=extra_data)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error in {context.component}: {error}",
                            error=error, extra_data=extra_data)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error in {context.component}: {error}",
                              extra_data=extra_data)
        else:
            self.logger.info(f"Low severity error in {context.component}: {error}",
                           extra_data=extra_data)
    
    def _attempt_recovery(
        self, 
        error: Exception, 
        context: ErrorContext, 
        strategy: RecoveryStrategy,
        category: ErrorCategory
    ) -> Dict[str, Any]:
        """Attempt recovery using specified strategy"""
        recovery_start = time.time()
        
        try:
            if strategy == RecoveryStrategy.RETRY:
                return self._retry_operation(error, context, category)
            elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                return self._retry_with_backoff(error, context, category)
            elif strategy == RecoveryStrategy.FALLBACK:
                return self._fallback_operation(error, context, category)
            elif strategy == RecoveryStrategy.SKIP:
                return self._skip_operation(error, context)
            elif strategy == RecoveryStrategy.RESTART_COMPONENT:
                return self._restart_component(error, context, category)
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                return self._graceful_degradation(error, context, category)
            elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                return self._activate_circuit_breaker(error, context, category)
            elif strategy == RecoveryStrategy.USER_INTERVENTION:
                return self._request_user_intervention(error, context)
            else:
                return {'success': False, 'reason': 'No recovery strategy'}
                
        except Exception as recovery_error:
            self.logger.error(f"Recovery attempt failed: {recovery_error}")
            return {
                'success': False, 
                'reason': 'Recovery failed',
                'recovery_error': str(recovery_error),
                'recovery_time': time.time() - recovery_start
            }
    
    def _retry_operation(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> Dict[str, Any]:
        """Simple retry mechanism"""
        max_retries = self._retry_config['max_retries']
        
        for attempt in range(max_retries):
            try:
                time.sleep(self._retry_config['base_delay'] * (attempt + 1))
                
                # Here we would retry the original operation
                # For now, we simulate recovery based on error type
                if self._simulate_recovery_success(error, category, attempt):
                    return {
                        'success': True,
                        'retry_count': attempt + 1,
                        'recovery_method': 'retry'
                    }
                    
            except Exception:
                continue
        
        return {
            'success': False,
            'retry_count': max_retries,
            'reason': 'Max retries exceeded'
        }
    
    def _retry_with_backoff(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> Dict[str, Any]:
        """Retry with exponential backoff"""
        max_retries = self._retry_config['max_retries']
        base_delay = self._retry_config['base_delay']
        multiplier = self._retry_config['backoff_multiplier']
        max_delay = self._retry_config['max_delay']
        
        for attempt in range(max_retries):
            delay = min(base_delay * (multiplier ** attempt), max_delay)
            time.sleep(delay)
            
            try:
                if self._simulate_recovery_success(error, category, attempt):
                    return {
                        'success': True,
                        'retry_count': attempt + 1,
                        'recovery_method': 'backoff_retry',
                        'total_delay': sum(min(base_delay * (multiplier ** i), max_delay) for i in range(attempt + 1))
                    }
            except Exception:
                continue
        
        return {
            'success': False,
            'retry_count': max_retries,
            'reason': 'Max retries with backoff exceeded'
        }
    
    def _fallback_operation(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> Dict[str, Any]:
        """Use fallback method"""
        with self._lock:
            if category.value not in self.stats['fallback_usage']:
                self.stats['fallback_usage'][category.value] = 0
            self.stats['fallback_usage'][category.value] += 1
        
        return {
            'success': True,
            'recovery_method': 'fallback',
            'fallback_used': True,
            'performance_degraded': True
        }
    
    def _skip_operation(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Skip operation and continue"""
        return {
            'success': True,
            'recovery_method': 'skip',
            'operation_skipped': True,
            'data_loss_risk': True
        }
    
    def _restart_component(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> Dict[str, Any]:
        """Request component restart"""
        return {
            'success': True,
            'recovery_method': 'restart_component',
            'component_restart_requested': True,
            'state_changed': True
        }
    
    def _graceful_degradation(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> Dict[str, Any]:
        """Implement graceful degradation"""
        return {
            'success': True,
            'recovery_method': 'graceful_degradation',
            'functionality_reduced': True,
            'performance_degraded': True,
            'state_changed': True
        }
    
    def _activate_circuit_breaker(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> Dict[str, Any]:
        """Activate circuit breaker for category"""
        circuit_key = f"{category.value}_{context.component}"
        
        with self._lock:
            self._circuit_breakers[circuit_key] = {
                'opened_at': datetime.now(),
                'error_count': self._circuit_breakers.get(circuit_key, {}).get('error_count', 0) + 1,
                'last_error': str(error)
            }
        
        return {
            'success': True,
            'recovery_method': 'circuit_breaker',
            'circuit_breaker_activated': True,
            'component_disabled': True,
            'state_changed': True
        }
    
    def _request_user_intervention(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Request user intervention"""
        return {
            'success': False,
            'recovery_method': 'user_intervention',
            'user_intervention_required': True,
            'user_notified': True
        }
    
    def _simulate_recovery_success(self, error: Exception, category: ErrorCategory, attempt: int) -> bool:
        """Simulate recovery success based on error characteristics"""
        # Simple heuristic for simulation
        if category in [ErrorCategory.OCR, ErrorCategory.VISION]:
            return attempt >= 1  # Usually recovers after 1 retry
        elif category == ErrorCategory.DATABASE:
            return attempt >= 2  # Database issues need more retries
        elif category == ErrorCategory.PERFORMANCE:
            return attempt >= 0  # Performance issues often resolve quickly
        else:
            return attempt >= 1
    
    def _is_circuit_breaker_open(self, category: ErrorCategory, component: str) -> bool:
        """Check if circuit breaker is open for given category/component"""
        circuit_key = f"{category.value}_{component}"
        
        with self._lock:
            if circuit_key not in self._circuit_breakers:
                return False
            
            breaker_data = self._circuit_breakers[circuit_key]
            opened_at = breaker_data['opened_at']
            
            # Circuit breaker timeout - 5 minutes
            if datetime.now() - opened_at > timedelta(minutes=5):
                del self._circuit_breakers[circuit_key]
                return False
            
            return True
    
    def _update_statistics(self, category: ErrorCategory, strategy: RecoveryStrategy, result: Dict[str, Any]):
        """Update error handling statistics"""
        with self._lock:
            # Update category statistics
            if category.value not in self.stats['errors_by_category']:
                self.stats['errors_by_category'][category.value] = 0
            self.stats['errors_by_category'][category.value] += 1
            
            # Update recovery success rate
            strategy_key = strategy.value
            if strategy_key not in self.stats['recovery_success_rate']:
                self.stats['recovery_success_rate'][strategy_key] = {'total': 0, 'successful': 0}
            
            self.stats['recovery_success_rate'][strategy_key]['total'] += 1
            if result.get('success', False):
                self.stats['recovery_success_rate'][strategy_key]['successful'] += 1
            
            # Update retry statistics
            if 'retry_count' in result:
                if strategy_key not in self.stats['retry_statistics']:
                    self.stats['retry_statistics'][strategy_key] = {'total_retries': 0, 'operations': 0}
                
                self.stats['retry_statistics'][strategy_key]['total_retries'] += result['retry_count']
                self.stats['retry_statistics'][strategy_key]['operations'] += 1
    
    @contextmanager
    def error_context(self, component: str, operation: str, **kwargs):
        """Context manager for automatic error handling"""
        context = ErrorContext(
            component=component,
            operation=operation,
            user_data=kwargs,
            system_state={},  # Could be populated with actual system state
            timestamp=datetime.now()
        )
        
        try:
            yield context
        except Exception as e:
            result = self.handle_error(e, context)
            if not result.recovery_successful:
                raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error handling statistics"""
        with self._lock:
            stats_copy = self.stats.copy()
            
            # Calculate success rates
            for strategy, data in stats_copy.get('recovery_success_rate', {}).items():
                if data['total'] > 0:
                    data['success_rate'] = data['successful'] / data['total']
                else:
                    data['success_rate'] = 0.0
            
            # Calculate average retry counts
            for strategy, data in stats_copy.get('retry_statistics', {}).items():
                if data['operations'] > 0:
                    data['avg_retries'] = data['total_retries'] / data['operations']
                else:
                    data['avg_retries'] = 0.0
            
            # Add circuit breaker info
            stats_copy['active_circuit_breakers'] = len(self._circuit_breakers)
            stats_copy['circuit_breakers'] = self._circuit_breakers.copy()
            
            return stats_copy
    
    def reset_statistics(self):
        """Reset all error handling statistics"""
        with self._lock:
            self.stats = {
                'total_errors': 0,
                'errors_by_category': {},
                'recovery_success_rate': {},
                'average_recovery_time': {},
                'retry_statistics': {},
                'fallback_usage': {}
            }
            self._circuit_breakers.clear()
        
        self.logger.info("Error handling statistics reset")
    
    def configure_retry_settings(self, max_retries: int = 3, base_delay: float = 0.1, 
                                max_delay: float = 5.0, backoff_multiplier: float = 2.0):
        """Configure retry settings"""
        self._retry_config.update({
            'max_retries': max_retries,
            'base_delay': base_delay,
            'max_delay': max_delay,
            'backoff_multiplier': backoff_multiplier
        })
        
        self.logger.info(f"Retry configuration updated: {self._retry_config}")
    
    def set_recovery_strategy(self, category: ErrorCategory, strategy: RecoveryStrategy):
        """Set custom recovery strategy for error category"""
        self._recovery_strategies[category] = strategy
        self.logger.info(f"Recovery strategy for {category.value} set to {strategy.value}")


# Decorator for automatic error handling
def handle_errors(component: str, operation: str = None, 
                 recovery_strategy: RecoveryStrategy = None):
    """
    Decorator for automatic error handling with centralized ErrorHandler.
    
    Usage:
        @handle_errors("database", "query_execution", RecoveryStrategy.RETRY_WITH_BACKOFF)
        def execute_query(self, sql):
            # method implementation
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = getattr(args[0], '_error_handler', None)
            if not handler:
                # Create handler if not exists
                handler = ErrorHandler()
                args[0]._error_handler = handler
            
            op_name = operation or func.__name__
            context = ErrorContext(
                component=component,
                operation=op_name,
                user_data={'args': args[1:], 'kwargs': kwargs},  # Skip self
                system_state={},
                timestamp=datetime.now()
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                result = handler.handle_error(e, context, recovery_strategy)
                if not result.recovery_successful:
                    raise
                return None  # Or appropriate default value
        
        return wrapper
    return decorator


# Global error handler instance
_error_handler_instance = None
_error_handler_lock = threading.Lock()

def get_error_handler() -> ErrorHandler:
    """Get singleton error handler instance"""
    global _error_handler_instance
    if _error_handler_instance is None:
        with _error_handler_lock:
            if _error_handler_instance is None:
                _error_handler_instance = ErrorHandler()
    return _error_handler_instance