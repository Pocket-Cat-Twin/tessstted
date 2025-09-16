#!/usr/bin/env python3
"""
Test script to verify YANDEX_OCR.py integration maintains backward compatibility.
Tests configuration loading, OCR client initialization, and dual API functionality.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from config.settings import SettingsManager
    from core.ocr_client import YandexOCRClient, OCRError
    print("✅ Import test passed - all modules imported successfully")
except ImportError as e:
    print(f"❌ Import test failed: {e}")
    sys.exit(1)

def test_configuration_loading():
    """Test that configuration loads with new dual API settings."""
    print("\n🔧 Testing configuration loading...")
    
    try:
        settings = SettingsManager()
        config = settings.yandex_ocr
        
        print(f"  API Key: {config.api_key[:8]}...")
        print(f"  API URL: {config.api_url}")
        print(f"  Primary Auth: {config.primary_auth_method}")
        print(f"  Primary Format: {config.primary_api_format}")
        print(f"  Fallback Enabled: {config.enable_fallback}")
        print(f"  Fallback Auth: {config.fallback_auth_method}")
        print(f"  Fallback Format: {config.fallback_api_format}")
        print(f"  MIME Types: {list(config.mime_types.keys())}")
        
        # Verify working API key is loaded
        if config.api_key == "your_api_key_here":
            print("❌ Configuration test failed: API key still placeholder")
            return False
            
        # Verify new fields are present
        required_fields = ['primary_auth_method', 'fallback_auth_method', 
                          'primary_api_format', 'fallback_api_format', 
                          'enable_fallback', 'mime_types']
        
        for field in required_fields:
            if not hasattr(config, field):
                print(f"❌ Configuration test failed: missing field {field}")
                return False
        
        print("✅ Configuration loading test passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_ocr_client_initialization():
    """Test OCR client can be initialized with new configuration."""
    print("\n🏭 Testing OCR client initialization...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        print(f"  Client initialized successfully")
        print(f"  Primary API: {client.config.primary_api_format}")
        print(f"  Primary Auth: {client.config.primary_auth_method}")
        
        # Test statistics initialization
        stats = client.get_ocr_statistics()
        dual_api_fields = ['ocr_api_requests', 'vision_api_requests', 
                          'fallback_usage', 'api_key_auth_requests']
        
        for field in dual_api_fields:
            if field not in stats:
                print(f"❌ OCR client test failed: missing stats field {field}")
                return False
        
        print(f"  Statistics fields: {len(stats)} total")
        print(f"  Config summary: {stats['config_summary']}")
        
        print("✅ OCR client initialization test passed")
        return True
        
    except Exception as e:
        print(f"❌ OCR client initialization test failed: {e}")
        return False

def test_dual_api_methods():
    """Test that dual API methods are available and working."""
    print("\n🔄 Testing dual API methods...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        # Test method availability
        required_methods = [
            '_prepare_ocr_request', '_prepare_vision_request',
            '_prepare_request_payload', '_get_mime_type',
            '_send_dual_api_request', '_track_api_attempt',
            '_is_ocr_api_response', '_extract_text_from_ocr_response',
            '_extract_text_from_vision_response'
        ]
        
        for method_name in required_methods:
            if not hasattr(client, method_name):
                print(f"❌ Dual API test failed: missing method {method_name}")
                return False
        
        # Test MIME type detection
        test_path = Path("test.jpg")
        mime_type = client._get_mime_type(test_path)
        if mime_type != "JPEG":
            print(f"❌ MIME type test failed: expected JPEG, got {mime_type}")
            return False
        
        # Test auth header generation
        api_key_header = client._get_auth_header("api_key")
        bearer_header = client._get_auth_header("bearer")
        
        if not api_key_header.startswith("Api-Key"):
            print(f"❌ Auth header test failed: api_key format wrong")
            return False
            
        if not bearer_header.startswith("Bearer"):
            print(f"❌ Auth header test failed: bearer format wrong")
            return False
        
        print("✅ Dual API methods test passed")
        return True
        
    except Exception as e:
        print(f"❌ Dual API methods test failed: {e}")
        return False

def test_response_format_detection():
    """Test response format detection for OCR vs Vision API."""
    print("\n🔍 Testing response format detection...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        # Test OCR API response format
        ocr_response = {
            "result": {
                "textAnnotation": {
                    "fullText": "Test text from OCR API"
                }
            }
        }
        
        if not client._is_ocr_api_response(ocr_response):
            print("❌ Response detection test failed: OCR format not detected")
            return False
        
        # Test Vision API response format
        vision_response = {
            "result": {
                "textAnnotation": {
                    "blocks": [
                        {"lines": [{"words": [{"text": "Test"}]}]}
                    ]
                }
            }
        }
        
        if client._is_ocr_api_response(vision_response):
            print("❌ Response detection test failed: Vision format incorrectly detected as OCR")
            return False
        
        # Test text extraction from OCR format
        ocr_text = client._extract_text_from_ocr_response(ocr_response)
        if ocr_text != "Test text from OCR API":
            print(f"❌ OCR text extraction test failed: got '{ocr_text}'")
            return False
        
        # Test text extraction from Vision format  
        vision_text = client._extract_text_from_vision_response(vision_response)
        if vision_text != "Test":
            print(f"❌ Vision text extraction test failed: got '{vision_text}'")
            return False
        
        print("✅ Response format detection test passed")
        return True
        
    except Exception as e:
        print(f"❌ Response format detection test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 YANDEX_OCR.py Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_configuration_loading,
        test_ocr_client_initialization,
        test_dual_api_methods,
        test_response_format_detection
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Integration is backward compatible.")
        return True
    else:
        print(f"\n⚠️  {failed} tests failed. Integration needs fixes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)