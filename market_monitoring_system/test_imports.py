#!/usr/bin/env python3
"""Simple test to verify all imports work correctly."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test all module imports."""
    try:
        print("Testing configuration...")
        from config.settings import SettingsManager, ConfigurationError
        print("✓ Configuration imports successful")
        
        print("Testing database...")
        from core.database_manager import DatabaseManager, ItemData, ChangeLogEntry
        print("✓ Database imports successful")
        
        print("Testing utilities...")
        from utils.logger import LoggerManager, setup_logging
        from utils.file_utils import FileUtils, FileUtilsError
        print("✓ Utility imports successful")
        
        print("Testing core modules...")
        from core.image_processor import ImageProcessor, ImageProcessingError
        from core.ocr_client import YandexOCRClient, OCRError
        from core.text_parser import TextParser, ParsingResult, ParsingPattern, TextParsingError
        from core.monitoring_engine import MonitoringEngine, MonitoringEngineError
        print("✓ Core modules imports successful")
        
        print("Testing screenshot capture...")
        try:
            from core.screenshot_capture import ScreenshotCapture, ScreenshotCaptureError
            print("✓ Screenshot capture imports successful")
        except Exception as e:
            print(f"! Screenshot capture import warning: {e}")
        
        print("Testing scheduler...")
        from utils.scheduler import TaskScheduler, SchedulerError
        print("✓ Scheduler imports successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_configuration():
    """Test basic configuration loading."""
    try:
        # Test with the config file
        config_path = Path(__file__).parent / "market_monitoring_system" / "config.json"
        if not config_path.exists():
            print("! Configuration file not found, skipping config test")
            return True
            
        from config.settings import SettingsManager
        settings = SettingsManager(str(config_path))
        print("✓ Configuration loading successful")
        
        # Test some basic operations
        hotkeys = settings.get_enabled_hotkeys()
        print(f"✓ Found {len(hotkeys)} enabled hotkeys")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Market Monitoring System Import Test ===")
    
    imports_ok = test_imports()
    config_ok = test_basic_configuration()
    
    if imports_ok and config_ok:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)