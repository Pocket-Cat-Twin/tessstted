"""
Configuration management for market monitoring system.
Handles loading, validation, and access to all configuration parameters.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging


@dataclass
class HotkeyConfig:
    """Configuration for individual hotkey."""
    area: Tuple[int, int, int, int]  # x1, y1, x2, y2
    folder: str
    merge_interval: int
    enabled: bool
    description: str = ""
    screenshot_type: str = "individual_seller_items"
    processing_type: str = "full"  # NEW FIELD: 'full' or 'minimal'


@dataclass  
class YandexOCRConfig:
    """Configuration for Yandex OCR API."""
    api_key: str
    api_url: str
    max_retries: int = 3
    timeout: int = 30
    retry_delay: int = 5
    max_image_size_mb: int = 20


@dataclass
class MonitoringConfig:
    """Configuration for monitoring system."""
    status_check_interval: int = 600
    cleanup_old_data_days: int = 30
    max_screenshots_per_batch: int = 50
    status_transition_delay: int = 600


@dataclass
class PathsConfig:
    """Configuration for file paths."""
    temp_screenshots: str
    temp_merged: str
    database: str
    logs: str
    
    def __post_init__(self):
        """Ensure all paths are Path objects."""
        self.temp_screenshots = Path(self.temp_screenshots)
        self.temp_merged = Path(self.temp_merged)
        self.database = Path(self.database)
        self.logs = Path(self.logs)


@dataclass
class LoggingConfig:
    """Configuration for logging system."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_log_size_mb: int = 100
    backup_count: int = 5
    console_output: bool = True


@dataclass
class DatabaseConfig:
    """Configuration for database operations."""
    connection_timeout: int = 30
    max_retries: int = 3
    backup_enabled: bool = True
    vacuum_interval_days: int = 7


@dataclass
class ImageProcessingConfig:
    """Configuration for image processing."""
    max_image_width: int = 4000
    max_image_height: int = 8000
    jpeg_quality: int = 85
    optimize_for_ocr: bool = True


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


