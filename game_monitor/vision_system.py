"""
High-Performance Vision System for Game Monitor

Optimized OCR and image processing with <1 second response time,
caching, and multi-region support.
"""

import logging
import time
import hashlib
import threading
import sys
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from pathlib import Path
import re
import io
import json
from datetime import datetime

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
from .advanced_logger import get_vision_logger
from .error_tracker import ErrorTracker
from .performance_logger import PerformanceMonitor
from .error_handler import ErrorHandler, ErrorContext, ErrorCategory, RecoveryStrategy, get_error_handler
from .constants import OCR

logger = logging.getLogger(__name__)  # Keep for compatibility

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
        init_start = time.time()
        
        # Initialize basic components first
        self.db = get_database()
        self._lock = threading.Lock()
        
        # Advanced logging and monitoring
        self.advanced_logger = get_vision_logger()
        self.error_tracker = ErrorTracker()
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = get_error_handler()
        
        with self.advanced_logger.operation_context('vision_system', 'initialization'):
            try:
                self.advanced_logger.info(
                    "Starting VisionSystem initialization",
                    extra_data={
                        'python_version': sys.version,
                        'initialization_started': datetime.now().isoformat()
                    }
                )
                
                # OCR configuration for different regions
                config_start = time.time()
                self.ocr_configs = {
                    'trader_name': f'--psm 8 -c tessedit_char_whitelist={OCR.TRADER_NAME_WHITELIST}',
                    'quantity': f'--psm 8 -c tessedit_char_whitelist={OCR.QUANTITY_WHITELIST}',
                    'price': f'--psm 8 -c tessedit_char_whitelist={OCR.PRICE_WHITELIST}',
                    'item_name': '--psm 7 -l eng+rus',
                    'general': '--psm 6 -l eng+rus'
                }
                config_time = time.time() - config_start
                
                # OCR timeout configuration (in seconds)
                self.ocr_timeout = 30  # Default 30 seconds timeout for OCR operations
                
                self.advanced_logger.debug(
                    f"OCR configurations loaded for {len(self.ocr_configs)} region types",
                    extra_data={
                        'config_count': len(self.ocr_configs),
                        'region_types': list(self.ocr_configs.keys()),
                        'config_load_time_ms': config_time * 1000,
                        'ocr_timeout_seconds': self.ocr_timeout
                    }
                )
                
                # Pre-compiled regex patterns for parsing
                patterns_start = time.time()
                self.patterns = {
                    'trader_name': re.compile(r'^[A-Za-z0-9_-]{3,16}$'),
                    'quantity': re.compile(r'^[1-9]\d{0,5}$'),  # 1-999999
                    'price': re.compile(r'^\d{1,8}(?:\.\d{1,2})?$'),  # 1-99999999.99
                    'item_name': re.compile(r'^[A-Za-zА-Яа-я0-9\s]{3,50}$')
                }
                patterns_time = time.time() - patterns_start
                
                self.advanced_logger.debug(
                    f"Regex patterns compiled for {len(self.patterns)} data types",
                    extra_data={
                        'pattern_count': len(self.patterns),
                        'pattern_types': list(self.patterns.keys()),
                        'compilation_time_ms': patterns_time * 1000
                    }
                )
                
                # Performance tracking initialization
                self.stats = {
                    'screenshots_taken': 0,
                    'ocr_operations': 0,
                    'cache_hits': 0,
                    'cache_misses': 0,
                    'total_processing_time': 0.0,
                    'avg_ocr_time': 0.0
                }
                
                self.advanced_logger.debug(
                    "Performance statistics initialized",
                    extra_data={'stats_fields': list(self.stats.keys())}
                )
                
                # Testing output configuration
                directory_start = time.time()
                self.testing_enabled = False
                self.testing_output_file = Path("data/testing_output.txt")
                self.testing_detailed_file = Path("data/testing_detailed.json")
                
                # Ensure testing output directory exists
                self.testing_output_file.parent.mkdir(parents=True, exist_ok=True)
                directory_time = time.time() - directory_start
                
                self.advanced_logger.debug(
                    "Testing output directories created",
                    extra_data={
                        'output_file': str(self.testing_output_file),
                        'detailed_file': str(self.testing_detailed_file),
                        'directory_setup_time_ms': directory_time * 1000
                    }
                )
                
                # Check available libraries
                deps_start = time.time()
                self._check_dependencies()
                deps_time = time.time() - deps_start
                
                init_time = time.time() - init_start
                
                # Final initialization log
                self.advanced_logger.info(
                    f"VisionSystem initialized successfully in {init_time*1000:.2f}ms",
                    extra_data={
                        'total_initialization_time_ms': init_time * 1000,
                        'timing_breakdown': {
                            'ocr_configs_ms': config_time * 1000,
                            'regex_patterns_ms': patterns_time * 1000,
                            'directories_ms': directory_time * 1000,
                            'dependencies_check_ms': deps_time * 1000
                        },
                        'system_ready': True,
                        'available_libraries': {
                            'pyautogui': PYAUTOGUI_AVAILABLE,
                            'opencv': OPENCV_AVAILABLE,
                            'ocr': OCR_AVAILABLE
                        }
                    }
                )
                
                logger.info("VisionSystem initialized")
                
            except ImportError as e:
                # Handle missing dependency errors
                init_time = time.time() - init_start
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='initialization_import_error',
                    user_data={
                        'missing_module': str(e),
                        'initialization_time_ms': init_time * 1000
                    },
                    system_state={'libraries_available': {'pyautogui': PYAUTOGUI_AVAILABLE, 'opencv': OPENCV_AVAILABLE, 'ocr': OCR_AVAILABLE}},
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.FALLBACK)
                
                if not recovery_result.recovery_successful:
                    raise
                    
            except (OSError, PermissionError) as e:
                # Handle system/permission errors
                init_time = time.time() - init_start
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='initialization_system_error',
                    user_data={
                        'error_type': type(e).__name__,
                        'initialization_time_ms': init_time * 1000
                    },
                    system_state={},
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.GRACEFUL_DEGRADATION)
                
                if not recovery_result.recovery_successful:
                    raise
                    
            except Exception as e:
                # Handle all other unexpected initialization errors
                init_time = time.time() - init_start
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='initialization_unexpected',
                    user_data={
                        'error_type': type(e).__name__,
                        'initialization_time_ms': init_time * 1000
                    },
                    system_state={},
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.USER_INTERVENTION)
                
                # For initialization errors, we usually can't recover
                self.advanced_logger.critical(f"Critical initialization error: {e}")
                raise
    
    def __del__(self):
        """Cleanup resources when VisionSystem is destroyed"""
        try:
            # This helps ensure any remaining resources are cleaned up
            if hasattr(self, 'stats') and hasattr(self, 'advanced_logger'):
                self.advanced_logger.debug("VisionSystem cleanup - releasing resources")
        except:
            pass  # Don't raise exceptions in destructor
    
    def _check_dependencies(self):
        """Check and log available dependencies with comprehensive logging"""
        with self.advanced_logger.operation_context('vision_system', 'dependency_check'):
            deps_start = time.time()
            
            try:
                status = {
                    'pyautogui': PYAUTOGUI_AVAILABLE,
                    'opencv': OPENCV_AVAILABLE, 
                    'ocr': OCR_AVAILABLE
                }
                
                available_count = sum(status.values())
                total_count = len(status)
                
                self.advanced_logger.info(
                    f"Dependency check: {available_count}/{total_count} libraries available",
                    extra_data={
                        'library_status': status,
                        'available_libraries': [lib for lib, available in status.items() if available],
                        'missing_libraries': [lib for lib, available in status.items() if not available],
                        'availability_rate': available_count / total_count
                    }
                )
                
                # Log each dependency status
                for lib, available in status.items():
                    if available:
                        self.advanced_logger.debug(f"Library {lib} available and ready")
                        logger.info(f"✅ {lib} available")
                    else:
                        self.advanced_logger.warning(
                            f"Library {lib} not available - features will be limited",
                            extra_data={
                                'missing_library': lib,
                                'impact': self._get_library_impact(lib)
                            }
                        )
                        logger.warning(f"❌ {lib} not available - some features disabled")
                
                # Check for critical situation
                if not any(status.values()):
                    self.advanced_logger.error(
                        "CRITICAL: No vision libraries available - system running in simulation mode",
                        extra_data={
                            'simulation_mode': True,
                            'all_libraries_missing': True,
                            'system_capabilities': 'severely_limited'
                        }
                    )
                    logger.error("No vision libraries available - running in simulation mode")
                    
                    # Record critical error
                    self.error_tracker.record_error(
                        'vision_system', 'dependency_check', 
                        Exception("No vision libraries available"),
                        context={'available_libraries': available_count}
                    )
                
                deps_time = time.time() - deps_start
                
                self.advanced_logger.info(
                    f"Dependency check completed in {deps_time*1000:.2f}ms",
                    extra_data={
                        'check_time_ms': deps_time * 1000,
                        'libraries_checked': total_count,
                        'system_status': 'operational' if available_count > 0 else 'simulation_only'
                    }
                )
                
            except ImportError as e:
                # Handle import errors during dependency check
                deps_time = time.time() - deps_start
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='dependency_check_import_error',
                    user_data={
                        'missing_import': str(e),
                        'check_time_ms': deps_time * 1000
                    },
                    system_state={'simulation_mode': True},
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.FALLBACK)
                
            except AttributeError as e:
                # Handle attribute errors during library checks
                deps_time = time.time() - deps_start
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='dependency_check_attribute_error',
                    user_data={
                        'attribute_error': str(e),
                        'check_time_ms': deps_time * 1000
                    },
                    system_state={'simulation_mode': True},
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
                
            except Exception as e:
                # Handle other unexpected dependency check errors
                deps_time = time.time() - deps_start
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='dependency_check_unexpected',
                    user_data={
                        'error_type': type(e).__name__,
                        'check_time_ms': deps_time * 1000
                    },
                    system_state={'fallback_mode': 'simulation'},
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.GRACEFUL_DEGRADATION)
    
    def _get_library_impact(self, library_name: str) -> str:
        """Get impact description for missing library"""
        impacts = {
            'pyautogui': 'Screenshot capture disabled, will use simulation mode',
            'opencv': 'Image preprocessing disabled, OCR accuracy may be reduced',
            'ocr': 'Text recognition disabled, will use simulation mode'
        }
        return impacts.get(library_name, 'Unknown impact')
    
    def take_screenshot(self, region: Optional[ScreenRegion] = None, 
                       save_path: Optional[str] = None) -> Optional[Any]:
        """
        Take optimized screenshot of screen or region with comprehensive logging
        Returns PIL Image or None if failed
        """
        
        # Start performance tracking
        trace_id = self.performance_monitor.start_operation(
            'vision_system', 'screenshot',
            context={
                'region': f"{region.x},{region.y} {region.width}x{region.height}" if region else "fullscreen",
                'save_path': save_path
            }
        )
        
        with self.advanced_logger.operation_context('vision_system', 'take_screenshot'):
            try:
                if not PYAUTOGUI_AVAILABLE:
                    self.advanced_logger.warning(
                        "Screenshot requested but pyautogui not available - using simulation",
                        extra_data={'libraries_available': {'pyautogui': False}}
                    )
                    
                    dummy_image = self._create_dummy_image()
                    self.performance_monitor.finish_operation(trace_id, success=True)
                    return dummy_image
                
                # Log screenshot attempt with detailed context
                region_info = {}
                if region:
                    region_info = {
                        'x': region.x, 'y': region.y,
                        'width': region.width, 'height': region.height,
                        'area_pixels': region.width * region.height
                    }
                    self.advanced_logger.info(
                        f"Taking screenshot of region {region.name or 'unnamed'}",
                        extra_data={'region': region_info, 'save_path': save_path}
                    )
                else:
                    self.advanced_logger.info(
                        "Taking fullscreen screenshot",
                        extra_data={'save_path': save_path}
                    )
                
                start_time = time.time()
                
                # Take screenshot
                if region:
                    screenshot = pyautogui.screenshot(
                        region=(region.x, region.y, region.width, region.height)
                    )
                else:
                    screenshot = pyautogui.screenshot()
                
                processing_time = time.time() - start_time
                
                # Save if path provided
                file_size_bytes = 0
                if save_path:
                    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                    screenshot.save(save_path)
                    file_size_bytes = Path(save_path).stat().st_size
                    
                    self.advanced_logger.debug(
                        f"Screenshot saved to {save_path}",
                        extra_data={
                            'file_path': save_path,
                            'file_size_bytes': file_size_bytes,
                            'file_size_mb': file_size_bytes / (1024 * 1024)
                        }
                    )
                
                # Update statistics
                with self._lock:
                    self.stats['screenshots_taken'] += 1
                
                # Log successful completion with metrics
                self.advanced_logger.info(
                    f"Screenshot captured successfully in {processing_time*1000:.2f}ms",
                    extra_data={
                        'processing_time_ms': processing_time * 1000,
                        'image_size': screenshot.size if hasattr(screenshot, 'size') else None,
                        'file_size_bytes': file_size_bytes,
                        'region': region_info if region else None
                    }
                )
                
                # Finish performance tracking
                self.performance_monitor.finish_operation(
                    trace_id, success=True,
                    operation_data={
                        'processing_time_ms': processing_time * 1000,
                        'file_size_bytes': file_size_bytes,
                        'image_dimensions': screenshot.size if hasattr(screenshot, 'size') else None
                    }
                )
                
                # IMPORTANT: Caller is responsible for cleaning up this screenshot image
                # to prevent memory leaks. Call self.cleanup_image(screenshot) when done.
                return screenshot
                
            except Exception as e:
                # Comprehensive error logging
                self.advanced_logger.error(
                    f"Screenshot capture failed: {str(e)}",
                    error=e,
                    extra_data={
                        'region': region_info if region else None,
                        'save_path': save_path,
                        'pyautogui_available': PYAUTOGUI_AVAILABLE
                    }
                )
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'vision_system', 'take_screenshot', e,
                    context={
                        'region': region.__dict__ if region else None,
                        'save_path': save_path
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                return None
    
    def preprocess_image(self, image: Any, region_type: str = 'general') -> Any:
        """
        Preprocess image for optimal OCR performance with comprehensive logging
        """
        with self.advanced_logger.operation_context('vision_system', 'preprocess_image'):
            start_time = time.time()
            
            try:
                # Log preprocessing start
                original_size = getattr(image, 'size', None) if hasattr(image, 'size') else None
                
                self.advanced_logger.debug(
                    f"Starting image preprocessing for {region_type}",
                    extra_data={
                        'region_type': region_type,
                        'opencv_available': OPENCV_AVAILABLE,
                        'original_image_size': original_size
                    }
                )
                
                if not OPENCV_AVAILABLE:
                    self.advanced_logger.warning(
                        "OpenCV not available - returning original image without preprocessing",
                        extra_data={'libraries_available': {'opencv': False}}
                    )
                    return image  # Return original if opencv not available
                
                # Convert PIL to OpenCV format
                conversion_start = time.time()
                img_array = np.array(image)
                if len(img_array.shape) == 3:
                    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                else:
                    img_cv = img_array
                conversion_time = time.time() - conversion_start
                
                self.advanced_logger.debug(
                    f"Image format conversion completed in {conversion_time*1000:.2f}ms",
                    extra_data={
                        'conversion_time_ms': conversion_time * 1000,
                        'input_channels': len(img_array.shape),
                        'array_shape': img_array.shape
                    }
                )
                
                # Convert to grayscale
                grayscale_start = time.time()
                if len(img_cv.shape) == 3:
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                else:
                    gray = img_cv
                grayscale_time = time.time() - grayscale_start
                
                # Apply preprocessing based on region type
                processing_start = time.time()
                processing_method = ""
                
                if region_type in ['quantity', 'price']:
                    # High contrast for numbers
                    processing_method = "threshold_otsu_median_blur"
                    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                    gray = cv2.medianBlur(gray, 3)
                
                elif region_type == 'trader_name':
                    # Optimize for text
                    processing_method = "adaptive_threshold_gaussian"
                    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                               cv2.THRESH_BINARY, 11, 2)
                
                else:
                    # General preprocessing
                    processing_method = "bilateral_filter_otsu"
                    gray = cv2.bilateralFilter(gray, 9, 75, 75)
                    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                
                processing_time = time.time() - processing_start
                
                # Convert back to PIL format
                pil_conversion_start = time.time()
                processed_image = Image.fromarray(gray)
                pil_conversion_time = time.time() - pil_conversion_start
                
                total_time = time.time() - start_time
                processed_size = getattr(processed_image, 'size', None) if hasattr(processed_image, 'size') else None
                
                # Log successful completion
                self.advanced_logger.info(
                    f"Image preprocessing completed for {region_type} in {total_time*1000:.2f}ms",
                    extra_data={
                        'processing_method': processing_method,
                        'total_time_ms': total_time * 1000,
                        'timing_breakdown': {
                            'conversion_ms': conversion_time * 1000,
                            'grayscale_ms': grayscale_time * 1000,
                            'processing_ms': processing_time * 1000,
                            'pil_conversion_ms': pil_conversion_time * 1000
                        },
                        'original_size': original_size,
                        'processed_size': processed_size,
                        'size_preserved': original_size == processed_size
                    }
                )
                
                # Note: processed_image will be returned and used by caller
                # The caller is responsible for cleaning up this image
                # Adding cleanup hint as attribute for memory management awareness
                if hasattr(processed_image, '_needs_cleanup'):
                    processed_image._needs_cleanup = True
                
                return processed_image
                
            except Exception as e:
                # Comprehensive error logging
                total_time = time.time() - start_time
                
                self.advanced_logger.error(
                    f"Image preprocessing failed for {region_type}: {str(e)}",
                    error=e,
                    extra_data={
                        'region_type': region_type,
                        'opencv_available': OPENCV_AVAILABLE,
                        'elapsed_time_ms': total_time * 1000,
                        'fallback_action': 'returning_original_image'
                    }
                )
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'vision_system', 'preprocess_image', e,
                    context={
                        'region_type': region_type,
                        'image_available': image is not None
                    }
                )
                
                return image  # Return original on error
    
    def perform_ocr(self, image: Any, region_type: str = 'general', 
                   use_cache: bool = True) -> OCRResult:
        """
        Perform OCR on image with caching and optimization with comprehensive logging
        """
        # Start performance tracking
        trace_id = self.performance_monitor.start_operation(
            'vision_system', 'ocr',
            context={
                'region_type': region_type,
                'use_cache': use_cache,
                'image_size': getattr(image, 'size', None) if hasattr(image, 'size') else 'unknown'
            }
        )
        
        with self.advanced_logger.operation_context('vision_system', 'perform_ocr'):
            start_time = time.time()
            
            try:
                # Log OCR operation start
                self.advanced_logger.info(
                    f"Starting OCR processing for {region_type}",
                    extra_data={
                        'region_type': region_type,
                        'use_cache': use_cache,
                        'ocr_available': OCR_AVAILABLE,
                        'image_dimensions': getattr(image, 'size', None) if hasattr(image, 'size') else None
                    }
                )
                
                # Generate image hash for caching
                image_hash = None
                if use_cache:
                    hash_start = time.time()
                    image_hash = self._generate_image_hash(image)
                    hash_time = time.time() - hash_start
                    
                    self.advanced_logger.debug(
                        f"Image hash generated in {hash_time*1000:.2f}ms",
                        extra_data={
                            'hash_generation_time_ms': hash_time * 1000,
                            'image_hash': image_hash[:16] + '...' if image_hash else None
                        }
                    )
                
                # Check cache first
                cache_hit = False
                if use_cache and image_hash:
                    cache_start = time.time()
                    cached_result = self.db.get_cached_ocr(image_hash)
                    cache_time = time.time() - cache_start
                    
                    if cached_result:
                        cache_hit = True
                        with self._lock:
                            self.stats['cache_hits'] += 1
                        
                        processing_time = time.time() - start_time
                        
                        self.advanced_logger.info(
                            f"OCR cache hit for {region_type}",
                            extra_data={
                                'cache_lookup_time_ms': cache_time * 1000,
                                'cached_text': cached_result['ocr_result'][:50] + '...' if len(cached_result['ocr_result']) > 50 else cached_result['ocr_result'],
                                'cached_confidence': cached_result['confidence_score'],
                                'total_processing_time_ms': processing_time * 1000
                            }
                        )
                        
                        # Finish performance tracking
                        self.performance_monitor.finish_operation(
                            trace_id, success=True,
                            operation_data={
                                'cache_hit': True,
                                'processing_time_ms': processing_time * 1000,
                                'confidence': cached_result['confidence_score']
                            }
                        )
                        
                        return OCRResult(
                            text=cached_result['ocr_result'],
                            confidence=cached_result['confidence_score'],
                            processing_time=processing_time,
                            region_type=region_type,
                            cached=True
                        )
                    else:
                        self.advanced_logger.debug(
                            f"OCR cache miss for {region_type}",
                            extra_data={'cache_lookup_time_ms': cache_time * 1000}
                        )
                
                # Perform OCR
                ocr_start = time.time()
                if not OCR_AVAILABLE:
                    # Fallback for when OCR is not available
                    self.advanced_logger.warning(
                        "OCR libraries not available - using simulation",
                        extra_data={'libraries_available': {'pytesseract': False, 'PIL': False}}
                    )
                    text = self._simulate_ocr(region_type)
                    confidence = 0.85
                    
                    self.advanced_logger.debug(
                        f"OCR simulation completed for {region_type}",
                        extra_data={
                            'simulated_text': text,
                            'simulated_confidence': confidence
                        }
                    )
                else:
                    text, confidence = self._execute_ocr(image, region_type)
                    
                ocr_time = time.time() - ocr_start
                processing_time = time.time() - start_time
                
                # Log OCR completion
                self.advanced_logger.info(
                    f"OCR completed for {region_type} in {ocr_time*1000:.2f}ms",
                    extra_data={
                        'ocr_processing_time_ms': ocr_time * 1000,
                        'total_processing_time_ms': processing_time * 1000,
                        'extracted_text': text[:100] + '...' if len(text) > 100 else text,
                        'confidence_score': confidence,
                        'text_length': len(text),
                        'cache_hit': cache_hit
                    }
                )
                
                # Cache result
                if use_cache and image_hash and confidence > 0.7:
                    cache_store_start = time.time()
                    self.db.cache_ocr_result(image_hash, text, confidence, region_type)
                    cache_store_time = time.time() - cache_store_start
                    
                    self.advanced_logger.debug(
                        f"OCR result cached for {region_type}",
                        extra_data={
                            'cache_store_time_ms': cache_store_time * 1000,
                            'confidence_threshold_met': confidence > 0.7
                        }
                    )
                elif use_cache and confidence <= 0.7:
                    self.advanced_logger.debug(
                        f"OCR result not cached due to low confidence: {confidence:.2f}",
                        extra_data={'confidence_threshold': 0.7}
                    )
                
                # Update stats
                with self._lock:
                    if use_cache and not cache_hit:
                        self.stats['cache_misses'] += 1
                    self.stats['ocr_operations'] += 1
                    self.stats['total_processing_time'] += processing_time
                    self.stats['avg_ocr_time'] = (
                        self.stats['total_processing_time'] / self.stats['ocr_operations']
                    )
                
                # Finish performance tracking
                self.performance_monitor.finish_operation(
                    trace_id, success=True,
                    operation_data={
                        'cache_hit': cache_hit,
                        'processing_time_ms': processing_time * 1000,
                        'ocr_time_ms': ocr_time * 1000,
                        'confidence': confidence,
                        'text_length': len(text)
                    }
                )
                
                return OCRResult(
                    text=text,
                    confidence=confidence,
                    processing_time=processing_time,
                    region_type=region_type,
                    cached=False
                )
                
            except ImportError as e:
                # Handle OCR library not available
                processing_time = time.time() - start_time
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='ocr_import_error',
                    user_data={
                        'region_type': region_type,
                        'missing_library': str(e),
                        'processing_time_ms': processing_time * 1000
                    },
                    system_state={'ocr_available': OCR_AVAILABLE},
                    timestamp=datetime.now(),
                    trace_id=trace_id
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.FALLBACK)
                
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                return OCRResult(
                    text="[OCR_UNAVAILABLE]",
                    confidence=0.0,
                    processing_time=processing_time,
                    region_type=region_type,
                    cached=False
                )
                
            except (OSError, IOError) as e:
                # Handle file/image I/O errors
                processing_time = time.time() - start_time
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='ocr_io_error',
                    user_data={
                        'region_type': region_type,
                        'error_type': type(e).__name__,
                        'processing_time_ms': processing_time * 1000
                    },
                    system_state={'image_hash': image_hash[:16] + '...' if image_hash else None},
                    timestamp=datetime.now(),
                    trace_id=trace_id
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.RETRY)
                
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                return OCRResult(
                    text="[IO_ERROR]",
                    confidence=0.0,
                    processing_time=processing_time,
                    region_type=region_type,
                    cached=False
                )
                
            except TimeoutError as e:
                # Handle OCR timeout
                processing_time = time.time() - start_time
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='ocr_timeout',
                    user_data={
                        'region_type': region_type,
                        'processing_time_ms': processing_time * 1000
                    },
                    system_state={'timeout_threshold_exceeded': True},
                    timestamp=datetime.now(),
                    trace_id=trace_id
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
                
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                return OCRResult(
                    text="[TIMEOUT]",
                    confidence=0.0,
                    processing_time=processing_time,
                    region_type=region_type,
                    cached=False
                )
                
            except Exception as e:
                # Handle all other unexpected OCR errors
                processing_time = time.time() - start_time
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='ocr_unexpected_error',
                    user_data={
                        'region_type': region_type,
                        'error_type': type(e).__name__,
                        'use_cache': use_cache,
                        'processing_time_ms': processing_time * 1000,
                        'image_available': image is not None
                    },
                    system_state={'ocr_available': OCR_AVAILABLE, 'image_hash': image_hash[:16] + '...' if image_hash else None},
                    timestamp=datetime.now(),
                    trace_id=trace_id
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.RETRY_WITH_BACKOFF)
                
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                # If recovery was successful, could potentially retry, but for now return error result
                return OCRResult(
                    text="[ERROR]",
                    confidence=0.0,
                    processing_time=processing_time,
                    region_type=region_type,
                    cached=False
                )
    
    def _execute_ocr(self, image: Any, region_type: str) -> Tuple[str, float]:
        """Execute actual OCR using pytesseract with comprehensive logging"""
        with self.advanced_logger.operation_context('vision_system', '_execute_ocr'):
            start_time = time.time()
            
            try:
                # Log OCR execution start
                self.advanced_logger.debug(
                    f"Starting pytesseract OCR execution for {region_type}",
                    extra_data={
                        'region_type': region_type,
                        'tesseract_available': OCR_AVAILABLE,
                        'image_available': image is not None
                    }
                )
                
                # Preprocess image
                preprocess_start = time.time()
                processed_image = self.preprocess_image(image, region_type)
                preprocess_time = time.time() - preprocess_start
                
                # Get OCR config for region type
                config = self.ocr_configs.get(region_type, self.ocr_configs['general'])
                
                self.advanced_logger.debug(
                    f"Using OCR config for {region_type}: {config}",
                    extra_data={
                        'config': config,
                        'preprocessing_time_ms': preprocess_time * 1000
                    }
                )
                
                # Perform OCR with timeout handling
                text_extraction_start = time.time()
                try:
                    # Set timeout for OCR operation (default 30 seconds)
                    ocr_timeout = getattr(self, 'ocr_timeout', 30)
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError(f"OCR operation timed out after {ocr_timeout} seconds")
                    
                    # Set timeout alarm for Unix systems
                    if hasattr(signal, 'SIGALRM'):
                        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(ocr_timeout)
                    
                    text = pytesseract.image_to_string(processed_image, config=config).strip()
                    
                    # Clear timeout alarm
                    if hasattr(signal, 'SIGALRM'):
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
                        
                except TimeoutError as timeout_e:
                    # Clear timeout alarm if it was set
                    if hasattr(signal, 'SIGALRM'):
                        signal.alarm(0)
                        if 'old_handler' in locals():
                            signal.signal(signal.SIGALRM, old_handler)
                    raise timeout_e
                    
                text_extraction_time = time.time() - text_extraction_start
                
                self.advanced_logger.debug(
                    f"Text extraction completed in {text_extraction_time*1000:.2f}ms",
                    extra_data={
                        'text_extraction_time_ms': text_extraction_time * 1000,
                        'extracted_text_length': len(text),
                        'text_preview': text[:100] + '...' if len(text) > 100 else text
                    }
                )
                
                # Get confidence (requires detailed output)
                confidence_start = time.time()
                confidence = 0.0
                confidence_method = "fallback"
                
                try:
                    # Apply timeout to confidence calculation as well
                    if hasattr(signal, 'SIGALRM'):
                        old_conf_handler = signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(ocr_timeout)
                    
                    data = pytesseract.image_to_data(processed_image, config=config, 
                                                   output_type=pytesseract.Output.DICT)
                    
                    # Clear timeout alarm
                    if hasattr(signal, 'SIGALRM'):
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_conf_handler)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    
                    if confidences:
                        confidence = sum(confidences) / len(confidences) / 100.0
                        confidence_method = "tesseract_detailed"
                        
                        self.advanced_logger.debug(
                            f"Confidence calculated from {len(confidences)} word(s)",
                            extra_data={
                                'confidence_values': confidences[:10],  # First 10 values
                                'avg_confidence': confidence,
                                'confidence_method': confidence_method
                            }
                        )
                    else:
                        confidence = 0.8 if text else 0.0
                        confidence_method = "fallback_with_text" if text else "fallback_empty"
                        
                except Exception as conf_e:
                    confidence = 0.8 if text else 0.0
                    confidence_method = "fallback_exception"
                    
                    self.advanced_logger.debug(
                        f"Confidence calculation failed, using fallback: {str(conf_e)}",
                        extra_data={
                            'confidence_error': str(conf_e),
                            'fallback_confidence': confidence,
                            'confidence_method': confidence_method
                        }
                    )
                
                confidence_time = time.time() - confidence_start
                total_time = time.time() - start_time
                
                # Log successful completion
                self.advanced_logger.info(
                    f"OCR execution completed for {region_type} in {total_time*1000:.2f}ms",
                    extra_data={
                        'total_time_ms': total_time * 1000,
                        'timing_breakdown': {
                            'preprocessing_ms': preprocess_time * 1000,
                            'text_extraction_ms': text_extraction_time * 1000,
                            'confidence_calculation_ms': confidence_time * 1000
                        },
                        'results': {
                            'text_length': len(text),
                            'confidence': confidence,
                            'confidence_method': confidence_method,
                            'text_preview': text[:50] + '...' if len(text) > 50 else text
                        },
                        'config_used': config
                    }
                )
                
                # Clean up processed image to prevent memory leak
                # Only clean up if processed_image is different from original image
                if processed_image is not image:
                    self.cleanup_image(processed_image)
                
                return text, confidence
                
            except pytesseract.pytesseract.TesseractNotFoundError as e:
                # Handle specific case where Tesseract binary is not found
                total_time = time.time() - start_time
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='ocr_tesseract_not_found',
                    user_data={
                        'region_type': region_type,
                        'error_message': str(e),
                        'processing_time_ms': total_time * 1000
                    },
                    system_state={
                        'tesseract_installed': False,
                        'ocr_fallback_available': True
                    },
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.FALLBACK)
                
                self.advanced_logger.error(
                    f"Tesseract binary not found for {region_type}. Please install Tesseract OCR.",
                    error=e,
                    extra_data={
                        'region_type': region_type,
                        'solution': 'Install Tesseract OCR binary and ensure it is in PATH',
                        'fallback_action': 'returning_empty_result',
                        'elapsed_time_ms': total_time * 1000
                    }
                )
                
                # Record critical error for tracking
                self.error_tracker.record_error(
                    'vision_system', '_execute_ocr_tesseract_not_found', e,
                    context={
                        'region_type': region_type,
                        'tesseract_installation_required': True
                    }
                )
                
                # Clean up processed image
                try:
                    if 'processed_image' in locals() and processed_image is not image:
                        self.cleanup_image(processed_image)
                except:
                    pass
                
                return "", 0.0
                
            except pytesseract.pytesseract.TesseractError as e:
                # Handle Tesseract processing errors (data files, config issues, etc.)
                total_time = time.time() - start_time
                
                error_context = ErrorContext(
                    component='vision_system',
                    operation='ocr_tesseract_processing_error',
                    user_data={
                        'region_type': region_type,
                        'tesseract_status': str(e),
                        'processing_time_ms': total_time * 1000
                    },
                    system_state={
                        'tesseract_config': self.ocr_configs.get(region_type, 'default'),
                        'recovery_strategy': 'retry_with_fallback_config'
                    },
                    timestamp=datetime.now()
                )
                
                recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.RETRY)
                
                self.advanced_logger.error(
                    f"Tesseract processing error for {region_type}: {str(e)}",
                    error=e,
                    extra_data={
                        'region_type': region_type,
                        'tesseract_status': str(e),
                        'config_used': self.ocr_configs.get(region_type, self.ocr_configs['general']),
                        'fallback_action': 'attempting_retry_with_basic_config',
                        'elapsed_time_ms': total_time * 1000
                    }
                )
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'vision_system', '_execute_ocr_tesseract_error', e,
                    context={
                        'region_type': region_type,
                        'tesseract_config': self.ocr_configs.get(region_type, 'default'),
                        'retry_attempted': True
                    }
                )
                
                # Try fallback with basic config
                try:
                    self.advanced_logger.info(f"Attempting OCR retry with basic config for {region_type}")
                    
                    # Apply timeout to fallback OCR as well
                    if hasattr(signal, 'SIGALRM'):
                        fallback_timeout = getattr(self, 'ocr_timeout', 30)
                        def fallback_timeout_handler(signum, frame):
                            raise TimeoutError(f"Fallback OCR operation timed out after {fallback_timeout} seconds")
                        
                        old_fallback_handler = signal.signal(signal.SIGALRM, fallback_timeout_handler)
                        signal.alarm(fallback_timeout)
                    
                    fallback_text = pytesseract.image_to_string(processed_image, config='').strip()
                    
                    # Clear timeout alarm
                    if hasattr(signal, 'SIGALRM'):
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_fallback_handler)
                    
                    # Clean up processed image
                    if processed_image is not image:
                        self.cleanup_image(processed_image)
                    
                    return fallback_text, 0.5  # Lower confidence due to fallback
                    
                except Exception as fallback_e:
                    self.advanced_logger.error(
                        f"Fallback OCR also failed for {region_type}: {str(fallback_e)}",
                        error=fallback_e
                    )
                
                # Clean up processed image
                try:
                    if 'processed_image' in locals() and processed_image is not image:
                        self.cleanup_image(processed_image)
                except:
                    pass
                
                return "", 0.0
                
            except Exception as e:
                # Handle all other unexpected errors
                total_time = time.time() - start_time
                
                self.advanced_logger.error(
                    f"Unexpected OCR execution error for {region_type}: {str(e)}",
                    error=e,
                    extra_data={
                        'region_type': region_type,
                        'error_type': type(e).__name__,
                        'tesseract_available': OCR_AVAILABLE,
                        'config': self.ocr_configs.get(region_type, self.ocr_configs['general']),
                        'elapsed_time_ms': total_time * 1000,
                        'fallback_action': 'returning_empty_result'
                    }
                )
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'vision_system', '_execute_ocr', e,
                    context={
                        'region_type': region_type,
                        'image_available': image is not None,
                        'tesseract_config': self.ocr_configs.get(region_type, 'default')
                    }
                )
                
                # Clean up processed image even in error case to prevent memory leak
                try:
                    if 'processed_image' in locals() and processed_image is not image:
                        self.cleanup_image(processed_image)
                except:
                    pass  # Don't let cleanup errors mask the original error
                
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
        """Generate hash for image caching with proper memory management"""
        buffer = None
        try:
            # Convert image to bytes
            if hasattr(image, 'tobytes'):
                image_bytes = image.tobytes()
            else:
                # Fallback for PIL images with proper buffer cleanup
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
            
            # Generate hash
            return hashlib.md5(image_bytes).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to generate image hash: {e}")
            return None
        finally:
            # Always clean up buffer to prevent memory leaks
            if buffer is not None:
                buffer.close()
                del buffer
    
    def cleanup_image(self, image: Any):
        """
        Clean up image resources to prevent memory leaks.
        Call this when done with an image to free memory immediately.
        """
        if image is None:
            return
        
        try:
            # Close PIL images
            if hasattr(image, 'close'):
                image.close()
            
            # Clean up numpy arrays
            if hasattr(image, '__array__'):
                del image
        except Exception as e:
            logger.debug(f"Error during image cleanup: {e}")
    
    def _create_dummy_image(self) -> Any:
        """Create dummy image for testing with cleanup awareness"""
        try:
            from PIL import Image
            dummy = Image.new('RGB', (100, 50), color='white')
            # Mark for cleanup awareness
            if hasattr(dummy, '_needs_cleanup'):
                dummy._needs_cleanup = True
            return dummy
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
        Complete pipeline: capture region, OCR, and parse with comprehensive logging
        Optimized for <1 second processing
        """
        # Start performance tracking for complete pipeline
        trace_id = self.performance_monitor.start_operation(
            'vision_system', 'capture_and_process',
            context={
                'region_name': region.name,
                'region_type': region_type,
                'region_area': region.width * region.height,
                'performance_target_ms': 1000
            }
        )
        
        with self.advanced_logger.operation_context('vision_system', 'capture_and_process_region'):
            total_start = time.time()
            
            try:
                # Log pipeline start
                self.advanced_logger.info(
                    f"Starting complete vision pipeline for region '{region.name}'",
                    extra_data={
                        'region': {
                            'name': region.name,
                            'coordinates': f"({region.x}, {region.y})",
                            'dimensions': f"{region.width}x{region.height}",
                            'area_pixels': region.width * region.height
                        },
                        'region_type': region_type,
                        'performance_target_ms': 1000
                    }
                )
                
                # Stage 1: Take screenshot
                screenshot_start = time.time()
                screenshot = self.take_screenshot(region)
                screenshot_time = time.time() - screenshot_start
                
                if screenshot is None:
                    self.advanced_logger.error(
                        f"Screenshot failed for region '{region.name}' - aborting pipeline",
                        extra_data={
                            'stage': 'screenshot',
                            'elapsed_time_ms': (time.time() - total_start) * 1000
                        }
                    )
                    
                    # Record error and finish tracking
                    self.error_tracker.record_error(
                        'vision_system', 'capture_and_process_region', 
                        Exception("Screenshot capture failed"),
                        context={'region_name': region.name, 'stage': 'screenshot'},
                        trace_id=trace_id
                    )
                    
                    self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                    return None
                
                self.advanced_logger.debug(
                    f"Screenshot captured in {screenshot_time*1000:.2f}ms",
                    extra_data={'screenshot_time_ms': screenshot_time * 1000}
                )
                
                # Stage 2: Perform OCR
                ocr_start = time.time()
                ocr_result = self.perform_ocr(screenshot, region_type)
                ocr_time = time.time() - ocr_start
                
                self.advanced_logger.debug(
                    f"OCR completed in {ocr_time*1000:.2f}ms",
                    extra_data={
                        'ocr_time_ms': ocr_time * 1000,
                        'confidence': ocr_result.confidence,
                        'text_preview': ocr_result.text[:50] + '...' if len(ocr_result.text) > 50 else ocr_result.text
                    }
                )
                
                # Stage 3: Parse result
                parse_start = time.time()
                parsed_data = self.parse_trader_data(ocr_result)
                parse_time = time.time() - parse_start
                
                total_time = time.time() - total_start
                
                # Log parsing results
                if parsed_data:
                    parsed_data['ocr_confidence'] = ocr_result.confidence
                    parsed_data['processing_time'] = total_time
                    
                    self.advanced_logger.info(
                        f"Data parsing successful for region '{region.name}'",
                        extra_data={
                            'parse_time_ms': parse_time * 1000,
                            'parsed_fields': list(parsed_data.keys()),
                            'data_preview': {k: str(v)[:50] for k, v in parsed_data.items() if k not in ['ocr_confidence', 'processing_time']}
                        }
                    )
                else:
                    self.advanced_logger.warning(
                        f"Data parsing failed for region '{region.name}' - no valid data extracted",
                        extra_data={
                            'parse_time_ms': parse_time * 1000,
                            'raw_ocr_text': ocr_result.text,
                            'confidence': ocr_result.confidence,
                            'region_type': region_type
                        }
                    )
                
                # Performance analysis
                performance_status = "EXCELLENT" if total_time < 0.5 else \
                                   "GOOD" if total_time < 1.0 else \
                                   "SLOW" if total_time < 2.0 else "CRITICAL"
                
                if total_time > 1.0:
                    self.advanced_logger.warning(
                        f"Slow region processing: {total_time*1000:.2f}ms for '{region.name}' (target: <1000ms)",
                        extra_data={
                            'performance_status': performance_status,
                            'total_time_ms': total_time * 1000,
                            'target_time_ms': 1000,
                            'breakdown': {
                                'screenshot_ms': screenshot_time * 1000,
                                'ocr_ms': ocr_time * 1000,
                                'parsing_ms': parse_time * 1000
                            }
                        }
                    )
                else:
                    self.advanced_logger.info(
                        f"Region processing completed successfully: {total_time*1000:.2f}ms for '{region.name}'",
                        extra_data={
                            'performance_status': performance_status,
                            'total_time_ms': total_time * 1000,
                            'breakdown': {
                                'screenshot_ms': screenshot_time * 1000,
                                'ocr_ms': ocr_time * 1000,
                                'parsing_ms': parse_time * 1000
                            },
                            'confidence': ocr_result.confidence,
                            'data_extracted': parsed_data is not None
                        }
                    )
                
                # Log testing output if enabled
                self.log_testing_output(ocr_result, region, parsed_data)
                
                # Finish performance tracking
                self.performance_monitor.finish_operation(
                    trace_id, success=True,
                    operation_data={
                        'total_time_ms': total_time * 1000,
                        'screenshot_time_ms': screenshot_time * 1000,
                        'ocr_time_ms': ocr_time * 1000,
                        'parse_time_ms': parse_time * 1000,
                        'confidence': ocr_result.confidence,
                        'data_extracted': parsed_data is not None,
                        'performance_status': performance_status
                    }
                )
                
                return parsed_data
                
            except Exception as e:
                # Comprehensive error logging
                total_time = time.time() - total_start
                
                self.advanced_logger.error(
                    f"Vision pipeline failed for region '{region.name}': {str(e)}",
                    error=e,
                    extra_data={
                        'region': {
                            'name': region.name,
                            'coordinates': f"({region.x}, {region.y})",
                            'dimensions': f"{region.width}x{region.height}"
                        },
                        'region_type': region_type,
                        'elapsed_time_ms': total_time * 1000,
                        'pipeline_stage': 'unknown'
                    }
                )
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'vision_system', 'capture_and_process_region', e,
                    context={
                        'region_name': region.name,
                        'region_type': region_type,
                        'region_area': region.width * region.height
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                return None
    
    def process_multiple_regions(self, regions: List[Tuple[ScreenRegion, str]]) -> List[Dict[str, Any]]:
        """
        Process multiple regions efficiently with comprehensive logging
        """
        # Start performance tracking for batch processing
        trace_id = self.performance_monitor.start_operation(
            'vision_system', 'process_multiple_regions',
            context={
                'region_count': len(regions),
                'region_names': [region.name for region, _ in regions]
            }
        )
        
        with self.advanced_logger.operation_context('vision_system', 'process_multiple_regions'):
            batch_start = time.time()
            results = []
            failed_regions = []
            
            try:
                # Log batch processing start
                self.advanced_logger.info(
                    f"Starting batch processing of {len(regions)} regions",
                    extra_data={
                        'region_count': len(regions),
                        'regions': [
                            {
                                'name': region.name,
                                'type': region_type,
                                'area': region.width * region.height
                            } for region, region_type in regions
                        ]
                    }
                )
                
                # Process each region
                for i, (region, region_type) in enumerate(regions):
                    region_start = time.time()
                    
                    self.advanced_logger.debug(
                        f"Processing region {i+1}/{len(regions)}: '{region.name}'",
                        extra_data={
                            'progress': f"{i+1}/{len(regions)}",
                            'region_name': region.name,
                            'region_type': region_type
                        }
                    )
                    
                    try:
                        result = self.capture_and_process_region(region, region_type)
                        region_time = time.time() - region_start
                        
                        if result:
                            result['region_name'] = region.name
                            results.append(result)
                            
                            self.advanced_logger.debug(
                                f"Region '{region.name}' processed successfully in {region_time*1000:.2f}ms",
                                extra_data={
                                    'region_processing_time_ms': region_time * 1000,
                                    'data_fields': list(result.keys()),
                                    'confidence': result.get('ocr_confidence', 0.0)
                                }
                            )
                        else:
                            failed_regions.append({
                                'name': region.name,
                                'type': region_type,
                                'processing_time_ms': region_time * 1000
                            })
                            
                            self.advanced_logger.warning(
                                f"Region '{region.name}' processing failed - no data extracted",
                                extra_data={
                                    'region_processing_time_ms': region_time * 1000,
                                    'region_type': region_type
                                }
                            )
                            
                    except Exception as e:
                        region_time = time.time() - region_start
                        failed_regions.append({
                            'name': region.name,
                            'type': region_type,
                            'processing_time_ms': region_time * 1000,
                            'error': str(e)
                        })
                        
                        self.advanced_logger.error(
                            f"Region '{region.name}' processing failed with error: {str(e)}",
                            error=e,
                            extra_data={
                                'region_processing_time_ms': region_time * 1000,
                                'region_type': region_type,
                                'progress': f"{i+1}/{len(regions)}"
                            }
                        )
                        
                        # Record individual region error
                        self.error_tracker.record_error(
                            'vision_system', 'process_multiple_regions_individual', e,
                            context={
                                'region_name': region.name,
                                'region_type': region_type,
                                'batch_position': f"{i+1}/{len(regions)}"
                            },
                            trace_id=trace_id
                        )
                
                total_time = time.time() - batch_start
                success_count = len(results)
                failure_count = len(failed_regions)
                success_rate = success_count / len(regions) if regions else 0.0
                
                # Log batch completion summary
                if success_count > 0:
                    avg_confidence = sum(r.get('ocr_confidence', 0.0) for r in results) / success_count
                    avg_processing_time = sum(r.get('processing_time', 0.0) for r in results) / success_count
                else:
                    avg_confidence = 0.0
                    avg_processing_time = 0.0
                
                self.advanced_logger.info(
                    f"Batch processing completed: {success_count}/{len(regions)} regions successful",
                    extra_data={
                        'batch_summary': {
                            'total_regions': len(regions),
                            'successful_regions': success_count,
                            'failed_regions': failure_count,
                            'success_rate': success_rate,
                            'total_time_ms': total_time * 1000,
                            'avg_region_time_ms': (total_time / len(regions) * 1000) if regions else 0.0,
                            'avg_confidence': avg_confidence,
                            'avg_processing_time_ms': avg_processing_time * 1000
                        },
                        'failed_region_names': [f['name'] for f in failed_regions]
                    }
                )
                
                # Log performance warnings if needed
                if success_rate < 0.8:
                    self.advanced_logger.warning(
                        f"Low batch success rate: {success_rate:.1%}",
                        extra_data={'failed_regions': failed_regions}
                    )
                
                if total_time > len(regions) * 1.5:  # More than 1.5s per region on average
                    self.advanced_logger.warning(
                        f"Slow batch processing: {total_time:.2f}s for {len(regions)} regions",
                        extra_data={
                            'avg_time_per_region_ms': (total_time / len(regions) * 1000) if regions else 0.0,
                            'performance_target_ms': 1000
                        }
                    )
                
                # Finish performance tracking
                self.performance_monitor.finish_operation(
                    trace_id, success=True,
                    operation_data={
                        'total_time_ms': total_time * 1000,
                        'regions_processed': len(regions),
                        'successful_regions': success_count,
                        'failed_regions': failure_count,
                        'success_rate': success_rate,
                        'avg_confidence': avg_confidence,
                        'avg_processing_time_ms': avg_processing_time * 1000
                    }
                )
                
                return results
                
            except Exception as e:
                # Comprehensive batch error logging
                total_time = time.time() - batch_start
                
                self.advanced_logger.error(
                    f"Batch processing failed: {str(e)}",
                    error=e,
                    extra_data={
                        'total_regions': len(regions),
                        'processed_count': len(results),
                        'elapsed_time_ms': total_time * 1000,
                        'partial_results': len(results) > 0
                    }
                )
                
                # Record batch error for tracking
                self.error_tracker.record_error(
                    'vision_system', 'process_multiple_regions_batch', e,
                    context={
                        'region_count': len(regions),
                        'processed_count': len(results),
                        'failed_count': len(failed_regions)
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                # Return partial results even on error
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
    
    def enable_testing_output(self, enabled: bool = True):
        """Enable or disable testing output to console and files"""
        self.testing_enabled = enabled
        if enabled:
            logger.info("Testing output enabled - OCR results will be logged to console and files")
            # Initialize testing output file
            with open(self.testing_output_file, 'w', encoding='utf-8') as f:
                f.write(f"OCR Testing Output - Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
        else:
            logger.info("Testing output disabled")
    
    def log_testing_output(self, ocr_result: OCRResult, region: ScreenRegion, parsed_data: Optional[Dict[str, Any]] = None):
        """Log OCR testing results to console and file"""
        if not self.testing_enabled:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Console output
        print("\n" + "=" * 60)
        print(f"📊 OCR TEST RESULT [{timestamp}]")
        print("=" * 60)
        print(f"🎯 Region: {region.name} ({region.x}, {region.y}) {region.width}x{region.height}")
        print(f"📝 Region Type: {ocr_result.region_type}")
        print(f"⚡ Processing Time: {ocr_result.processing_time:.3f}s")
        print(f"🎯 Confidence: {ocr_result.confidence:.2f}")
        print(f"📋 Cached: {'Yes' if ocr_result.cached else 'No'}")
        print(f"📄 Raw OCR Text: '{ocr_result.text}'")
        
        if parsed_data:
            print("✅ Parsed Data:")
            for key, value in parsed_data.items():
                print(f"   {key}: {value}")
        else:
            print("❌ No valid data parsed")
        
        print("=" * 60 + "\n")
        
        # File output (simple text)
        try:
            with open(self.testing_output_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] Region: {region.name} | Type: {ocr_result.region_type}\n")
                f.write(f"   Text: '{ocr_result.text}' | Confidence: {ocr_result.confidence:.2f} | Time: {ocr_result.processing_time:.3f}s\n")
                if parsed_data:
                    f.write(f"   Parsed: {parsed_data}\n")
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write to testing output file: {e}")
        
        # Detailed JSON output
        try:
            detailed_result = {
                'timestamp': datetime.now().isoformat(),
                'region': {
                    'name': region.name,
                    'x': region.x,
                    'y': region.y,
                    'width': region.width,
                    'height': region.height
                },
                'ocr': {
                    'text': ocr_result.text,
                    'confidence': ocr_result.confidence,
                    'processing_time': ocr_result.processing_time,
                    'region_type': ocr_result.region_type,
                    'cached': ocr_result.cached
                },
                'parsed_data': parsed_data or {}
            }
            
            # Append to JSON lines file
            with open(self.testing_detailed_file, 'a', encoding='utf-8') as f:
                json.dump(detailed_result, f, ensure_ascii=False)
                f.write('\n')
                
        except Exception as e:
            logger.error(f"Failed to write detailed testing output: {e}")
    
    def clear_testing_output(self):
        """Clear testing output files"""
        try:
            if self.testing_output_file.exists():
                self.testing_output_file.unlink()
            if self.testing_detailed_file.exists():
                self.testing_detailed_file.unlink()
            logger.info("Testing output files cleared")
        except Exception as e:
            logger.error(f"Failed to clear testing output files: {e}")
    
    def get_testing_summary(self) -> Dict[str, Any]:
        """Get summary of testing results"""
        summary = {
            'testing_enabled': self.testing_enabled,
            'output_file': str(self.testing_output_file),
            'detailed_file': str(self.testing_detailed_file),
            'output_file_exists': self.testing_output_file.exists(),
            'detailed_file_exists': self.testing_detailed_file.exists()
        }
        
        # Count lines in output file
        try:
            if self.testing_output_file.exists():
                with open(self.testing_output_file, 'r', encoding='utf-8') as f:
                    summary['total_tests'] = len([line for line in f if line.startswith('[')])
        except:
            summary['total_tests'] = 0
        
        return summary

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