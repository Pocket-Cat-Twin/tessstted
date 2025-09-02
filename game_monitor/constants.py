"""
System Constants for Game Monitor System
Centralizes all hardcoded values for easy maintenance and configuration.
"""

from typing import Dict, Tuple, Any

# === APPLICATION METADATA ===
APP_VERSION = "1.0.0"
APP_NAME = "Game Monitor System"
APP_TITLE = f"{APP_NAME} - v{APP_VERSION}"

# === PERFORMANCE CONSTANTS ===
class Performance:
    """Performance-related constants"""
    # Time thresholds (seconds)
    MAX_PROCESSING_TIME = 0.8        # Reserve 0.2s for other operations
    MAX_CAPTURE_TIME = 1.0           # Maximum total capture time
    WARNING_THRESHOLD = 0.8          # Warning threshold for slow operations
    TIMEOUT_STANDARD = 1.0           # Standard timeout for operations
    TIMEOUT_QUEUE = 1.0              # Queue operation timeout
    
    # Performance categories
    EXCELLENT_THRESHOLD = 0.5        # < 0.5s = excellent
    GOOD_THRESHOLD = 1.0             # < 1.0s = good, >= 1.0s = slow
    
    # Batch processing
    BATCH_TIMEOUT = 1.0              # Process batches every second

# === DATABASE CONSTANTS ===
class Database:
    """Database-related constants"""
    # Connection and caching
    CACHE_SIZE_PAGES = 10000         # SQLite cache size (10MB cache)
    DEFAULT_POOL_SIZE = 5            # Default connection pool size
    CONNECTION_TIMEOUT = 5.0         # Connection timeout in seconds
    
    # Storage and cleanup
    DISK_SPACE_WARNING_GB = 1.0      # Less than 1GB free space warning
    
    # Query performance
    MAX_METRICS_HISTORY = 10000      # Keep last 10K query metrics

# === VALIDATION CONSTANTS ===  
class Validation:
    """Data validation constants"""
    # Confidence levels
    PERFECT_CONFIDENCE = 1.0         # Maximum confidence score
    MIN_CONFIDENCE = 0.0             # Minimum confidence score
    
    # String length limits
    MIN_TRADER_NAME_LENGTH = 3       # Minimum trader name length
    MAX_TRADER_NAME_LENGTH = 16      # Maximum trader name length
    MIN_TRADER_NAME_FLEXIBLE = 2     # Flexible minimum trader name length
    MAX_TRADER_NAME_FLEXIBLE = 20    # Flexible maximum trader name length
    
    # Numeric validation limits
    MIN_QUANTITY = 1                 # Minimum item quantity
    MAX_QUANTITY_STRICT = 999999     # Maximum quantity (strict mode)
    MAX_QUANTITY_FLEXIBLE = 99999999 # Maximum quantity (flexible mode)
    MAX_PRICE_DIGITS = 8             # Maximum digits in price
    MAX_PRICE_DECIMALS = 2           # Maximum decimal places in price
    
    # Quantity validation ranges
    ITEM_QUANTITY_RANGES: Dict[str, Tuple[int, int]] = {
        'consumable': (1, 999),      # potions, food
        'equipment': (1, 5),         # weapons, armor (stackable pieces)
        'material': (1, 9999),       # crafting materials
        'currency': (1, 999999),     # gold, gems
        'accessory': (1, 10),        # rings, amulets (limited slots)
        'rare': (1, 99),             # rare items
        'epic': (1, 9),              # epic items (very limited)
        'legendary': (1, 3)          # legendary items (extremely rare)
    }
    
    # Price validation ranges (in gold)
    ITEM_PRICE_RANGES: Dict[str, Tuple[int, int]] = {
        'consumable': (1, 1000),     # potions, food
        'equipment': (100, 50000),   # weapons, armor
        'material': (1, 500),        # crafting materials  
        'currency': (1, 1),          # 1:1 exchange rate
        'accessory': (500, 100000),  # rings, amulets
        'rare': (1000, 25000),       # rare items
        'epic': (5000, 100000),      # epic items
        'legendary': (25000, 500000) # legendary items
    }
    
    # Quantity thresholds for warnings
    HIGH_QUANTITY_THRESHOLD = 10000   # Warn if quantity >= 10000
    SUSPICIOUS_QUANTITY_THRESHOLD = 100000  # Flag as suspicious if >= 100000

