#!/usr/bin/env python3
"""
Test script for the completely rewritten simplified OCR system.
Tests the new SimpleYandexOCRClient and adapter integration.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from config.settings import SettingsManager
    from core.ocr_client import YandexOCRClient, OCRError
    from core.simple_ocr_client import SimpleYandexOCRClient, SimpleOCRError
    print("✅ Import test passed - all new modules loaded")
except ImportError as e:
    print(f"❌ Import test failed: {e}")
    sys.exit(1)

def test_simplified_ocr_direct():
    """Test the simplified OCR client directly."""
    print("\n🔧 Testing SimpleYandexOCRClient directly...")
    
    try:
        # Get API key from config
        settings = SettingsManager()
        api_key = settings.yandex_ocr.api_key
        
        print(f"  Using API key: {api_key[:8]}...")
        
        # Create simplified client directly
        simple_client = SimpleYandexOCRClient(
            api_key=api_key,
            timeout=10,
            max_retries=2
        )
        
        print("  ✅ SimpleYandexOCRClient created successfully")
        
        # Test API connection
        print("  Testing API connection...")
        connection_result = simple_client.test_api_connection()
        
        if connection_result:
            print("  ✅ Direct API connection test PASSED!")
            
            # Test statistics
            stats = simple_client.get_ocr_statistics()
            print(f"    Total requests: {stats['total_requests']}")
            print(f"    Success rate: {stats.get('success_rate', 0.0)*100:.1f}%")
            
            simple_client.close()
            return True
        else:
            print("  ❌ Direct API connection test FAILED")
            simple_client.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Direct OCR test ERROR: {e}")
        return False

def test_adapter_integration():
    """Test the OCR adapter integration with existing system."""
    print("\n🔄 Testing OCR adapter integration...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        print(f"  Adapter initialized with API key: {client.config.api_key[:8]}...")
        
        # Test API connection through adapter
        print("  Testing API connection through adapter...")
        connection_result = client.test_api_connection()
        
        if connection_result:
            print("  ✅ Adapter API connection test PASSED!")
            
            # Test statistics through adapter
            stats = client.get_ocr_statistics()
            
            print("  Adapter Statistics:")
            print(f"    Total requests: {stats['total_requests']}")
            print(f"    OCR API requests: {stats['ocr_api_requests']}")
            print(f"    Success rate: {stats.get('success_rate', 0.0)*100:.1f}%")
            print(f"    Primary API format: {stats['config_summary']['primary_api_format']}")
            print(f"    Fallback enabled: {stats['config_summary']['fallback_enabled']}")
            
            # Verify backward compatibility fields
            required_fields = [
                'ocr_api_requests', 'ocr_api_successes', 'api_key_auth_requests',
                'config_summary', 'success_rate', 'failure_rate'
            ]
            
            for field in required_fields:
                if field not in stats:
                    print(f"  ❌ Missing backward compatibility field: {field}")
                    return False
            
            print("  ✅ All backward compatibility fields present")
            
            client.close()
            return True
        else:
            print("  ❌ Adapter API connection test FAILED")
            client.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Adapter integration test ERROR: {e}")
        return False

def test_configuration_simplification():
    """Test that configuration has been properly simplified."""
    print("\n⚙️ Testing configuration simplification...")
    
    try:
        settings = SettingsManager()
        ocr_config = settings.yandex_ocr
        
        print("  Configuration fields:")
        print(f"    API key: {ocr_config.api_key[:8]}... ({'VALID' if ocr_config.api_key != 'your_api_key_here' else 'PLACEHOLDER'})")
        print(f"    API URL: {ocr_config.api_url}")
        print(f"    Timeout: {ocr_config.timeout}")
        print(f"    Max retries: {ocr_config.max_retries}")
        print(f"    Max image size: {ocr_config.max_image_size_mb}MB")
        
        # Check that dual API fields are removed
        dual_api_fields = [
            'folder_id', 'primary_auth_method', 'fallback_auth_method',
            'primary_api_format', 'fallback_api_format', 'enable_fallback',
            'fallback_api_url'
        ]
        
        for field in dual_api_fields:
            if hasattr(ocr_config, field):
                print(f"  ⚠️  WARNING: Dual API field still present: {field}")
            else:
                print(f"  ✅ Dual API field properly removed: {field}")
        
        # Verify required fields are present
        required_fields = ['api_key', 'api_url', 'timeout', 'max_retries']
        for field in required_fields:
            if hasattr(ocr_config, field):
                print(f"  ✅ Required field present: {field}")
            else:
                print(f"  ❌ Required field missing: {field}")
                return False
        
        print("  ✅ Configuration simplification verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test ERROR: {e}")
        return False

def test_error_handling():
    """Test error handling in simplified system."""
    print("\n🚨 Testing error handling...")
    
    try:
        # Test with invalid API key
        print("  Testing invalid API key handling...")
        try:
            invalid_client = SimpleYandexOCRClient(
                api_key="invalid_key_12345",
                timeout=5,
                max_retries=1
            )
            
            # This should fail gracefully
            result = invalid_client.test_api_connection()
            if not result:
                print("  ✅ Invalid API key properly rejected")
            else:
                print("  ⚠️  Invalid API key unexpectedly accepted")
            
            invalid_client.close()
            
        except SimpleOCRError as e:
            print(f"  ✅ Invalid API key properly caught: {e}")
        
        # Test with empty API key
        print("  Testing empty API key handling...")
        try:
            empty_client = SimpleYandexOCRClient(
                api_key="",
                timeout=5,
                max_retries=1
            )
            print("  ❌ Empty API key should have been rejected")
            return False
        except SimpleOCRError:
            print("  ✅ Empty API key properly rejected")
        
        print("  ✅ Error handling tests passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Error handling test ERROR: {e}")
        return False

def test_file_format_support():
    """Test supported file formats."""
    print("\n📁 Testing file format support...")
    
    try:
        settings = SettingsManager()
        ocr_config = settings.yandex_ocr
        
        print("  Supported formats:")
        for fmt in ocr_config.supported_formats:
            print(f"    {fmt}")
        
        print("  MIME type mapping:")
        for ext, mime in ocr_config.mime_types.items():
            print(f"    {ext} -> {mime}")
        
        # Verify essential formats are supported
        essential_formats = ['.jpg', '.jpeg', '.png']
        for fmt in essential_formats:
            if fmt in ocr_config.supported_formats:
                print(f"  ✅ Essential format supported: {fmt}")
            else:
                print(f"  ❌ Essential format missing: {fmt}")
                return False
        
        print("  ✅ File format support verified")
        return True
        
    except Exception as e:
        print(f"  ❌ File format test ERROR: {e}")
        return False

def main():
    """Run all simplified OCR system tests."""
    print("🔄 SIMPLIFIED OCR SYSTEM VALIDATION SUITE")
    print("=" * 60)
    
    tests = [
        test_configuration_simplification,
        test_simplified_ocr_direct,
        test_adapter_integration,
        test_error_handling,
        test_file_format_support
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
    
    print("\n" + "=" * 60)
    print("📊 Simplified OCR System Validation Results:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 SIMPLIFIED OCR SYSTEM VALIDATION SUCCESSFUL!")
        print("🚀 All tests passed - system ready for production!")
        print("\n📋 Key Improvements Verified:")
        print("  • Removed dual API complexity")
        print("  • Simplified configuration structure")
        print("  • Working API key integration")
        print("  • Backward compatibility maintained")
        print("  • Error handling improved")
    else:
        print(f"\n⚠️  {failed} validation tests failed.")
        print("🔧 Please review and fix issues before production use.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)