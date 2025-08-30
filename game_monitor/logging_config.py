"""
Structured Logging Configuration for Game Monitor System

Comprehensive logging setup with file rotation, different log levels,
and structured formatting for debugging and monitoring.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
import json


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        if hasattr(record, 'performance_data'):
            log_entry['performance_data'] = record.performance_data
        
        return json.dumps(log_entry)


class GameMonitorLogger:
    """Centralized logging configuration for Game Monitor system"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure different loggers
        self.setup_root_logger()
        self.setup_performance_logger()
        self.setup_error_logger()
        self.setup_database_logger()
        self.setup_ocr_logger()
        
    def setup_root_logger(self):
        """Setup root logger with console and file output"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler with simple formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Main log file with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "game_monitor.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(console_formatter)
        file_handler.setLevel(logging.DEBUG)
        
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    def setup_performance_logger(self):
        """Setup dedicated performance logger"""
        perf_logger = logging.getLogger('performance')
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False  # Don't propagate to root
        
        # Performance log with structured format
        perf_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "performance.log",
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3
        )
        perf_handler.setFormatter(StructuredFormatter())
        perf_handler.setLevel(logging.INFO)
        
        perf_logger.addHandler(perf_handler)
    
    def setup_error_logger(self):
        """Setup dedicated error logger"""
        error_logger = logging.getLogger('errors')
        error_logger.setLevel(logging.ERROR)
        error_logger.propagate = False
        
        # Error log with stack traces
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3
        )
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            '%(pathname)s:%(lineno)d in %(funcName)s\n'
            '%(exc_info)s\n'
        )
        error_handler.setFormatter(error_formatter)
        
        error_logger.addHandler(error_handler)
    
    def setup_database_logger(self):
        """Setup database operations logger"""
        db_logger = logging.getLogger('database')
        db_logger.setLevel(logging.INFO)
        db_logger.propagate = False
        
        db_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "database.log",
            maxBytes=3 * 1024 * 1024,
            backupCount=2
        )
        db_handler.setFormatter(StructuredFormatter())
        
        db_logger.addHandler(db_handler)
    
    def setup_ocr_logger(self):
        """Setup OCR operations logger"""
        ocr_logger = logging.getLogger('ocr')
        ocr_logger.setLevel(logging.INFO)
        ocr_logger.propagate = False
        
        ocr_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "ocr.log",
            maxBytes=3 * 1024 * 1024,
            backupCount=2
        )
        ocr_handler.setFormatter(StructuredFormatter())
        
        ocr_logger.addHandler(ocr_handler)
    
    @staticmethod
    def log_performance(operation: str, duration: float, success: bool = True, **kwargs):
        """Log performance metric"""
        perf_logger = logging.getLogger('performance')
        
        # Create log record with extra data
        extra = {
            'operation': operation,
            'duration': duration,
            'performance_data': {
                'success': success,
                **kwargs
            }
        }
        
        level = logging.INFO if success else logging.WARNING
        perf_logger.log(level, f"Operation '{operation}' completed in {duration:.3f}s", extra=extra)
    
    @staticmethod
    def log_database_operation(operation: str, table: str, duration: float, 
                             rows_affected: int = 0, **kwargs):
        """Log database operation"""
        db_logger = logging.getLogger('database')
        
        extra = {
            'operation': operation,
            'duration': duration,
            'performance_data': {
                'table': table,
                'rows_affected': rows_affected,
                **kwargs
            }
        }
        
        db_logger.info(f"DB {operation} on {table}: {rows_affected} rows in {duration:.3f}s", extra=extra)
    
    @staticmethod
    def log_ocr_operation(region: str, confidence: float, duration: float, 
                         text_length: int = 0, **kwargs):
        """Log OCR operation"""
        ocr_logger = logging.getLogger('ocr')
        
        extra = {
            'operation': 'ocr_process',
            'duration': duration,
            'performance_data': {
                'region': region,
                'confidence': confidence,
                'text_length': text_length,
                **kwargs
            }
        }
        
        ocr_logger.info(f"OCR {region}: {confidence:.1f}% confidence, {text_length} chars in {duration:.3f}s", extra=extra)
    
    @staticmethod
    def log_error_with_context(error: Exception, operation: str = None, **context):
        """Log error with context information"""
        error_logger = logging.getLogger('errors')
        
        context_str = ', '.join([f"{k}={v}" for k, v in context.items()])
        message = f"Error in {operation}: {type(error).__name__}: {str(error)}"
        if context_str:
            message += f" [{context_str}]"
        
        error_logger.error(message, exc_info=error)


# Global logger setup function
def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """Setup comprehensive logging for the entire system"""
    
    # Ensure logs directory exists
    Path(log_dir).mkdir(exist_ok=True)
    
    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Initialize logging system
    logger_system = GameMonitorLogger(log_dir)
    
    # Log startup message
    logging.info("Game Monitor logging system initialized")
    logging.info(f"Log directory: {os.path.abspath(log_dir)}")
    logging.info(f"Log level: {log_level}")
    
    return logger_system


# Convenience functions for common logging patterns
def log_timing(operation: str, duration: float, success: bool = True, **kwargs):
    """Log operation timing"""
    GameMonitorLogger.log_performance(operation, duration, success, **kwargs)

def log_db_operation(operation: str, table: str, duration: float, rows: int = 0, **kwargs):
    """Log database operation"""
    GameMonitorLogger.log_database_operation(operation, table, duration, rows, **kwargs)

def log_ocr(region: str, confidence: float, duration: float, text_len: int = 0, **kwargs):
    """Log OCR operation"""
    GameMonitorLogger.log_ocr_operation(region, confidence, duration, text_len, **kwargs)

def log_error(error: Exception, operation: str = None, **context):
    """Log error with context"""
    GameMonitorLogger.log_error_with_context(error, operation, **context)