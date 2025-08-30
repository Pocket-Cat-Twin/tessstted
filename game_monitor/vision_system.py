"""
High-Performance Vision System for Game Monitor

Optimized OCR and image processing with <1 second response time,
caching, and multi-region support.
"""

import logging
import time
import hashlib
import threading
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from pathlib import Path
import re
import io

# Try to import required libraries with fallbacks
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from .database_manager import get_database

logger = logging.getLogger(__name__)

@dataclass
class ScreenRegion:
    """Screen region definition"""
    x: int
    y: int
    width: int
    height: int
    name: str = ""

@dataclass
class OCRResult:
    """OCR processing result"""
    text: str
    confidence: float
    processing_time: float
    region_type: str
    cached: bool = False

class VisionSystem:
    """High-performance vision system with caching and optimization"""
    
    def __init__(self):
        self.db = get_database()
        self._lock = threading.Lock()
        
        # OCR configuration for different regions
        self.ocr_configs = {
            'trader_name': '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-',
            'quantity': '--psm 8 -c tessedit_char_whitelist=0123456789',
            'price': '--psm 8 -c tessedit_char_whitelist=0123456789.',
            'item_name': '--psm 7 -l eng+rus',
            'general': '--psm 6 -l eng+rus'
        }
        
        # Pre-compiled regex patterns for parsing
        self.patterns = {
            'trader_name': re.compile(r'^[A-Za-z0-9_-]{3,16}$'),
            'quantity': re.compile(r'^[1-9]\d{0,5}$'),  # 1-999999
            'price': re.compile(r'^\d{1,8}(?:\.\d{1,2})?$'),  # 1-99999999.99
            'item_name': re.compile(r'^[A-Za-zА-Яа-я0-9\s]{3,50}$')
        }
        
        # Performance tracking
        self.stats = {
            'screenshots_taken': 0,
            'ocr_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_processing_time': 0.0,
            'avg_ocr_time': 0.0
        }
        
        # Check available libraries
        self._check_dependencies()
        
        logger.info("VisionSystem initialized")
    
    def _check_dependencies(self):
        """Check and log available dependencies"""
        status = {
            'pyautogui': PYAUTOGUI_AVAILABLE,
            'opencv': OPENCV_AVAILABLE, 
            'ocr': OCR_AVAILABLE
        }
        
        for lib, available in status.items():
            if available:
                logger.info(f"✅ {lib} available")
            else:
                logger.warning(f"❌ {lib} not available - some features disabled")
        
        if not any(status.values()):
            logger.error("No vision libraries available - running in simulation mode")
    
    def take_screenshot(self, region: Optional[ScreenRegion] = None, 
                       save_path: Optional[str] = None) -> Optional[Any]:
        """
        Take optimized screenshot of screen or region
        Returns PIL Image or None if failed
        """
        if not PYAUTOGUI_AVAILABLE:
            logger.warning("Screenshot requested but pyautogui not available")
            return self._create_dummy_image()
        
        start_time = time.time()
        
        try:
            if region:
                # Capture specific region
                screenshot = pyautogui.screenshot(
                    region=(region.x, region.y, region.width, region.height)
                )
            else:
                # Capture full screen
                screenshot = pyautogui.screenshot()
            
            # Save if path provided
            if save_path:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                screenshot.save(save_path)
            
            # Update stats
            with self._lock:
                self.stats['screenshots_taken'] += 1
            
            processing_time = time.time() - start_time
            logger.debug(f"Screenshot taken in {processing_time:.3f}s")
            
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def preprocess_image(self, image: Any, region_type: str = 'general') -> Any:
        """
        Preprocess image for optimal OCR performance
        """
        if not OPENCV_AVAILABLE:
            return image  # Return original if opencv not available
        
        try:
            # Convert PIL to OpenCV format
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                img_cv = img_array
            
            # Convert to grayscale
            if len(img_cv.shape) == 3:
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            else:
                gray = img_cv
            
            # Apply preprocessing based on region type
            if region_type in ['quantity', 'price']:
                # High contrast for numbers
                gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                gray = cv2.medianBlur(gray, 3)
            
            elif region_type == 'trader_name':
                # Optimize for text
                gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)
            
            else:
                # General preprocessing
                gray = cv2.bilateralFilter(gray, 9, 75, 75)
                gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Convert back to PIL format
            processed_image = Image.fromarray(gray)
            return processed_image
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image  # Return original on error
    
    def perform_ocr(self, image: Any, region_type: str = 'general', 
                   use_cache: bool = True) -> OCRResult:
        """
        Perform OCR on image with caching and optimization
        """
        start_time = time.time()
        
        # Generate image hash for caching
        image_hash = self._generate_image_hash(image) if use_cache else None
        
        # Check cache first
        if use_cache and image_hash:
            cached_result = self.db.get_cached_ocr(image_hash)
            if cached_result:
                with self._lock:
                    self.stats['cache_hits'] += 1
                
                return OCRResult(
                    text=cached_result['ocr_result'],
                    confidence=cached_result['confidence_score'],
                    processing_time=time.time() - start_time,
                    region_type=region_type,
                    cached=True
                )
        
        # Perform OCR
        if not OCR_AVAILABLE:
            # Fallback for when OCR is not available
            text = self._simulate_ocr(region_type)
            confidence = 0.85
        else:
            text, confidence = self._execute_ocr(image, region_type)
        
        processing_time = time.time() - start_time
        
        # Cache result
        if use_cache and image_hash and confidence > 0.7:
            self.db.cache_ocr_result(image_hash, text, confidence, region_type)
        
        # Update stats
        with self._lock:
            if use_cache:
                self.stats['cache_misses'] += 1
            self.stats['ocr_operations'] += 1
            self.stats['total_processing_time'] += processing_time
            self.stats['avg_ocr_time'] = (
                self.stats['total_processing_time'] / self.stats['ocr_operations']
            )
        
        return OCRResult(
            text=text,
            confidence=confidence,
            processing_time=processing_time,
            region_type=region_type,
            cached=False
        )
    
    def _execute_ocr(self, image: Any, region_type: str) -> Tuple[str, float]:
        """Execute actual OCR using pytesseract"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image, region_type)
            
            # Get OCR config for region type
            config = self.ocr_configs.get(region_type, self.ocr_configs['general'])
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_image, config=config).strip()
            
            # Get confidence (requires detailed output)
            try:
                data = pytesseract.image_to_data(processed_image, config=config, 
                                               output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            except:
                confidence = 0.8 if text else 0.0  # Fallback confidence
            
            return text, confidence
            
        except Exception as e:
            logger.error(f"OCR execution failed: {e}")
            return "", 0.0
    
    def _simulate_ocr(self, region_type: str) -> str:
        """Simulate OCR for testing when libraries not available"""
        simulation_data = {
            'trader_name': 'TestTrader',
            'quantity': '42',
            'price': '1500.00',
            'item_name': 'Test Item',
            'general': 'Sample Text'
        }
        return simulation_data.get(region_type, 'Sample')
    
    def _generate_image_hash(self, image: Any) -> str:
        """Generate hash for image caching"""
        try:
            # Convert image to bytes
            if hasattr(image, 'tobytes'):
                image_bytes = image.tobytes()
            else:
                # Fallback for PIL images
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
            
            # Generate hash
            return hashlib.md5(image_bytes).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to generate image hash: {e}")
            return None
    
    def _create_dummy_image(self) -> Any:
        """Create dummy image for testing"""
        try:
            from PIL import Image
            return Image.new('RGB', (100, 50), color='white')
        except:
            return None
    
    def parse_trader_data(self, ocr_result: OCRResult) -> Optional[Dict[str, Any]]:
        """Parse trader data from OCR result"""
        text = ocr_result.text.strip()
        
        if ocr_result.region_type == 'trader_name':
            if self.patterns['trader_name'].match(text):
                return {'trader_nickname': text}
        
        elif ocr_result.region_type == 'quantity':
            if self.patterns['quantity'].match(text):
                return {'quantity': int(text)}
        
        elif ocr_result.region_type == 'price':
            if self.patterns['price'].match(text):
                return {'price_per_unit': float(text)}
        
        elif ocr_result.region_type == 'item_name':
            if self.patterns['item_name'].match(text):
                return {'item_name': text}
        
        return None
    
    def capture_and_process_region(self, region: ScreenRegion, 
                                  region_type: str = 'general') -> Optional[Dict[str, Any]]:
        """
        Complete pipeline: capture region, OCR, and parse
        Optimized for <1 second processing
        """
        total_start = time.time()
        
        # Take screenshot
        screenshot = self.take_screenshot(region)
        if screenshot is None:
            return None
        
        # Perform OCR
        ocr_result = self.perform_ocr(screenshot, region_type)
        
        # Parse result
        parsed_data = self.parse_trader_data(ocr_result)
        
        total_time = time.time() - total_start
        
        if total_time > 1.0:
            logger.warning(f"Slow region processing: {total_time:.3f}s for {region.name}")
        
        logger.debug(f"Region {region.name} processed in {total_time:.3f}s, "
                    f"confidence: {ocr_result.confidence:.2f}")
        
        if parsed_data:
            parsed_data['ocr_confidence'] = ocr_result.confidence
            parsed_data['processing_time'] = total_time
        
        return parsed_data
    
    def process_multiple_regions(self, regions: List[Tuple[ScreenRegion, str]]) -> List[Dict[str, Any]]:
        """
        Process multiple regions efficiently
        """
        results = []
        
        for region, region_type in regions:
            result = self.capture_and_process_region(region, region_type)
            if result:
                result['region_name'] = region.name
                results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vision system performance statistics"""
        with self._lock:
            stats = self.stats.copy()
        
        # Calculate additional metrics
        if stats['ocr_operations'] > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])
        else:
            stats['cache_hit_rate'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """Reset performance statistics"""
        with self._lock:
            self.stats = {
                'screenshots_taken': 0,
                'ocr_operations': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'total_processing_time': 0.0,
                'avg_ocr_time': 0.0
            }
        logger.info("Vision system statistics reset")

# Global instance for easy access
_vision_system_instance = None
_vision_system_lock = threading.Lock()

def get_vision_system() -> VisionSystem:
    """Get singleton vision system instance"""
    global _vision_system_instance
    if _vision_system_instance is None:
        with _vision_system_lock:
            if _vision_system_instance is None:
                _vision_system_instance = VisionSystem()
    return _vision_system_instance