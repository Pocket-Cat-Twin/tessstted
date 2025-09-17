"""Test AI services functionality."""

import sys
import time
import asyncio
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_ai_imports():
    """Test AI service imports."""
    print("Testing AI imports...")
    
    try:
        from ai import BaseAIService, AIResponse, AIProvider, MockAIService
        print("✓ Base AI classes imported")
        
        from ai import OpenAIClient, AnthropicClient
        print("✓ All AI service implementations imported")
        
        # Test enums
        providers = list(AIProvider)
        print(f"✓ AI providers available: {[p.value for p in providers]}")
        
        return True
        
    except Exception as e:
        print(f"✗ AI import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_response_format():
    """Test AI response data structure."""
    print("\nTesting AI response format...")
    
    try:
        from ai import AIResponse
        
        # Create test response
        response = AIResponse(
            text="Test AI response",
            is_complete=True,
            tokens_used=10,
            model="test-model",
            processing_time=0.5,
            finish_reason="completed",
            usage_stats={
                "prompt_tokens": 5,
                "completion_tokens": 5,
                "total_tokens": 10
            }
        )
        
        print(f"✓ AI Response created:")
        print(f"  - Text: '{response.text}'")
        print(f"  - Complete: {response.is_complete}")
        print(f"  - Tokens used: {response.tokens_used}")
        print(f"  - Model: {response.model}")
        print(f"  - Processing time: {response.processing_time}s")
        print(f"  - Finish reason: {response.finish_reason}")
        print(f"  - Timestamp: {response.timestamp}")
        
        return True
        
    except Exception as e:
        print(f"✗ AI response test error: {e}")
        return False

def test_mock_ai_service():
    """Test mock AI service."""
    print("\nTesting Mock AI service...")
    
    try:
        from ai import MockAIService, AIProvider
        from config.settings import AISettings
        
        # Create mock service
        settings = AISettings()
        mock_ai = MockAIService(settings)
        
        print(f"✓ Mock AI service created - Provider: {mock_ai.get_provider().value}")
        
        # Test initialization
        if mock_ai.initialize():
            print("✓ Mock AI service initialized")
        else:
            print("✗ Mock AI service initialization failed")
            return False
        
        # Test response generation
        test_prompt = "What is artificial intelligence?"
        
        response = mock_ai.generate_response(test_prompt)
        if response:
            print(f"✓ Mock AI response: '{response.text[:100]}...'")
            print(f"  - Complete: {response.is_complete}")
            print(f"  - Tokens: {response.tokens_used}")
            print(f"  - Model: {response.model}")
            print(f"  - Processing time: {response.processing_time:.3f}s")
        else:
            print("✗ Mock AI response generation failed")
            return False
        
        # Test conversation history
        print(f"✓ Conversation history: {len(mock_ai._conversation_history)} messages")
        
        # Test with context
        context_response = mock_ai.generate_response("Follow up question", context="Previous discussion")
        if context_response:
            print(f"✓ Mock AI with context: '{context_response.text[:50]}...'")
        
        # Test statistics
        stats = mock_ai.get_statistics()
        print(f"✓ Mock AI statistics:")
        print(f"  - Requests: {stats['requests_count']}")
        print(f"  - Error rate: {stats['error_rate']:.2f}")
        print(f"  - Avg processing time: {stats['average_processing_time']:.3f}s")
        print(f"  - Total tokens: {stats['total_tokens_used']}")
        
        # Test shutdown
        mock_ai.shutdown()
        print("✓ Mock AI service shutdown")
        
        return True
        
    except Exception as e:
        print(f"✗ Mock AI test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openai_client():
    """Test OpenAI client (without actual API call)."""
    print("\nTesting OpenAI client...")
    
    try:
        from ai import OpenAIClient
        from config.settings import AISettings
        
        # Create client
        settings = AISettings()
        openai_client = OpenAIClient(settings)
        
        print(f"✓ OpenAI client created - Provider: {openai_client.get_provider().value}")
        
        # Test service info
        info = openai_client.get_service_info()
        print(f"✓ OpenAI info: {info['name']}")
        print(f"  - Available: {info['available']}")
        print(f"  - Features: {list(info['features'].keys())}")
        print(f"  - Models: {len(info['models'])} available")
        
        # Test configuration methods
        if openai_client.set_temperature(0.7):
            print("✓ Temperature setting works")
        
        if openai_client.set_max_tokens(150):
            print("✓ Max tokens setting works")
        
        # Test model listing
        models = openai_client.get_available_models()
        print(f"✓ OpenAI models: {models[:3]}..." if len(models) > 3 else f"✓ OpenAI models: {models}")
        
        return True
        
    except Exception as e:
        print(f"✗ OpenAI client test error: {e}")
        return False

def test_anthropic_client():
    """Test Anthropic client (without actual API call)."""
    print("\nTesting Anthropic client...")
    
    try:
        from ai import AnthropicClient
        from config.settings import AISettings
        
        # Create client
        settings = AISettings()
        anthropic_client = AnthropicClient(settings)
        
        print(f"✓ Anthropic client created - Provider: {anthropic_client.get_provider().value}")
        
        # Test service info
        info = anthropic_client.get_service_info()
        print(f"✓ Anthropic info: {info['name']}")
        print(f"  - Available: {info['available']}")
        print(f"  - Features: {list(info['features'].keys())}")
        print(f"  - Models: {len(info['models'])} available")
        
        # Test configuration methods
        if anthropic_client.set_temperature(0.7):
            print("✓ Temperature setting works")
        
        if anthropic_client.set_max_tokens(150):
            print("✓ Max tokens setting works")
        
        # Test model listing
        models = anthropic_client.get_available_models()
        print(f"✓ Anthropic models: {models[:3]}..." if len(models) > 3 else f"✓ Anthropic models: {models}")
        
        return True
        
    except Exception as e:
        print(f"✗ Anthropic client test error: {e}")
        return False

def test_ai_configuration():
    """Test AI configuration system."""
    print("\nTesting AI configuration...")
    
    try:
        from config.settings import AISettings, ConfigManager
        
        # Test default settings
        config_manager = ConfigManager()
        settings = config_manager.get_settings()
        ai_settings = settings.ai
        
        print(f"✓ AI Settings loaded:")
        print(f"  - Primary provider: {ai_settings.primary_provider}")
        print(f"  - Fallback provider: {ai_settings.fallback_provider}")
        print(f"  - Model: {ai_settings.model}")
        print(f"  - Max tokens: {ai_settings.max_tokens}")
        print(f"  - Temperature: {ai_settings.temperature}")
        print(f"  - Stream response: {ai_settings.stream_response}")
        print(f"  - Response timeout: {ai_settings.response_timeout}")
        
        return True
        
    except Exception as e:
        print(f"✗ AI configuration test error: {e}")
        return False

def test_streaming_simulation():
    """Test streaming response simulation."""
    print("\nTesting streaming simulation...")
    
    try:
        from ai import MockAIService
        from config.settings import AISettings
        
        # Create mock service
        settings = AISettings()
        mock_ai = MockAIService(settings)
        mock_ai.initialize()
        
        async def test_streaming():
            responses = []
            async for response in mock_ai.stream_response("Test streaming question"):
                responses.append(response)
                if response.is_complete:
                    break
            return responses
        
        # Run async test
        responses = asyncio.run(test_streaming())
        
        print(f"✓ Streaming test completed:")
        print(f"  - Total chunks: {len(responses)}")
        print(f"  - Final response complete: {responses[-1].is_complete if responses else False}")
        
        complete_responses = [r for r in responses if r.is_complete]
        partial_responses = [r for r in responses if not r.is_complete]
        
        print(f"  - Partial chunks: {len(partial_responses)}")
        print(f"  - Complete chunks: {len(complete_responses)}")
        
        mock_ai.shutdown()
        return True
        
    except Exception as e:
        print(f"✗ Streaming test error: {e}")
        return False

def main():
    """Run all AI tests."""
    print("Voice-to-AI System - AI Services Test")
    print("=" * 45)
    
    tests = [
        ("AI Imports", test_ai_imports),
        ("AI Response Format", test_ai_response_format),
        ("Mock AI Service", test_mock_ai_service),
        ("OpenAI Client", test_openai_client),
        ("Anthropic Client", test_anthropic_client),
        ("AI Configuration", test_ai_configuration),
        ("Streaming Simulation", test_streaming_simulation)
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
    print(f"AI Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All AI tests passed!")
        print("✓ AI services are ready for integration")
        print("✓ Mock AI service works for testing")
        print("✓ Both OpenAI and Anthropic clients implemented")
        print("✓ Streaming responses supported")
    else:
        print("❌ Some AI tests failed")
        print("Check the output above for details")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)