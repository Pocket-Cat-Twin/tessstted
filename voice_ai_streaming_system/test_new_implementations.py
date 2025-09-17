#!/usr/bin/env python3
"""Test script for new STT and AI implementations."""

import sys
import os
import logging
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_imports():
    """Test that all new modules can be imported."""
    try:
        logger.info("Testing imports...")
        
        # Test STT imports
        from stt import (
            BaseSTTService, STTResult, STTProvider, 
            MockSTTService, YandexSTTService, WhisperXSTTService,
            create_stt_service
        )
        logger.info("✓ STT imports successful")
        
        # Test AI imports
        from ai import (
            BaseAIService, AIResponse, AIProvider,
            MockAIService, OpenRouterAIService,
            create_ai_service
        )
        logger.info("✓ AI imports successful")
        
        # Test provider enums
        logger.info(f"STT Providers: {[p.value for p in STTProvider]}")
        logger.info(f"AI Providers: {[p.value for p in AIProvider]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Import test failed: {e}")
        return False


def test_mock_services():
    """Test mock services to ensure basic functionality."""
    try:
        logger.info("Testing mock services...")
        
        # Import required modules
        from stt import MockSTTService, STTProvider
        from ai import MockAIService, AIProvider
        from config.settings import STTSettings, AISettings
        
        # Create mock settings
        stt_settings = STTSettings()
        ai_settings = AISettings()
        
        # Test mock STT service
        mock_stt = MockSTTService(stt_settings)
        logger.info(f"Mock STT provider: {mock_stt.provider}")
        
        if mock_stt.initialize():
            logger.info("✓ Mock STT initialized")
            
            # Test audio processing
            test_audio = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
            result = mock_stt.process_audio(test_audio, 16000)
            
            if result:
                logger.info(f"✓ Mock STT result: '{result.text}' (confidence: {result.confidence})")
            else:
                logger.warning("Mock STT returned no result")
                
            mock_stt.shutdown()
        else:
            logger.error("Failed to initialize mock STT")
            return False
        
        # Test mock AI service
        mock_ai = MockAIService(ai_settings)
        logger.info(f"Mock AI provider: {mock_ai.provider}")
        
        if mock_ai.initialize():
            logger.info("✓ Mock AI initialized")
            
            # Test response generation
            response = mock_ai.generate_response("Hello, test prompt")
            
            if response:
                logger.info(f"✓ Mock AI response: '{response.text}' (tokens: {response.tokens_used})")
            else:
                logger.warning("Mock AI returned no response")
                
            mock_ai.shutdown()
        else:
            logger.error("Failed to initialize mock AI")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Mock services test failed: {e}")
        return False


def test_factory_functions():
    """Test factory functions for creating services."""
    try:
        logger.info("Testing factory functions...")
        
        from stt import create_stt_service, STTProvider
        from ai import create_ai_service, AIProvider
        from config.settings import STTSettings, AISettings
        
        # Create settings
        stt_settings = STTSettings()
        ai_settings = AISettings()
        
        # Test STT factory
        for provider in STTProvider:
            try:
                service = create_stt_service(provider, stt_settings)
                logger.info(f"✓ Created STT service: {provider.value} -> {type(service).__name__}")
            except Exception as e:
                logger.error(f"Failed to create STT service {provider.value}: {e}")
                return False
        
        # Test AI factory
        for provider in AIProvider:
            try:
                service = create_ai_service(provider, ai_settings)
                logger.info(f"✓ Created AI service: {provider.value} -> {type(service).__name__}")
            except Exception as e:
                logger.error(f"Failed to create AI service {provider.value}: {e}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Factory functions test failed: {e}")
        return False


def test_service_initialization():
    """Test service initialization without API keys."""
    try:
        logger.info("Testing service initialization...")
        
        from stt import YandexSTTService, WhisperXSTTService
        from ai import OpenRouterAIService
        from config.settings import STTSettings, AISettings
        
        # Create settings (without API keys)
        stt_settings = STTSettings()
        ai_settings = AISettings()
        
        # Test Yandex STT (should fail gracefully without credentials)
        yandex_stt = YandexSTTService(stt_settings)
        logger.info(f"✓ Created Yandex STT service: {yandex_stt.provider}")
        
        # Test WhisperX STT (should handle missing dependencies gracefully)
        whisperx_stt = WhisperXSTTService(stt_settings)
        logger.info(f"✓ Created WhisperX STT service: {whisperx_stt.provider}")
        
        # Test OpenRouter AI (should fail gracefully without API key)
        openrouter_ai = OpenRouterAIService(ai_settings)
        logger.info(f"✓ Created OpenRouter AI service: {openrouter_ai.provider}")
        
        # Test statistics
        for service in [yandex_stt, whisperx_stt, openrouter_ai]:
            stats = service.get_statistics()
            logger.info(f"✓ {service.provider.value} statistics: {len(stats)} metrics")
        
        return True
        
    except Exception as e:
        logger.error(f"Service initialization test failed: {e}")
        return False


def test_configuration_compatibility():
    """Test that configuration changes are compatible."""
    try:
        logger.info("Testing configuration compatibility...")
        
        # Test reading updated configuration
        from config.settings import load_config_from_file
        
        config_path = Path(__file__).parent / "config" / "default_config.json"
        if config_path.exists():
            config = load_config_from_file(str(config_path))
            logger.info("✓ Configuration file loaded successfully")
            
            # Check new sections
            required_sections = ['apis', 'stt', 'ai']
            for section in required_sections:
                if section in config:
                    logger.info(f"✓ Configuration section '{section}' present")
                else:
                    logger.error(f"Missing configuration section: {section}")
                    return False
            
            # Check new API configurations
            apis = config.get('apis', {})
            required_apis = ['yandex_speechkit', 'whisperx', 'openrouter']
            for api in required_apis:
                if api in apis:
                    logger.info(f"✓ API configuration '{api}' present")
                else:
                    logger.error(f"Missing API configuration: {api}")
                    return False
            
            return True
        else:
            logger.error(f"Configuration file not found: {config_path}")
            return False
        
    except Exception as e:
        logger.error(f"Configuration compatibility test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("Starting comprehensive test of new implementations...")
    
    tests = [
        ("Import Test", test_imports),
        ("Mock Services Test", test_mock_services),
        ("Factory Functions Test", test_factory_functions),
        ("Service Initialization Test", test_service_initialization),
        ("Configuration Compatibility Test", test_configuration_compatibility)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            failed += 1
    
    logger.info(f"\n{'='*50}")
    logger.info(f"TEST SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total:  {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error(f"💥 {failed} TEST(S) FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())