"""Logging configuration and utilities for Voice-to-AI system."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

try:
    from ..config.settings import LoggingSettings
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config.settings import LoggingSettings


class VoiceAIFormatter(logging.Formatter):
    """Custom formatter for Voice-AI system logs."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with additional context."""
        # Add timestamp if not present
        if not hasattr(record, 'timestamp'):
            record.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Add component name based on logger name
        if hasattr(record, 'name'):
            parts = record.name.split('.')
            if len(parts) > 1:
                record.component = parts[-1]
            else:
                record.component = 'main'
        else:
            record.component = 'unknown'
        
        return super().format(record)


def setup_logging(
    settings: Optional[LoggingSettings] = None,
    log_dir: Optional[Path] = None
) -> None:
    """Setup logging configuration for the application.
    
    Args:
        settings: Logging settings configuration
        log_dir: Directory for log files
    """
    if settings is None:
        settings = LoggingSettings()
    
    if log_dir is None:
        # Default log directory
        project_root = Path(__file__).parent.parent.parent
        log_dir = project_root / "data" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    log_level = getattr(logging, settings.level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Console handler with colors (if available)
    if settings.console_enabled:
        if COLORLOG_AVAILABLE:
            console_handler = colorlog.StreamHandler(sys.stdout)
            console_formatter = colorlog.ColoredFormatter(
                fmt='%(log_color)s%(asctime)s [%(levelname)8s] %(component)s: %(message)s',
                datefmt='%H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = VoiceAIFormatter(
                fmt='%(asctime)s [%(levelname)8s] %(component)s: %(message)s',
                datefmt='%H:%M:%S'
            )
        
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings.file_enabled:
        log_file = log_dir / "voice_ai_system.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=settings.max_file_size,
            backupCount=settings.backup_count,
            encoding='utf-8'
        )
        
        file_formatter = VoiceAIFormatter(
            fmt='%(timestamp)s [%(levelname)8s] %(component)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # Specialized loggers
    _setup_specialized_loggers(settings, log_dir)
    
    # Test logging setup
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {settings.level}")
    logger.info(f"Console logging: {settings.console_enabled}")
    logger.info(f"File logging: {settings.file_enabled}")
    if settings.file_enabled:
        logger.info(f"Log directory: {log_dir}")


def _setup_specialized_loggers(settings: LoggingSettings, log_dir: Path) -> None:
    """Setup specialized loggers for different components."""
    
    # Audio events logger
    if settings.log_audio_events:
        audio_logger = logging.getLogger('voice_ai.audio')
        audio_file = log_dir / "audio_events.log"
        audio_handler = logging.handlers.RotatingFileHandler(
            filename=audio_file,
            maxBytes=settings.max_file_size,
            backupCount=3,
            encoding='utf-8'
        )
        audio_formatter = VoiceAIFormatter(
            fmt='%(timestamp)s [AUDIO] %(message)s'
        )
        audio_handler.setFormatter(audio_formatter)
        audio_logger.addHandler(audio_handler)
        audio_logger.setLevel(logging.DEBUG)
    
    # API calls logger
    if settings.log_api_calls:
        api_logger = logging.getLogger('voice_ai.api')
        api_file = log_dir / "api_calls.log"
        api_handler = logging.handlers.RotatingFileHandler(
            filename=api_file,
            maxBytes=settings.max_file_size,
            backupCount=3,
            encoding='utf-8'
        )
        api_formatter = VoiceAIFormatter(
            fmt='%(timestamp)s [API] %(component)s - %(message)s'
        )
        api_handler.setFormatter(api_formatter)
        api_logger.addHandler(api_handler)
        api_logger.setLevel(logging.INFO)
    
    # Error logger for critical issues
    error_logger = logging.getLogger('voice_ai.errors')
    error_file = log_dir / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_file,
        maxBytes=settings.max_file_size,
        backupCount=5,
        encoding='utf-8'
    )
    error_formatter = VoiceAIFormatter(
        fmt='%(timestamp)s [ERROR] %(component)s:%(funcName)s:%(lineno)d - %(message)s\nStack trace: %(exc_info)s'
    )
    error_handler.setFormatter(error_formatter)
    error_handler.setLevel(logging.ERROR)
    error_logger.addHandler(error_handler)
    
    # Performance logger
    perf_logger = logging.getLogger('voice_ai.performance')
    perf_file = log_dir / "performance.log"
    perf_handler = logging.handlers.RotatingFileHandler(
        filename=perf_file,
        maxBytes=settings.max_file_size,
        backupCount=3,
        encoding='utf-8'
    )
    perf_formatter = VoiceAIFormatter(
        fmt='%(timestamp)s [PERF] %(component)s - %(message)s'
    )
    perf_handler.setFormatter(perf_formatter)
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)


