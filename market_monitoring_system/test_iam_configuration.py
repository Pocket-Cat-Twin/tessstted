#!/usr/bin/env python3
"""
Test script to validate IAM configuration for Yandex OCR integration.
Verifies that the system properly loads and uses IAM token and folder_id.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import SettingsManager, ConfigurationError
from core.ocr_client import YandexOCRClient, OCRError


def test_configuration_loading():
    """Test that configuration loads properly with IAM token and folder_id."""
    print("=== Testing Configuration Loading ===")
    
    try:
        settings = SettingsManager()
        print("✓ Configuration loaded successfully")
        
        # Test OCR configuration
        ocr_config = settings.yandex_ocr
        if not ocr_config:
            print("✗ OCR configuration not found")
            return False
        
        print(f"✓ OCR configuration found")
        print(f"  - API Key length: {len(ocr_config.api_key)} characters")
        print(f"  - Folder ID: {ocr_config.folder_id}")
        print(f"  - Primary Auth Method: {ocr_config.primary_auth_method}")
        print(f"  - API URL: {ocr_config.api_url}")
        
        # Validate key parts
        if ocr_config.api_key == "your_api_key_here":
            print("✗ API key still uses placeholder value")
            return False
        print("✓ API key properly configured")
        
        if not ocr_config.folder_id:
            print("✗ Folder ID not configured")
            return False
        print("✓ Folder ID properly configured")
        
        if ocr_config.primary_auth_method != "bearer":
            print(f"✗ Expected bearer auth, got: {ocr_config.primary_auth_method}")
            return False
        print("✓ Bearer authentication properly configured")
        
        return True
        
    except ConfigurationError as e:
        print(f"✗ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_ocr_client_initialization():
    """Test that OCR client initializes properly with new configuration."""
    print("\n=== Testing OCR Client Initialization ===")
    
    try:
        settings = SettingsManager()
        
        # Initialize OCR client
        ocr_client = YandexOCRClient(settings)
        print("✓ OCR client initialized successfully")
        
        # Check authorization header
        auth_header = ocr_client.session.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            print(f"✗ Expected Bearer auth header, got: {auth_header[:20]}...")
            return False
        print("✓ Bearer authorization header properly set")
        
        # Check configuration access
        if not hasattr(ocr_client.config, 'folder_id'):
            print("✗ OCR client doesn't have folder_id attribute")
            return False
        
        if not ocr_client.config.folder_id:
            print("✗ OCR client folder_id is empty")
            return False
        
        print(f"✓ OCR client has folder_id: {ocr_client.config.folder_id}")
        
        return True
        
    except OCRError as e:
        print(f"✗ OCR client error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_api_connection():
    """Test actual API connection with IAM configuration."""
    print("\n=== Testing API Connection ===")
    
    try:
        settings = SettingsManager()
        ocr_client = YandexOCRClient(settings)
        
        print("Attempting to connect to Yandex OCR API...")
        connection_success = ocr_client.test_api_connection()
        
        if connection_success:
            print("✓ API connection successful")
        else:
            print("✗ API connection failed")
            
        return connection_success
        
    except Exception as e:
        print(f"✗ Connection test error: {e}")
        return False


def test_statistics_tracking():
    """Test that statistics tracking works with new configuration."""
    print("\n=== Testing Statistics Tracking ===")
    
    try:
        settings = SettingsManager()
        ocr_client = YandexOCRClient(settings)
        
        # Get initial statistics
        stats = ocr_client.get_ocr_statistics()
        print("✓ Statistics retrieved successfully")
        
        # Check for dual API configuration in stats
        config_summary = stats.get('config_summary', {})
        
        expected_config = {
            'primary_api_format': 'ocr',
            'primary_auth_method': 'bearer',
            'fallback_enabled': True
        }
        
        for key, expected_value in expected_config.items():
            actual_value = config_summary.get(key)
            if actual_value != expected_value:
                print(f"✗ Config mismatch for {key}: expected {expected_value}, got {actual_value}")
                return False
        
        print("✓ Configuration properly reflected in statistics")
        print(f"  - Primary API Format: {config_summary['primary_api_format']}")
        print(f"  - Primary Auth Method: {config_summary['primary_auth_method']}")
        print(f"  - Fallback Enabled: {config_summary['fallback_enabled']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Statistics test error: {e}")
        return False


def main():
    """Run all IAM configuration tests."""
    print("Yandex OCR IAM Configuration Test")
    print("=" * 50)
    
    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("OCR Client Initialization", test_ocr_client_initialization), 
        ("API Connection", test_api_connection),
        ("Statistics Tracking", test_statistics_tracking)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! IAM configuration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())