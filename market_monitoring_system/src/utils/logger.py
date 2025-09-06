"""
Comprehensive logging system for market monitoring application.
Provides structured logging with file rotation and multiple output targets.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs log records as JSON for better parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
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
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
            
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Colored console formatter for better readability during development.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green  
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console output."""
        # Add color codes
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format the message
        record.levelname = f"{color}{record.levelname}{reset}"
        formatted = super().format(record)
        
        return formatted


class LoggerManager:
    """
    Centralized logger management for the market monitoring system.
    Handles configuration, file rotation, and multiple output formats.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize logger manager with configuration.
        
        Args:
            config: Logging configuration dictionary
        """
        self.config = config
        self.logs_dir = Path(config.get('logs_dir', 'data/logs'))
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Logger configuration
        self.log_level = getattr(logging, config.get('level', 'INFO').upper())
        self.format_string = config.get('format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.max_bytes = config.get('max_log_size_mb', 100) * 1024 * 1024
        self.backup_count = config.get('backup_count', 5)
        self.console_output = config.get('console_output', True)
        
        # Setup root logger
        self._setup_root_logger()
        
        # Component-specific loggers
        self._component_loggers = {}
        
    def _setup_root_logger(self) -> None:
        """Setup the root logger with handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.logs_dir / 'market_monitoring.log',
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(self.format_string)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # JSON file handler for structured logs
        json_handler = logging.handlers.RotatingFileHandler(
            filename=self.logs_dir / 'market_monitoring.json.log',
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(self.log_level)
        json_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(json_handler)
        
        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_formatter = ColoredConsoleFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get logger for specific component.
        
        Args:
            name: Logger name (typically module name)
            
        Returns:
            Configured logger instance
        """
        if name not in self._component_loggers:
            logger = logging.getLogger(name)
            self._component_loggers[name] = logger
            
        return self._component_loggers[name]
    
    def log_performance(self, component: str, operation: str, 
                       duration: float, extra_data: Optional[Dict] = None) -> None:
        """
        Log performance metrics for operations.
        
        Args:
            component: Component name
            operation: Operation name
            duration: Operation duration in seconds
            extra_data: Additional data to log
        """
        logger = self.get_logger(f'{component}.performance')
        
        perf_data = {
            'operation': operation,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        if extra_data:
            perf_data.update(extra_data)
            
        # Create log record with extra data
        logger.info(f"Performance: {operation} completed in {duration:.3f}s", 
                   extra={'extra_data': perf_data})
    
    def log_ocr_session(self, session_id: int, hotkey: str, 
                       items_processed: int, processing_time: float,
                       success: bool, error_message: Optional[str] = None) -> None:
        """
        Log OCR session details.
        
        Args:
            session_id: OCR session ID
            hotkey: Hotkey that triggered the session
            items_processed: Number of items processed
            processing_time: Total processing time
            success: Whether session was successful
            error_message: Error message if failed
        """
        logger = self.get_logger('ocr.sessions')
        
        session_data = {
            'session_id': session_id,
            'hotkey': hotkey,
            'items_processed': items_processed,
            'processing_time': processing_time,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if error_message:
            session_data['error'] = error_message
            
        if success:
            logger.info(f"OCR session {session_id} completed successfully", 
                       extra={'extra_data': session_data})
        else:
            logger.error(f"OCR session {session_id} failed: {error_message}", 
                        extra={'extra_data': session_data})
    
    def log_change_detection(self, changes: list, hotkey: str) -> None:
        """
        Log change detection results.
        
        Args:
            changes: List of detected changes
            hotkey: Hotkey that triggered the detection
        """
        logger = self.get_logger('monitoring.changes')
        
        change_data = {
            'hotkey': hotkey,
            'changes_count': len(changes),
            'changes': [
                {
                    'seller': change.seller_name,
                    'item': change.item_name,
                    'type': change.change_type,
                    'old_value': change.old_value,
                    'new_value': change.new_value
                }
                for change in changes
            ],
            'timestamp': datetime.now().isoformat()
        }
        
        if changes:
            logger.info(f"Detected {len(changes)} changes for {hotkey}", 
                       extra={'extra_data': change_data})
        else:
            logger.debug(f"No changes detected for {hotkey}", 
                        extra={'extra_data': change_data})
    
    def log_database_operation(self, operation: str, table: str, 
                              rows_affected: int, success: bool,
                              error_message: Optional[str] = None) -> None:
        """
        Log database operations.
        
        Args:
            operation: Database operation (INSERT, UPDATE, DELETE)
            table: Table name
            rows_affected: Number of rows affected
            success: Whether operation was successful
            error_message: Error message if failed
        """
        logger = self.get_logger('database.operations')
        
        db_data = {
            'operation': operation,
            'table': table,
            'rows_affected': rows_affected,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if error_message:
            db_data['error'] = error_message
            
        if success:
            logger.info(f"Database {operation} on {table}: {rows_affected} rows", 
                       extra={'extra_data': db_data})
        else:
            logger.error(f"Database {operation} failed on {table}: {error_message}", 
                        extra={'extra_data': db_data})
    
    def log_system_event(self, event_type: str, component: str, 
                        message: str, level: str = 'INFO',
                        extra_data: Optional[Dict] = None) -> None:
        """
        Log general system events.
        
        Args:
            event_type: Type of event (startup, shutdown, error, etc.)
            component: Component generating the event
            message: Event message
            level: Log level
            extra_data: Additional event data
        """
        logger = self.get_logger(f'system.{component}')
        
        event_data = {
            'event_type': event_type,
            'component': component,
            'timestamp': datetime.now().isoformat()
        }
        
        if extra_data:
            event_data.update(extra_data)
            
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, message, extra={'extra_data': event_data})
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """
        Clean up log files older than specified days.
        
        Args:
            days_to_keep: Number of days to keep log files
        """
        logger = self.get_logger('system.maintenance')
        
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            removed_count = 0
            
            for log_file in self.logs_dir.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} old log files")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get logging statistics.
        
        Returns:
            Dictionary with logging statistics
        """
        try:
            stats = {
                'logs_directory': str(self.logs_dir),
                'log_level': logging.getLevelName(self.log_level),
                'log_files': [],
                'total_size_mb': 0
            }
            
            for log_file in self.logs_dir.glob('*.log*'):
                file_size = log_file.stat().st_size
                stats['log_files'].append({
                    'name': log_file.name,
                    'size_mb': file_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
                stats['total_size_mb'] += file_size / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            self.get_logger('system.logger').error(f"Failed to get log statistics: {e}")
            return {}


def setup_logging(logs_dir: str = 'data/logs', 
                 level: str = 'INFO',
                 console_output: bool = True) -> LoggerManager:
    """
    Convenience function to setup logging with default configuration.
    
    Args:
        logs_dir: Directory for log files
        level: Log level
        console_output: Whether to output to console
        
    Returns:
        Configured LoggerManager instance
    """
    config = {
        'logs_dir': logs_dir,
        'level': level,
        'console_output': console_output,
        'max_log_size_mb': 100,
        'backup_count': 5,
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    }
    
    return LoggerManager(config)