# === OCR CONSTANTS ===
class OCR:
    """OCR processing constants"""
    # Character whitelists
    TRADER_NAME_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
    QUANTITY_WHITELIST = "0123456789"
    PRICE_WHITELIST = "0123456789."
    
    # Processing limits
    MAX_TEXT_LENGTH = 200            # Maximum OCR text length for validation
    CONFIDENCE_THRESHOLD_DEFAULT = 0.85  # Default confidence threshold

# === QUEUE AND BUFFER CONSTANTS ===
class Queues:
    """Queue and buffer size constants"""
    # History and metrics storage
    MAX_ERROR_HISTORY = 10000        # Keep last 10K errors
    MAX_OPERATION_HISTORY = 10000    # Keep last 10K operations  
    MAX_PERFORMANCE_METRICS = 10000  # Keep last 10K performance metrics
    
    # Processing queues
    MAX_HOTKEY_QUEUE_SIZE = 100      # Maximum hotkey queue size
    MAX_BATCH_SIZE = 100             # Maximum batch operation size

# === GUI CONSTANTS ===
class GUI:
    """GUI-related constants"""
    # Window dimensions
    DEFAULT_WIDTH = 800              # Default window width
    DEFAULT_HEIGHT = 600             # Default window height
    MIN_WINDOW_WIDTH = 800           # Minimum window width
    MIN_WINDOW_HEIGHT = 600          # Minimum window height
    
    # Text widget operations
    TEXT_DELETE_START = "1.0"        # Text widget start position
    TEXT_DELETE_SINGLE_LINE = "2.0"  # Delete single line position
    TEXT_INSERT_START = "1.0"        # Text insert start position
    
    # Update intervals (seconds)
    STATISTICS_UPDATE_INTERVAL = 1.0  # Statistics refresh rate
    STATUS_UPDATE_INTERVAL = 0.5      # Status refresh rate
    LOG_UPDATE_INTERVAL = 2.0         # Log refresh rate
    
    # Log display settings
    MAX_LOG_LINES = 1000             # Maximum lines in log display
    LOG_CLEANUP_BATCH_SIZE = 100     # Lines to delete when cleaning up
    
    # Widget dimensions and spacing
    STATUS_INDICATOR_X_OFFSET = 100  # X offset for status indicator
    STATUS_INDICATOR_Y_OFFSET = 120  # Y offset for status text
    STATUS_PADDING = 20              # General padding for status elements
    
    # Column widths for tables
    TABLE_COLUMN_TIME = 120          # Time column width
    TABLE_COLUMN_TRADER = 120        # Trader column width  
    TABLE_COLUMN_ITEM = 150          # Item column width
    TABLE_COLUMN_QUANTITY = 80       # Quantity column width
    TABLE_COLUMN_PRICE = 100         # Price column width
    TABLE_COLUMN_CONFIDENCE = 80     # Confidence column width
    
    # Data display limits
    MAX_DISPLAY_ITEMS = 50           # Maximum items in tables
    DEFAULT_RECENT_TRADES_LIMIT = 20 # Default number of recent trades
    TRADER_NAME_TRUNCATE_LENGTH = 20 # Truncate trader names to this length
    ITEM_NAME_TRUNCATE_LENGTH = 30   # Truncate item names to this length
    
    # Widget sizing
    ENTRY_FIELD_WIDTH = 30           # Default entry field width
    SCALE_LENGTH = 200               # Scale widget length
    SCALE_MIN_VALUE = 50             # Scale minimum value
    SCALE_MAX_VALUE = 100            # Scale maximum value
    
    # Default thresholds
    DEFAULT_RESPONSE_TIME_TARGET = 1000  # Default response time target (ms)
    DEFAULT_CONFIDENCE_THRESHOLD = 85    # Default OCR confidence threshold

# === LOGGING CONSTANTS ===
class Logging:
    """Logging-related constants"""
    # File sizes and rotation
    MAX_LOG_SIZE_MB = 50             # Maximum log file size in MB
    DEFAULT_BACKUP_COUNT = 5         # Number of backup log files
    
    # Log levels
    DEFAULT_LEVEL = "INFO"           # Default logging level
    
    # Log format
    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# === COMPRESSION CONSTANTS ===
class Compression:
    """Compression-related constants"""
    NO_COMPRESSION_RATIO = 1.0       # No compression achieved
    MIN_COMPRESSION_RATIO = 0.1      # Minimum expected compression ratio

