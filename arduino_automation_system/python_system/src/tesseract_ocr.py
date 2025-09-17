"""
Tesseract OCR Integration for Arduino Automation System
Free OCR alternative to Yandex OCR with screen monitoring capabilities
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import logging
import time
import threading
from typing import Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import mss
import hashlib


@dataclass
class OCRRegion:
    """Screen region for OCR monitoring"""
    x: int
    y: int
    width: int
    height: int
    
    def to_mss_dict(self) -> Dict[str, int]:
        """Convert to mss screenshot format"""
        return {
            'left': self.x,
            'top': self.y,
            'width': self.width,
            'height': self.height
        }


@dataclass
class OCRResult:
    """OCR processing result"""
    text: str
    confidence: float
    processing_time: float
    region: OCRRegion
    timestamp: float
    text_hash: str


class TesseractOCRProcessor:
    """
    Tesseract OCR processor with preprocessing and optimization.
    Free alternative to Yandex OCR with enhanced accuracy.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Tesseract OCR processor.
        
        Args:
            config: OCR configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Tesseract configuration
        self.language = config.get('language', 'rus+eng')
        self.oem = config.get('oem', 3)  # OCR Engine Mode
        self.psm = config.get('psm', 6)  # Page Segmentation Mode
        self.confidence_threshold = config.get('confidence_threshold', 60)
        
        # Image preprocessing settings
        self.preprocessing_enabled = config.get('preprocessing_enabled', True)
        self.preprocessing_config = config.get('image_preprocessing', {})
        
        # Tesseract command configuration
        self.tesseract_config = self._build_tesseract_config()
        
        # Validate Tesseract installation
        self._validate_tesseract()
    
    def _build_tesseract_config(self) -> str:
        """Build Tesseract configuration string."""
        config_parts = []
        
        # Output options
        config_parts.append('-c tessedit_create_hocr=0')
        config_parts.append('-c tessedit_create_pdf=0')
        
        # Language and engine mode
        config_parts.append(f'--oem {self.oem}')
        config_parts.append(f'--psm {self.psm}')
        
        # Performance optimizations
        config_parts.append('-c preserve_interword_spaces=1')
        config_parts.append('-c textord_really_old_xheight=1')
        
        return ' '.join(config_parts)
    
    def _validate_tesseract(self) -> None:
        """Validate Tesseract installation and language support."""
        try:
            # Test basic Tesseract functionality
            test_image = Image.new('RGB', (100, 50), color='white')
            pytesseract.image_to_string(test_image, config=self.tesseract_config)
            
            # Check language support
            available_languages = pytesseract.get_languages()
            required_languages = self.language.split('+')
            
            for lang in required_languages:
                if lang not in available_languages:
                    self.logger.warning(f"Language '{lang}' not available in Tesseract")
            
            self.logger.info(f"Tesseract OCR initialized with language: {self.language}")
            
        except Exception as e:
            self.logger.error(f"Tesseract validation failed: {e}")
            raise RuntimeError(f"Tesseract OCR not properly installed: {e}")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        if not self.preprocessing_enabled:
            return image
        
        try:
            # Convert to OpenCV format for advanced processing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale if enabled
            if self.preprocessing_config.get('grayscale', True):
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                
                # Apply histogram equalization for better contrast
                cv_image = cv2.equalizeHist(cv_image)
            
            # Noise reduction
            if self.preprocessing_config.get('noise_reduction', True):
                cv_image = cv2.medianBlur(cv_image, 3)
            
            # Contrast enhancement
            if self.preprocessing_config.get('contrast_enhancement', True):
                cv_image = cv2.convertScaleAbs(cv_image, alpha=1.2, beta=10)
            
            # Convert back to PIL Image
            if len(cv_image.shape) == 2:  # Grayscale
                processed_image = Image.fromarray(cv_image, mode='L')
            else:  # Color
                processed_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Additional PIL-based enhancements
            if self.preprocessing_config.get('contrast_enhancement', True):
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(1.3)
            
            # Scale up for better OCR (if image is small)
            width, height = processed_image.size
            if width < 200 or height < 100:
                scale_factor = max(200 / width, 100 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                processed_image = processed_image.resize(new_size, Image.Resampling.LANCZOS)
            
            return processed_image
            
        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {e}")
            return image  # Return original if preprocessing fails
    
    def extract_text(self, image: Image.Image, region: Optional[OCRRegion] = None) -> OCRResult:
        """
        Extract text from image using Tesseract OCR.
        
        Args:
            image: PIL Image to process
            region: Optional region information
            
        Returns:
            OCRResult with extracted text and metadata
        """
        start_time = time.time()
        
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract text with Tesseract
            extracted_text = pytesseract.image_to_string(
                processed_image,
                lang=self.language,
                config=self.tesseract_config
            ).strip()
            
            # Get confidence data
            confidence_data = pytesseract.image_to_data(
                processed_image,
                lang=self.language,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [int(conf) for conf in confidence_data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            # Create text hash for change detection
            text_hash = hashlib.md5(extracted_text.encode()).hexdigest()
            
            result = OCRResult(
                text=extracted_text,
                confidence=avg_confidence,
                processing_time=processing_time,
                region=region,
                timestamp=time.time(),
                text_hash=text_hash
            )
            
            self.logger.debug(f"OCR extracted {len(extracted_text)} characters with {avg_confidence:.1f}% confidence")
            return result
            
        except Exception as e:
            self.logger.error(f"OCR text extraction failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                processing_time=time.time() - start_time,
                region=region,
                timestamp=time.time(),
                text_hash=""
            )


class ScreenMonitor:
    """
    Screen region monitoring with OCR change detection.
    Monitors specific screen area for visual changes using Tesseract OCR.
    """
    
    def __init__(self, region: OCRRegion, ocr_processor: TesseractOCRProcessor):
        """
        Initialize screen monitor.
        
        Args:
            region: Screen region to monitor
            ocr_processor: OCR processor for text extraction
        """
        self.region = region
        self.ocr_processor = ocr_processor
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_ocr_result: Optional[OCRResult] = None
        
        # Change detection settings
        self.similarity_threshold = 0.85  # Keep for backward compatibility
        self.change_threshold_percent = 50  # NEW: 50% threshold for character changes
        self.minimum_change_length = 3
        self.ignore_whitespace = True
        
        # Callbacks
        self.change_callbacks: List[Callable[[OCRResult, OCRResult], None]] = []
        
        # Screenshots using mss for performance
        self.screenshot_tool = mss.mss()
    
    def capture_region(self) -> Optional[Image.Image]:
        """
        Capture screenshot of monitored region.
        
        Returns:
            PIL Image of the region or None if capture fails
        """
        try:
            # Capture screenshot using mss (faster than PIL)
            screenshot = self.screenshot_tool.grab(self.region.to_mss_dict())
            
            # Convert to PIL Image
            image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            return image
            
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return None
    
    def detect_change(self, new_result: OCRResult, old_result: Optional[OCRResult]) -> bool:
        """
        Detect if OCR result represents a significant change using 50% threshold.
        
        Args:
            new_result: Latest OCR result
            old_result: Previous OCR result
            
        Returns:
            True if significant change detected
        """
        if not old_result:
            return True  # First result is always a change
        
        # Compare text hashes for quick detection
        if new_result.text_hash == old_result.text_hash:
            return False  # Identical content
        
        # Use character-level change detection
        change_percent = self._calculate_character_change_percentage(
            new_result.text, old_result.text
        )
        
        # Check if change exceeds 50% threshold
        if change_percent > self.change_threshold_percent:
            self.logger.debug(f"Change detected: {change_percent:.1f}% > {self.change_threshold_percent}%")
            self.logger.debug(f"Text change: '{old_result.text[:50]}...' -> '{new_result.text[:50]}...'")
            return True
        
        self.logger.debug(f"Change below threshold: {change_percent:.1f}% <= {self.change_threshold_percent}%")
        return False
    
    def _calculate_character_change_percentage(self, text1: str, text2: str) -> float:
        """
        Calculate percentage of character changes between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Percentage of characters that are different (0-100)
        """
        if not text1 and not text2:
            return 0.0
        if not text1 or not text2:
            return 100.0
        
        # Normalize texts if needed
        if self.ignore_whitespace:
            text1 = ''.join(text1.split())
            text2 = ''.join(text2.split())
        
        # Calculate character differences
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 0.0
        
        # Count different characters at each position
        differences = 0
        min_len = min(len(text1), len(text2))
        
        # Compare overlapping characters
        for i in range(min_len):
            if text1[i] != text2[i]:
                differences += 1
        
        # Add length difference as additional changes
        differences += abs(len(text1) - len(text2))
        
        return (differences / max_len) * 100.0
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using simple character-based comparison.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        max_len = max(len(text1), len(text2))
        matches = sum(c1 == c2 for c1, c2 in zip(text1, text2))
        
        return matches / max_len
    
    def add_change_callback(self, callback: Callable[[OCRResult, OCRResult], None]) -> None:
        """
        Add callback function to be called when change is detected.
        
        Args:
            callback: Function to call with (new_result, old_result)
        """
        self.change_callbacks.append(callback)
    
    def start_monitoring(self, interval: float = 1.0) -> None:
        """
        Start monitoring screen region for changes.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.is_monitoring:
            self.logger.warning("Screen monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        
        self.logger.info(f"Started screen monitoring of region ({self.region.x}, {self.region.y}, {self.region.width}x{self.region.height})")
    
    def stop_monitoring(self) -> None:
        """Stop screen monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("Stopped screen monitoring")
    
    def _monitor_loop(self, interval: float) -> None:
        """
        Main monitoring loop running in separate thread.
        
        Args:
            interval: Monitoring interval in seconds
        """
        while self.is_monitoring:
            try:
                # Capture screen region
                image = self.capture_region()
                if not image:
                    time.sleep(interval)
                    continue
                
                # Extract text using OCR
                ocr_result = self.ocr_processor.extract_text(image, self.region)
                
                # Check for changes
                if self.detect_change(ocr_result, self.last_ocr_result):
                    # Notify callbacks about change
                    for callback in self.change_callbacks:
                        try:
                            callback(ocr_result, self.last_ocr_result)
                        except Exception as e:
                            self.logger.error(f"Change callback failed: {e}")
                
                # Update last result
                self.last_ocr_result = ocr_result
                
                # Wait for next iteration
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(interval)
    
    def get_current_text(self) -> Optional[str]:
        """
        Get current text from monitored region.
        
        Returns:
            Current OCR text or None if not available
        """
        image = self.capture_region()
        if not image:
            return None
        
        result = self.ocr_processor.extract_text(image, self.region)
        return result.text if result.confidence > self.ocr_processor.confidence_threshold else None


class TesseractOCRManager:
    """
    High-level manager for Tesseract OCR operations.
    Combines OCR processing with screen monitoring functionality.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OCR manager.
        
        Args:
            config: OCR configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize OCR processor
        self.ocr_processor = TesseractOCRProcessor(config)
        
        # Active screen monitors
        self.monitors: Dict[str, ScreenMonitor] = {}
        
        self.logger.info("Tesseract OCR Manager initialized successfully")
    
    def create_screen_monitor(self, name: str, region: OCRRegion) -> ScreenMonitor:
        """
        Create and register screen monitor.
        
        Args:
            name: Monitor name for identification
            region: Screen region to monitor
            
        Returns:
            Created ScreenMonitor instance
        """
        monitor = ScreenMonitor(region, self.ocr_processor)
        self.monitors[name] = monitor
        
        self.logger.info(f"Created screen monitor '{name}' for region {region.x},{region.y} {region.width}x{region.height}")
        return monitor
    
    def get_monitor(self, name: str) -> Optional[ScreenMonitor]:
        """
        Get screen monitor by name.
        
        Args:
            name: Monitor name
            
        Returns:
            ScreenMonitor instance or None if not found
        """
        return self.monitors.get(name)
    
    def stop_all_monitors(self) -> None:
        """Stop all active screen monitors."""
        for name, monitor in self.monitors.items():
            monitor.stop_monitoring()
            self.logger.info(f"Stopped monitor '{name}'")
    
    def process_image_file(self, image_path: str) -> OCRResult:
        """
        Process image file with OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            OCR result
        """
        try:
            image = Image.open(image_path)
            return self.ocr_processor.extract_text(image)
        except Exception as e:
            self.logger.error(f"Failed to process image file {image_path}: {e}")
            return OCRResult("", 0.0, 0.0, None, time.time(), "")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get OCR system statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'active_monitors': len(self.monitors),
            'monitor_names': list(self.monitors.keys()),
            'ocr_config': {
                'language': self.ocr_processor.language,
                'preprocessing_enabled': self.ocr_processor.preprocessing_enabled,
                'confidence_threshold': self.ocr_processor.confidence_threshold
            }
        }