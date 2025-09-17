"""Simple test to verify basic functionality without complex imports."""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_basic_imports():
    """Test basic imports that should work."""
    print("Testing basic imports...")
    
    try:
        # Test config system
        import config.settings
        print("✓ Config module imported")
        
        config_manager = config.settings.ConfigManager()
        settings = config_manager.get_settings()
        print(f"✓ Configuration loaded - Sample rate: {settings.audio.sample_rate}")
        
        # Test core event bus
        import core.event_bus
        print("✓ Event bus module imported")
        
        event_bus = core.event_bus.get_event_bus()
        print("✓ Event bus instance created")
        
        # Test state manager
        import core.state_manager
        print("✓ State manager module imported")
        
        state_manager = core.state_manager.get_state_manager()
        print("✓ State manager instance created")
        
        # Test thread coordinator
        import core.thread_coordinator
        print("✓ Thread coordinator module imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_classes():
    """Test audio classes without audio hardware."""
    print("\nTesting audio classes...")
    
    try:
        from audio.capture_service import AudioDeviceType, AudioFrame
        print("✓ Audio types imported")
        
        from audio.buffer_manager import BufferMode
        print("✓ Buffer manager imported")
        
        from audio.vad_detector import VADMode
        print("✓ VAD detector imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Audio test error: {e}")
        return False

def test_hotkey_classes():
    """Test hotkey classes."""
    print("\nTesting hotkey classes...")
    
    try:
        from hotkeys.hotkey_manager import HotkeyBackend
        print("✓ Hotkey manager imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Hotkey test error: {e}")
        return False

def test_configuration_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    try:
        import config.settings
        
        config_manager = config.settings.ConfigManager()
        
        # Test validation
        if config_manager.validate_settings():
            print("✓ Configuration validation passed")
            return True
        else:
            print("✗ Configuration validation failed")
            return False
        
    except Exception as e:
        print(f"✗ Configuration validation error: {e}")
        return False

def test_data_structures():
    """Test core data structures."""
    print("\nTesting data structures...")
    
    try:
        from core.event_bus import EventType
        from core.state_manager import SystemState, ComponentState
        from core.thread_coordinator import ThreadType
        
        print(f"✓ Event types available: {len(list(EventType))}")
        print(f"✓ System states available: {len(list(SystemState))}")
        print(f"✓ Component states available: {len(list(ComponentState))}")
        print(f"✓ Thread types available: {len(list(ThreadType))}")
        
        return True
        
    except Exception as e:
        print(f"✗ Data structures test error: {e}")
        return False

def main():
    """Run simple tests."""
    print("Voice-to-AI System - Simple Validation")
    print("=" * 45)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Audio Classes", test_audio_classes),
        ("Hotkey Classes", test_hotkey_classes),
        ("Configuration Validation", test_configuration_validation),
        ("Data Structures", test_data_structures)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n{'='*45}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        print("✓ Core system architecture is working")
        print("✓ Ready for next development phase")
    else:
        print("❌ Some tests failed")
        print("Need to fix issues before proceeding")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)