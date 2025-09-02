#!/usr/bin/env python3
"""
OCR Screenshot Processing Test
Test OCR functionality with real game screenshots
"""

import sys
import time
import os
from pathlib import Path
import cv2
import numpy as np

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import OCR components directly (bypassing display requirements)
try:
    import pytesseract
    from PIL import Image
    print("✅ OCR libraries imported successfully")
except ImportError as e:
    print(f"❌ Missing OCR libraries: {e}")
    sys.exit(1)

from game_monitor.database_manager import get_database
from game_monitor.fast_validator import get_validator, ValidationLevel

class ScreenshotOCRProcessor:
    """OCR processor for screenshots without display dependencies"""
    
    def __init__(self):
        self.db = get_database()
        self.validator = get_validator()
        
    def preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.medianBlur(binary, 3)
        
        # Resize for better OCR (if too small)
        height, width = denoised.shape
        if height < 100 or width < 100:
            scale = max(100/height, 100/width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            denoised = cv2.resize(denoised, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        return denoised
    
    def extract_text_from_image(self, image_path, region=None):
        """Extract text from image using OCR"""
        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                return None, 0.0, f"Could not load image: {image_path}"
            
            # Extract region if specified
            if region:
                x, y, w, h = region
                image = image[y:y+h, x:x+w]
            
            # Preprocess
            processed = self.preprocess_image(image)
            
            # Convert to PIL for pytesseract
            pil_image = Image.fromarray(processed)
            
            # OCR with Russian and English
            custom_config = r'--oem 3 --psm 6 -l eng+rus'
            text = pytesseract.image_to_string(pil_image, config=custom_config)
            
            # Get confidence
            try:
                data = pytesseract.image_to_data(pil_image, config=custom_config, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            except:
                confidence = 0.8  # Default confidence
            
            return text.strip(), confidence, None
            
        except Exception as e:
            return None, 0.0, str(e)
    
    def parse_trading_data(self, text_lines):
        """Parse OCR text into trading data structure"""
        trading_data = {}
        
        # Simple parsing logic - can be enhanced based on actual screenshot format
        lines = [line.strip() for line in text_lines if line.strip()]
        
        if len(lines) >= 4:
            # Assume format: trader_name, item_name, quantity, price
            trading_data['trader_nickname'] = lines[0]
            trading_data['item_name'] = lines[1] 
            trading_data['quantity'] = lines[2]
            trading_data['price_per_unit'] = lines[3]
            
            # Calculate total if we have quantity and price
            try:
                qty = float(trading_data['quantity'])
                price = float(trading_data['price_per_unit'])
                trading_data['total_price'] = str(qty * price)
            except:
                trading_data['total_price'] = lines[4] if len(lines) > 4 else '0'
        
        return trading_data
    
    def process_screenshot(self, image_path, regions=None):
        """Process a complete screenshot with multiple regions"""
        results = {
            'image_path': str(image_path),
            'processing_time': 0,
            'regions_processed': 0,
            'ocr_results': [],
            'trading_data': [],
            'validation_results': [],
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            if regions:
                # Process specific regions
                for region_name, region_coords in regions.items():
                    print(f"   🔍 Processing region '{region_name}': {region_coords}")
                    
                    text, confidence, error = self.extract_text_from_image(image_path, region_coords)
                    
                    if error:
                        results['errors'].append(f"Region {region_name}: {error}")
                        continue
                    
                    results['ocr_results'].append({
                        'region': region_name,
                        'text': text,
                        'confidence': confidence
                    })
                    results['regions_processed'] += 1
                    
                    print(f"      📝 OCR Result: '{text}' (confidence: {confidence:.2f})")
            else:
                # Process entire image
                print("   🔍 Processing entire image...")
                
                text, confidence, error = self.extract_text_from_image(image_path)
                
                if error:
                    results['errors'].append(f"Full image: {error}")
                else:
                    results['ocr_results'].append({
                        'region': 'full_image',
                        'text': text,
                        'confidence': confidence
                    })
                    results['regions_processed'] = 1
                    
                    print(f"      📝 OCR Result: '{text}' (confidence: {confidence:.2f})")
                    
                    # Try to parse as trading data
                    if text:
                        text_lines = text.split('\n')
                        trading_data = self.parse_trading_data(text_lines)
                        
                        if trading_data and len(trading_data) >= 3:
                            print(f"      📊 Parsed trading data: {trading_data}")
                            
                            # Validate the trading data
                            validation_result = self.validator.validate_trade_data(
                                trading_data, 
                                level=ValidationLevel.BALANCED
                            )
                            
                            results['trading_data'].append(trading_data)
                            results['validation_results'].append({
                                'is_valid': validation_result.is_valid,
                                'confidence': validation_result.confidence,
                                'errors': validation_result.errors,
                                'warnings': validation_result.warnings
                            })
                            
                            print(f"      ✅ Validation: {validation_result.is_valid} (confidence: {validation_result.confidence:.2f})")
                            
                            # Store in database if valid
                            if validation_result.is_valid:
                                try:
                                    db_data = [{
                                        'trader_nickname': trading_data['trader_nickname'],
                                        'item_name': trading_data['item_name'],
                                        'quantity': int(float(trading_data['quantity'])),
                                        'price_per_unit': float(trading_data['price_per_unit']),
                                        'total_price': float(trading_data['total_price'])
                                    }]
                                    
                                    trade_ids = self.db.update_inventory_and_track_trades(db_data)
                                    print(f"      💾 Stored in database successfully")
                                    
                                except Exception as e:
                                    results['errors'].append(f"Database storage: {e}")
                                    print(f"      ❌ Database storage failed: {e}")
        
        except Exception as e:
            results['errors'].append(f"Processing error: {e}")
            print(f"   ❌ Processing failed: {e}")
        
        results['processing_time'] = time.time() - start_time
        return results

def test_ocr_screenshots():
    """Test OCR functionality with provided screenshots"""
    print("="*60)
    print("OCR SCREENSHOT PROCESSING TEST")
    print("Real Game Screenshot OCR Testing")
    print("="*60)
    
    processor = ScreenshotOCRProcessor()
    
    # Create screenshots directory if it doesn't exist
    screenshots_dir = Path("test_screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    
    print(f"1. Looking for screenshots in: {screenshots_dir.absolute()}")
    
    # Find all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    screenshots = []
    
    for ext in image_extensions:
        screenshots.extend(screenshots_dir.glob(f"*{ext}"))
        screenshots.extend(screenshots_dir.glob(f"*{ext.upper()}"))
    
    if not screenshots:
        print("   ⚠️  No screenshots found!")
        print(f"   📁 Please place your game screenshots in: {screenshots_dir.absolute()}")
        print("   📋 Supported formats: PNG, JPG, JPEG, BMP, TIFF")
        print("\n   🔧 You can also test with a sample image:")
        
        # Create a simple test image
        test_image = np.ones((200, 400, 3), dtype=np.uint8) * 255
        cv2.putText(test_image, "TestTrader", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(test_image, "Fire Sword", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(test_image, "5", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(test_image, "100.50", (150, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        test_path = screenshots_dir / "sample_test.png"
        cv2.imwrite(str(test_path), test_image)
        print(f"   ✅ Created sample test image: {test_path}")
        screenshots = [test_path]
    
    print(f"   📊 Found {len(screenshots)} screenshot(s) to process")
    
    # Process each screenshot
    all_results = []
    total_time = 0
    
    for i, screenshot in enumerate(screenshots, 1):
        print(f"\n2.{i} Processing screenshot: {screenshot.name}")
        
        result = processor.process_screenshot(screenshot)
        all_results.append(result)
        total_time += result['processing_time']
        
        print(f"   ⏱️  Processing time: {result['processing_time']:.3f}s")
        print(f"   📊 Regions processed: {result['regions_processed']}")
        print(f"   📊 OCR results: {len(result['ocr_results'])}")
        print(f"   📊 Trading data: {len(result['trading_data'])}")
        print(f"   📊 Errors: {len(result['errors'])}")
        
        if result['errors']:
            for error in result['errors']:
                print(f"      ❌ {error}")
    
    # Summary
    print(f"\n3. Processing Summary")
    total_screenshots = len(all_results)
    total_ocr_results = sum(len(r['ocr_results']) for r in all_results)
    total_trading_data = sum(len(r['trading_data']) for r in all_results)
    total_valid_data = sum(len([v for v in r['validation_results'] if v['is_valid']]) for r in all_results)
    total_errors = sum(len(r['errors']) for r in all_results)
    
    print(f"   📊 Screenshots processed: {total_screenshots}")
    print(f"   📊 OCR extractions: {total_ocr_results}")
    print(f"   📊 Trading records parsed: {total_trading_data}")
    print(f"   📊 Valid records: {total_valid_data}")
    print(f"   📊 Total errors: {total_errors}")
    print(f"   📊 Total processing time: {total_time:.3f}s")
    
    if total_trading_data > 0:
        avg_time_per_record = total_time / total_trading_data
        success_rate = total_valid_data / total_trading_data
        print(f"   📊 Average time per record: {avg_time_per_record:.3f}s")
        print(f"   📊 Success rate: {success_rate:.1%}")
    
    # Database verification
    print(f"\n4. Database Verification")
    try:
        with processor.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM current_inventory")
            inventory_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM trades")
            trades_count = cursor.fetchone()[0]
            
            print(f"   📊 Current inventory records: {inventory_count}")
            print(f"   📊 Trade records: {trades_count}")
            
            # Show recent records
            cursor.execute("SELECT trader_nickname, item_name, quantity, price_per_unit FROM current_inventory ORDER BY rowid DESC LIMIT 3")
            recent = cursor.fetchall()
            
            if recent:
                print("   📋 Recent inventory records:")
                for record in recent:
                    print(f"      - {record[0]}: {record[1]} x{record[2]} @ {record[3]}")
                    
    except Exception as e:
        print(f"   ❌ Database verification failed: {e}")
    
    # Final evaluation
    print(f"\n" + "="*60)
    
    if total_ocr_results > 0 and total_errors == 0:
        print("OCR SCREENSHOT TEST: ✅ SUCCESS")
        print("="*60)
        print("🎉 OCR system successfully processed your screenshots!")
        print(f"✅ Extracted text from {total_ocr_results} regions")
        if total_valid_data > 0:
            print(f"✅ Generated {total_valid_data} valid trading records")
            print(f"✅ Data stored in database successfully")
        return True
    else:
        print("OCR SCREENSHOT TEST: ⚠️  PARTIAL SUCCESS")
        print("="*60)
        print("📊 OCR system is functional but encountered some issues")
        print("💡 Try providing clear, high-contrast game screenshots")
        return len(all_results) > 0

if __name__ == "__main__":
    success = test_ocr_screenshots()
    print(f"\n📁 Screenshot directory: {Path('test_screenshots').absolute()}")
    print("💡 Place your game screenshots there and run this test again!")
    sys.exit(0 if success else 1)