class SettingsManager:
    """
    Centralized configuration management for the market monitoring system.
    Handles loading, validation, and access to all configuration parameters.
    """
    
    DEFAULT_CONFIG_FILE = "config.json"
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = Path(config_file) if config_file else Path(self.DEFAULT_CONFIG_FILE)
        self._config_data: Dict[str, Any] = {}
        self._last_modified: Optional[float] = None
        
        # Configuration objects
        self.hotkeys: Dict[str, HotkeyConfig] = {}
        self.yandex_ocr: Optional[YandexOCRConfig] = None
        self.monitoring: Optional[MonitoringConfig] = None
        self.paths: Optional[PathsConfig] = None
        self.logging: Optional[LoggingConfig] = None
        self.database: Optional[DatabaseConfig] = None
        self.image_processing: Optional[ImageProcessingConfig] = None
        
        # Load initial configuration
        self.load_config()
        
    def load_config(self, force_reload: bool = False) -> None:
        """
        Load configuration from file.
        
        Args:
            force_reload: Force reload even if file hasn't changed
        """
        try:
            if not self.config_file.exists():
                raise ConfigurationError(f"Configuration file not found: {self.config_file}")
            
            # Check if file has been modified
            current_modified = self.config_file.stat().st_mtime
            if not force_reload and self._last_modified == current_modified:
                return
            
            # Load configuration data
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
            
            self._last_modified = current_modified
            
            # Parse configuration sections
            self._parse_hotkeys_config()
            self._parse_yandex_ocr_config()
            self._parse_monitoring_config()
            self._parse_paths_config()
            self._parse_logging_config()
            self._parse_database_config()
            self._parse_image_processing_config()
            
            # Validate configuration
            self._validate_config()
            
            # Create necessary directories
            self._create_directories()
            
            logging.getLogger(__name__).info("Configuration loaded successfully")
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _parse_hotkeys_config(self) -> None:
        """Parse hotkeys configuration."""
        hotkeys_data = self._config_data.get('hotkeys', {})
        self.hotkeys = {}
        
        for key, config in hotkeys_data.items():
            try:
                self.hotkeys[key] = HotkeyConfig(
                    area=tuple(config['area']),
                    folder=config['folder'],
                    merge_interval=config['merge_interval'],
                    enabled=config.get('enabled', True),
                    description=config.get('description', ''),
                    screenshot_type=config.get('screenshot_type', 'individual_seller_items')
                )
            except (KeyError, TypeError, ValueError) as e:
                raise ConfigurationError(f"Invalid hotkey configuration for '{key}': {e}")
    
    def _parse_yandex_ocr_config(self) -> None:
        """Parse Yandex OCR configuration."""
        ocr_data = self._config_data.get('yandex_ocr', {})
        
        try:
            self.yandex_ocr = YandexOCRConfig(
                api_key=ocr_data['api_key'],
                api_url=ocr_data['api_url'],
                max_retries=ocr_data.get('max_retries', 3),
                timeout=ocr_data.get('timeout', 30),
                retry_delay=ocr_data.get('retry_delay', 5),
                max_image_size_mb=ocr_data.get('max_image_size_mb', 20)
            )
        except KeyError as e:
            raise ConfigurationError(f"Missing required OCR configuration: {e}")
    
    def _parse_monitoring_config(self) -> None:
        """Parse monitoring configuration."""
        monitoring_data = self._config_data.get('monitoring', {})
        
        self.monitoring = MonitoringConfig(
            status_check_interval=monitoring_data.get('status_check_interval', 600),
            cleanup_old_data_days=monitoring_data.get('cleanup_old_data_days', 30),
            max_screenshots_per_batch=monitoring_data.get('max_screenshots_per_batch', 50),
            status_transition_delay=monitoring_data.get('status_transition_delay', 600)
        )
    
    def _parse_paths_config(self) -> None:
        """Parse paths configuration."""
        paths_data = self._config_data.get('paths', {})
        
        try:
            self.paths = PathsConfig(
                temp_screenshots=paths_data.get('temp_screenshots', 'data/temp/screenshots'),
                temp_merged=paths_data.get('temp_merged', 'data/temp/merged'),
                database=paths_data.get('database', 'database/market_data.db'),
                logs=paths_data.get('logs', 'data/logs')
            )
        except Exception as e:
            raise ConfigurationError(f"Invalid paths configuration: {e}")
    
    def _parse_logging_config(self) -> None:
        """Parse logging configuration."""
        logging_data = self._config_data.get('logging', {})
        
        self.logging = LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            format=logging_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            max_log_size_mb=logging_data.get('max_log_size_mb', 100),
            backup_count=logging_data.get('backup_count', 5),
            console_output=logging_data.get('console_output', True)
        )
    
    def _parse_database_config(self) -> None:
        """Parse database configuration."""
        db_data = self._config_data.get('database', {})
        
        self.database = DatabaseConfig(
            connection_timeout=db_data.get('connection_timeout', 30),
            max_retries=db_data.get('max_retries', 3),
            backup_enabled=db_data.get('backup_enabled', True),
            vacuum_interval_days=db_data.get('vacuum_interval_days', 7)
        )
    
    def _parse_image_processing_config(self) -> None:
        """Parse image processing configuration."""
        img_data = self._config_data.get('image_processing', {})
        
        self.image_processing = ImageProcessingConfig(
            max_image_width=img_data.get('max_image_width', 4000),
            max_image_height=img_data.get('max_image_height', 8000),
            jpeg_quality=img_data.get('jpeg_quality', 85),
            optimize_for_ocr=img_data.get('optimize_for_ocr', True)
        )
    
    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        errors = []
        
        # Validate hotkeys
        if not self.hotkeys:
            errors.append("No hotkeys configured")
        
        for key, config in self.hotkeys.items():
            if len(config.area) != 4:
                errors.append(f"Hotkey '{key}': area must have 4 coordinates")
            if config.merge_interval <= 0:
                errors.append(f"Hotkey '{key}': merge_interval must be positive")
        
        # Validate OCR config
        if self.yandex_ocr:
            if not self.yandex_ocr.api_key or self.yandex_ocr.api_key == "your_api_key_here":
                errors.append("Yandex OCR API key not configured")
            if not self.yandex_ocr.api_url:
                errors.append("Yandex OCR API URL not configured")
            if self.yandex_ocr.timeout <= 0:
                errors.append("OCR timeout must be positive")
        
        # Validate monitoring config
        if self.monitoring:
            if self.monitoring.status_check_interval <= 0:
                errors.append("Status check interval must be positive")
            if self.monitoring.cleanup_old_data_days <= 0:
                errors.append("Cleanup days must be positive")
        
        if errors:
            raise ConfigurationError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def _create_directories(self) -> None:
        """Create necessary directories based on configuration."""
        if self.paths:
            # Create base directories
            directories = [
                self.paths.temp_screenshots,
                self.paths.temp_merged,
                self.paths.logs,
                self.paths.database.parent
            ]
            
            # Create hotkey-specific screenshot directories
            for hotkey_config in self.hotkeys.values():
                directories.append(self.paths.temp_screenshots / hotkey_config.folder)
            
            # Create all directories
            for directory in directories:
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to create directory {directory}: {e}")
    
    def get_enabled_hotkeys(self) -> Dict[str, HotkeyConfig]:
        """Get only enabled hotkeys."""
        return {key: config for key, config in self.hotkeys.items() if config.enabled}
    
    def get_hotkey_config(self, key: str) -> Optional[HotkeyConfig]:
        """
        Get configuration for specific hotkey.
        
        Args:
            key: Hotkey name
            
        Returns:
            HotkeyConfig object or None if not found
        """
        return self.hotkeys.get(key)
    
    def is_hotkey_enabled(self, key: str) -> bool:
        """
        Check if hotkey is enabled.
        
        Args:
            key: Hotkey name
            
        Returns:
            True if enabled, False otherwise
        """
        config = self.hotkeys.get(key)
        return config.enabled if config else False
    
    def get_screenshot_path(self, hotkey: str) -> Optional[Path]:
        """
        Get screenshot directory path for hotkey.
        
        Args:
            hotkey: Hotkey name
            
        Returns:
            Path to screenshot directory or None
        """
        config = self.get_hotkey_config(hotkey)
        if config and self.paths:
            return self.paths.temp_screenshots / config.folder
        return None
    
    def reload_if_changed(self) -> bool:
        """
        Reload configuration if file has been modified.
        
        Returns:
            True if configuration was reloaded, False otherwise
        """
        if not self.config_file.exists():
            return False
        
        current_modified = self.config_file.stat().st_mtime
        if self._last_modified != current_modified:
            try:
                self.load_config()
                return True
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to reload configuration: {e}")
        
        return False
    
    def save_config(self, backup: bool = True) -> None:
        """
        Save current configuration to file.
        
        Args:
            backup: Whether to create backup of existing file
        """
        try:
            # Create backup if requested
            if backup and self.config_file.exists():
                backup_path = self.config_file.with_suffix('.backup.json')
                backup_path.write_text(self.config_file.read_text(encoding='utf-8'), encoding='utf-8')
            
            # Save configuration
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=4, ensure_ascii=False)
            
            logging.getLogger(__name__).info("Configuration saved successfully")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get summary of current configuration.
        
        Returns:
            Dictionary with configuration summary
        """
        return {
            'config_file': str(self.config_file),
            'last_modified': datetime.fromtimestamp(self._last_modified).isoformat() if self._last_modified else None,
            'hotkeys': {
                'total': len(self.hotkeys),
                'enabled': len(self.get_enabled_hotkeys()),
                'disabled': len(self.hotkeys) - len(self.get_enabled_hotkeys())
            },
            'yandex_ocr': {
                'configured': bool(self.yandex_ocr and self.yandex_ocr.api_key != "your_api_key_here"),
                'api_url': self.yandex_ocr.api_url if self.yandex_ocr else None
            },
            'monitoring': {
                'check_interval': self.monitoring.status_check_interval if self.monitoring else None,
                'cleanup_days': self.monitoring.cleanup_old_data_days if self.monitoring else None
            },
            'paths': {
                'database': str(self.paths.database) if self.paths else None,
                'logs': str(self.paths.logs) if self.paths else None
            }
        }