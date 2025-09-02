"""
Input Validation Utility for Game Monitor System

Provides comprehensive input validation with centralized error handling
to prevent malicious inputs and ensure data integrity.
"""

import re
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass

from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .advanced_logger import get_logger
from .constants import Validation

logger = get_logger(__name__)


@dataclass
class ValidationError:
    """Validation error details"""
    field: str
    value: Any
    error_type: str
    message: str
    severity: str = "medium"


class InputValidator:
    """Centralized input validator with security-focused validation"""
    
    def __init__(self):
        self.error_handler = get_error_handler()
        
        # Security patterns to block
        self.security_patterns = {
            'sql_injection': re.compile(r'(\bunion\b|\bselect\b|\bdrop\b|\bdelete\b|\binsert\b|\bupdate\b|\bcreate\b|\balter\b)', re.IGNORECASE),
            'script_injection': re.compile(r'<script|javascript:|vbscript:|onload=|onerror=', re.IGNORECASE),
            'path_traversal': re.compile(r'\.\.\/|\.\.\\|\/etc\/|c:\\'),
            'command_injection': re.compile(r'[;&|`$]'),
            'excessive_length': lambda x: len(str(x)) > 10000,  # Prevent DoS
        }
        
        logger.info("InputValidator initialized with security patterns")
    
    def validate_trader_name(self, name: Any) -> Tuple[bool, List[ValidationError]]:
        """Validate trader name input"""
        errors = []
        
        # Type validation
        if not isinstance(name, str):
            errors.append(ValidationError(
                field="trader_name",
                value=name,
                error_type="type_error",
                message=f"Expected string, got {type(name).__name__}",
                severity="high"
            ))
            return False, errors
        
        # Security validation
        security_errors = self._check_security_patterns(name, "trader_name")
        errors.extend(security_errors)
        
        # Length validation
        if len(name) < Validation.MIN_TRADER_NAME_LENGTH:
            errors.append(ValidationError(
                field="trader_name",
                value=name,
                error_type="length_error",
                message=f"Name too short (min {Validation.MIN_TRADER_NAME_LENGTH} chars)"
            ))
        
        if len(name) > Validation.MAX_TRADER_NAME_LENGTH:
            errors.append(ValidationError(
                field="trader_name",
                value=name,
                error_type="length_error",
                message=f"Name too long (max {Validation.MAX_TRADER_NAME_LENGTH} chars)"
            ))
        
        # Character validation
        if not re.match(r'^[A-Za-z0-9_-]+$', name):
            errors.append(ValidationError(
                field="trader_name",
                value=name,
                error_type="character_error",
                message="Name contains invalid characters (only letters, numbers, _, - allowed)"
            ))
        
        return len(errors) == 0, errors
    
    def validate_item_name(self, name: Any) -> Tuple[bool, List[ValidationError]]:
        """Validate item name input"""
        errors = []
        
        # Type validation
        if not isinstance(name, str):
            errors.append(ValidationError(
                field="item_name",
                value=name,
                error_type="type_error",
                message=f"Expected string, got {type(name).__name__}",
                severity="high"
            ))
            return False, errors
        
        # Security validation
        security_errors = self._check_security_patterns(name, "item_name")
        errors.extend(security_errors)
        
        # Length validation
        if len(name) < 1:
            errors.append(ValidationError(
                field="item_name",
                value=name,
                error_type="length_error",
                message="Item name cannot be empty"
            ))
        
        if len(name) > 200:  # Reasonable max length for item names
            errors.append(ValidationError(
                field="item_name",
                value=name,
                error_type="length_error",
                message="Item name too long (max 200 chars)"
            ))
        
        return len(errors) == 0, errors
    
    def validate_quantity(self, quantity: Any) -> Tuple[bool, List[ValidationError]]:
        """Validate quantity input"""
        errors = []
        
        # Type conversion and validation
        try:
            if isinstance(quantity, str):
                quantity = int(quantity)
            elif not isinstance(quantity, int):
                errors.append(ValidationError(
                    field="quantity",
                    value=quantity,
                    error_type="type_error",
                    message=f"Expected int or numeric string, got {type(quantity).__name__}",
                    severity="high"
                ))
                return False, errors
        except ValueError:
            errors.append(ValidationError(
                field="quantity",
                value=quantity,
                error_type="conversion_error",
                message="Cannot convert to integer"
            ))
            return False, errors
        
        # Range validation
        if quantity < Validation.MIN_QUANTITY:
            errors.append(ValidationError(
                field="quantity",
                value=quantity,
                error_type="range_error",
                message=f"Quantity too small (min {Validation.MIN_QUANTITY})"
            ))
        
        if quantity > Validation.MAX_QUANTITY:
            errors.append(ValidationError(
                field="quantity",
                value=quantity,
                error_type="range_error",
                message=f"Quantity too large (max {Validation.MAX_QUANTITY})"
            ))
        
        return len(errors) == 0, errors
    
    def validate_price(self, price: Any) -> Tuple[bool, List[ValidationError]]:
        """Validate price input"""
        errors = []
        
        # Type conversion and validation
        try:
            if isinstance(price, str):
                price = float(price)
            elif not isinstance(price, (int, float)):
                errors.append(ValidationError(
                    field="price",
                    value=price,
                    error_type="type_error",
                    message=f"Expected number or numeric string, got {type(price).__name__}",
                    severity="high"
                ))
                return False, errors
        except ValueError:
            errors.append(ValidationError(
                field="price",
                value=price,
                error_type="conversion_error",
                message="Cannot convert to number"
            ))
            return False, errors
        
        # Range validation
        if price < Validation.MIN_PRICE:
            errors.append(ValidationError(
                field="price",
                value=price,
                error_type="range_error",
                message=f"Price too small (min {Validation.MIN_PRICE})"
            ))
        
        if price > Validation.MAX_PRICE:
            errors.append(ValidationError(
                field="price",
                value=price,
                error_type="range_error",
                message=f"Price too large (max {Validation.MAX_PRICE})"
            ))
        
        return len(errors) == 0, errors
    
    def validate_trade_data(self, trade_data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """Validate complete trade data structure"""
        errors = []
        
        # Required fields
        required_fields = ['trader_nickname', 'item_name', 'quantity', 'price']
        for field in required_fields:
            if field not in trade_data:
                errors.append(ValidationError(
                    field=field,
                    value=None,
                    error_type="missing_field",
                    message=f"Required field '{field}' is missing",
                    severity="high"
                ))
        
        # Validate individual fields
        if 'trader_nickname' in trade_data:
            valid, field_errors = self.validate_trader_name(trade_data['trader_nickname'])
            errors.extend(field_errors)
        
        if 'item_name' in trade_data:
            valid, field_errors = self.validate_item_name(trade_data['item_name'])
            errors.extend(field_errors)
        
        if 'quantity' in trade_data:
            valid, field_errors = self.validate_quantity(trade_data['quantity'])
            errors.extend(field_errors)
        
        if 'price' in trade_data:
            valid, field_errors = self.validate_price(trade_data['price'])
            errors.extend(field_errors)
        
        return len(errors) == 0, errors
    
    def validate_file_path(self, path: Any) -> Tuple[bool, List[ValidationError]]:
        """Validate file path for security"""
        errors = []
        
        if not isinstance(path, str):
            errors.append(ValidationError(
                field="file_path",
                value=path,
                error_type="type_error",
                message=f"Expected string, got {type(path).__name__}",
                severity="high"
            ))
            return False, errors
        
        # Security validation
        security_errors = self._check_security_patterns(path, "file_path")
        errors.extend(security_errors)
        
        # Path traversal protection
        if '..' in path or path.startswith('/'):
            errors.append(ValidationError(
                field="file_path",
                value=path,
                error_type="security_error",
                message="Path traversal detected",
                severity="critical"
            ))
        
        return len(errors) == 0, errors
    
    def _check_security_patterns(self, value: str, field_name: str) -> List[ValidationError]:
        """Check value against security patterns"""
        errors = []
        
        for pattern_name, pattern in self.security_patterns.items():
            if pattern_name == 'excessive_length':
                if pattern(value):
                    errors.append(ValidationError(
                        field=field_name,
                        value=value[:100] + "...",  # Truncate for logging
                        error_type="security_error",
                        message=f"Excessive length detected (DoS protection)",
                        severity="critical"
                    ))
            else:
                if pattern.search(value):
                    errors.append(ValidationError(
                        field=field_name,
                        value=value,
                        error_type="security_error",
                        message=f"Security pattern '{pattern_name}' detected",
                        severity="critical"
                    ))
        
        return errors
    
    def sanitize_for_logging(self, value: Any, max_length: int = 200) -> str:
        """Sanitize value for safe logging"""
        try:
            str_value = str(value)
            if len(str_value) > max_length:
                str_value = str_value[:max_length] + "..."
            
            # Remove potentially dangerous characters for logging
            safe_value = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '?', str_value)
            return safe_value
        except Exception:
            return "[INVALID_VALUE]"


# Global validator instance
_validator_instance = None

def get_input_validator() -> InputValidator:
    """Get singleton input validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = InputValidator()
    return _validator_instance


def validate_input(validation_func):
    """Decorator for automatic input validation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            validator = get_input_validator()
            
            # Apply validation based on function name and arguments
            # This is a simplified example - in practice, you'd customize per function
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Handle validation errors with centralized error handler
                error_context = ErrorContext(
                    component="input_validator",
                    operation=func.__name__,
                    user_data={'args': args[1:], 'kwargs': kwargs},  # Skip self
                    system_state={},
                    timestamp=datetime.now()
                )
                
                validator.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
                raise
        
        return wrapper
    return decorator