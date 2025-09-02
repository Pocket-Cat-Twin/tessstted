"""
High-Speed Data Validation System

Ultra-fast validation with pre-compiled patterns, lookup tables,
and optimized algorithms for <1 second response time.
"""

import re
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .database_manager import get_database
from .constants import Validation, OCR
from .data_sanitizer import get_data_sanitizer, SanitizationLevel
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .advanced_logger import get_logger

logger = get_logger(__name__)  # Use centralized logger

class ValidationLevel(Enum):
    """Validation strictness levels"""
    PERMISSIVE = "permissive"  # Fast, 70%+ confidence
    BALANCED = "balanced"      # Medium, 85%+ confidence  
    STRICT = "strict"          # Slow, 95%+ confidence

@dataclass
class ValidationResult:
    """Validation result with scoring"""
    is_valid: bool
    confidence: float
    errors: List[str]
    warnings: List[str]
    processing_time: float
    data_type: str

class FastValidator:
    """High-performance data validator with multi-level validation"""
    
    def __init__(self):
        init_start = time.time()
        
        try:
            self.db = get_database()
            self._lock = threading.Lock()
            self.error_handler = get_error_handler()
            
            # Pre-compiled regex patterns for maximum speed
            self._patterns = self._compile_patterns()
            
            # Lookup tables for fast validation
            self._lookup_tables = self._build_lookup_tables()
            
            # Known valid items cache
            self._known_items: Set[str] = set()
            self._known_traders: Set[str] = set()
            
            # Initialize data sanitizer
            self.sanitizer = get_data_sanitizer()
            
            # Load known data from database
            self._load_known_data()
            
            # Performance tracking
            self.stats = {
                'validations_performed': 0,
                'validation_time_total': 0.0,
                'avg_validation_time': 0.0,
                'passed_validations': 0,
                'failed_validations': 0
            }
            
            init_time = time.time() - init_start
            logger.info(f"FastValidator initialized with optimized patterns in {init_time:.3f}s")
            
        except Exception as e:
            init_time = time.time() - init_start
            error_context = ErrorContext(
                component="fast_validator",
                operation="initialization",
                user_data={'init_time': init_time},
                system_state={'patterns_loaded': hasattr(self, '_patterns')},
                timestamp=datetime.now()
            )
            
            # Use error handler for centralized processing
            recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.FALLBACK)
            
            if not recovery_result.recovery_successful:
                logger.critical(f"FastValidator initialization failed critically: {e}")
                raise
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile all regex patterns for maximum performance"""
        patterns = {
            # Trader nickname patterns
            'trader_nickname': re.compile(rf'^[A-Za-z0-9_-]{{{Validation.MIN_TRADER_NAME_LENGTH},{Validation.MAX_TRADER_NAME_LENGTH}}}$'),
            'trader_nickname_flexible': re.compile(rf'^[A-Za-z0-9_-]{{{Validation.MIN_TRADER_NAME_FLEXIBLE},{Validation.MAX_TRADER_NAME_FLEXIBLE}}}$'),
            
            # Quantity patterns
            'quantity_strict': re.compile(rf'^[{Validation.MIN_QUANTITY}-9]\d{{0,5}}$'),  # 1-999999
            'quantity_flexible': re.compile(rf'^[{Validation.MIN_QUANTITY}-9]\d{{0,7}}$'),  # 1-99999999
            
            # Price patterns
            'price_strict': re.compile(rf'^\d{{1,{Validation.MAX_PRICE_DIGITS}}}(?:\.\d{{1,{Validation.MAX_PRICE_DECIMALS}}})?$'),
            'price_flexible': re.compile(r'^\d{1,10}(?:[.,]\d{1,3})?$'),
            'price_integer': re.compile(r'^\d{1,10}$'),
            
            # Item name patterns
            'item_name_eng': re.compile(r'^[A-Za-z0-9\s]{3,50}$'),
            'item_name_rus': re.compile(r'^[А-Яа-я0-9\s]{3,50}$'),
            'item_name_mixed': re.compile(r'^[A-Za-zА-Яа-я0-9\s]{3,50}$'),
            
            # Clean text patterns
            'clean_text': re.compile(r'^[A-Za-zА-Яа-я0-9\s_-]+$'),
            'numeric_only': re.compile(r'^\d+$'),
            'alphanumeric': re.compile(r'^[A-Za-z0-9]+$'),
            
            # Special characters to remove
            'noise_chars': re.compile(r'[^\w\s.-]'),
            'multiple_spaces': re.compile(r'\s+'),
        }
        
        logger.debug(f"Compiled {len(patterns)} validation patterns")
        return patterns
    
    def _build_lookup_tables(self) -> Dict[str, Any]:
        """Build lookup tables for fast validation"""
        tables = {
            # Common price ranges for different item types
            'price_ranges': Validation.ITEM_PRICE_RANGES.copy(),
            
            # Reasonable quantity ranges
            'quantity_ranges': Validation.ITEM_QUANTITY_RANGES.copy(),
            
            # Common words in item names
            'item_keywords_eng': {
                'sword', 'axe', 'bow', 'staff', 'shield', 'armor', 'helm', 'boots',
                'ring', 'amulet', 'potion', 'scroll', 'gem', 'stone', 'crystal',
                'fire', 'ice', 'lightning', 'dark', 'light', 'magic', 'holy'
            },
            
            'item_keywords_rus': {
                'меч', 'топор', 'лук', 'посох', 'щит', 'броня', 'шлем', 'сапоги',
                'кольцо', 'амулет', 'зелье', 'свиток', 'камень', 'кристалл',
                'огня', 'льда', 'молнии', 'тьмы', 'света', 'магии', 'света'
            },
            
            # Invalid/suspicious patterns
            'suspicious_patterns': {
                re.compile(r'(.)\1{4,}'),  # Same character repeated 5+ times
                re.compile(r'^[^A-Za-zА-Яа-я]*$'),  # No letters at all
                re.compile(r'[<>{}[\]()]+'),  # HTML/markup characters
            }
        }
        
        return tables
    
    def _load_known_data(self):
        """Load known valid data from database with comprehensive error handling"""
        load_start = time.time()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Load known item names with size limit
                    cursor.execute("SELECT DISTINCT item_name FROM current_inventory LIMIT 10000")
                    for row in cursor.fetchall():
                        try:
                            if row['item_name'] and isinstance(row['item_name'], str):
                                # Normalize and validate item name before adding
                                item_name = row['item_name'].strip().lower()
                                if 3 <= len(item_name) <= 100:  # Reasonable length
                                    self._known_items.add(item_name)
                        except (IndexError, KeyError):
                            continue  # Skip rows without item_name column
                    
                except Exception as e:
                    logger.warning(f"Failed to load known items: {e}")
                
                try:
                    # Load known trader names with size limit
                    cursor.execute("SELECT DISTINCT trader_nickname FROM current_inventory LIMIT 10000")
                    for row in cursor.fetchall():
                        try:
                            if row['trader_nickname'] and isinstance(row['trader_nickname'], str):
                                # Normalize and validate trader name before adding
                                trader_name = row['trader_nickname'].strip().lower()
                                if 2 <= len(trader_name) <= 50:  # Reasonable length
                                    self._known_traders.add(trader_name)
                        except (IndexError, KeyError):
                            continue  # Skip rows without trader_nickname column
                                
                except Exception as e:
                    logger.warning(f"Failed to load known traders: {e}")
                
                load_time = time.time() - load_start
                logger.info(f"Loaded {len(self._known_items)} known items, "
                          f"{len(self._known_traders)} known traders in {load_time:.3f}s")
        
        except Exception as e:
            load_time = time.time() - load_start
            
            error_context = ErrorContext(
                component="fast_validator",
                operation="load_known_data",
                user_data={'load_time': load_time},
                system_state={'db_available': self.db is not None},
                timestamp=datetime.now()
            )
            
            # Use error handler for centralized processing
            recovery_result = self.error_handler.handle_error(e, error_context, RecoveryStrategy.FALLBACK)
            
            # Initialize empty sets as fallback (graceful degradation)
            self._known_items = set()
            self._known_traders = set()
            
            if recovery_result.recovery_successful:
                logger.warning(f"Known data loading failed, continuing with empty cache: {e}")
            else:
                logger.error(f"Critical error loading known data: {e}")
    
    def validate_trader_nickname(self, nickname: str, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate trader nickname with specified strictness"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = Validation.PERFECT_CONFIDENCE
        
        # Enhanced input validation
        if nickname is None:
            errors.append("Nickname is None")
            confidence = 0.0
            nickname_clean = ""
        elif not isinstance(nickname, str):
            errors.append(f"Nickname must be string, got {type(nickname).__name__}")
            confidence = 0.0
            nickname_clean = ""
        elif not nickname.strip():
            errors.append("Nickname is empty or whitespace only")
            confidence = 0.0
            nickname_clean = ""
        else:
            # Use sanitizer for initial cleaning
            sanitized = self.sanitizer.sanitize_trader_nickname(nickname, SanitizationLevel.BASIC)
            nickname_clean = sanitized.sanitized_value
            
            # Add sanitization warnings to validation warnings
            if sanitized.warnings:
                warnings.extend([f"Sanitization: {w}" for w in sanitized.warnings])
            
            # Adjust confidence based on sanitization
            if sanitized.was_modified:
                confidence *= 0.95  # Small penalty for modified data
            
            # Check length
            if len(nickname_clean) < 3:
                errors.append("Nickname too short (minimum 3 characters)")
                confidence *= 0.3
            elif len(nickname_clean) > 16:
                if level == ValidationLevel.STRICT:
                    errors.append("Nickname too long (maximum 16 characters)")
                    confidence *= 0.5
                else:
                    warnings.append("Nickname longer than usual")
                    confidence *= 0.8
            
            # Pattern validation
            if level == ValidationLevel.STRICT:
                if not self._patterns['trader_nickname'].match(nickname_clean):
                    errors.append("Invalid characters in nickname")
                    confidence *= 0.2
            else:
                if not self._patterns['trader_nickname_flexible'].match(nickname_clean):
                    errors.append("Invalid characters in nickname")
                    confidence *= 0.4
            
            # Historical validation with safety checks
            try:
                if len(self._known_traders) > 0 and nickname_clean.lower() in self._known_traders:
                    confidence = min(confidence * 1.1, Validation.PERFECT_CONFIDENCE)
                elif len(self._known_traders) > 10:  # Only penalize if we have enough data
                    confidence *= 0.9
            except (AttributeError, TypeError) as e:
                logger.debug(f"Error in historical validation: {e}")
                # Continue without historical validation
            
            # Suspicious patterns
            for pattern in self._lookup_tables['suspicious_patterns']:
                if pattern.search(nickname_clean):
                    warnings.append("Suspicious character pattern detected")
                    confidence *= 0.7
                    break
        
        processing_time = time.time() - start_time
        is_valid = confidence >= self._get_confidence_threshold(level)
        
        self._update_stats(processing_time, is_valid)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(0.0, min(confidence, Validation.PERFECT_CONFIDENCE)),  # Clamp confidence
            errors=errors,
            warnings=warnings,
            processing_time=max(0.0, processing_time),  # Ensure non-negative time
            data_type='trader_nickname'
        )
    
    def validate_quantity(self, quantity: Any, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate item quantity"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = Validation.PERFECT_CONFIDENCE
        
        # Enhanced type and conversion handling
        quantity_int = None
        try:
            if quantity is None:
                raise ValueError("Quantity is None")
            elif isinstance(quantity, str):
                # Use sanitizer for quantity cleaning
                sanitized = self.sanitizer.sanitize_quantity(quantity, SanitizationLevel.STANDARD)
                quantity_clean = sanitized.sanitized_value
                
                # Add sanitization warnings
                if sanitized.warnings:
                    warnings.extend([f"Sanitization: {w}" for w in sanitized.warnings])
                
                if not quantity_clean:
                    raise ValueError("No valid digits found after sanitization")
                
                # Adjust confidence based on sanitization
                if sanitized.was_modified:
                    confidence *= 0.95
                
                # Check for overflow before conversion
                if len(quantity_clean) > 10:  # More than 10 digits likely to overflow
                    raise ValueError("Number too large")
                    
                quantity_int = int(quantity_clean)
                
            elif isinstance(quantity, (int, float)):
                # Check for special float values
                if isinstance(quantity, float):
                    if not float('inf') > quantity > float('-inf'):
                        raise ValueError("Infinite or NaN value")
                    if quantity != quantity:  # NaN check
                        raise ValueError("NaN value")
                        
                quantity_int = int(quantity)
                
            else:
                raise ValueError(f"Invalid type: {type(quantity).__name__}")
                
        except (ValueError, OverflowError, TypeError) as e:
            errors.append(f"Cannot convert to integer: {str(e)}")
            confidence = 0.0
            quantity_int = None
        
        if quantity_int is not None:
            # Range validation
            if quantity_int <= 0:
                errors.append("Quantity must be positive")
                confidence = 0.0
            elif quantity_int > 999999:
                if level == ValidationLevel.STRICT:
                    errors.append("Quantity too large (maximum 999,999)")
                    confidence *= 0.3
                else:
                    warnings.append("Unusually large quantity")
                    confidence *= 0.7
            
            # Reasonable ranges
            if 1 <= quantity_int <= 999:
                confidence *= 1.0  # Perfect range
            elif 1000 <= quantity_int <= 9999:
                confidence *= 0.9  # Large but reasonable
            elif quantity_int >= Validation.HIGH_QUANTITY_THRESHOLD:
                confidence *= 0.8  # Very large
        
        processing_time = time.time() - start_time
        is_valid = confidence >= self._get_confidence_threshold(level)
        
        self._update_stats(processing_time, is_valid)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(0.0, min(confidence, Validation.PERFECT_CONFIDENCE)),  # Clamp confidence
            errors=errors,
            warnings=warnings,
            processing_time=max(0.0, processing_time),  # Ensure non-negative time
            data_type='quantity'
        )
    
    def validate_price(self, price: Any, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate item price"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = Validation.PERFECT_CONFIDENCE
        
        # Enhanced price conversion with better error handling
        price_float = None
        try:
            if price is None:
                raise ValueError("Price is None")
            elif isinstance(price, str):
                if len(price.strip()) == 0:
                    raise ValueError("Empty price string")
                if len(price) > 30:  # Prevent extremely long price strings
                    raise ValueError("Price string too long")
                    
                # Use sanitizer for price cleaning
                sanitized = self.sanitizer.sanitize_price(price, SanitizationLevel.STANDARD)
                price_clean = sanitized.sanitized_value
                
                # Add sanitization warnings
                if sanitized.warnings:
                    warnings.extend([f"Sanitization: {w}" for w in sanitized.warnings])
                
                if not price_clean:
                    raise ValueError("No valid digits found after sanitization")
                
                # Adjust confidence based on sanitization
                if sanitized.was_modified:
                    confidence *= 0.95
                
                # Additional validation for decimal points
                if price_clean.count('.') > 1:
                    raise ValueError("Multiple decimal separators")
                    
                # Check length after cleaning
                if len(price_clean) > 20:
                    raise ValueError("Number too long")
                    
                price_float = float(price_clean)
                
            elif isinstance(price, (int, float)):
                # Enhanced float validation
                if isinstance(price, float):
                    if not (-float('inf') < price < float('inf')):
                        raise ValueError("Infinite value")
                    if price != price:  # NaN check
                        raise ValueError("NaN value")
                        
                price_float = float(price)
                
            else:
                raise ValueError(f"Invalid type: {type(price).__name__}")
                
        except (ValueError, OverflowError, TypeError) as e:
            errors.append(f"Cannot convert to number: {str(e)}")
            confidence = 0.0
            price_float = None
        
        if price_float is not None:
            # Range validation
            if price_float <= 0:
                errors.append("Price must be positive")
                confidence = 0.0
            elif price_float > 99999999:
                if level == ValidationLevel.STRICT:
                    errors.append("Price too large")
                    confidence *= 0.2
                else:
                    warnings.append("Unusually high price")
                    confidence *= 0.6
            
            # Decimal places check
            if level == ValidationLevel.STRICT:
                decimal_places = len(str(price_float).split('.')[-1]) if '.' in str(price_float) else 0
                if decimal_places > 2:
                    warnings.append("Too many decimal places for currency")
                    confidence *= 0.9
            
            # Reasonable price ranges
            if 1 <= price_float <= 999999:
                confidence *= 1.0  # Good range
            elif price_float < 1:
                confidence *= 0.7  # Too cheap
            else:
                confidence *= 0.8  # Very expensive
        
        processing_time = time.time() - start_time
        is_valid = confidence >= self._get_confidence_threshold(level)
        
        self._update_stats(processing_time, is_valid)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(0.0, min(confidence, Validation.PERFECT_CONFIDENCE)),  # Clamp confidence
            errors=errors,
            warnings=warnings,
            processing_time=max(0.0, processing_time),  # Ensure non-negative time
            data_type='price'
        )
    
    def validate_item_name(self, item_name: str, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate item name"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = Validation.PERFECT_CONFIDENCE
        
        # Enhanced item name validation
        if item_name is None:
            errors.append("Item name is None")
            confidence = 0.0
            name_clean = ""
        elif not isinstance(item_name, str):
            errors.append(f"Item name must be string, got {type(item_name).__name__}")
            confidence = 0.0
            name_clean = ""
        elif not item_name.strip():
            errors.append("Item name is empty or whitespace only")
            confidence = 0.0
            name_clean = ""
        else:
            # Use sanitizer for initial cleaning
            sanitized = self.sanitizer.sanitize_item_name(item_name, SanitizationLevel.BASIC)
            name_clean = sanitized.sanitized_value
            
            # Add sanitization warnings to validation warnings
            if sanitized.warnings:
                warnings.extend([f"Sanitization: {w}" for w in sanitized.warnings])
            
            # Adjust confidence based on sanitization
            if sanitized.was_modified:
                confidence *= 0.95  # Small penalty for modified data
            
            # Additional pattern cleaning if needed
            try:
                name_clean = self._patterns['multiple_spaces'].sub(' ', name_clean)
            except Exception as e:
                logger.debug(f"Error cleaning item name: {e}")
            
            # Length validation
            if len(name_clean) < 3:
                errors.append("Item name too short")
                confidence *= 0.3
            elif len(name_clean) > 50:
                if level == ValidationLevel.STRICT:
                    errors.append("Item name too long")
                    confidence *= 0.4
                else:
                    warnings.append("Item name longer than usual")
                    confidence *= 0.8
            
            # Character validation
            if not self._patterns['item_name_mixed'].match(name_clean):
                if level == ValidationLevel.STRICT:
                    errors.append("Invalid characters in item name")
                    confidence *= 0.3
                else:
                    warnings.append("Unusual characters in item name")
                    confidence *= 0.7
            
            # Historical validation with safety checks
            try:
                if len(self._known_items) > 0 and name_clean.lower() in self._known_items:
                    confidence = min(confidence * 1.2, Validation.PERFECT_CONFIDENCE)
                elif len(self._known_items) > 5:
                    confidence *= 0.9
            except (AttributeError, TypeError) as e:
                logger.debug(f"Error in historical validation for item: {e}")
                # Continue without historical validation
            
            # Keyword validation
            has_valid_keyword = False
            name_lower = name_clean.lower()
            
            # Check English keywords
            for keyword in self._lookup_tables['item_keywords_eng']:
                if keyword in name_lower:
                    has_valid_keyword = True
                    confidence *= 1.1
                    break
            
            # Check Russian keywords
            if not has_valid_keyword:
                for keyword in self._lookup_tables['item_keywords_rus']:
                    if keyword in name_lower:
                        has_valid_keyword = True
                        confidence *= 1.1
                        break
            
            if not has_valid_keyword and level == ValidationLevel.STRICT:
                warnings.append("No recognizable item keywords found")
                confidence *= 0.8
            
            # Suspicious patterns
            for pattern in self._lookup_tables['suspicious_patterns']:
                if pattern.search(name_clean):
                    warnings.append("Suspicious pattern in item name")
                    confidence *= 0.6
                    break
        
        processing_time = time.time() - start_time
        is_valid = confidence >= self._get_confidence_threshold(level)
        
        self._update_stats(processing_time, is_valid)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(0.0, min(confidence, Validation.PERFECT_CONFIDENCE)),  # Clamp confidence
            errors=errors,
            warnings=warnings,
            processing_time=max(0.0, processing_time),  # Ensure non-negative time
            data_type='item_name'
        )
    
    def validate_trade_data(self, trade_data: Dict[str, Any], 
                          level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate complete trade data record with sanitization"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = Validation.PERFECT_CONFIDENCE
        
        # Pre-sanitize the entire trade data
        try:
            sanitization_level = SanitizationLevel.STANDARD
            if level == ValidationLevel.STRICT:
                sanitization_level = SanitizationLevel.AGGRESSIVE
            elif level == ValidationLevel.PERMISSIVE:
                sanitization_level = SanitizationLevel.BASIC
                
            sanitized_data = self.sanitizer.sanitize_trade_data(trade_data, sanitization_level)
            
            # Check if sanitization found issues
            for field, result in sanitized_data.items():
                if result.warnings:
                    warnings.extend([f"{field} sanitization: {w}" for w in result.warnings])
                if result.was_modified:
                    confidence *= 0.98  # Small penalty for sanitized data
                    
        except Exception as e:
            errors.append(f"Data sanitization failed: {e}")
            sanitized_data = {}
            confidence *= 0.8
        
        # Validate individual fields using sanitized data when available
        validations = {}
        
        if 'trader_nickname' in trade_data:
            # Use sanitized value if available
            value_to_validate = (sanitized_data.get('trader_nickname', {}).sanitized_value 
                               if 'trader_nickname' in sanitized_data 
                               else trade_data['trader_nickname'])
            validations['trader'] = self.validate_trader_nickname(value_to_validate, level)
        
        if 'quantity' in trade_data:
            value_to_validate = (sanitized_data.get('quantity', {}).sanitized_value 
                               if 'quantity' in sanitized_data 
                               else trade_data['quantity'])
            validations['quantity'] = self.validate_quantity(value_to_validate, level)
        
        if 'price_per_unit' in trade_data:
            value_to_validate = (sanitized_data.get('price_per_unit', {}).sanitized_value 
                               if 'price_per_unit' in sanitized_data 
                               else trade_data['price_per_unit'])
            validations['price'] = self.validate_price(value_to_validate, level)
        
        if 'item_name' in trade_data:
            value_to_validate = (sanitized_data.get('item_name', {}).sanitized_value 
                               if 'item_name' in sanitized_data 
                               else trade_data['item_name'])
            validations['item'] = self.validate_item_name(value_to_validate, level)
        
        # Enhanced result aggregation with safety checks
        all_valid = True
        total_confidence = 0.0
        total_count = 0
        
        for field, result in validations.items():
            if result is not None:  # Safety check
                # Safely add errors and warnings
                if hasattr(result, 'errors') and result.errors:
                    errors.extend([f"{field}: {error}" for error in result.errors if error])
                if hasattr(result, 'warnings') and result.warnings:
                    warnings.extend([f"{field}: {warning}" for warning in result.warnings if warning])
                
                if not result.is_valid:
                    all_valid = False
                
                # Validate confidence value before adding
                if hasattr(result, 'confidence') and isinstance(result.confidence, (int, float)):
                    confidence_val = max(0.0, min(result.confidence, 1.0))  # Clamp confidence
                    total_confidence += confidence_val
                    total_count += 1
            else:
                errors.append(f"{field}: Validation failed to complete")
                all_valid = False
        
        # Safe confidence calculation
        if total_count > 0:
            confidence = total_confidence / total_count
        else:
            confidence = 0.0  # No valid validations completed
        
        # Enhanced cross-field validation with proper error handling
        if 'quantity' in trade_data and 'price_per_unit' in trade_data:
            try:
                quantity_val = trade_data['quantity']
                price_val = trade_data['price_per_unit']
                
                # Validate both values exist and are convertible
                if quantity_val is not None and price_val is not None:
                    quantity_float = float(quantity_val)
                    price_float = float(price_val)
                    
                    # Check for reasonable values before multiplication
                    if 0 < quantity_float < 1e10 and 0 < price_float < 1e10:
                        total_value = quantity_float * price_float
                        
                        if total_value > 999999999:  # 1 billion limit
                            warnings.append("Total trade value extremely high")
                            confidence *= 0.9
                        elif total_value < 0.01:  # Suspiciously low
                            warnings.append("Total trade value suspiciously low")
                            confidence *= 0.95
                            
                    else:
                        warnings.append("Quantity or price values out of reasonable range")
                        confidence *= 0.8
                        
            except (ValueError, TypeError, OverflowError) as e:
                warnings.append(f"Cannot calculate total trade value: {str(e)}")
                confidence *= 0.9
        
        processing_time = time.time() - start_time
        is_valid = all_valid and confidence >= self._get_confidence_threshold(level)
        
        self._update_stats(processing_time, is_valid)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(0.0, min(confidence, Validation.PERFECT_CONFIDENCE)),  # Clamp confidence
            errors=errors,
            warnings=warnings,
            processing_time=max(0.0, processing_time),  # Ensure non-negative time
            data_type='trade_data'
        )
    
    def _get_confidence_threshold(self, level: ValidationLevel) -> float:
        """Get confidence threshold for validation level"""
        thresholds = {
            ValidationLevel.PERMISSIVE: 0.70,
            ValidationLevel.BALANCED: 0.85,
            ValidationLevel.STRICT: 0.95
        }
        return thresholds[level]
    
    def _update_stats(self, processing_time: float, is_valid: bool):
        """Update performance statistics with overflow protection"""
        with self._lock:
            # Prevent integer overflow and division by zero
            try:
                if self.stats['validations_performed'] >= 2**31 - 1:  # Reset if near overflow
                    logger.info("Resetting statistics due to overflow protection")
                    self._reset_stats_internal()
                    
                self.stats['validations_performed'] += 1
                
                # Validate processing_time is reasonable
                if isinstance(processing_time, (int, float)) and 0 <= processing_time < 3600:
                    self.stats['validation_time_total'] += processing_time
                else:
                    logger.debug(f"Invalid processing time ignored: {processing_time}")
                    
                # Safe division
                if self.stats['validations_performed'] > 0:
                    self.stats['avg_validation_time'] = (
                        self.stats['validation_time_total'] / self.stats['validations_performed']
                    )
                
                if is_valid:
                    self.stats['passed_validations'] += 1
                else:
                    self.stats['failed_validations'] += 1
                    
            except Exception as e:
                logger.error(f"Error updating statistics: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation performance statistics with safe calculations"""
        with self._lock:
            stats = self.stats.copy()
        
        # Safe division for pass rate
        try:
            if stats['validations_performed'] > 0:
                stats['pass_rate'] = stats['passed_validations'] / stats['validations_performed']
            else:
                stats['pass_rate'] = 0.0
        except (ZeroDivisionError, TypeError):
            stats['pass_rate'] = 0.0
            
        # Add additional safety metrics
        stats['known_items_count'] = len(self._known_items) if hasattr(self, '_known_items') else 0
        stats['known_traders_count'] = len(self._known_traders) if hasattr(self, '_known_traders') else 0
        
        # Add sanitizer statistics
        try:
            sanitizer_stats = self.sanitizer.get_statistics()
            stats['sanitizer'] = sanitizer_stats
        except Exception as e:
            logger.debug(f"Could not get sanitizer stats: {e}")
            stats['sanitizer'] = {}
        
        return stats
    
    def _reset_stats_internal(self):
        """Internal method to reset statistics"""
        self.stats = {
            'validations_performed': 0,
            'validation_time_total': 0.0,
            'avg_validation_time': 0.0,
            'passed_validations': 0,
            'failed_validations': 0
        }
    
    def reset_statistics(self):
        """Reset performance statistics"""
        with self._lock:
            self._reset_stats_internal()
        logger.info("FastValidator statistics reset")
    
    def refresh_known_data(self):
        """Refresh known data from database with error handling"""
        try:
            # Store current data as backup
            backup_items = self._known_items.copy() if hasattr(self, '_known_items') else set()
            backup_traders = self._known_traders.copy() if hasattr(self, '_known_traders') else set()
            
            # Clear and reload
            self._known_items.clear()
            self._known_traders.clear()
            self._load_known_data()
            
            # Check if load was successful
            if len(self._known_items) == 0 and len(self._known_traders) == 0:
                logger.warning("No data loaded, restoring backup")
                self._known_items = backup_items
                self._known_traders = backup_traders
            else:
                logger.info(f"Known data refreshed: {len(self._known_items)} items, {len(self._known_traders)} traders")
                
        except Exception as e:
            logger.error(f"Failed to refresh known data: {e}")
            # Ensure we have valid empty sets if all else fails
            if not hasattr(self, '_known_items'):
                self._known_items = set()
            if not hasattr(self, '_known_traders'):
                self._known_traders = set()

# Global instance for easy access
_validator_instance = None
_validator_lock = threading.Lock()

def get_validator() -> FastValidator:
    """Get singleton validator instance"""
    global _validator_instance
    if _validator_instance is None:
        with _validator_lock:
            if _validator_instance is None:
                _validator_instance = FastValidator()
    return _validator_instance