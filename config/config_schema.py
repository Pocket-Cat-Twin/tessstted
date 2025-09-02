"""
Comprehensive Configuration Validation Schema for Game Monitor System
Provides JSON Schema validation for all configuration parameters with range checking and type validation.
"""

import json
import logging
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import jsonschema
from jsonschema import Draft7Validator, ValidationError
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_config: Optional[Dict[str, Any]] = None


class ConfigValidator:
    """
    Comprehensive configuration validator with JSON Schema validation and business rules.
    
    Features:
    - JSON Schema validation for all config parameters
    - Range validation for numeric values
    - Path existence checking
    - Business logic validation
    - Configuration normalization
    - Hot-reload capability
    """
    
    def __init__(self):
        self.schema = self._create_comprehensive_schema()
        self.validator = Draft7Validator(self.schema)
        logger.info("ConfigValidator initialized with comprehensive schema")
    
    def _create_comprehensive_schema(self) -> Dict[str, Any]:
        """Create comprehensive JSON Schema for all configuration parameters"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Game Monitor System Configuration Schema",
            "type": "object",
            "required": ["screen", "ocr", "validation", "performance", "database", "hotkeys", "logging"],
            "additionalProperties": False,
            "properties": {
                # Screen capture settings
                "screen": {
                    "type": "object",
                    "required": ["trader_list_region", "item_scan_region", "trader_inventory_region"],
                    "additionalProperties": False,
                    "properties": {
                        "trader_list_region": self._create_region_schema("Trader list region"),
                        "item_scan_region": self._create_region_schema("Item scan region"),
                        "trader_inventory_region": self._create_region_schema("Trader inventory region"),
                        "screenshot_save_path": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 255,
                            "pattern": "^[^<>:\"|?*]*$",
                            "description": "Path for saving screenshots"
                        },
                        "save_screenshots": {
                            "type": "boolean",
                            "description": "Auto-save screenshots for debugging"
                        },
                        "screenshot_format": {
                            "type": "string",
                            "enum": ["png", "jpg", "jpeg", "bmp", "tiff"],
                            "description": "Screenshot image format"
                        }
                    }
                },
                
                # OCR engine settings
                "ocr": {
                    "type": "object",
                    "required": ["confidence_threshold", "max_processing_time"],
                    "additionalProperties": False,
                    "properties": {
                        "confidence_threshold": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Confidence threshold for accepting OCR results"
                        },
                        "max_processing_time": {
                            "type": "number",
                            "minimum": 0.1,
                            "maximum": 10.0,
                            "description": "Maximum OCR processing time in seconds"
                        },
                        "use_cache": {
                            "type": "boolean",
                            "description": "Use OCR result caching for performance"
                        },
                        "languages": {
                            "type": "string",
                            "pattern": "^[a-z]{3}(\\+[a-z]{3})*$",
                            "description": "OCR language packs (e.g., 'eng+rus')"
                        },
                        "region_configs": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "trader_name": self._create_ocr_region_config_schema(),
                                "quantity": self._create_ocr_region_config_schema(),
                                "price": self._create_ocr_region_config_schema(),
                                "item_name": self._create_ocr_region_config_schema()
                            }
                        },
                        "preprocessing": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "enable": {"type": "boolean"},
                                "contrast_enhancement": {"type": "boolean"},
                                "noise_reduction": {"type": "boolean"},
                                "text_region_detection": {"type": "boolean"}
                            }
                        }
                    }
                },
                
                # Data validation settings
                "validation": {
                    "type": "object",
                    "required": ["default_level"],
                    "additionalProperties": False,
                    "properties": {
                        "default_level": {
                            "type": "string",
                            "enum": ["permissive", "balanced", "strict"],
                            "description": "Default validation level"
                        },
                        "strict_mode_items": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 50
                            },
                            "uniqueItems": True,
                            "description": "Items requiring strict validation"
                        },
                        "auto_approve_threshold": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Auto-approve threshold for skipping manual verification"
                        },
                        "use_historical_validation": {
                            "type": "boolean",
                            "description": "Use historical data for validation"
                        },
                        "detect_suspicious_patterns": {
                            "type": "boolean",
                            "description": "Enable suspicious pattern detection"
                        }
                    }
                },
                
                # Performance settings
                "performance": {
                    "type": "object",
                    "required": ["max_capture_time", "warning_threshold"],
                    "additionalProperties": False,
                    "properties": {
                        "max_capture_time": {
                            "type": "number",
                            "minimum": 0.1,
                            "maximum": 30.0,
                            "description": "Maximum total capture time in seconds"
                        },
                        "warning_threshold": {
                            "type": "number",
                            "minimum": 0.1,
                            "maximum": 30.0,
                            "description": "Warning threshold for slow operations"
                        },
                        "enable_performance_logging": {
                            "type": "boolean",
                            "description": "Enable detailed performance logging"
                        },
                        "enable_monitoring": {
                            "type": "boolean",
                            "description": "Enable performance monitoring"
                        },
                        "alert_thresholds": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "slow_capture": {
                                    "type": "number",
                                    "minimum": 0.1,
                                    "maximum": 60.0
                                },
                                "low_confidence": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0
                                },
                                "high_error_rate": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0
                                }
                            }
                        }
                    }
                },
                
                # Database settings
                "database": {
                    "type": "object",
                    "required": ["path", "pool_size"],
                    "additionalProperties": False,
                    "properties": {
                        "path": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 255,
                            "pattern": "^[^<>:\"|?*]*\\.db$",
                            "description": "Database file path"
                        },
                        "pool_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Connection pool size"
                        },
                        "enable_wal": {
                            "type": "boolean",
                            "description": "Enable Write-Ahead Logging"
                        },
                        "cache_size": {
                            "type": "integer",
                            "minimum": 1000,
                            "maximum": 100000,
                            "description": "Database cache size in pages"
                        },
                        "batch_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "description": "Batch operation size"
                        },
                        "cleanup": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "ocr_cache_days": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 365,
                                    "description": "Clean old OCR cache entries after N days"
                                },
                                "screenshot_days": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 3650,
                                    "description": "Clean old screenshots after N days"
                                },
                                "trade_records_days": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 3650,
                                    "description": "Clean old trade records after N days (0 = never)"
                                }
                            }
                        }
                    }
                },
                
                # Hotkey settings
                "hotkeys": {
                    "type": "object",
                    "required": ["mappings"],
                    "additionalProperties": False,
                    "properties": {
                        "mappings": {
                            "type": "object",
                            "required": ["trader_list", "item_scan", "trader_inventory", "manual_verification", "emergency_stop"],
                            "additionalProperties": False,
                            "properties": {
                                "trader_list": self._create_hotkey_schema(),
                                "item_scan": self._create_hotkey_schema(),
                                "trader_inventory": self._create_hotkey_schema(),
                                "manual_verification": self._create_hotkey_schema(),
                                "emergency_stop": self._create_hotkey_schema()
                            }
                        },
                        "max_queue_size": {
                            "type": "integer",
                            "minimum": 10,
                            "maximum": 1000,
                            "description": "Maximum hotkey queue size"
                        },
                        "processing_timeout": {
                            "type": "number",
                            "minimum": 1.0,
                            "maximum": 60.0,
                            "description": "Hotkey processing timeout in seconds"
                        },
                        "enable_statistics": {
                            "type": "boolean",
                            "description": "Enable hotkey statistics"
                        }
                    }
                },
                
                # Logging settings
                "logging": {
                    "type": "object",
                    "required": ["level", "file"],
                    "additionalProperties": False,
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            "description": "Logging level"
                        },
                        "file": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 255,
                            "pattern": "^[^<>:\"|?*]*\\.log$",
                            "description": "Log file path"
                        },
                        "max_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "description": "Maximum log file size in MB"
                        },
                        "backup_count": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Number of backup log files"
                        },
                        "format": {
                            "type": "string",
                            "minLength": 10,
                            "maxLength": 500,
                            "description": "Log message format"
                        },
                        "console": {
                            "type": "boolean",
                            "description": "Enable console logging"
                        }
                    }
                },
                
                # GUI settings (optional)
                "gui": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "window": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "width": {"type": "integer", "minimum": 400, "maximum": 3840},
                                "height": {"type": "integer", "minimum": 300, "maximum": 2160},
                                "title": {"type": "string", "minLength": 1, "maxLength": 100}
                            }
                        },
                        "theme": {
                            "type": "string",
                            "enum": ["light", "dark", "auto"],
                            "description": "GUI theme"
                        },
                        "update_intervals": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "statistics": {"type": "number", "minimum": 0.1, "maximum": 10.0},
                                "status": {"type": "number", "minimum": 0.1, "maximum": 5.0},
                                "logs": {"type": "number", "minimum": 0.5, "maximum": 10.0}
                            }
                        }
                    }
                },
                
                # Advanced settings (optional)
                "advanced": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "thread_pool_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 16,
                            "description": "Thread pool size for background operations"
                        },
                        "max_memory_mb": {
                            "type": "integer",
                            "minimum": 50,
                            "maximum": 4096,
                            "description": "Maximum memory usage in MB"
                        },
                        "experimental": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "multi_engine_ocr": {"type": "boolean"},
                                "ai_enhancement": {"type": "boolean"},
                                "auto_calibration": {"type": "boolean"}
                            }
                        },
                        "debug": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "save_processed_images": {"type": "boolean"},
                                "enable_timing_logs": {"type": "boolean"},
                                "verbose_validation": {"type": "boolean"}
                            }
                        }
                    }
                }
            }
        }
    
    def _create_region_schema(self, description: str) -> Dict[str, Any]:
        """Create schema for screen region configuration"""
        return {
            "type": "object",
            "required": ["x", "y", "width", "height"],
            "additionalProperties": False,
            "properties": {
                "x": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 7680,  # Support 8K monitors
                    "description": "Region X coordinate"
                },
                "y": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 4320,  # Support 8K monitors
                    "description": "Region Y coordinate"
                },
                "width": {
                    "type": "integer",
                    "minimum": 50,
                    "maximum": 7680,
                    "description": "Region width"
                },
                "height": {
                    "type": "integer",
                    "minimum": 30,
                    "maximum": 4320,
                    "description": "Region height"
                }
            },
            "description": description
        }
    
    def _create_ocr_region_config_schema(self) -> Dict[str, Any]:
        """Create schema for OCR region-specific configuration"""
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "psm": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 13,
                    "description": "Tesseract Page Segmentation Mode"
                },
                "whitelist": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Allowed characters for OCR"
                },
                "languages": {
                    "type": "string",
                    "pattern": "^[a-z]{3}(\\+[a-z]{3})*$",
                    "description": "Language pack override for this region"
                }
            }
        }
    
    def _create_hotkey_schema(self) -> Dict[str, Any]:
        """Create schema for hotkey mapping"""
        return {
            "type": "string",
            "pattern": "^(F([1-9]|1[0-2])|ctrl\\+[a-z]|alt\\+[a-z]|shift\\+[a-z]|[a-z])$",
            "description": "Hotkey binding (F1-F12, ctrl+letter, alt+letter, shift+letter, single letter)"
        }
    
    def validate_config(self, config: Dict[str, Any]) -> ConfigValidationResult:
        """
        Validate configuration with comprehensive checking.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            ConfigValidationResult with validation status and details
        """
        errors = []
        warnings = []
        
        try:
            # JSON Schema validation
            schema_errors = list(self.validator.iter_errors(config))
            for error in schema_errors:
                error_path = " -> ".join([str(p) for p in error.absolute_path])
                errors.append(f"Schema validation error at '{error_path}': {error.message}")
            
            if not schema_errors:
                # Business logic validation
                business_errors, business_warnings = self._validate_business_rules(config)
                errors.extend(business_errors)
                warnings.extend(business_warnings)
                
                # Path validation
                path_errors, path_warnings = self._validate_paths(config)
                errors.extend(path_errors)
                warnings.extend(path_warnings)
                
                # Cross-reference validation
                cross_ref_errors, cross_ref_warnings = self._validate_cross_references(config)
                errors.extend(cross_ref_errors)
                warnings.extend(cross_ref_warnings)
            
            # Normalize configuration if no errors
            normalized_config = None
            if not errors:
                normalized_config = self._normalize_config(config)
            
            return ConfigValidationResult(
                is_valid=(len(errors) == 0),
                errors=errors,
                warnings=warnings,
                normalized_config=normalized_config
            )
            
        except Exception as e:
            logger.error(f"Configuration validation failed with exception: {e}")
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"Validation exception: {str(e)}"],
                warnings=[]
            )
    
    def _validate_business_rules(self, config: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate business logic rules"""
        errors = []
        warnings = []
        
        # Performance thresholds validation
        if 'performance' in config:
            perf = config['performance']
            if perf.get('warning_threshold', 0) >= perf.get('max_capture_time', 1):
                errors.append("Performance warning_threshold must be less than max_capture_time")
        
        # OCR confidence vs validation auto-approve threshold
        if 'ocr' in config and 'validation' in config:
            ocr_confidence = config['ocr'].get('confidence_threshold', 0.85)
            auto_approve = config['validation'].get('auto_approve_threshold', 0.95)
            
            if auto_approve <= ocr_confidence:
                warnings.append("Validation auto_approve_threshold should be higher than OCR confidence_threshold")
        
        # Database pool size vs performance expectations
        if 'database' in config:
            pool_size = config['database'].get('pool_size', 5)
            if pool_size > 10:
                warnings.append(f"Database pool_size {pool_size} is quite high - consider if needed")
            elif pool_size < 3:
                warnings.append(f"Database pool_size {pool_size} might be too small for concurrent operations")
        
        # Screen region overlap detection
        if 'screen' in config:
            regions = []
            for region_name in ['trader_list_region', 'item_scan_region', 'trader_inventory_region']:
                if region_name in config['screen']:
                    region = config['screen'][region_name]
                    regions.append((region_name, region))
            
            # Check for overlapping regions
            for i, (name1, region1) in enumerate(regions):
                for name2, region2 in regions[i+1:]:
                    if self._regions_overlap(region1, region2):
                        warnings.append(f"Screen regions '{name1}' and '{name2}' overlap - this may cause conflicts")
        
        return errors, warnings
    
    def _validate_paths(self, config: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate file paths and directories"""
        errors = []
        warnings = []
        
        # Database path directory check
        if 'database' in config and 'path' in config['database']:
            db_path = Path(config['database']['path'])
            parent_dir = db_path.parent
            
            if not parent_dir.exists():
                warnings.append(f"Database directory '{parent_dir}' does not exist - will be created")
        
        # Screenshot save path check
        if 'screen' in config and 'screenshot_save_path' in config['screen']:
            screenshot_path = Path(config['screen']['screenshot_save_path'])
            
            if not screenshot_path.exists():
                warnings.append(f"Screenshot directory '{screenshot_path}' does not exist - will be created")
        
        # Log file path check
        if 'logging' in config and 'file' in config['logging']:
            log_path = Path(config['logging']['file'])
            log_parent = log_path.parent
            
            if not log_parent.exists():
                warnings.append(f"Log directory '{log_parent}' does not exist - will be created")
        
        return errors, warnings
    
    def _validate_cross_references(self, config: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate cross-references between configuration sections"""
        errors = []
        warnings = []
        
        # Hotkey uniqueness validation
        if 'hotkeys' in config and 'mappings' in config['hotkeys']:
            mappings = config['hotkeys']['mappings']
            hotkey_values = list(mappings.values())
            
            # Check for duplicate hotkeys
            unique_hotkeys = set(hotkey_values)
            if len(unique_hotkeys) != len(hotkey_values):
                # Find duplicates
                seen = set()
                duplicates = set()
                for hotkey in hotkey_values:
                    if hotkey in seen:
                        duplicates.add(hotkey)
                    seen.add(hotkey)
                
                errors.append(f"Duplicate hotkeys found: {', '.join(duplicates)}")
        
        # OCR region configs vs defined regions
        if 'ocr' in config and 'region_configs' in config['ocr']:
            region_configs = set(config['ocr']['region_configs'].keys())
            expected_regions = {'trader_name', 'quantity', 'price', 'item_name'}
            
            missing_regions = expected_regions - region_configs
            if missing_regions:
                warnings.append(f"OCR region configs missing for: {', '.join(missing_regions)}")
            
            extra_regions = region_configs - expected_regions
            if extra_regions:
                warnings.append(f"Unknown OCR region configs: {', '.join(extra_regions)}")
        
        return errors, warnings
    
    def _regions_overlap(self, region1: Dict[str, int], region2: Dict[str, int]) -> bool:
        """Check if two screen regions overlap"""
        x1, y1, w1, h1 = region1['x'], region1['y'], region1['width'], region1['height']
        x2, y2, w2, h2 = region2['x'], region2['y'], region2['width'], region2['height']
        
        # Check if rectangles overlap
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)
    
    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize configuration with defaults and computed values"""
        normalized = config.copy()
        
        # Add computed values
        if 'performance' in normalized:
            # Ensure warning threshold is reasonable relative to max capture time
            max_time = normalized['performance'].get('max_capture_time', 1.0)
            warning_threshold = normalized['performance'].get('warning_threshold', max_time * 0.8)
            
            if warning_threshold >= max_time:
                normalized['performance']['warning_threshold'] = max_time * 0.8
        
        # Ensure directories end with proper separators
        if 'screen' in normalized and 'screenshot_save_path' in normalized['screen']:
            path = normalized['screen']['screenshot_save_path']
            if not path.endswith('/') and not path.endswith('\\'):
                # Use forward slash as default
                normalized['screen']['screenshot_save_path'] = path.rstrip('/\\') + '/'
        
        return normalized
    
    def validate_config_file(self, config_path: str) -> ConfigValidationResult:
        """
        Validate configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            ConfigValidationResult with validation status
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            return self.validate_config(config)
            
        except FileNotFoundError:
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"Configuration file not found: {config_path}"],
                warnings=[]
            )
        except yaml.YAMLError as e:
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"YAML parsing error: {str(e)}"],
                warnings=[]
            )
        except Exception as e:
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"Configuration file validation failed: {str(e)}"],
                warnings=[]
            )
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get a default configuration that passes validation"""
        return {
            "screen": {
                "trader_list_region": {"x": 100, "y": 200, "width": 600, "height": 400},
                "item_scan_region": {"x": 200, "y": 150, "width": 500, "height": 300},
                "trader_inventory_region": {"x": 300, "y": 250, "width": 700, "height": 500},
                "screenshot_save_path": "data/screenshots/",
                "save_screenshots": True,
                "screenshot_format": "png"
            },
            "ocr": {
                "confidence_threshold": 0.85,
                "max_processing_time": 0.8,
                "use_cache": True,
                "languages": "eng+rus"
            },
            "validation": {
                "default_level": "balanced",
                "auto_approve_threshold": 0.95,
                "use_historical_validation": True,
                "detect_suspicious_patterns": True
            },
            "performance": {
                "max_capture_time": 1.0,
                "warning_threshold": 0.8,
                "enable_performance_logging": True,
                "enable_monitoring": True
            },
            "database": {
                "path": "data/game_monitor.db",
                "pool_size": 5,
                "enable_wal": True,
                "cache_size": 10000
            },
            "hotkeys": {
                "mappings": {
                    "trader_list": "F1",
                    "item_scan": "F2", 
                    "trader_inventory": "F3",
                    "manual_verification": "F4",
                    "emergency_stop": "F5"
                },
                "max_queue_size": 100,
                "processing_timeout": 5.0,
                "enable_statistics": True
            },
            "logging": {
                "level": "INFO",
                "file": "logs/game_monitor.log",
                "max_size": 50,
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "console": True
            }
        }


# Global validator instance for easy access
_validator_instance = None

def get_config_validator() -> ConfigValidator:
    """Get singleton config validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ConfigValidator()
    return _validator_instance


def validate_config_file(config_path: str) -> ConfigValidationResult:
    """Convenience function to validate a config file"""
    validator = get_config_validator()
    return validator.validate_config_file(config_path)


def validate_config_dict(config: Dict[str, Any]) -> ConfigValidationResult:
    """Convenience function to validate a config dictionary"""
    validator = get_config_validator()
    return validator.validate_config(config)