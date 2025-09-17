"""
Arduino Automation System - Core Package
Hybrid Python-Arduino automation system with dual threading architecture
"""

__version__ = "1.0.0"
__author__ = "Arduino Automation System"
__description__ = "Hybrid Python-Arduino automation system with OCR monitoring and database integration"

# Core components
from .main import AutomationSystemCoordinator
from .arduino_controller import ArduinoController, DelayManager, ArduinoCommandResult
from .database_integration import AutomationDatabaseManager, AutomationTarget
from .tesseract_ocr import TesseractOCRManager, OCRRegion, OCRResult
from .database_monitor import DatabaseMonitorThread
from .array_processor import ArrayProcessorThread
from .config_manager import ConfigManager, PlaceholderManager, ArduinoPortDetector

# Configuration and setup
from .config_manager import ConfigurationError

__all__ = [
    # Main coordinator
    "AutomationSystemCoordinator",
    
    # Core controllers
    "ArduinoController", 
    "DelayManager",
    "ArduinoCommandResult",
    
    # Database integration
    "AutomationDatabaseManager",
    "AutomationTarget",
    
    # OCR system
    "TesseractOCRManager",
    "OCRRegion", 
    "OCRResult",
    
    # Processing threads
    "DatabaseMonitorThread",
    "ArrayProcessorThread",
    
    # Configuration management
    "ConfigManager",
    "PlaceholderManager", 
    "ArduinoPortDetector",
    "ConfigurationError",
    
    # Version info
    "__version__",
    "__author__", 
    "__description__"
]

# Package metadata
SYSTEM_INFO = {
    "name": "Arduino Automation System",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "python_requires": ">=3.8",
    "arduino_requirements": {
        "board": "Arduino Micro (USB HID support required)",
        "libraries": ["Mouse.h", "Keyboard.h"],
        "ide_version": "1.8.0+"
    },
    "features": [
        "Free Tesseract OCR (alternative to Yandex OCR)",
        "Arduino Micro USB HID control",
        "Dual-thread automation (database monitor + array processor)",
        "SQLite database integration",
        "Screen region OCR monitoring",
        "Randomized delay system (1-2 seconds)",
        "Placeholder configuration system",
        "Windows COM port auto-detection",
        "Comprehensive logging and statistics",
        "Graceful shutdown handling"
    ],
    "supported_platforms": ["Windows", "Linux", "macOS"],
    "primary_platform": "Windows"
}

def get_system_info():
    """Get system information dictionary."""
    return SYSTEM_INFO.copy()

def print_system_info():
    """Print formatted system information."""
    info = get_system_info()
    print(f"{info['name']} v{info['version']}")
    print("=" * 50)
    print(f"Description: {info['description']}")
    print(f"Author: {info['author']}")
    print(f"Python Requirements: {info['python_requires']}")
    print(f"Primary Platform: {info['primary_platform']}")
    print()
    print("Arduino Requirements:")
    arduino_req = info['arduino_requirements']
    print(f"  Board: {arduino_req['board']}")
    print(f"  Libraries: {', '.join(arduino_req['libraries'])}")
    print(f"  IDE Version: {arduino_req['ide_version']}")
    print()
    print("Features:")
    for feature in info['features']:
        print(f"  - {feature}")
    print()
    print(f"Supported Platforms: {', '.join(info['supported_platforms'])}")

# Convenience imports for common usage patterns
def create_automation_system(config_dir=None):
    """
    Create and return AutomationSystemCoordinator instance.
    
    Args:
        config_dir: Optional path to configuration directory
        
    Returns:
        AutomationSystemCoordinator instance
    """
    return AutomationSystemCoordinator(config_dir)

def quick_arduino_test(port='COM3'):
    """
    Quick Arduino connection test.
    
    Args:
        port: COM port to test
        
    Returns:
        True if Arduino responds, False otherwise
    """
    try:
        with ArduinoController(port=port) as arduino:
            return arduino.ping()
    except Exception:
        return False

# Module initialization
def _check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    try:
        import pytesseract
    except ImportError:
        missing_deps.append("pytesseract")
    
    try:
        import PIL
    except ImportError:
        missing_deps.append("Pillow")
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import serial
    except ImportError:
        missing_deps.append("pyserial")
    
    try:
        import mss
    except ImportError:
        missing_deps.append("mss")
    
    if missing_deps:
        import warnings
        warnings.warn(
            f"Missing dependencies: {', '.join(missing_deps)}. "
            f"Install with: pip install {' '.join(missing_deps)}",
            ImportWarning
        )
    
    return len(missing_deps) == 0

# Check dependencies on import
_dependencies_available = _check_dependencies()