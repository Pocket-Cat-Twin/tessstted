"""Test script to validate Voice-to-AI system components."""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test all critical imports."""
    print("Testing imports...")
    
    try:
        # Core modules
        from config.settings import ConfigManager, Settings
        print("✓ Configuration system imported successfully")
        
        from utils.logger import setup_logging, get_logger
        print("✓ Logging system imported successfully")
        
        from core.event_bus import EventBus, EventType, get_event_bus
        print("✓ Event bus imported successfully")
        
        from core.state_manager import StateManager, SystemState, get_state_manager
        print("✓ State manager imported successfully")
        
        from core.thread_coordinator import ThreadCoordinator, ThreadType, get_thread_coordinator
        print("✓ Thread coordinator imported successfully")
        
        # Audio modules
        from audio.capture_service import AudioCaptureService, AudioDeviceType
        print("✓ Audio capture service imported successfully")
        
        from audio.buffer_manager import AudioBufferManager, BufferMode
        print("✓ Audio buffer manager imported successfully")
        
        from audio.vad_detector import VoiceActivityDetector, VADMode
        print("✓ Voice activity detector imported successfully")
        
        # Hotkey modules
        from hotkeys.hotkey_manager import HotkeyManager, HotkeyBackend
        print("✓ Hotkey manager imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during imports: {e}")
        return False

def test_configuration():
    """Test configuration system."""
    print("\nTesting configuration system...")
    
    try:
        from config.settings import ConfigManager
        
        # Test configuration loading
        config_manager = ConfigManager()
        settings = config_manager.get_settings()
        
        print(f"✓ Configuration loaded - Audio sample rate: {settings.audio.sample_rate}")
        print(f"✓ Hotkeys configured - Start recording: {settings.hotkeys.start_recording}")
        
        # Test validation
        if config_manager.validate_settings():
            print("✓ Configuration validation passed")
        else:
            print("✗ Configuration validation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_logging():
    """Test logging system."""
    print("\nTesting logging system...")
    
    try:
        from utils.logger import setup_logging, get_logger
        from config.settings import ConfigManager
        
        # Setup logging
        config_manager = ConfigManager()
        settings = config_manager.get_settings()
        setup_logging(settings.logging)
        
        # Test logger
        logger = get_logger(__name__)
        logger.info("Test log message")
        logger.debug("Test debug message")
        logger.warning("Test warning message")
        
        print("✓ Logging system working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        return False

def test_event_system():
    """Test event bus system."""
    print("\nTesting event system...")
    
    try:
        from core.event_bus import get_event_bus, EventType
        
        event_bus = get_event_bus()
        
        # Test event subscription and emission
        received_events = []
        
        def test_handler(event):
            received_events.append(event)
        
        # Subscribe to test event
        event_bus.subscribe(EventType.APPLICATION_STARTED, test_handler)
        
        # Emit test event
        event_bus.emit(EventType.APPLICATION_STARTED, "test_system", {"test": True})
        
        if len(received_events) > 0:
            print("✓ Event system working correctly")
            return True
        else:
            print("✗ Event not received")
            return False
        
    except Exception as e:
        print(f"✗ Event system test failed: {e}")
        return False

def test_state_management():
    """Test state management system."""
    print("\nTesting state management...")
    
    try:
        from core.state_manager import get_state_manager, SystemState
        
        state_manager = get_state_manager()
        
        # Test state operations
        initial_state = state_manager.get_system_state()
        print(f"✓ Initial system state: {initial_state.value}")
        
        # Test state change
        state_manager.set_system_state(SystemState.READY)
        current_state = state_manager.get_system_state()
        
        if current_state == SystemState.READY:
            print("✓ State management working correctly")
            return True
        else:
            print("✗ State change failed")
            return False
        
    except Exception as e:
        print(f"✗ State management test failed: {e}")
        return False

def test_dependencies():
    """Test external dependencies."""
    print("\nTesting external dependencies...")
    
    dependencies = {
        "numpy": "Audio processing",
        "threading": "Multi-threading support",
        "queue": "Thread-safe queues",
        "dataclasses": "Configuration structures",
        "enum": "Enumeration support",
        "pathlib": "Path handling",
        "json": "Configuration files",
        "logging": "Logging system",
        "time": "Timing operations"
    }
    
    missing_deps = []
    
    for dep, description in dependencies.items():
        try:
            __import__(dep)
            print(f"✓ {dep}: {description}")
        except ImportError:
            print(f"✗ {dep}: {description} - NOT AVAILABLE")
            missing_deps.append(dep)
    
    # Test optional dependencies
    optional_deps = {
        "pyaudio": "Audio capture",
        "keyboard": "Global hotkeys",
        "pynput": "Alternative hotkey backend",
        "webrtcvad": "Voice activity detection",
        "colorlog": "Colored logging"
    }
    
    print("\nOptional dependencies:")
    for dep, description in optional_deps.items():
        try:
            __import__(dep)
            print(f"✓ {dep}: {description}")
        except ImportError:
            print(f"⚠ {dep}: {description} - Not available (will use fallback)")
    
    return len(missing_deps) == 0

def main():
    """Run all tests."""
    print("Voice-to-AI System Validation\n" + "="*40)
    
    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("Logging Tests", test_logging),
        ("Event System Tests", test_event_system),
        ("State Management Tests", test_state_management),
        ("Dependency Tests", test_dependencies)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        
        try:
            if test_func():
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n{'='*40}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)