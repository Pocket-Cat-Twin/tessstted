"""
Data Sanitization Layer for Game Monitor System

Comprehensive input sanitization, cleaning, and normalization
to prevent injection attacks, data corruption, and ensure data quality.
"""

import re
import html
import unicodedata
import logging
import threading
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import string
from urllib.parse import quote, unquote

from .constants import OCR, Validation, Patterns

logger = logging.getLogger(__name__)


class SanitizationLevel(Enum):
    """Levels of sanitization aggressiveness"""
    BASIC = "basic"           # Remove dangerous characters only
    STANDARD = "standard"     # Standard cleaning and normalization
    AGGRESSIVE = "aggressive" # Aggressive cleaning, may alter data
    STRICT = "strict"        # Very strict, may reject valid data


@dataclass
class SanitizationResult:
    """Result of data sanitization"""
    original_value: str
    sanitized_value: str
    was_modified: bool
    removed_characters: List[str]
    warnings: List[str]
    sanitization_level: SanitizationLevel


class DataSanitizer:
    """Comprehensive data sanitization system"""
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Pre-compiled patterns for performance
        self._patterns = self._compile_sanitization_patterns()
        
        # Character whitelists
        self._whitelists = self._build_character_whitelists()
        
        # Dangerous patterns to detect/remove
        self._dangerous_patterns = self._build_dangerous_patterns()
        
        # Statistics
        self.stats = {
            'items_processed': 0,
            'items_modified': 0,
            'dangerous_patterns_found': 0,
            'characters_removed': 0
        }
        
        logger.info("DataSanitizer initialized with comprehensive patterns")
    
    def _compile_sanitization_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for sanitization"""
        patterns = {
            # Basic cleaning patterns
            'control_chars': re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]'),
            'multiple_whitespace': re.compile(r'\s+'),
            'leading_trailing_space': re.compile(r'^\s+|\s+$'),
            
            # Injection patterns
            'sql_injection': re.compile(
                r'(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript|vbscript)',
                re.IGNORECASE
            ),
            'html_tags': re.compile(r'<[^>]*>'),
            'script_tags': re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            
            # Path traversal
            'path_traversal': re.compile(r'\.\.[\\/]'),
            'absolute_paths': re.compile(r'^[a-zA-Z]:[\\\/]|^[\\\/]'),
            
            # Special characters
            'html_entities': re.compile(r'&[a-zA-Z][a-zA-Z0-9]*;|&#\d+;|&#x[0-9a-fA-F]+;'),
            'url_encoded': re.compile(r'%[0-9a-fA-F]{2}'),
            
            # Game-specific patterns
            'trader_name_clean': re.compile(r'[^' + re.escape(OCR.TRADER_NAME_WHITELIST) + ']'),
            'quantity_clean': re.compile(r'[^' + re.escape(OCR.QUANTITY_WHITELIST) + ']'),
            'price_clean': re.compile(r'[^' + re.escape(OCR.PRICE_WHITELIST) + ']'),
            
            # Unicode normalization
            'unicode_confusables': re.compile(r'[ĸ]'),  # Example confusables
            'zero_width_chars': re.compile(r'[\u200B-\u200D\u2060\uFEFF]'),
            
            # Suspicious patterns
            'repeated_chars': re.compile(r'(.)\1{10,}'),  # 10+ repeated characters
            'all_caps': re.compile(r'^[A-Z\s\d]{20,}$'),  # 20+ character all caps
        }
        
        return patterns
    
    def _build_character_whitelists(self) -> Dict[str, str]:
        """Build character whitelists for different data types"""
        return {
            'trader_nickname': OCR.TRADER_NAME_WHITELIST,
            'quantity': OCR.QUANTITY_WHITELIST,
            'price': OCR.PRICE_WHITELIST,
            'item_name': string.ascii_letters + string.digits + ' -_абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
            'general_text': string.ascii_letters + string.digits + ' .,!?()-_',
            'safe_filename': string.ascii_letters + string.digits + '-_.',
        }
    
    def _build_dangerous_patterns(self) -> List[Dict[str, Any]]:
        """Build list of dangerous patterns to detect"""
        return [
            {
                'name': 'sql_injection',
                'pattern': self._patterns['sql_injection'],
                'severity': 'high',
                'action': 'remove'
            },
            {
                'name': 'script_injection',
                'pattern': self._patterns['script_tags'],
                'severity': 'critical',
                'action': 'remove'
            },
            {
                'name': 'path_traversal',
                'pattern': self._patterns['path_traversal'],
                'severity': 'high',
                'action': 'remove'
            },
            {
                'name': 'html_tags',
                'pattern': self._patterns['html_tags'],
                'severity': 'medium',
                'action': 'remove'
            }
        ]
    
    def sanitize_trader_nickname(self, nickname: str, 
                                level: SanitizationLevel = SanitizationLevel.STANDARD) -> SanitizationResult:
        """Sanitize trader nickname"""
        if not isinstance(nickname, str):
            nickname = str(nickname) if nickname is not None else ""
        
        return self._sanitize_with_whitelist(
            nickname, 'trader_nickname', level, max_length=50
        )
    
    def sanitize_item_name(self, item_name: str,
                          level: SanitizationLevel = SanitizationLevel.STANDARD) -> SanitizationResult:
        """Sanitize item name"""
        if not isinstance(item_name, str):
            item_name = str(item_name) if item_name is not None else ""
            
        return self._sanitize_with_whitelist(
            item_name, 'item_name', level, max_length=100
        )
    
    def sanitize_quantity(self, quantity: Union[str, int, float],
                         level: SanitizationLevel = SanitizationLevel.STANDARD) -> SanitizationResult:
        """Sanitize quantity value"""
        if isinstance(quantity, (int, float)):
            quantity = str(int(quantity)) if quantity >= 0 else "0"
        elif not isinstance(quantity, str):
            quantity = str(quantity) if quantity is not None else "0"
            
        return self._sanitize_with_whitelist(
            quantity, 'quantity', level, max_length=20
        )
    
    def sanitize_price(self, price: Union[str, int, float],
                      level: SanitizationLevel = SanitizationLevel.STANDARD) -> SanitizationResult:
        """Sanitize price value"""
        if isinstance(price, (int, float)):
            price = f"{price:.2f}" if price >= 0 else "0.00"
        elif not isinstance(price, str):
            price = str(price) if price is not None else "0.00"
            
        return self._sanitize_with_whitelist(
            price, 'price', level, max_length=30
        )
    
    def sanitize_filename(self, filename: str,
                         level: SanitizationLevel = SanitizationLevel.STANDARD) -> SanitizationResult:
        """Sanitize filename for safe file system operations"""
        if not isinstance(filename, str):
            filename = str(filename) if filename is not None else "unknown"
            
        return self._sanitize_with_whitelist(
            filename, 'safe_filename', level, max_length=255
        )
    
    def sanitize_general_text(self, text: str,
                             level: SanitizationLevel = SanitizationLevel.STANDARD) -> SanitizationResult:
        """Sanitize general text content"""
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
            
        return self._sanitize_with_whitelist(
            text, 'general_text', level, max_length=1000
        )
    
    def _sanitize_with_whitelist(self, value: str, whitelist_key: str,
                                level: SanitizationLevel, max_length: int = None) -> SanitizationResult:
        """Core sanitization using character whitelists"""
        original_value = value
        warnings = []
        removed_chars = []
        
        # Step 1: Length limiting
        if max_length and len(value) > max_length:
            value = value[:max_length]
            warnings.append(f"Truncated to {max_length} characters")
        
        # Step 2: Unicode normalization
        try:
            value = unicodedata.normalize('NFKC', value)
        except Exception as e:
            warnings.append(f"Unicode normalization failed: {e}")
        
        # Step 3: Remove control characters
        original_len = len(value)
        value = self._patterns['control_chars'].sub('', value)
        if len(value) != original_len:
            removed_chars.extend(['control_chars'])
            warnings.append("Removed control characters")
        
        # Step 4: Remove zero-width characters
        original_len = len(value)
        value = self._patterns['zero_width_chars'].sub('', value)
        if len(value) != original_len:
            removed_chars.extend(['zero_width'])
            warnings.append("Removed zero-width characters")
        
        # Step 5: Detect and handle dangerous patterns
        for danger in self._dangerous_patterns:
            if danger['pattern'].search(value):
                warnings.append(f"Dangerous pattern detected: {danger['name']}")
                if level in [SanitizationLevel.AGGRESSIVE, SanitizationLevel.STRICT]:
                    value = danger['pattern'].sub('', value)
                    removed_chars.append(danger['name'])
                    with self._lock:
                        self.stats['dangerous_patterns_found'] += 1
        
        # Step 6: HTML entity decoding (if needed)
        if level in [SanitizationLevel.STANDARD, SanitizationLevel.AGGRESSIVE]:
            if self._patterns['html_entities'].search(value):
                try:
                    decoded = html.unescape(value)
                    if decoded != value:
                        value = decoded
                        warnings.append("Decoded HTML entities")
                except Exception as e:
                    warnings.append(f"HTML decoding failed: {e}")
        
        # Step 7: URL decoding (if needed)
        if level in [SanitizationLevel.AGGRESSIVE]:
            if self._patterns['url_encoded'].search(value):
                try:
                    decoded = unquote(value)
                    if decoded != value:
                        value = decoded
                        warnings.append("URL decoded")
                except Exception as e:
                    warnings.append(f"URL decoding failed: {e}")
        
        # Step 8: Whitelist filtering
        if whitelist_key in self._whitelists:
            whitelist = self._whitelists[whitelist_key]
            original_len = len(value)
            filtered_chars = []
            
            for char in value:
                if char in whitelist:
                    filtered_chars.append(char)
                else:
                    removed_chars.append(char)
            
            value = ''.join(filtered_chars)
            
            if len(value) != original_len:
                warnings.append("Filtered non-whitelisted characters")
        
        # Step 9: Whitespace normalization
        value = self._patterns['multiple_whitespace'].sub(' ', value)
        value = self._patterns['leading_trailing_space'].sub('', value)
        
        # Step 10: Additional level-specific processing
        if level == SanitizationLevel.STRICT:
            # Very strict validation
            if len(value) < 1 and whitelist_key in ['trader_nickname', 'item_name']:
                warnings.append("Value too short after sanitization")
                value = ""
        elif level == SanitizationLevel.AGGRESSIVE:
            # Remove suspicious patterns
            if self._patterns['repeated_chars'].search(value):
                value = self._patterns['repeated_chars'].sub(r'\1\1\1', value)
                warnings.append("Reduced repeated characters")
        
        # Update statistics
        with self._lock:
            self.stats['items_processed'] += 1
            if value != original_value:
                self.stats['items_modified'] += 1
            self.stats['characters_removed'] += len(removed_chars)
        
        return SanitizationResult(
            original_value=original_value,
            sanitized_value=value,
            was_modified=(value != original_value),
            removed_characters=list(set(removed_chars)),  # Remove duplicates
            warnings=warnings,
            sanitization_level=level
        )
    
    def sanitize_trade_data(self, trade_data: Dict[str, Any],
                           level: SanitizationLevel = SanitizationLevel.STANDARD) -> Dict[str, SanitizationResult]:
        """Sanitize complete trade data dictionary"""
        results = {}
        
        # Define field mappings
        field_sanitizers = {
            'trader_nickname': self.sanitize_trader_nickname,
            'item_name': self.sanitize_item_name,
            'quantity': self.sanitize_quantity,
            'price_per_unit': self.sanitize_price,
            'total_value': self.sanitize_price,
        }
        
        for field, value in trade_data.items():
            if field in field_sanitizers:
                try:
                    results[field] = field_sanitizers[field](value, level)
                except Exception as e:
                    logger.error(f"Error sanitizing field {field}: {e}")
                    # Return empty result on error
                    results[field] = SanitizationResult(
                        original_value=str(value),
                        sanitized_value="",
                        was_modified=True,
                        removed_characters=[],
                        warnings=[f"Sanitization error: {e}"],
                        sanitization_level=level
                    )
            else:
                # For unknown fields, apply general text sanitization
                try:
                    results[field] = self.sanitize_general_text(str(value), level)
                except Exception as e:
                    logger.error(f"Error sanitizing unknown field {field}: {e}")
        
        return results
    
    def detect_encoding_issues(self, text: str) -> List[str]:
        """Detect potential encoding issues in text"""
        issues = []
        
        try:
            # Check for common encoding artifacts
            if 'Ã¡' in text or 'Ã©' in text or 'Ã±' in text:
                issues.append("Possible double UTF-8 encoding")
            
            # Check for replacement characters
            if '\ufffd' in text:
                issues.append("Contains Unicode replacement characters")
            
            # Check for mixed encodings
            try:
                text.encode('ascii')
            except UnicodeEncodeError:
                issues.append("Contains non-ASCII characters")
            
            # Check for suspicious byte patterns
            if re.search(r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{5,}', text):
                issues.append("Possible encoding corruption")
                
        except Exception as e:
            issues.append(f"Encoding detection error: {e}")
        
        return issues
    
    def normalize_unicode(self, text: str, form: str = 'NFKC') -> str:
        """Normalize Unicode text using specified form"""
        try:
            return unicodedata.normalize(form, text)
        except Exception as e:
            logger.error(f"Unicode normalization failed: {e}")
            return text
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get sanitization statistics"""
        with self._lock:
            stats = self.stats.copy()
        
        if stats['items_processed'] > 0:
            stats['modification_rate'] = stats['items_modified'] / stats['items_processed']
            stats['avg_chars_removed'] = stats['characters_removed'] / stats['items_processed']
        else:
            stats['modification_rate'] = 0.0
            stats['avg_chars_removed'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """Reset sanitization statistics"""
        with self._lock:
            self.stats = {
                'items_processed': 0,
                'items_modified': 0,
                'dangerous_patterns_found': 0,
                'characters_removed': 0
            }
        logger.info("DataSanitizer statistics reset")


# Global instance
_sanitizer_instance = None
_sanitizer_lock = threading.Lock()

def get_data_sanitizer() -> DataSanitizer:
    """Get singleton data sanitizer instance"""
    global _sanitizer_instance
    if _sanitizer_instance is None:
        with _sanitizer_lock:
            if _sanitizer_instance is None:
                _sanitizer_instance = DataSanitizer()
    return _sanitizer_instance


def quick_sanitize(value: str, data_type: str = 'general') -> str:
    """Quick sanitization function for common use cases"""
    sanitizer = get_data_sanitizer()
    
    sanitization_map = {
        'trader': sanitizer.sanitize_trader_nickname,
        'item': sanitizer.sanitize_item_name,
        'quantity': sanitizer.sanitize_quantity,
        'price': sanitizer.sanitize_price,
        'filename': sanitizer.sanitize_filename,
        'general': sanitizer.sanitize_general_text
    }
    
    sanitize_func = sanitization_map.get(data_type, sanitizer.sanitize_general_text)
    result = sanitize_func(value)
    
    if result.warnings:
        logger.debug(f"Sanitization warnings for {data_type}: {result.warnings}")
    
    return result.sanitized_value