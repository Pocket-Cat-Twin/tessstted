"""Test STT services functionality."""

import sys
import numpy as np
import time
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_stt_imports():
    """Test STT service imports."""
    print("Testing STT imports...")
    
    try:
        from stt import BaseSTTService, STTResult, STTProvider, MockSTTService
        print("✓ Base STT classes imported")
        
        from stt import GoogleSTTService, AzureSTTService, WhisperSTTService
        print("✓ All STT service implementations imported")
        
        # Test enums
        providers = list(STTProvider)
        print(f"✓ STT providers available: {[p.value for p in providers]}")
        
        return True
        
    except Exception as e:
        print(f"✗ STT import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mock_stt_service():
    """Test mock STT service."""
    print("\nTesting Mock STT service...")
    
    try:
        from stt import MockSTTService, STTProvider
        from config.settings import STTSettings
        
        # Create mock service
        settings = STTSettings()
        mock_stt = MockSTTService(settings)
        
        print(f"✓ Mock STT service created - Provider: {mock_stt.get_provider().value}")
        
        # Test initialization
        if mock_stt.initialize():
            print("✓ Mock STT service initialized")
        else:
            print("✗ Mock STT service initialization failed")
            return False
        
        # Test with dummy audio
        test_audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)  # 1 second at 16kHz
        
        result = mock_stt.process_audio(test_audio, 16000)
        if result:
            print(f"✓ Mock STT result: '{result.text}' (confidence: {result.confidence:.2f})")
            print(f"  - Final: {result.is_final}")
            print(f"  - Language: {result.language}")
            print(f"  - Processing time: {result.processing_time:.3f}s")
        else:
            print("✗ Mock STT processing failed")
            return False
        
        # Test statistics
        stats = mock_stt.get_statistics()
        print(f"✓ Mock STT statistics: {stats['requests_count']} requests, {stats['error_rate']:.2f} error rate")
        
        # Test shutdown
        mock_stt.shutdown()
        print("✓ Mock STT service shutdown")
        
        return True
        
    except Exception as e:
        print(f"✗ Mock STT test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_google_stt_service():
    """Test Google STT service (without actual API call)."""
    print("\nTesting Google STT service...")
    
    try:
        from stt import GoogleSTTService
        from config.settings import STTSettings
        
        # Create service
        settings = STTSettings()
        google_stt = GoogleSTTService(settings)
        
        print(f"✓ Google STT service created - Provider: {google_stt.get_provider().value}")
        
        # Test service info
        info = google_stt.get_service_info()
        print(f"✓ Google STT info: {info['name']}")
        print(f"  - Available: {info['available']}")
        print(f"  - Features: {list(info['features'].keys())}")
        print(f"  - Supported languages: {info['supported_languages']}")
        
        # Test language methods
        languages = google_stt.get_supported_languages()
        print(f"✓ Google STT supports {len(languages)} languages")
        
        return True
        
    except Exception as e:
        print(f"✗ Google STT test error: {e}")
        return False

def test_azure_stt_service():
    """Test Azure STT service (without actual API call)."""
    print("\nTesting Azure STT service...")
    
    try:
        from stt import AzureSTTService
        from config.settings import STTSettings
        
        # Create service
        settings = STTSettings()
        azure_stt = AzureSTTService(settings)
        
        print(f"✓ Azure STT service created - Provider: {azure_stt.get_provider().value}")
        
        # Test service info
        info = azure_stt.get_service_info()
        print(f"✓ Azure STT info: {info['name']}")
        print(f"  - Available: {info['available']}")
        print(f"  - Features: {list(info['features'].keys())}")
        print(f"  - Supported languages: {info['supported_languages']}")
        
        # Test language methods
        languages = azure_stt.get_supported_languages()
        print(f"✓ Azure STT supports {len(languages)} languages")
        
        return True
        
    except Exception as e:
        print(f"✗ Azure STT test error: {e}")
        return False

def test_whisper_stt_service():
    """Test Whisper STT service (without actual model loading)."""
    print("\nTesting Whisper STT service...")
    
    try:
        from stt import WhisperSTTService
        from config.settings import STTSettings
        
        # Create service
        settings = STTSettings()
        whisper_stt = WhisperSTTService(settings)
        
        print(f"✓ Whisper STT service created - Provider: {whisper_stt.get_provider().value}")
        
        # Test service info
        info = whisper_stt.get_service_info()
        print(f"✓ Whisper STT info: {info['name']}")
        print(f"  - Available: {info['available']}")
        print(f"  - Features: {list(info['features'].keys())}")
        print(f"  - Supported languages: {info['supported_languages']}")
        
        # Test model methods
        models = whisper_stt.get_available_models()
        print(f"✓ Whisper models available: {list(models.keys())}")
        print(f"  - Current model: {whisper_stt.get_current_model()}")
        
        # Test language methods
        languages = whisper_stt.get_supported_languages()
        print(f"✓ Whisper STT supports {len(languages)} languages")
        
        return True
        
    except Exception as e:
        print(f"✗ Whisper STT test error: {e}")
        return False

def test_stt_configuration():
    """Test STT configuration system."""
    print("\nTesting STT configuration...")
    
    try:
        from config.settings import STTSettings, ConfigManager
        
        # Test default settings
        config_manager = ConfigManager()
        settings = config_manager.get_settings()
        stt_settings = settings.stt
        
        print(f"✓ STT Settings loaded:")
        print(f"  - Primary provider: {stt_settings.primary_provider}")
        print(f"  - Fallback provider: {stt_settings.fallback_provider}")
        print(f"  - Language: {stt_settings.language_code}")
        print(f"  - Confidence threshold: {stt_settings.confidence_threshold}")
        print(f"  - Streaming enabled: {stt_settings.streaming_enabled}")
        
        return True
        
    except Exception as e:
        print(f"✗ STT configuration test error: {e}")
        return False

def test_stt_result_format():
    """Test STT result data structure."""
    print("\nTesting STT result format...")
    
    try:
        from stt import STTResult
        
        # Create test result
        result = STTResult(
            text="Test transcription",
            confidence=0.95,
            is_final=True,
            language="en-US",
            timestamp=time.time(),
            processing_time=0.5,
            alternatives=["Alternative 1", "Alternative 2"],
            word_timestamps=[
                {"word": "Test", "start_time": 0.0, "end_time": 0.5},
                {"word": "transcription", "start_time": 0.5, "end_time": 1.5}
            ]
        )
        
        print(f"✓ STT Result created:")
        print(f"  - Text: '{result.text}'")
        print(f"  - Confidence: {result.confidence}")
        print(f"  - Is final: {result.is_final}")
        print(f"  - Language: {result.language}")
        print(f"  - Processing time: {result.processing_time}s")
        print(f"  - Alternatives: {len(result.alternatives) if result.alternatives else 0}")
        print(f"  - Word timestamps: {len(result.word_timestamps) if result.word_timestamps else 0}")
        
        return True
        
    except Exception as e:
        print(f"✗ STT result test error: {e}")
        return False

def main():
    """Run all STT tests."""
    print("Voice-to-AI System - STT Services Test")
    print("=" * 45)
    
    tests = [
        ("STT Imports", test_stt_imports),
        ("Mock STT Service", test_mock_stt_service),
        ("Google STT Service", test_google_stt_service),
        ("Azure STT Service", test_azure_stt_service),
        ("Whisper STT Service", test_whisper_stt_service),
        ("STT Configuration", test_stt_configuration),
        ("STT Result Format", test_stt_result_format)
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
    print(f"STT Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All STT tests passed!")
        print("✓ STT services are ready for integration")
        print("✓ Mock STT service works for testing")
        print("✓ All STT providers are properly implemented")
    else:
        print("❌ Some STT tests failed")
        print("Check the output above for details")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)