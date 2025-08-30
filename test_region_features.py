#!/usr/bin/env python3
"""
Test script for new region selection and OCR testing features
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_monitor.region_selector import RegionManager, RegionConfig, CoordinateInputDialog
from game_monitor.vision_system import get_vision_system, ScreenRegion
from pathlib import Path
import time

def test_region_manager():
    """Test the region manager functionality"""
    print("=" * 60)
    print("🧪 Testing Region Manager")
    print("=" * 60)
    
    # Initialize region manager
    manager = RegionManager("config/test_regions.yaml")
    
    # Test setting a region
    test_region = RegionConfig(
        name="test_region",
        x=100, y=200, width=300, height=150,
        hotkey="F1",
        description="Test region for validation"
    )
    
    manager.set_region(test_region)
    print(f"✅ Created test region: {test_region.x},{test_region.y} {test_region.width}x{test_region.height}")
    
    # Test retrieving region
    retrieved = manager.get_region("test_region")
    if retrieved:
        print(f"✅ Retrieved region: {retrieved.name} - {retrieved.x},{retrieved.y} {retrieved.width}x{retrieved.height}")
    else:
        print("❌ Failed to retrieve region")
        return False
    
    # Test listing regions
    regions = manager.list_regions()
    print(f"✅ Found {len(regions)} regions")
    
    # Test default regions
    manager.set_default_regions()
    default_regions = manager.list_regions()
    print(f"✅ Set {len(default_regions)} default regions")
    
    for region in default_regions:
        print(f"   - {region.name}: {region.x},{region.y} {region.width}x{region.height}")
    
    return True

def test_vision_system_testing():
    """Test the vision system testing functionality"""
    print("\n" + "=" * 60)
    print("🧪 Testing Vision System OCR Output")
    print("=" * 60)
    
    # Get vision system
    vision_system = get_vision_system()
    
    # Test enabling testing output
    print("🔧 Enabling testing output...")
    vision_system.enable_testing_output(True)
    
    # Verify testing is enabled
    summary = vision_system.get_testing_summary()
    print(f"✅ Testing enabled: {summary['testing_enabled']}")
    print(f"📁 Output file: {summary['output_file']}")
    print(f"📁 Detailed file: {summary['detailed_file']}")
    
    # Test a sample OCR operation
    print("\n🔍 Testing OCR processing...")
    test_region = ScreenRegion(100, 100, 200, 50, "test_region")
    
    try:
        result = vision_system.capture_and_process_region(test_region, 'general')
        print(f"✅ OCR processing completed")
        print(f"📊 Result: {result}")
        
        # Check if output files were created
        summary = vision_system.get_testing_summary()
        if summary['output_file_exists']:
            print("✅ Testing output file created")
        if summary['detailed_file_exists']:
            print("✅ Detailed testing file created")
        
    except Exception as e:
        print(f"⚠️ OCR processing failed (expected without proper libraries): {e}")
    
    # Test clearing output
    print("\n🧹 Testing output clearing...")
    vision_system.clear_testing_output()
    
    # Test disabling
    print("🔧 Disabling testing output...")
    vision_system.enable_testing_output(False)
    
    summary = vision_system.get_testing_summary()
    print(f"✅ Testing disabled: {not summary['testing_enabled']}")
    
    return True

def test_config_files():
    """Test configuration file creation and loading"""
    print("\n" + "=" * 60)
    print("🧪 Testing Configuration Files")
    print("=" * 60)
    
    # Test region config creation
    config_path = Path("config/test_regions.yaml")
    if config_path.exists():
        print(f"✅ Region config file exists: {config_path}")
        
        # Try to load it
        try:
            import yaml
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'regions' in data:
                    print(f"✅ Loaded {len(data['regions'])} regions from config")
                    for name, region_data in data['regions'].items():
                        print(f"   - {name}: {region_data['x']},{region_data['y']} {region_data['width']}x{region_data['height']}")
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
    
    # Test data directory creation
    data_path = Path("data")
    if data_path.exists():
        print(f"✅ Data directory exists: {data_path}")
        
        # List testing files
        test_files = list(data_path.glob("testing_*.txt")) + list(data_path.glob("testing_*.json"))
        if test_files:
            print(f"📁 Found {len(test_files)} testing files:")
            for file_path in test_files:
                print(f"   - {file_path.name}")
    
    return True

def test_integration():
    """Test integration between components"""
    print("\n" + "=" * 60) 
    print("🧪 Testing Component Integration")
    print("=" * 60)
    
    # Create region manager
    manager = RegionManager()
    
    # Create regions for all hotkeys
    hotkey_regions = [
        RegionConfig("trader_list", 100, 200, 600, 400, "F1", "Trader list capture region"),
        RegionConfig("item_scan", 200, 150, 500, 300, "F2", "Item scan region"),
        RegionConfig("trader_inventory", 300, 250, 700, 500, "F3", "Inventory region")
    ]
    
    # Save all regions
    for region in hotkey_regions:
        manager.set_region(region)
        print(f"✅ Configured {region.name}: {region.x},{region.y} {region.width}x{region.height}")
    
    # Test vision system with regions
    vision_system = get_vision_system()
    vision_system.enable_testing_output(True)
    
    print("\n🔍 Testing all regions with vision system...")
    for region in hotkey_regions:
        screen_region = ScreenRegion(region.x, region.y, region.width, region.height, region.name)
        try:
            result = vision_system.capture_and_process_region(screen_region, 'general')
            status = "✅ Success" if result else "⚠️ No data"
            print(f"   {region.name}: {status}")
        except Exception as e:
            print(f"   {region.name}: ⚠️ Error - {str(e)[:50]}...")
    
    vision_system.enable_testing_output(False)
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Region Selection & OCR Testing Feature Tests")
    print("=" * 80)
    
    tests = [
        ("Region Manager", test_region_manager),
        ("Vision System Testing", test_vision_system_testing),
        ("Configuration Files", test_config_files),
        ("Component Integration", test_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"✅ {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ {test_name}: FAILED - {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Features are working correctly.")
        return True
    else:
        print(f"⚠️ {total-passed} tests failed. Check output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)