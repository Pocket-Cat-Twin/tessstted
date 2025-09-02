#!/usr/bin/env python3
"""
Test Configuration Schema Validation
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.config_schema import validate_config_file

def test_config_validation():
    """Test configuration validation on existing config.yaml"""
    config_path = "config/config.yaml"
    
    print("Testing Configuration Schema Validation")
    print("=" * 50)
    
    result = validate_config_file(config_path)
    
    print(f"Configuration file: {config_path}")
    print(f"Validation result: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
    
    if result.errors:
        print("\n🚨 Errors:")
        for error in result.errors:
            print(f"  ❌ {error}")
    
    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")
    
    if result.is_valid and result.normalized_config:
        print("\n✅ Configuration normalized successfully")
        print("📊 Schema validation passed!")
    
    return result.is_valid

if __name__ == "__main__":
    success = test_config_validation()
    sys.exit(0 if success else 1)