"""
Advanced Logging System for Game Monitor
Enterprise-grade comprehensive logging with trace correlation, 
performance metrics, and structured error handling.
"""

import logging
import json
import threading
import time
import uuid
import traceback
import psutil
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from enum import Enum
import queue


class LogLevel(Enum):
    """Extended log levels for comprehensive tracking"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    AUDIT = 25    # For user actions
    PERF = 15     # For performance metrics


class ErrorSeverity(Enum):
    """Error severity classification"""
    LOW = "low"           # Minor issues, system continues normally
    MEDIUM = "medium"     # Some functionality affected
    HIGH = "high"        # Major functionality broken
    CRITICAL = "critical" # System-wide failure


@dataclass
class LogContext:
    """Context information for log entries"""
    trace_id: str
    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations"""
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    memory_before_mb: Optional[float] = None
    memory_after_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    def finish(self):
        """Mark operation as finished and calculate metrics"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        
        # Get current memory usage
        try:
            process = psutil.Process()
            self.memory_after_mb = process.memory_info().rss / 1024 / 1024
            self.cpu_usage_percent = process.cpu_percent()
        except:
            pass  # Non-critical if psutil fails
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class StructuredLogger:
    """Advanced structured logger with JSON output and correlation"""
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Thread-local storage for context
        self._local = threading.local()
        
        # Initialize loggers
        self._setup_loggers()
        
        # GUI log queue for system log display
        self.gui_log_queue = queue.Queue(maxsize=1000)
        
        # Performance tracking
        self._active_operations = {}
        self._operation_lock = threading.Lock()
    
    def _setup_loggers(self):
        """Setup structured loggers with different outputs"""
        # Main structured logger (JSON)
        self.structured_logger = logging.getLogger(f"{self.name}.structured")
        self.structured_logger.setLevel(logging.DEBUG)
        
        # JSON file handler
        json_handler = logging.FileHandler(self.log_dir / f"{self.name}_structured.json")
        json_handler.setFormatter(self._create_json_formatter())
        self.structured_logger.addHandler(json_handler)
        
        # Error logger (separate file)
        self.error_logger = logging.getLogger(f"{self.name}.errors")
        self.error_logger.setLevel(logging.WARNING)
        
        error_handler = logging.FileHandler(self.log_dir / f"{self.name}_errors.log")
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.error_logger.addHandler(error_handler)
        
        # Performance logger
        self.perf_logger = logging.getLogger(f"{self.name}.performance")
        self.perf_logger.setLevel(logging.DEBUG)
        
        perf_handler = logging.FileHandler(self.log_dir / f"{self.name}_performance.log")
        perf_handler.setFormatter(logging.Formatter(
            '%(asctime)s - PERF - %(message)s'
        ))
        self.perf_logger.addHandler(perf_handler)
    
    def _create_json_formatter(self):
        """Create JSON formatter for structured logs"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage()
                }
                
                # Add structured data if available
                if hasattr(record, 'structured_data'):
                    log_entry.update(record.structured_data)
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        return JSONFormatter()
    
    def get_context(self) -> Optional[LogContext]:
        """Get current log context from thread-local storage"""
        return getattr(self._local, 'context', None)
    
    def set_context(self, context: LogContext):
        """Set log context for current thread"""
        self._local.context = context
    
    def clear_context(self):
        """Clear log context for current thread"""
        if hasattr(self._local, 'context'):
            delattr(self._local, 'context')
    
    @contextmanager
    def operation_context(self, component: str, operation: str, **kwargs):
        """Context manager for operation logging with automatic performance tracking"""
        trace_id = str(uuid.uuid4())[:8]
        context = LogContext(
            trace_id=trace_id,
            component=component,
            operation=operation,
            **kwargs
        )
        
        # Set context and start performance tracking
        old_context = self.get_context()
        self.set_context(context)
        
        # Start performance metrics
        metrics = PerformanceMetrics(start_time=time.time())
        try:
            process = psutil.Process()
            metrics.memory_before_mb = process.memory_info().rss / 1024 / 1024
        except:
            pass
        
        with self._operation_lock:
            self._active_operations[trace_id] = metrics
        
        self.info(f"Started operation: {operation}", extra_data={'action': 'operation_start'})
        
        try:
            yield context
            
            # Mark as successful
            metrics.finish()
            self.info(
                f"Completed operation: {operation}", 
                extra_data={
                    'action': 'operation_complete',
                    'performance': metrics.to_dict()
                }
            )
            
        except Exception as e:
            # Mark as failed and log error
            metrics.finish()
            self.error(
                f"Failed operation: {operation}",
                error=e,
                extra_data={
                    'action': 'operation_failed',
                    'performance': metrics.to_dict()
                }
            )
            raise
        finally:
            # Clean up
            with self._operation_lock:
                self._active_operations.pop(trace_id, None)
            
            # Restore previous context
            if old_context:
                self.set_context(old_context)
            else:
                self.clear_context()
    
    def _create_log_entry(self, level: str, message: str, 
                         error: Optional[Exception] = None,
                         extra_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create structured log entry"""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'logger': self.name,
            'message': message
        }
        
        # Add context if available
        context = self.get_context()
        if context:
            entry['context'] = context.to_dict()
        
        # Add error information
        if error:
            entry['error'] = {
                'type': error.__class__.__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        # Add extra data
        if extra_data:
            entry['data'] = extra_data
        
        return entry
    
    def _log_to_gui(self, level: str, message: str, context_info: str = ""):
        """Add log entry to GUI queue (simplified for display)"""
        try:
            gui_message = f"[{level}] {message}"
            if context_info:
                gui_message += f" | {context_info}"
            
            # Add to queue (non-blocking)
            try:
                self.gui_log_queue.put_nowait({
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'level': level,
                    'message': gui_message
                })
            except queue.Full:
                # Remove oldest and add new
                try:
                    self.gui_log_queue.get_nowait()
                    self.gui_log_queue.put_nowait({
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'level': level,
                        'message': gui_message
                    })
                except queue.Empty:
                    pass
        except:
            pass  # Don't fail main operation if GUI logging fails
    
    def trace(self, message: str, **kwargs):
        """Log trace level message"""
        entry = self._create_log_entry('TRACE', message, **kwargs)
        
        # Create log record for structured logger
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=LogLevel.TRACE.value,
            pathname='', lineno=0, msg=message, 
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        entry = self._create_log_entry('DEBUG', message, **kwargs)
        
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=logging.DEBUG,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
    
    def info(self, message: str, **kwargs):
        """Log info level message"""
        entry = self._create_log_entry('INFO', message, **kwargs)
        
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=logging.INFO,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
        
        # Add to GUI log
        context = self.get_context()
        context_info = f"{context.component}.{context.operation}" if context else ""
        self._log_to_gui('INFO', message, context_info)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        entry = self._create_log_entry('WARNING', message, **kwargs)
        
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=logging.WARNING,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
        self.error_logger.warning(message)
        
        # Add to GUI log
        context = self.get_context()
        context_info = f"{context.component}.{context.operation}" if context else ""
        self._log_to_gui('WARNING', message, context_info)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error level message"""
        entry = self._create_log_entry('ERROR', message, error=error, **kwargs)
        
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=logging.ERROR,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
        
        # Also log to error logger
        error_msg = message
        if error:
            error_msg += f" - {error.__class__.__name__}: {error}"
        self.error_logger.error(error_msg)
        
        # Add to GUI log
        context = self.get_context()
        context_info = f"{context.component}.{context.operation}" if context else ""
        self._log_to_gui('ERROR', message, context_info)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical level message"""
        entry = self._create_log_entry('CRITICAL', message, error=error, **kwargs)
        
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=logging.CRITICAL,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
        self.error_logger.critical(message)
        
        # Add to GUI log
        context = self.get_context()
        context_info = f"{context.component}.{context.operation}" if context else ""
        self._log_to_gui('CRITICAL', message, context_info)
    
    def audit(self, message: str, **kwargs):
        """Log audit trail message"""
        entry = self._create_log_entry('AUDIT', message, **kwargs)
        
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=LogLevel.AUDIT.value,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
        
        # Add to GUI log
        context = self.get_context()
        context_info = f"{context.component}.{context.operation}" if context else ""
        self._log_to_gui('AUDIT', message, context_info)
    
    def performance(self, message: str, metrics: Dict[str, Any], **kwargs):
        """Log performance metrics"""
        entry = self._create_log_entry('PERF', message, extra_data={'metrics': metrics}, **kwargs)
        
        record = logging.LogRecord(
            name=self.perf_logger.name,
            level=LogLevel.PERF.value,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        self.perf_logger.handle(record)
        
        # Also log to structured logger
        record = logging.LogRecord(
            name=self.structured_logger.name,
            level=LogLevel.PERF.value,
            pathname='', lineno=0, msg=message,
            args=(), exc_info=None
        )
        record.structured_data = entry
        self.structured_logger.handle(record)
    
    def get_gui_logs(self, limit: int = 100) -> List[Dict[str, str]]:
        """Get recent logs for GUI display"""
        logs = []
        try:
            while not self.gui_log_queue.empty() and len(logs) < limit:
                logs.append(self.gui_log_queue.get_nowait())
        except queue.Empty:
            pass
        return logs[-limit:] if logs else []


# Global logger instances
_loggers = {}
_logger_lock = threading.Lock()


def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger instance"""
    with _logger_lock:
        if name not in _loggers:
            _loggers[name] = StructuredLogger(name)
        return _loggers[name]


# Convenience functions for component-specific loggers
def get_vision_logger() -> StructuredLogger:
    """Get logger for vision system"""
    return get_logger('vision_system')


def get_database_logger() -> StructuredLogger:
    """Get logger for database operations"""
    return get_logger('database_manager')


def get_hotkey_logger() -> StructuredLogger:
    """Get logger for hotkey system"""
    return get_logger('hotkey_manager')


def get_gui_logger() -> StructuredLogger:
    """Get logger for GUI operations"""
    return get_logger('gui_interface')


def get_main_logger() -> StructuredLogger:
    """Get logger for main application"""
    return get_logger('game_monitor')


def get_all_gui_logs(limit: int = 100) -> List[Dict[str, str]]:
    """Get recent logs from all loggers for GUI display"""
    all_logs = []
    for logger in _loggers.values():
        all_logs.extend(logger.get_gui_logs(limit))
    
    # Sort by timestamp and return most recent
    all_logs.sort(key=lambda x: x['timestamp'])
    return all_logs[-limit:] if all_logs else []