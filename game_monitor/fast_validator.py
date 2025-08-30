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

from .database_manager import get_database

logger = logging.getLogger(__name__)

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
        self.db = get_database()
        self._lock = threading.Lock()
        
        # Pre-compiled regex patterns for maximum speed
        self._patterns = self._compile_patterns()
        
        # Lookup tables for fast validation
        self._lookup_tables = self._build_lookup_tables()
        
        # Known valid items cache
        self._known_items: Set[str] = set()
        self._known_traders: Set[str] = set()
        
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
        
        logger.info("FastValidator initialized with optimized patterns")
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile all regex patterns for maximum performance"""
        patterns = {
            # Trader nickname patterns
            'trader_nickname': re.compile(r'^[A-Za-z0-9_-]{3,16}$'),
            'trader_nickname_flexible': re.compile(r'^[A-Za-z0-9_-]{2,20}$'),
            
            # Quantity patterns
            'quantity_strict': re.compile(r'^[1-9]\d{0,5}$'),  # 1-999999
            'quantity_flexible': re.compile(r'^[1-9]\d{0,7}$'),  # 1-99999999
            
            # Price patterns
            'price_strict': re.compile(r'^\d{1,8}(?:\.\d{1,2})?$'),
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
            'price_ranges': {
                'consumable': (1, 1000),      # potions, food
                'weapon': (100, 50000),       # weapons
                'armor': (200, 30000),        # armor pieces
                'accessory': (500, 100000),   # rings, amulets
                'rare': (1000, 500000),       # rare items
                'epic': (5000, 999999),       # epic items
            },
            
            # Reasonable quantity ranges
            'quantity_ranges': {
                'consumable': (1, 999),
                'weapon': (1, 50),
                'armor': (1, 50),
                'accessory': (1, 20),
                'rare': (1, 10),
                'epic': (1, 5),
            },
            
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
        """Load known valid data from database"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Load known item names
                cursor.execute("SELECT DISTINCT item_name FROM current_inventory")
                for row in cursor.fetchall():
                    if row['item_name']:
                        self._known_items.add(row['item_name'].lower())
                
                # Load known trader names
                cursor.execute("SELECT DISTINCT trader_nickname FROM current_inventory")
                for row in cursor.fetchall():
                    if row['trader_nickname']:
                        self._known_traders.add(row['trader_nickname'].lower())
                
                logger.info(f"Loaded {len(self._known_items)} known items, "
                          f"{len(self._known_traders)} known traders")
        
        except Exception as e:
            logger.warning(f"Failed to load known data: {e}")
    
    def validate_trader_nickname(self, nickname: str, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate trader nickname with specified strictness"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = 1.0
        
        if not nickname or not isinstance(nickname, str):
            errors.append("Nickname is empty or not a string")
            confidence = 0.0
        else:
            nickname_clean = nickname.strip()
            
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
            
            # Historical validation
            if nickname_clean.lower() in self._known_traders:
                confidence *= 1.1  # Boost confidence for known traders
            elif len(self._known_traders) > 10:  # Only penalize if we have enough data
                confidence *= 0.9
            
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
            confidence=min(confidence, 1.0),
            errors=errors,
            warnings=warnings,
            processing_time=processing_time,
            data_type='trader_nickname'
        )
    
    def validate_quantity(self, quantity: Any, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate item quantity"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = 1.0
        
        # Convert to int if possible
        try:
            if isinstance(quantity, str):
                # Clean string
                quantity_clean = self._patterns['noise_chars'].sub('', quantity)
                quantity_int = int(quantity_clean)
            elif isinstance(quantity, (int, float)):
                quantity_int = int(quantity)
            else:
                raise ValueError("Invalid type")
        except ValueError:
            errors.append("Cannot convert to integer")
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
            elif quantity_int >= 10000:
                confidence *= 0.8  # Very large
        
        processing_time = time.time() - start_time
        is_valid = confidence >= self._get_confidence_threshold(level)
        
        self._update_stats(processing_time, is_valid)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=min(confidence, 1.0),
            errors=errors,
            warnings=warnings,
            processing_time=processing_time,
            data_type='quantity'
        )
    
    def validate_price(self, price: Any, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate item price"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = 1.0
        
        # Convert to float if possible
        try:
            if isinstance(price, str):
                # Clean and normalize
                price_clean = price.replace(',', '.')
                price_clean = self._patterns['noise_chars'].sub('', price_clean)
                price_float = float(price_clean)
            elif isinstance(price, (int, float)):
                price_float = float(price)
            else:
                raise ValueError("Invalid type")
        except ValueError:
            errors.append("Cannot convert to number")
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
            confidence=min(confidence, 1.0),
            errors=errors,
            warnings=warnings,
            processing_time=processing_time,
            data_type='price'
        )
    
    def validate_item_name(self, item_name: str, level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate item name"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = 1.0
        
        if not item_name or not isinstance(item_name, str):
            errors.append("Item name is empty or not a string")
            confidence = 0.0
        else:
            name_clean = item_name.strip()
            name_clean = self._patterns['multiple_spaces'].sub(' ', name_clean)
            
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
            
            # Historical validation
            if name_clean.lower() in self._known_items:
                confidence *= 1.2  # Strong boost for known items
            elif len(self._known_items) > 5:
                confidence *= 0.9
            
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
            confidence=min(confidence, 1.0),
            errors=errors,
            warnings=warnings,
            processing_time=processing_time,
            data_type='item_name'
        )
    
    def validate_trade_data(self, trade_data: Dict[str, Any], 
                          level: ValidationLevel = ValidationLevel.BALANCED) -> ValidationResult:
        """Validate complete trade data record"""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = 1.0
        
        # Validate individual fields
        validations = {}
        
        if 'trader_nickname' in trade_data:
            validations['trader'] = self.validate_trader_nickname(trade_data['trader_nickname'], level)
        
        if 'quantity' in trade_data:
            validations['quantity'] = self.validate_quantity(trade_data['quantity'], level)
        
        if 'price_per_unit' in trade_data:
            validations['price'] = self.validate_price(trade_data['price_per_unit'], level)
        
        if 'item_name' in trade_data:
            validations['item'] = self.validate_item_name(trade_data['item_name'], level)
        
        # Aggregate results
        all_valid = True
        total_confidence = 0.0
        total_count = 0
        
        for field, result in validations.items():
            errors.extend([f"{field}: {error}" for error in result.errors])
            warnings.extend([f"{field}: {warning}" for warning in result.warnings])
            
            if not result.is_valid:
                all_valid = False
            
            total_confidence += result.confidence
            total_count += 1
        
        # Calculate average confidence
        if total_count > 0:
            confidence = total_confidence / total_count
        
        # Cross-field validation
        if 'quantity' in trade_data and 'price_per_unit' in trade_data:
            try:
                total_value = float(trade_data['quantity']) * float(trade_data['price_per_unit'])
                if total_value > 999999999:  # 1 billion limit
                    warnings.append("Total trade value extremely high")
                    confidence *= 0.9
            except:
                pass
        
        processing_time = time.time() - start_time
        is_valid = all_valid and confidence >= self._get_confidence_threshold(level)
        
        self._update_stats(processing_time, is_valid)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=min(confidence, 1.0),
            errors=errors,
            warnings=warnings,
            processing_time=processing_time,
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
        """Update performance statistics"""
        with self._lock:
            self.stats['validations_performed'] += 1
            self.stats['validation_time_total'] += processing_time
            self.stats['avg_validation_time'] = (
                self.stats['validation_time_total'] / self.stats['validations_performed']
            )
            
            if is_valid:
                self.stats['passed_validations'] += 1
            else:
                self.stats['failed_validations'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation performance statistics"""
        with self._lock:
            stats = self.stats.copy()
        
        if stats['validations_performed'] > 0:
            stats['pass_rate'] = stats['passed_validations'] / stats['validations_performed']
        else:
            stats['pass_rate'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """Reset performance statistics"""
        with self._lock:
            self.stats = {
                'validations_performed': 0,
                'validation_time_total': 0.0,
                'avg_validation_time': 0.0,
                'passed_validations': 0,
                'failed_validations': 0
            }
        logger.info("FastValidator statistics reset")
    
    def refresh_known_data(self):
        """Refresh known data from database"""
        self._known_items.clear()
        self._known_traders.clear()
        self._load_known_data()
        logger.info("Known data refreshed from database")

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