# === SCREEN CAPTURE CONSTANTS ===
class Screen:
    """Screen capture constants"""
    # Supported image formats
    SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "bmp", "tiff"]
    DEFAULT_FORMAT = "png"
    
    # Region constraints (for validation)
    MIN_REGION_WIDTH = 50            # Minimum capture region width
    MIN_REGION_HEIGHT = 30           # Minimum capture region height
    MAX_SCREEN_WIDTH = 7680          # Support up to 8K width
    MAX_SCREEN_HEIGHT = 4320         # Support up to 8K height

# === THREAD POOL CONSTANTS ===
class Threading:
    """Threading-related constants"""
    DEFAULT_THREAD_POOL_SIZE = 4     # Default thread pool size
    MAX_THREAD_POOL_SIZE = 16        # Maximum thread pool size
    THREAD_TIMEOUT = 1.0             # Thread operation timeout

# === MEMORY CONSTANTS ===
class Memory:
    """Memory usage constants"""  
    DEFAULT_MAX_MEMORY_MB = 200      # Default memory limit in MB
    MIN_MEMORY_MB = 50               # Minimum memory requirement
    MAX_MEMORY_MB = 4096             # Maximum memory limit

# === HOTKEY CONSTANTS ===
class Hotkeys:
    """Hotkey system constants"""
    # Default hotkey mappings
    DEFAULT_MAPPINGS = {
        'trader_list': 'F1',
        'item_scan': 'F2', 
        'trader_inventory': 'F3',
        'manual_verification': 'F4',
        'emergency_stop': 'F5'
    }
    
    # Processing timeouts and limits
    DEFAULT_CALLBACK_TIMEOUT = 5.0      # Default callback execution timeout
    SHUTDOWN_COMPLETION_TIMEOUT = 3.0   # Timeout for callback completion during shutdown
    EXECUTOR_SHUTDOWN_TIMEOUT = 2.0     # ThreadPoolExecutor shutdown timeout
    QUEUE_PUT_TIMEOUT = 0.1              # Fast timeout for queue operations
    CALLBACK_WAIT_SLEEP = 0.1            # Sleep interval when waiting for callbacks
    MAX_QUEUE_UTILIZATION = 1.0          # Maximum queue utilization ratio

# === FILE SYSTEM CONSTANTS ===
class FileSystem:
    """File system constants"""
    # Default paths
    DEFAULT_DATA_DIR = "data"
    DEFAULT_CONFIG_DIR = "config" 
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_SCREENSHOT_DIR = "data/screenshots"
    
    # Database files
    DEFAULT_DB_NAME = "game_monitor.db"
    DEFAULT_DB_PATH = f"{DEFAULT_DATA_DIR}/{DEFAULT_DB_NAME}"
    
    # Configuration files
    CONFIG_FILE_NAME = "config.yaml"
    CONFIG_FILE_PATH = f"{DEFAULT_CONFIG_DIR}/{CONFIG_FILE_NAME}"
    
    # Log files
    LOG_FILE_NAME = "game_monitor.log"
    LOG_FILE_PATH = f"{DEFAULT_LOG_DIR}/{LOG_FILE_NAME}"

# === VALIDATION LEVELS ===
class ValidationLevels:
    """Validation strictness levels"""
    PERMISSIVE = "permissive"        # Lenient validation
    BALANCED = "balanced"            # Default validation level  
    STRICT = "strict"                # Strict validation
    
    # Auto-approval thresholds by level
    AUTO_APPROVE_THRESHOLDS = {
        PERMISSIVE: 0.7,
        BALANCED: 0.85,
        STRICT: 0.95
    }

# === ERROR CATEGORIES ===
class ErrorCategories:
    """Error classification constants"""
    CRITICAL_KEYWORDS = ["fatal", "critical", "corrupt", "crash"]
    HIGH_SEVERITY_KEYWORDS = ["timeout", "connection", "memory", "thread"]
    WARNING_KEYWORDS = ["slow", "degraded", "retry", "fallback"]

# === BUSINESS LOGIC CONSTANTS ===
class BusinessLogic:
    """Business rule constants"""
    # Trade validation
    MIN_TRADE_VALUE = 1              # Minimum trade value in gold
    MAX_TRADE_VALUE = 1000000        # Maximum reasonable trade value
    
    # Item categories requiring strict validation
    STRICT_VALIDATION_ITEMS = ["epic", "legendary", "artifact"]
    
    # Time-based validation
    MAX_ITEM_AGE_DAYS = 365          # Maximum item age for historical validation
    CACHE_CLEANUP_DAYS = 7           # Clean cache after N days
    SCREENSHOT_CLEANUP_DAYS = 30     # Clean screenshots after N days

