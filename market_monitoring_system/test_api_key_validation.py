#!/usr/bin/env python3
"""
Test script to validate the working API key from YANDEX_OCR.py integration.
Tests actual API connectivity and authentication.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from config.settings import SettingsManager
    from core.ocr_client import YandexOCRClient, OCRError
    print("✅ Import test passed")
except ImportError as e:
    print(f"❌ Import test failed: {e}")
    sys.exit(1)

def test_api_connection():
    """Test API connection with working key."""
    print("\n🌐 Testing API connection...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        print(f"  Using API key: {client.config.api_key[:8]}...")
        print(f"  Primary API: {client.config.primary_api_format}")
        print(f"  Primary Auth: {client.config.primary_auth_method}")
        print(f"  API URL: {client.config.api_url}")
        
        # Test connection
        print("  Attempting API connection test...")
        connection_result = client.test_api_connection()
        
        if connection_result:
            print("✅ API connection test PASSED - API key is working!")
            return True
        else:
            print("❌ API connection test FAILED - API key may not be working")
            return False
            
    except Exception as e:
        print(f"❌ API connection test ERROR: {e}")
        return False

def test_ocr_statistics():
    """Test OCR statistics tracking."""
    print("\n📊 Testing OCR statistics...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        stats = client.get_ocr_statistics()
        
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  OCR API requests: {stats['ocr_api_requests']}")
        print(f"  Vision API requests: {stats['vision_api_requests']}")
        print(f"  API key auth requests: {stats['api_key_auth_requests']}")
        print(f"  Bearer auth requests: {stats['bearer_auth_requests']}")
        print(f"  Fallback usage: {stats['fallback_usage']}")
        print(f"  Preferred API: {stats['preferred_api']}")
        
        # Verify all dual API stats are present
        required_stats = [
            'ocr_api_requests', 'ocr_api_successes', 'vision_api_requests', 
            'vision_api_successes', 'fallback_usage', 'api_key_auth_requests',
            'bearer_auth_requests', 'config_summary', 'preferred_api'
        ]
        
        for stat in required_stats:
            if stat not in stats:
                print(f"❌ Statistics test failed: missing {stat}")
                return False
        
        print("✅ OCR statistics test passed")
        return True
        
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        return False

def test_configuration_summary():
    """Test configuration summary in statistics."""
    print("\n⚙️ Testing configuration summary...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        stats = client.get_ocr_statistics()
        config_summary = stats['config_summary']
        
        print("  Configuration Summary:")
        for key, value in config_summary.items():
            print(f"    {key}: {value}")
        
        # Verify expected configuration
        expected_config = {
            'primary_api_format': 'ocr',
            'primary_auth_method': 'api_key',
            'fallback_enabled': True,
            'fallback_api_format': 'vision',
            'fallback_auth_method': 'bearer'
        }
        
        for key, expected_value in expected_config.items():
            if config_summary.get(key) != expected_value:
                print(f"❌ Config test failed: {key} = {config_summary.get(key)}, expected {expected_value}")
                return False
        
        print("✅ Configuration summary test passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration summary test failed: {e}")
        return False

def main():
    """Run API key validation tests."""
    print("🔑 YANDEX_OCR.py API Key Validation Suite")
    print("=" * 50)
    
    tests = [
        test_api_connection,
        test_ocr_statistics,
        test_configuration_summary
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
    print("📊 Validation Results Summary:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 API KEY VALIDATION SUCCESSFUL!")
        print("🚀 YANDEX_OCR.py integration is fully functional!")
    else:
        print(f"\n⚠️  {failed} validation tests failed.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)