def get_logger(name: str, component: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with proper configuration.
    
    Args:
        name: Logger name (usually __name__)
        component: Optional component name for categorization
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Add component information
    if component:
        logger = logging.LoggerAdapter(logger, {'component': component})
    
    return logger


class AudioLogger:
    """Specialized logger for audio events."""
    
    def __init__(self):
        self.logger = logging.getLogger('voice_ai.audio')
    
    def capture_started(self, device: str, sample_rate: int, channels: int) -> None:
        """Log audio capture start."""
        self.logger.info(f"Audio capture started - Device: {device}, Rate: {sample_rate}Hz, Channels: {channels}")
    
    def capture_stopped(self, device: str, duration: float) -> None:
        """Log audio capture stop."""
        self.logger.info(f"Audio capture stopped - Device: {device}, Duration: {duration:.2f}s")
    
    def buffer_overflow(self, device: str, dropped_frames: int) -> None:
        """Log audio buffer overflow."""
        self.logger.warning(f"Audio buffer overflow - Device: {device}, Dropped frames: {dropped_frames}")
    
    def device_error(self, device: str, error: str) -> None:
        """Log audio device error."""
        self.logger.error(f"Audio device error - Device: {device}, Error: {error}")


class APILogger:
    """Specialized logger for API calls."""
    
    def __init__(self):
        self.logger = logging.getLogger('voice_ai.api')
    
    def request_started(self, provider: str, endpoint: str, data_size: int = 0) -> None:
        """Log API request start."""
        self.logger.info(f"API request started - Provider: {provider}, Endpoint: {endpoint}, Data size: {data_size} bytes")
    
    def request_completed(self, provider: str, endpoint: str, duration: float, response_size: int = 0) -> None:
        """Log API request completion."""
        self.logger.info(f"API request completed - Provider: {provider}, Endpoint: {endpoint}, Duration: {duration:.3f}s, Response size: {response_size} bytes")
    
    def request_failed(self, provider: str, endpoint: str, error: str, retry_count: int = 0) -> None:
        """Log API request failure."""
        self.logger.error(f"API request failed - Provider: {provider}, Endpoint: {endpoint}, Error: {error}, Retry: {retry_count}")
    
    def rate_limit_hit(self, provider: str, retry_after: int) -> None:
        """Log rate limit hit."""
        self.logger.warning(f"API rate limit hit - Provider: {provider}, Retry after: {retry_after}s")


class PerformanceLogger:
    """Specialized logger for performance metrics."""
    
    def __init__(self):
        self.logger = logging.getLogger('voice_ai.performance')
    
    def latency_measurement(self, component: str, operation: str, duration: float) -> None:
        """Log latency measurement."""
        self.logger.info(f"Latency - {component}.{operation}: {duration:.3f}s")
    
    def resource_usage(self, cpu_percent: float, memory_mb: float, threads: int) -> None:
        """Log resource usage."""
        self.logger.info(f"Resources - CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB, Threads: {threads}")
    
    def throughput_measurement(self, component: str, items_per_second: float, queue_size: int = 0) -> None:
        """Log throughput measurement."""
        self.logger.info(f"Throughput - {component}: {items_per_second:.1f} items/s, Queue size: {queue_size}")


# Global logger instances for convenience
audio_logger = AudioLogger()
api_logger = APILogger()
performance_logger = PerformanceLogger()


def log_function_call(func):
    """Decorator to log function calls with timing."""
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            logger.debug(f"Calling {func.__name__} with args={len(args)}, kwargs={len(kwargs)}")
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"Function {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {duration:.3f}s: {e}")
            raise
    
    return wrapper


def log_performance(component: str, operation: str):
    """Decorator to log performance metrics."""
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                performance_logger.latency_measurement(component, operation, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_logger.latency_measurement(f"{component}_error", operation, duration)
                raise
        
        return wrapper
    return decorator