# === REGEX PATTERNS ===
class Patterns:
    """Common regex patterns"""
    # File path validation
    SAFE_FILENAME_PATTERN = r"^[^<>:\"|?*]*$"
    DB_FILE_PATTERN = r"^[^<>:\"|?*]*\.db$"
    LOG_FILE_PATTERN = r"^[^<>:\"|?*]*\.log$"
    
    # Language pack validation  
    LANGUAGE_PACK_PATTERN = r"^[a-z]{3}(\+[a-z]{3})*$"
    
    # Hotkey validation
    HOTKEY_PATTERN = r"^(F([1-9]|1[0-2])|ctrl\+[a-z]|alt\+[a-z]|shift\+[a-z]|[a-z])$"

# === CONFIGURATION DEFAULTS ===
class ConfigDefaults:
    """Default configuration values"""
    # Performance defaults
    PERFORMANCE = {
        'max_capture_time': Performance.MAX_CAPTURE_TIME,
        'warning_threshold': Performance.WARNING_THRESHOLD,
        'enable_performance_logging': True,
        'enable_monitoring': True
    }
    
    # Database defaults
    DATABASE = {
        'path': FileSystem.DEFAULT_DB_PATH,
        'pool_size': Database.DEFAULT_POOL_SIZE,
        'enable_wal': True,
        'cache_size': Database.CACHE_SIZE_PAGES
    }
    
    # Logging defaults
    LOGGING = {
        'level': Logging.DEFAULT_LEVEL,
        'file': FileSystem.LOG_FILE_PATH,
        'max_size': Logging.MAX_LOG_SIZE_MB,
        'backup_count': Logging.DEFAULT_BACKUP_COUNT,
        'format': Logging.DEFAULT_FORMAT,
        'console': True
    }
    
    # OCR defaults
    OCR = {
        'confidence_threshold': OCR.CONFIDENCE_THRESHOLD_DEFAULT,
        'max_processing_time': Performance.MAX_PROCESSING_TIME,
        'use_cache': True,
        'languages': "eng+rus"
    }


def get_constant_by_path(path: str) -> Any:
    """
    Get constant value by dot-separated path.
    
    Args:
        path: Dot-separated path like 'Performance.MAX_CAPTURE_TIME'
        
    Returns:
        Constant value or None if not found
        
    Example:
        >>> get_constant_by_path('Performance.MAX_CAPTURE_TIME')
        1.0
    """
    try:
        parts = path.split('.')
        current = globals()
        
        for part in parts:
            if hasattr(current.get(part, {}), '__dict__'):
                current = current[part].__dict__
            else:
                current = getattr(current.get(part, {}), part, None)
                break
        
        return current
    except (AttributeError, KeyError):
        return None


def validate_constant_usage() -> Dict[str, Any]:
    """
    Validate that all constants are properly defined and have reasonable values.
    
    Returns:
        Dictionary with validation results
    """
    issues = []
    warnings = []
    
    # Validate performance thresholds
    if Performance.WARNING_THRESHOLD >= Performance.MAX_CAPTURE_TIME:
        issues.append("Performance.WARNING_THRESHOLD should be less than MAX_CAPTURE_TIME")
    
    # Validate queue sizes
    if Queues.MAX_ERROR_HISTORY <= 0:
        issues.append("Queue sizes must be positive")
    
    # Validate file paths
    if not FileSystem.DEFAULT_DB_PATH.endswith('.db'):
        issues.append("Database path should end with .db")
    
    # Validate ranges
    for category, (min_val, max_val) in Validation.ITEM_QUANTITY_RANGES.items():
        if min_val >= max_val:
            issues.append(f"Invalid quantity range for {category}: min >= max")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'constants_count': sum(len(cls.__dict__) for cls in [
            Performance, Database, Validation, OCR, Queues, GUI, 
            Logging, Screen, Threading, Memory, Hotkeys, FileSystem
        ] if hasattr(cls, '__dict__'))
    }


# Validate constants on module import
_validation_result = validate_constant_usage()
if not _validation_result['valid']:
    import warnings
    warnings.warn(f"Constant validation failed: {_validation_result['issues']}")