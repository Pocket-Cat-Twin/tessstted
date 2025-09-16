"""
Yandex OCR client for market monitoring system.
Handles image recognition requests with retry logic and error handling.
"""

import base64
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError as e:
    REQUESTS_AVAILABLE = False
    REQUESTS_ERROR = str(e)

from config.settings import SettingsManager, YandexOCRConfig


class OCRError(Exception):
    """Exception raised for OCR processing errors."""
    pass


class YandexOCRClient:
    """
    Client for Yandex Cloud OCR API.
    Handles image recognition with retry logic, error handling, and rate limiting.
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
    
    def __init__(self, settings_manager: SettingsManager):
        """
        Initialize Yandex OCR client.
        
        Args:
            settings_manager: Configuration manager instance
        """
        if not REQUESTS_AVAILABLE:
            raise OCRError(f"Requests library not available: {REQUESTS_ERROR}")
        
        self.settings = settings_manager
        self.config: YandexOCRConfig = settings_manager.yandex_ocr
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        if not self.config or not self.config.api_key or self.config.api_key == "your_api_key_here":
            raise OCRError("Yandex OCR API key not configured")
        
        # Session for connection reuse
        self.session = requests.Session()
        
        # Set authorization header based on primary auth method
        auth_header = self._get_auth_header(self.config.primary_auth_method)
        self.session.headers.update({
            'Authorization': auth_header,
            'Content-Type': 'application/json',
            'User-Agent': 'MarketMonitoring/1.0'
        })
        
        self.logger.info(f"OCR client initialized with {self.config.primary_auth_method} auth, {self.config.primary_api_format} format")
        
        # Processing statistics (enhanced for dual API tracking)
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'total_processing_time': 0.0,
            'average_response_time': 0.0,
            'last_request_time': None,
            'rate_limit_hits': 0,
            'api_errors': {},
            # Dual API tracking
            'ocr_api_requests': 0,
            'ocr_api_successes': 0,
            'vision_api_requests': 0,
            'vision_api_successes': 0,
            'fallback_usage': 0,
            'api_key_auth_requests': 0,
            'bearer_auth_requests': 0
        }
    
    def _get_auth_header(self, auth_method: str) -> str:
        """
        Generate authentication header based on method.
        
        Args:
            auth_method: 'api_key' or 'bearer'
            
        Returns:
            Authentication header string
        """
        if auth_method == "api_key":
            return f'Api-Key {self.config.api_key}'
        elif auth_method == "bearer":
            return f'Bearer {self.config.api_key}'
        else:
            self.logger.warning(f"Unknown auth method '{auth_method}', using api_key")
            return f'Api-Key {self.config.api_key}'
    
    def send_image_for_recognition(self, image_path: Path, 
                                 language_codes: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Send image to Yandex OCR API for text recognition.
        
        Args:
            image_path: Path to image file
            language_codes: Optional list of language codes (e.g., ['ru', 'en'])
            
        Returns:
            OCR response dictionary or None if failed
        """
        if not image_path.exists():
            self.logger.error(f"Image file not found: {image_path}")
            return None
        
        start_time = time.time()
        session_id = uuid.uuid4().hex[:8]
        
        try:
            # Validate image file size
            file_size_mb = image_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.max_image_size_mb:
                raise OCRError(
                    f"Image file too large: {file_size_mb:.1f}MB "
                    f"(max: {self.config.max_image_size_mb}MB)"
                )
            
            self.logger.info(f"Starting OCR request {session_id} for {image_path.name} ({file_size_mb:.1f}MB)")
            
            # Try dual API approach with fallback
            response = self._send_dual_api_request(image_path, language_codes, session_id)
            
            if response:
                # Update statistics
                processing_time = time.time() - start_time
                self._update_success_stats(processing_time)
                
                self.logger.info(
                    f"OCR request {session_id} completed successfully in {processing_time:.3f}s"
                )
                
                return response
            else:
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
    
    def _prepare_vision_request(self, image_path: Path, 
                              language_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Prepare Vision API request payload (legacy format).
        
        Args:
            image_path: Path to image file
            language_codes: Optional language codes
            
        Returns:
            Request payload dictionary for Vision API
        """
        try:
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare request payload
            payload = {
                "folderId": "your_folder_id",  # This should be configured
                "analyze": {
                    "content": image_base64,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "textDetectionConfig": {
                            "languageCodes": language_codes or ["ru", "en"]
                        }
                    }]
                }
            }
            
            return payload
            
        except Exception as e:
            raise OCRError(f"Failed to prepare Vision API request: {e}")
    
    def _prepare_ocr_request(self, image_path: Path, 
                           language_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Prepare OCR API request payload (simplified format from YANDEX_OCR.py).
        
        Args:
            image_path: Path to image file
            language_codes: Optional language codes
            
        Returns:
            Request payload dictionary for OCR API
        """
        try:
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get MIME type from file extension
            mime_type = self._get_mime_type(image_path)
            
            # Prepare OCR API request payload (from YANDEX_OCR.py format)
            payload = {
                "mimeType": mime_type,
                "languageCodes": language_codes or ["en"],
                "model": "page",
                "content": image_base64
            }
            
            return payload
            
        except Exception as e:
            raise OCRError(f"Failed to prepare OCR API request: {e}")
    
    def _get_mime_type(self, image_path: Path) -> str:
        """
        Get MIME type from file extension using configuration.
        
        Args:
            image_path: Path to image file
            
        Returns:
            MIME type string
        """
        ext = image_path.suffix.lower()
        return self.config.mime_types.get(ext, 'JPEG')
    
    def _prepare_request_payload(self, image_path: Path, api_format: str,
                               language_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Prepare request payload based on API format.
        
        Args:
            image_path: Path to image file
            api_format: 'ocr' or 'vision'
            language_codes: Optional language codes
            
        Returns:
            Request payload dictionary
        """
        if api_format == "ocr":
            return self._prepare_ocr_request(image_path, language_codes)
        elif api_format == "vision":
            return self._prepare_vision_request(image_path, language_codes)
        else:
            raise OCRError(f"Unknown API format: {api_format}")
    
    def _send_dual_api_request(self, image_path: Path, 
                             language_codes: Optional[List[str]], 
                             session_id: str) -> Optional[Dict[str, Any]]:
        """
        Send request using dual API approach with fallback.
        
        Args:
            image_path: Path to image file
            language_codes: Optional language codes
            session_id: Session identifier for logging
            
        Returns:
            OCR response or None if failed
        """
        # Try primary API format first
        primary_format = self.config.primary_api_format
        primary_auth = self.config.primary_auth_method
        
        self.logger.info(f"Trying primary API: {primary_format} format with {primary_auth} auth")
        
        try:
            # Prepare payload for primary format
            payload = self._prepare_request_payload(image_path, primary_format, language_codes)
            
            # Update auth header for primary method
            auth_header = self._get_auth_header(primary_auth)
            original_auth = self.session.headers.get('Authorization')
            self.session.headers['Authorization'] = auth_header
            
            # Track primary API attempt
            self._track_api_attempt(primary_format, primary_auth)
            
            # Send request with primary API
            response = self._send_request_with_retry_to_url(
                payload, self.config.api_url, session_id, f"primary-{primary_format}"
            )
            
            if response:
                # Success with primary API
                self._track_api_success(primary_format, primary_auth)
                self.logger.info(f"Primary API ({primary_format}) succeeded")
                return response
            
        except Exception as e:
            self.logger.warning(f"Primary API ({primary_format}) failed: {e}")
        finally:
            # Restore original auth header
            if 'original_auth' in locals() and original_auth:
                self.session.headers['Authorization'] = original_auth
        
        # Try fallback API if enabled and primary failed
        if not self.config.enable_fallback:
            self.logger.info("Fallback disabled, primary API failed")
            return None
            
        fallback_format = self.config.fallback_api_format
        fallback_auth = self.config.fallback_auth_method
        fallback_url = self.config.fallback_api_url
        
        self.logger.info(f"Trying fallback API: {fallback_format} format with {fallback_auth} auth")
        self._stats['fallback_usage'] += 1
        
        try:
            # Prepare payload for fallback format
            payload = self._prepare_request_payload(image_path, fallback_format, language_codes)
            
            # Update auth header for fallback method
            auth_header = self._get_auth_header(fallback_auth)
            original_auth = self.session.headers.get('Authorization')
            self.session.headers['Authorization'] = auth_header
            
            # Track fallback API attempt
            self._track_api_attempt(fallback_format, fallback_auth)
            
            # Send request with fallback API
            response = self._send_request_with_retry_to_url(
                payload, fallback_url, session_id, f"fallback-{fallback_format}"
            )
            
            if response:
                # Success with fallback API
                self._track_api_success(fallback_format, fallback_auth)
                self.logger.info(f"Fallback API ({fallback_format}) succeeded")
                return response
            else:
                self.logger.error(f"Fallback API ({fallback_format}) also failed")
                
        except Exception as e:
            self.logger.error(f"Fallback API ({fallback_format}) failed: {e}")
        finally:
            # Restore original auth header
            if 'original_auth' in locals() and original_auth:
                self.session.headers['Authorization'] = original_auth
        
        # Both APIs failed
        return None
    
    def _track_api_attempt(self, api_format: str, auth_method: str) -> None:
        """Track API attempt in statistics."""
        if api_format == "ocr":
            self._stats['ocr_api_requests'] += 1
        elif api_format == "vision":
            self._stats['vision_api_requests'] += 1
            
        if auth_method == "api_key":
            self._stats['api_key_auth_requests'] += 1
        elif auth_method == "bearer":
            self._stats['bearer_auth_requests'] += 1
    
    def _track_api_success(self, api_format: str, auth_method: str) -> None:
        """Track API success in statistics."""
        if api_format == "ocr":
            self._stats['ocr_api_successes'] += 1
        elif api_format == "vision":
            self._stats['vision_api_successes'] += 1
    
    def _send_request_with_retry_to_url(self, payload: Dict[str, Any], 
                                      url: str, session_id: str, 
                                      api_type: str) -> Optional[Dict[str, Any]]:
        """
        Send request to specific URL with retry logic.
        
        Args:
            payload: Request payload
            url: Target URL
            session_id: Session identifier for logging
            api_type: API type for logging (e.g., "primary-ocr", "fallback-vision")
            
        Returns:
            OCR response or None if failed
        """
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Retry {attempt} for {api_type} request {session_id}")
                    time.sleep(self.config.retry_delay * attempt)  # Exponential backoff
                    self._stats['retry_attempts'] += 1
                
                # Send request
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout
                )
                
                # Handle different response codes
                if response.status_code == self.STATUS_SUCCESS:
                    return self._process_successful_response(response)
                
                elif response.status_code in self.RETRYABLE_CODES:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    
                    if response.status_code == self.STATUS_TOO_MANY_REQUESTS:
                        self._stats['rate_limit_hits'] += 1
                        # Longer delay for rate limiting
                        time.sleep(self.config.retry_delay * 2)
                    
                    self.logger.warning(f"Retryable error for {api_type} {session_id}: {last_error}")
                    continue
                
                else:
                    # Non-retryable error
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    self._record_api_error(response.status_code, error_msg)
                    self.logger.error(f"Non-retryable error for {api_type} {session_id}: {error_msg}")
                    return None
                
            except requests.exceptions.Timeout:
                last_error = f"Request timeout after {self.config.timeout}s"
                self.logger.warning(f"Timeout for {api_type} {session_id} (attempt {attempt + 1})")
                
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)[:200]}"
                self.logger.warning(f"Connection error for {api_type} {session_id}: {last_error}")
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)[:200]}"
                self.logger.error(f"Unexpected error for {api_type} {session_id}: {last_error}")
                break  # Don't retry for unexpected errors
        
        # All attempts failed
        self.logger.error(f"{api_type.title()} request {session_id} failed after {self.config.max_retries + 1} attempts. Last error: {last_error}")
        return None
    
    def _send_request_with_retry(self, payload: Dict[str, Any], 
                               session_id: str) -> Optional[Dict[str, Any]]:
        """
        Send request with retry logic (legacy method for backward compatibility).
        
        Args:
            payload: Request payload
            session_id: Session identifier for logging
            
        Returns:
            OCR response or None if failed
        """
        # Call new URL-specific method with default API URL for backward compatibility
        return self._send_request_with_retry_to_url(
            payload, self.config.api_url, session_id, "legacy"
        )
    
    def _process_successful_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Process successful OCR response.
        
        Args:
            response: HTTP response from OCR API
            
        Returns:
            Processed response data
        """
        try:
            response_data = response.json()
            
            # Validate response structure
            if 'result' not in response_data:
                raise OCRError("Invalid response structure: missing 'result' field")
            
            return response_data
            
        except json.JSONDecodeError as e:
            raise OCRError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise OCRError(f"Failed to process successful response: {e}")
    
    def _extract_text_from_vision_response(self, api_response: Dict[str, Any]) -> str:
        """
        Extract text content from Vision API response (legacy format).
        
        Args:
            api_response: Vision API response dictionary
            
        Returns:
            Extracted text content
        """
        try:
            text_blocks = []
            
            # Navigate response structure
            result = api_response.get('result', {})
            text_annotation = result.get('textAnnotation', {})
            blocks = text_annotation.get('blocks', [])
            
            # Extract text from blocks
            for block in blocks:
                for line in block.get('lines', []):
                    for word in line.get('words', []):
                        text = word.get('text', '').strip()
                        if text:
                            text_blocks.append(text)
            
            # Join with spaces
            extracted_text = ' '.join(text_blocks)
            
            self.logger.debug(f"Extracted {len(extracted_text)} characters from OCR response")
            return extracted_text
            
        except Exception as e:
            self.logger.error(f"Failed to extract text from Vision API response: {e}")
            return ""
    
    def _extract_text_from_ocr_response(self, api_response: Dict[str, Any]) -> str:
        """
        Extract text content from OCR API response (YANDEX_OCR.py format).
        
        Args:
            api_response: OCR API response dictionary
            
        Returns:
            Extracted text content
        """
        try:
            # OCR API has simpler structure: result.textAnnotation.fullText
            result = api_response.get('result', {})
            text_annotation = result.get('textAnnotation', {})
            extracted_text = text_annotation.get('fullText', '')
            
            if extracted_text:
                extracted_text = extracted_text.strip()
                self.logger.debug(f"Extracted {len(extracted_text)} characters from OCR API response")
                return extracted_text
            else:
                self.logger.warning("No fullText found in OCR API response")
                return ""
                
        except Exception as e:
            self.logger.error(f"Failed to extract text from OCR API response: {e}")
            return ""
    
    def extract_text_from_response(self, api_response: Dict[str, Any]) -> str:
        """
        Extract text content from API response (auto-detect format).
        
        Args:
            api_response: API response dictionary
            
        Returns:
            Extracted text content
        """
        try:
            # Try OCR API format first (simpler structure)
            if self._is_ocr_api_response(api_response):
                self.logger.debug("Detected OCR API response format")
                return self._extract_text_from_ocr_response(api_response)
            else:
                self.logger.debug("Using Vision API response format")
                return self._extract_text_from_vision_response(api_response)
                
        except Exception as e:
            self.logger.error(f"Failed to extract text from API response: {e}")
            return ""
    
    def _is_ocr_api_response(self, api_response: Dict[str, Any]) -> bool:
        """
        Detect if response is from OCR API or Vision API.
        
        Args:
            api_response: API response dictionary
            
        Returns:
            True if OCR API format, False if Vision API format
        """
        try:
            result = api_response.get('result', {})
            text_annotation = result.get('textAnnotation', {})
            
            # OCR API has 'fullText' field, Vision API has 'blocks' field
            has_full_text = 'fullText' in text_annotation
            has_blocks = 'blocks' in text_annotation
            
            if has_full_text and not has_blocks:
                return True  # OCR API format
            elif has_blocks and not has_full_text:
                return False  # Vision API format
            elif has_full_text and has_blocks:
                # Both present, prefer OCR format
                self.logger.debug("Response has both fullText and blocks, using OCR format")
                return True
            else:
                # Neither present, default to Vision format for backward compatibility
                self.logger.warning("Response format unclear, defaulting to Vision API format")
                return False
                
        except Exception as e:
            self.logger.error(f"Error detecting response format: {e}")
            return False  # Default to Vision API format
    
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
        try:
            # Send for OCR
            response = self.send_image_for_recognition(image_path, language_codes)
            if not response:
                return None
            
            # Extract text
            extracted_text = self.extract_text_from_response(response)
            
            # Cleanup image if requested
            if cleanup_image:
                try:
                    image_path.unlink()
                    self.logger.debug(f"Cleaned up processed image: {image_path.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup image {image_path}: {e}")
            
            return extracted_text if extracted_text else None
            
        except Exception as e:
            self.logger.error(f"Full OCR pipeline failed for {image_path}: {e}")
            return None
    
    def _update_success_stats(self, processing_time: float) -> None:
        """Update statistics for successful request."""
        self._stats['successful_requests'] += 1
        self._stats['total_processing_time'] += processing_time
        
        # Update average response time
        success_count = self._stats['successful_requests']
        current_avg = self._stats['average_response_time']
        self._stats['average_response_time'] = (
            (current_avg * (success_count - 1) + processing_time) / success_count
        )
    
    def _record_api_error(self, status_code: int, error_message: str) -> None:
        """Record API error in statistics."""
        if status_code not in self._stats['api_errors']:
            self._stats['api_errors'][status_code] = {
                'count': 0,
                'last_error': None,
                'last_occurrence': None
            }
        
        self._stats['api_errors'][status_code]['count'] += 1
        self._stats['api_errors'][status_code]['last_error'] = error_message
        self._stats['api_errors'][status_code]['last_occurrence'] = datetime.now().isoformat()
    
    def handle_api_errors(self, response: requests.Response) -> str:
        """
        Handle and categorize API errors.
        
        Args:
            response: HTTP response object
            
        Returns:
            Error description string
        """
        status_code = response.status_code
        
        error_descriptions = {
            self.STATUS_BAD_REQUEST: "Bad request - check image format and size",
            self.STATUS_UNAUTHORIZED: "Unauthorized - check API key",
            self.STATUS_FORBIDDEN: "Forbidden - check API permissions",
            self.STATUS_TOO_MANY_REQUESTS: "Rate limit exceeded - will retry",
            self.STATUS_INTERNAL_ERROR: "Internal server error - will retry",
            self.STATUS_SERVICE_UNAVAILABLE: "Service unavailable - will retry"
        }
        
        description = error_descriptions.get(
            status_code, 
            f"Unknown error (HTTP {status_code})"
        )
        
        try:
            error_details = response.json().get('message', 'No details available')
            description += f" - {error_details}"
        except:
            description += f" - {response.text[:100]}"
        
        return description
    
    def get_ocr_statistics(self) -> Dict[str, Any]:
        """
        Get OCR processing statistics.
        
        Returns:
            Dictionary with OCR statistics
        """
        stats = self._stats.copy()
        
        # Calculate overall success rates
        total_requests = stats['total_requests']
        if total_requests > 0:
            stats['success_rate'] = stats['successful_requests'] / total_requests
            stats['failure_rate'] = stats['failed_requests'] / total_requests
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Calculate OCR API success rates
        ocr_requests = stats['ocr_api_requests']
        if ocr_requests > 0:
            stats['ocr_api_success_rate'] = stats['ocr_api_successes'] / ocr_requests
            stats['ocr_api_failure_rate'] = (ocr_requests - stats['ocr_api_successes']) / ocr_requests
        else:
            stats['ocr_api_success_rate'] = 0.0
            stats['ocr_api_failure_rate'] = 0.0
        
        # Calculate Vision API success rates
        vision_requests = stats['vision_api_requests']
        if vision_requests > 0:
            stats['vision_api_success_rate'] = stats['vision_api_successes'] / vision_requests
            stats['vision_api_failure_rate'] = (vision_requests - stats['vision_api_successes']) / vision_requests
        else:
            stats['vision_api_success_rate'] = 0.0
            stats['vision_api_failure_rate'] = 0.0
        
        # Calculate authentication method usage
        total_auth_requests = stats['api_key_auth_requests'] + stats['bearer_auth_requests']
        if total_auth_requests > 0:
            stats['api_key_usage_rate'] = stats['api_key_auth_requests'] / total_auth_requests
            stats['bearer_usage_rate'] = stats['bearer_auth_requests'] / total_auth_requests
        else:
            stats['api_key_usage_rate'] = 0.0
            stats['bearer_usage_rate'] = 0.0
        
        # Add API preference summary
        if ocr_requests > 0 or vision_requests > 0:
            if ocr_requests > vision_requests:
                stats['preferred_api'] = 'OCR API'
            elif vision_requests > ocr_requests:
                stats['preferred_api'] = 'Vision API'
            else:
                stats['preferred_api'] = 'Equal usage'
        else:
            stats['preferred_api'] = 'No API usage yet'
        
        # Add configuration summary
        stats['config_summary'] = {
            'primary_api_format': self.config.primary_api_format,
            'primary_auth_method': self.config.primary_auth_method,
            'fallback_enabled': self.config.enable_fallback,
            'fallback_api_format': self.config.fallback_api_format,
            'fallback_auth_method': self.config.fallback_auth_method
        }
        
        return stats
    
    def test_api_connection(self) -> bool:
        """
        Test OCR API connection and authentication.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Create a minimal test image (1x1 white pixel)
            test_image_data = base64.b64encode(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0bIDATx\x9cc```\x00\x00\x00\x04\x00\x01]\xcc\xdb\x8d\x00\x00\x00\x00IEND\xaeB`\x82'
            ).decode('utf-8')
            
            payload = {
                "folderId": "test",
                "analyze": {
                    "content": test_image_data,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "textDetectionConfig": {
                            "languageCodes": ["en"]
                        }
                    }]
                }
            }
            
            response = self.session.post(
                self.config.api_url,
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
        self.logger.info("OCR client closed")