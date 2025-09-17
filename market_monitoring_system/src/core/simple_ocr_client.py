"""
Simplified Yandex OCR client based on working YANDEX_OCR.py implementation.
Uses only OCR API format without dual API complexity.
"""

import base64
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError as e:
    REQUESTS_AVAILABLE = False
    REQUESTS_ERROR = str(e)

from config.settings import SettingsManager


class SimpleOCRError(Exception):
    """Exception raised for OCR processing errors."""
    pass


class SimpleYandexOCRClient:
    """
    Simplified Yandex OCR client using only working OCR API format.
    Based on proven YANDEX_OCR.py implementation.
    """
    
    # API response status codes
    STATUS_SUCCESS = 200
    STATUS_BAD_REQUEST = 400
    STATUS_UNAUTHORIZED = 401
    STATUS_FORBIDDEN = 403
    STATUS_TOO_MANY_REQUESTS = 429
    STATUS_INTERNAL_ERROR = 500
    STATUS_SERVICE_UNAVAILABLE = 503
    
    # Retryable status codes
    RETRYABLE_CODES = {STATUS_TOO_MANY_REQUESTS, STATUS_INTERNAL_ERROR, STATUS_SERVICE_UNAVAILABLE}
    
    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 3):
        """
        Initialize simplified OCR client.
        
        Args:
            api_key: Yandex OCR API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        if not REQUESTS_AVAILABLE:
            raise SimpleOCRError(f"Requests library not available: {REQUESTS_ERROR}")
        
        if not api_key or api_key == "your_api_key_here":
            raise SimpleOCRError("Valid Yandex OCR API key is required")
        
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # OCR API endpoint (not Vision API)
        self.ocr_url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Api-Key {self.api_key}',
            'User-Agent': 'MarketMonitoring-SimpleOCR/1.0'
        })
        
        # MIME type mapping (from YANDEX_OCR.py)
        self.mime_types = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG', 
            '.png': 'PNG',
            '.pdf': 'PDF'
        }
        
        # Processing statistics
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'total_processing_time': 0.0,
            'average_response_time': 0.0,
            'last_request_time': None,
            'rate_limit_hits': 0,
            'api_errors': {}
        }
        
        self.logger.info(f"Simple OCR client initialized")
    
    def _get_mime_type(self, image_path: Path) -> str:
        """Get MIME type from file extension."""
        ext = image_path.suffix.lower()
        return self.mime_types.get(ext, 'JPEG')
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64."""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            raise SimpleOCRError(f"Failed to encode image {image_path}: {e}")
    
    def _prepare_ocr_request(self, image_path: Path, language_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Prepare OCR API request payload (proven format from YANDEX_OCR.py).
        
        Args:
            image_path: Path to image file
            language_codes: Optional language codes
            
        Returns:
            Request payload dictionary
        """
        try:
            # Encode image
            image_base64 = self._encode_image(image_path)
            
            # Get MIME type
            mime_type = self._get_mime_type(image_path)
            
            # Prepare OCR API request (exact format from working YANDEX_OCR.py)
            payload = {
                "mimeType": mime_type,
                "languageCodes": language_codes or ["en"],
                "model": "page",
                "content": image_base64
            }
            
            return payload
            
        except Exception as e:
            raise SimpleOCRError(f"Failed to prepare OCR request: {e}")
    
    def process_image_full_pipeline(self, image_path: Path, 
                                  cleanup_image: bool = True,
                                  language_codes: Optional[List[str]] = None) -> Optional[str]:
        """
        Full pipeline: send image for OCR and extract text.
        
        Args:
            image_path: Path to image file
            cleanup_image: Whether to delete image after processing
            language_codes: Optional language codes
            
        Returns:
            Extracted text or None if failed
        """
        if not image_path.exists():
            self.logger.error(f"Image file not found: {image_path}")
            return None
        
        start_time = time.time()
        session_id = uuid.uuid4().hex[:8]
        
        try:
            # Check file size
            file_size_mb = image_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 20:  # 20MB limit
                raise SimpleOCRError(f"Image file too large: {file_size_mb:.1f}MB (max: 20MB)")
            
            self.logger.info(f"Starting OCR request {session_id} for {image_path.name} ({file_size_mb:.1f}MB)")
            
            # Prepare request
            payload = self._prepare_ocr_request(image_path, language_codes)
            
            # Send request
            response = self.session.post(
                self.ocr_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == self.STATUS_SUCCESS:
                # Process successful response
                response_data = response.json()
                result = response_data.get('result', {})
                text_annotation = result.get('textAnnotation', {})
                extracted_text = text_annotation.get('fullText', '')
                
                if extracted_text:
                    extracted_text = extracted_text.strip()
                    
                    # Update statistics
                    processing_time = time.time() - start_time
                    self._stats['successful_requests'] += 1
                    self._stats['total_processing_time'] += processing_time
                    
                    self.logger.info(f"OCR request {session_id} completed successfully in {processing_time:.3f}s")
                    
                    # Cleanup image if requested
                    if cleanup_image:
                        try:
                            image_path.unlink()
                            self.logger.debug(f"Cleaned up processed image: {image_path.name}")
                        except Exception as e:
                            self.logger.warning(f"Failed to cleanup image {image_path}: {e}")
                    
                    return extracted_text
                else:
                    self.logger.warning("No text found in OCR response")
                    return None
            else:
                self.logger.error(f"OCR API error: HTTP {response.status_code}: {response.text[:200]}")
                self._stats['failed_requests'] += 1
                return None
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._stats['failed_requests'] += 1
            self.logger.error(f"OCR request {session_id} failed: {e} (failed after {processing_time:.3f}s)")
            return None
        finally:
            self._stats['total_requests'] += 1
            self._stats['last_request_time'] = datetime.now().isoformat()
    
    def get_ocr_statistics(self) -> Dict[str, Any]:
        """Get OCR processing statistics."""
        stats = self._stats.copy()
        
        # Calculate success rates
        total_requests = stats['total_requests']
        if total_requests > 0:
            stats['success_rate'] = stats['successful_requests'] / total_requests
            stats['failure_rate'] = stats['failed_requests'] / total_requests
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Add configuration summary
        stats['config_summary'] = {
            'api_url': self.ocr_url,
            'timeout': self.timeout,
            'max_retries': self.max_retries
        }
        
        return stats
    
    def test_api_connection(self) -> bool:
        """
        Test OCR API connection and authentication.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Create a minimal test image (1x1 white pixel PNG)
            test_image_data = base64.b64encode(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0bIDATx\x9cc```\x00\x00\x00\x04\x00\x01]\xcc\xdb\x8d\x00\x00\x00\x00IEND\xaeB`\x82'
            ).decode('utf-8')
            
            payload = {
                "mimeType": "PNG",
                "languageCodes": ["en"],
                "model": "page",
                "content": test_image_data
            }
            
            response = self.session.post(
                self.ocr_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [self.STATUS_SUCCESS, self.STATUS_BAD_REQUEST]:
                self.logger.info("OCR API connection test successful")
                return True
            else:
                self.logger.error(f"OCR API connection test failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"OCR API connection test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the OCR client and clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
        self.logger.info("Simple OCR client closed")