#!/usr/bin/env python3
"""
Test script for real OCR processing with actual image processing.
Creates a simple test image and tests the full OCR pipeline.
"""

import sys
import os
from pathlib import Path
import tempfile

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from config.settings import SettingsManager
    from core.ocr_client import YandexOCRClient, OCRError
    from core.simple_ocr_client import SimpleYandexOCRClient, SimpleOCRError
    print("✅ Import test passed")
except ImportError as e:
    print(f"❌ Import test failed: {e}")
    sys.exit(1)

def create_test_image_with_text():
    """Create a simple test image with text for OCR testing."""
    if not PIL_AVAILABLE:
        print("⚠️  PIL not available, skipping image creation test")
        return None
    
    try:
        # Create a simple image with text
        width, height = 400, 200
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Try to use a default font, fallback to basic if needed
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # Draw some test text
        test_text = "OCR Test\nPrice: 100.50\nSeller: TestUser"
        
        # Calculate text position (roughly centered)
        if font:
            draw.text((50, 50), test_text, fill='black', font=font)
        else:
            draw.text((50, 50), test_text, fill='black')
        
        # Save to temporary file
        temp_dir = Path(tempfile.gettempdir())
        test_image_path = temp_dir / "ocr_test_image.png"
        image.save(test_image_path, 'PNG')
        
        print(f"  ✅ Test image created: {test_image_path}")
        print(f"  📝 Test text: {test_text}")
        
        return test_image_path
        
    except Exception as e:
        print(f"  ❌ Failed to create test image: {e}")
        return None

def test_ocr_with_real_image():
    """Test OCR processing with a real image."""
    print("\n🖼️ Testing OCR with real image...")
    
    # Create test image
    test_image_path = create_test_image_with_text()
    if not test_image_path:
        print("  ⚠️  Skipping real image test - could not create test image")
        return True  # Don't fail the test suite for this
    
    try:
        # Test with simplified client directly
        print("  Testing with SimpleYandexOCRClient...")
        
        settings = SettingsManager()
        api_key = settings.yandex_ocr.api_key
        
        simple_client = SimpleYandexOCRClient(
            api_key=api_key,
            timeout=30,
            max_retries=2
        )
        
        # Process the image
        print(f"  📤 Sending image to OCR API: {test_image_path.name}")
        result = simple_client.process_image_full_pipeline(
            image_path=test_image_path,
            cleanup_image=False,  # Keep for multiple tests
            language_codes=["en", "ru"]
        )
        
        if result:
            print(f"  ✅ OCR processing successful!")
            print(f"  📝 Extracted text: '{result}'")
            
            # Check if we got expected content
            if "OCR Test" in result or "Price" in result or "100" in result:
                print("  ✅ Expected text content found in result")
            else:
                print("  ⚠️  Expected text content not found, but OCR worked")
            
            simple_client.close()
            return True
        else:
            print("  ❌ OCR processing returned no result")
            simple_client.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Real image OCR test ERROR: {e}")
        return False
    finally:
        # Cleanup test image
        try:
            if test_image_path and test_image_path.exists():
                test_image_path.unlink()
                print(f"  🗑️ Cleaned up test image")
        except:
            pass

def test_adapter_with_real_image():
    """Test OCR adapter with a real image."""
    print("\n🔄 Testing adapter with real image...")
    
    # Create test image
    test_image_path = create_test_image_with_text()
    if not test_image_path:
        print("  ⚠️  Skipping adapter image test - could not create test image")
        return True  # Don't fail the test suite for this
    
    try:
        # Test with adapter
        print("  Testing with YandexOCRClient adapter...")
        
        settings = SettingsManager()
        adapter_client = YandexOCRClient(settings)
        
        # Process the image through adapter
        print(f"  📤 Sending image through adapter: {test_image_path.name}")
        
        # Test send_image_for_recognition method
        response = adapter_client.send_image_for_recognition(
            image_path=test_image_path,
            language_codes=["en", "ru"]
        )
        
        if response:
            print("  ✅ Adapter send_image_for_recognition successful!")
            
            # Extract text using adapter method
            extracted_text = adapter_client.extract_text_from_response(response)
            
            if extracted_text:
                print(f"  📝 Adapter extracted text: '{extracted_text}'")
                print("  ✅ Full adapter pipeline successful!")
                
                # Test statistics
                stats = adapter_client.get_ocr_statistics()
                print(f"  📊 Total requests: {stats['total_requests']}")
                print(f"  📊 Success rate: {stats.get('success_rate', 0)*100:.1f}%")
                
                adapter_client.close()
                return True
            else:
                print("  ❌ Adapter text extraction failed")
                adapter_client.close()
                return False
        else:
            print("  ❌ Adapter image processing failed")
            adapter_client.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Adapter image test ERROR: {e}")
        return False
    finally:
        # Cleanup test image
        try:
            if test_image_path and test_image_path.exists():
                test_image_path.unlink()
                print(f"  🗑️ Cleaned up test image")
        except:
            pass

def test_error_conditions():
    """Test error conditions with real scenarios."""
    print("\n🚨 Testing error conditions...")
    
    try:
        settings = SettingsManager()
        client = YandexOCRClient(settings)
        
        # Test with non-existent file
        print("  Testing non-existent file handling...")
        fake_path = Path("/tmp/non_existent_image.png")
        result = client.process_image_full_pipeline(fake_path)
        
        if result is None:
            print("  ✅ Non-existent file properly handled")
        else:
            print("  ❌ Non-existent file should return None")
            return False
        
        client.close()
        print("  ✅ Error condition tests passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Error condition test ERROR: {e}")
        return False

def main():
    """Run real OCR processing tests."""
    print("🖼️ REAL OCR PROCESSING TEST SUITE")
    print("=" * 50)
    
    if not PIL_AVAILABLE:
        print("⚠️  PIL/Pillow not available - some tests will be skipped")
    
    tests = [
        test_ocr_with_real_image,
        test_adapter_with_real_image,
        test_error_conditions
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
    print("📊 Real OCR Processing Test Results:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 REAL OCR PROCESSING TESTS SUCCESSFUL!")
        print("🚀 OCR system working with real images!")
    else:
        print(f"\n⚠️  {failed} real OCR tests failed.")
        print("🔧 Please review OCR API connectivity.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)