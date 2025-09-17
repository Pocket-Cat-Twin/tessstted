"""
Yandex OCR client adapter for market monitoring system.
Uses simplified OCR client while maintaining backward compatibility.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from config.settings import SettingsManager, YandexOCRConfig
from .simple_ocr_client import SimpleYandexOCRClient, SimpleOCRError


class OCRError(Exception):
    """Exception raised for OCR processing errors."""
    pass


class YandexOCRClient:
    """
    Adapter for Yandex OCR client using simplified implementation.
    Maintains backward compatibility with existing system interfaces.
    """
    
    def __init__(self, settings_manager: SettingsManager):
        """
        Initialize Yandex OCR client adapter.
        
        Args:
            settings_manager: Configuration manager instance
        """
        self.settings = settings_manager
        self.config: YandexOCRConfig = settings_manager.yandex_ocr
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        if not self.config or not self.config.api_key or self.config.api_key == "your_api_key_here":
            raise OCRError("Yandex OCR API key not configured")
        
        # Initialize simplified OCR client
        try:
            self.simple_client = SimpleYandexOCRClient(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
        except SimpleOCRError as e:
            raise OCRError(f"Failed to initialize OCR client: {e}")
        
        self.logger.info(f"OCR client adapter initialized with simplified client")
        
        # Initialize statistics for backward compatibility
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
            # For backward compatibility with existing code
            'ocr_api_requests': 0,
            'ocr_api_successes': 0,
            'vision_api_requests': 0,
            'vision_api_successes': 0,
            'fallback_usage': 0,
            'api_key_auth_requests': 0,
            'bearer_auth_requests': 0
        }
    
    def send_image_for_recognition(self, image_path: Path, 
                                 language_codes: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Send image to Yandex OCR API for text recognition (adapter method).
        
        Args:
            image_path: Path to image file
            language_codes: Optional list of language codes
            
        Returns:
            OCR response dictionary or None if failed
        """
        try:
            # Use simplified client
            text_result = self.simple_client.process_image_full_pipeline(
                image_path=image_path,
                cleanup_image=False,  # Don't cleanup here, let caller decide
                language_codes=language_codes
            )
            
            if text_result:
                # Update adapter statistics
                self._update_adapter_stats(success=True)
                
                # Return in expected format for backward compatibility
                return {
                    'result': {
                        'textAnnotation': {
                            'fullText': text_result
                        }
                    }
                }
            else:
                self._update_adapter_stats(success=False)
                return None
                
        except Exception as e:
            self.logger.error(f"OCR adapter error: {e}")
            self._update_adapter_stats(success=False)
            return None
    
    def extract_text_from_response(self, api_response: Dict[str, Any]) -> str:
        """
        Extract text content from API response (backward compatibility).
        
        Args:
            api_response: API response dictionary
            
        Returns:
            Extracted text content
        """
        try:
            result = api_response.get('result', {})
            text_annotation = result.get('textAnnotation', {})
            extracted_text = text_annotation.get('fullText', '')
            return extracted_text.strip() if extracted_text else ""
        except Exception as e:
            self.logger.error(f"Failed to extract text from response: {e}")
            return ""
    
    def process_image_full_pipeline(self, image_path: Path, 
                                  cleanup_image: bool = True,
                                  language_codes: Optional[List[str]] = None) -> Optional[str]:
        """
        Full pipeline: send image for OCR and extract text (adapter method).
        
        Args:
            image_path: Path to image file
            cleanup_image: Whether to delete image after processing
            language_codes: Optional language codes
            
        Returns:
            Extracted text or None if failed
        """
        try:
            # Delegate to simplified client
            return self.simple_client.process_image_full_pipeline(
                image_path=image_path,
                cleanup_image=cleanup_image,
                language_codes=language_codes
            )
        except Exception as e:
            self.logger.error(f"OCR pipeline adapter error: {e}")
            return None
    
    def get_ocr_statistics(self) -> Dict[str, Any]:
        """
        Get OCR processing statistics (adapter method).
        
        Returns:
            Dictionary with OCR statistics
        """
        try:
            # Get stats from simplified client
            simple_stats = self.simple_client.get_ocr_statistics()
            
            # Merge with adapter stats for backward compatibility
            combined_stats = self._stats.copy()
            combined_stats.update(simple_stats)
            
            # Add backward compatibility fields
            combined_stats['ocr_api_requests'] = simple_stats['total_requests']
            combined_stats['ocr_api_successes'] = simple_stats['successful_requests']
            combined_stats['api_key_auth_requests'] = simple_stats['total_requests']
            combined_stats['success_rate'] = simple_stats.get('success_rate', 0.0)
            combined_stats['failure_rate'] = simple_stats.get('failure_rate', 0.0)
            
            # Add configuration summary
            combined_stats['config_summary'] = {
                'primary_api_format': 'ocr',
                'primary_auth_method': 'api_key',
                'fallback_enabled': False,
                'api_url': self.config.api_url,
                'timeout': self.config.timeout,
                'max_retries': self.config.max_retries
            }
            
            return combined_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get OCR statistics: {e}")
            return self._stats.copy()
    
    def test_api_connection(self) -> bool:
        """
        Test OCR API connection and authentication (adapter method).
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return self.simple_client.test_api_connection()
        except Exception as e:
            self.logger.error(f"API connection test adapter error: {e}")
            return False
    
    def _update_adapter_stats(self, success: bool) -> None:
        """Update adapter statistics for backward compatibility."""
        self._stats['total_requests'] += 1
        if success:
            self._stats['successful_requests'] += 1
            self._stats['ocr_api_requests'] += 1
            self._stats['ocr_api_successes'] += 1
            self._stats['api_key_auth_requests'] += 1
        else:
            self._stats['failed_requests'] += 1
    
    def close(self) -> None:
        """Close the OCR client and clean up resources (adapter method)."""
        try:
            if hasattr(self, 'simple_client'):
                self.simple_client.close()
            self.logger.info("OCR client adapter closed")
        except Exception as e:
            self.logger.error(f"Error closing OCR client adapter: {e}")