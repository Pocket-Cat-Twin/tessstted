"""
Configuration Manager for Arduino Automation System
Handles loading, validation, and management of configuration files
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import serial.tools.list_ports


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors"""
    pass


class PlaceholderManager:
    """Manages placeholder detection and validation in configuration"""
    
    PLACEHOLDER_PATTERNS = [
        'PLACEHOLDER_POINT1_X', 'PLACEHOLDER_POINT1_Y',
        'PLACEHOLDER_POINT2_X', 'PLACEHOLDER_POINT2_Y', 
        'PLACEHOLDER_OCR_X', 'PLACEHOLDER_OCR_Y',
        'PLACEHOLDER_OCR_WIDTH', 'PLACEHOLDER_OCR_HEIGHT',
        'PLACEHOLDER_TARGET_AREA_X', 'PLACEHOLDER_TARGET_AREA_Y',
        'PLACEHOLDER_OFFSET_1_X', 'PLACEHOLDER_OFFSET_1_Y',
        'PLACEHOLDER_OFFSET_2_X', 'PLACEHOLDER_OFFSET_2_Y',
        'PLACEHOLDER_OFFSET_3_X', 'PLACEHOLDER_OFFSET_3_Y',
        'PLACEHOLDER_OFFSET_4_X', 'PLACEHOLDER_OFFSET_4_Y',
        'PLACEHOLDER_OFFSET_5_X', 'PLACEHOLDER_OFFSET_5_Y',
        'PLACEHOLDER_OFFSET_6_X', 'PLACEHOLDER_OFFSET_6_Y',
        'PLACEHOLDER_OFFSET_7_X', 'PLACEHOLDER_OFFSET_7_Y',
        'PLACEHOLDER_OFFSET_8_X', 'PLACEHOLDER_OFFSET_8_Y',
        'PLACEHOLDER_OFFSET_9_X', 'PLACEHOLDER_OFFSET_9_Y',
        'PLACEHOLDER_MAIN_HOTKEY', 'PLACEHOLDER_SECONDARY_HOTKEY',
        'PLACEHOLDER_CHAT_HOTKEY', 'PLACEHOLDER_NAME_1',
        'PLACEHOLDER_NAME_2', 'PLACEHOLDER_NAME_3',
        'PLACEHOLDER_NAME_4', 'PLACEHOLDER_NAME_5'
    ]
    
    @classmethod
    def find_placeholders(cls, config: Dict[str, Any]) -> List[str]:
        """
        Find all placeholders in configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of found placeholder strings
        """
        placeholders = []
        
        def search_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    search_recursive(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_recursive(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                if obj.startswith("PLACEHOLDER_"):
                    placeholders.append(f"{path}: {obj}")
            
        search_recursive(config)
        return placeholders
    
    @classmethod
    def validate_no_placeholders(cls, config: Dict[str, Any], 
                                critical_only: bool = False) -> None:
        """
        Validate that no placeholders remain in configuration.
        
        Args:
            config: Configuration to validate
            critical_only: If True, only check critical placeholders
            
        Raises:
            ConfigurationError: If placeholders found
        """
        placeholders = cls.find_placeholders(config)
        
        if placeholders:
            if critical_only:
                # Only check critical sections
                critical_placeholders = [
                    p for p in placeholders 
                    if any(critical in p for critical in [
                        'arduino.serial_port', 'coordinates', 'hotkeys'
                    ])
                ]
                if critical_placeholders:
                    raise ConfigurationError(
                        f"Critical placeholders found: {critical_placeholders}"
                    )
            else:
                raise ConfigurationError(f"Placeholders found: {placeholders}")


class ArduinoPortDetector:
    """Handles automatic detection of Arduino COM ports"""
    
    @staticmethod
    def list_available_ports() -> List[Dict[str, str]]:
        """
        List all available serial ports.
        
        Returns:
            List of dictionaries with port information
        """
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports
    
    @staticmethod
    def find_arduino_ports() -> List[str]:
        """
        Find COM ports that likely contain Arduino devices.
        
        Returns:
            List of COM port names
        """
        arduino_ports = []
        for port in serial.tools.list_ports.comports():
            # Check for Arduino in description or hardware ID
            description = port.description.lower()
            hwid = port.hwid.lower() if port.hwid else ""
            
            if ('arduino' in description or 'arduino' in hwid or
                'usb serial' in description or 'usb' in hwid):
                arduino_ports.append(port.device)
        
        return arduino_ports
    
    @staticmethod
    def test_arduino_connection(port: str, baudrate: int = 9600, 
                              timeout: float = 5.0) -> bool:
        """
        Test if Arduino is connected on specific port.
        
        Args:
            port: COM port to test
            baudrate: Communication speed
            timeout: Connection timeout
            
        Returns:
            True if Arduino responds, False otherwise
        """
        try:
            import serial
            import time
            
            with serial.Serial(port, baudrate, timeout=timeout) as ser:
                time.sleep(2)  # Arduino reset delay
                ser.write(b"PING\n")
                ser.flush()
                
                # Wait for response
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if ser.in_waiting > 0:
                        response = ser.readline().decode().strip()
                        if response in ["PONG", "OK", "READY"]:
                            return True
                    time.sleep(0.1)
                    
        except Exception:
            pass
        
        return False


class ConfigManager:
    """
    Main configuration manager for Arduino automation system.
    Handles loading, validation, and management of all configuration files.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Path to configuration directory
        """
        if config_dir is None:
            # Default to config directory relative to this file
            config_dir = Path(__file__).parent.parent / "config"
        
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)
        
        # Configuration file paths
        self.automation_config_path = self.config_dir / "automation_config.json"
        self.arduino_setup_path = self.config_dir / "arduino_setup.json"
        
        # Loaded configurations
        self.automation_config: Optional[Dict[str, Any]] = None
        self.arduino_setup_config: Optional[Dict[str, Any]] = None
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_automation_config(self, validate: bool = True) -> Dict[str, Any]:
        """
        Load main automation configuration.
        
        Args:
            validate: Whether to validate configuration
            
        Returns:
            Automation configuration dictionary
        """
        try:
            with open(self.automation_config_path, 'r', encoding='utf-8') as f:
                self.automation_config = json.load(f)
            
            if validate:
                self._validate_automation_config()
            
            self.logger.info("Automation configuration loaded successfully")
            return self.automation_config
            
        except FileNotFoundError:
            raise ConfigurationError(
                f"Automation config not found: {self.automation_config_path}"
            )
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in automation config: {e}")
    
    def load_arduino_setup_config(self) -> Dict[str, Any]:
        """
        Load Arduino setup configuration.
        
        Returns:
            Arduino setup configuration dictionary
        """
        try:
            with open(self.arduino_setup_path, 'r', encoding='utf-8') as f:
                self.arduino_setup_config = json.load(f)
            
            self.logger.info("Arduino setup configuration loaded successfully")
            return self.arduino_setup_config
            
        except FileNotFoundError:
            raise ConfigurationError(
                f"Arduino setup config not found: {self.arduino_setup_path}"
            )
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in Arduino setup config: {e}")
    
    def _validate_automation_config(self) -> None:
        """Validate automation configuration structure and values."""
        if not self.automation_config:
            raise ConfigurationError("No automation configuration loaded")
        
        # Validate required sections
        required_sections = ['arduino', 'automation', 'tesseract_ocr', 'database']
        for section in required_sections:
            if section not in self.automation_config:
                raise ConfigurationError(f"Missing required section: {section}")
        
        # Validate Arduino configuration
        arduino_config = self.automation_config['arduino']
        if 'serial_port' not in arduino_config:
            raise ConfigurationError("Missing arduino.serial_port")
        
        # Check for placeholders (warning only)
        try:
            placeholders = PlaceholderManager.find_placeholders(self.automation_config)
            if placeholders:
                self.logger.warning(f"Configuration contains placeholders: {len(placeholders)} found")
                for placeholder in placeholders[:5]:  # Show first 5
                    self.logger.warning(f"  {placeholder}")
                if len(placeholders) > 5:
                    self.logger.warning(f"  ... and {len(placeholders) - 5} more")
        except Exception as e:
            self.logger.error(f"Error checking placeholders: {e}")
    
    def auto_detect_arduino_port(self) -> Optional[str]:
        """
        Automatically detect Arduino COM port.
        
        Returns:
            COM port name if found, None otherwise
        """
        self.logger.info("Auto-detecting Arduino COM port...")
        
        # Get possible Arduino ports
        arduino_ports = ArduinoPortDetector.find_arduino_ports()
        
        if not arduino_ports:
            self.logger.warning("No potential Arduino ports found")
            return None
        
        self.logger.info(f"Found potential Arduino ports: {arduino_ports}")
        
        # Test each port
        for port in arduino_ports:
            self.logger.info(f"Testing port: {port}")
            if ArduinoPortDetector.test_arduino_connection(port):
                self.logger.info(f"Arduino detected on port: {port}")
                return port
        
        self.logger.warning("No Arduino found on detected ports")
        return None
    
    def update_arduino_port(self, port: str) -> None:
        """
        Update Arduino port in configuration.
        
        Args:
            port: New COM port
        """
        if self.automation_config:
            self.automation_config['arduino']['serial_port'] = port
            self.save_automation_config()
            self.logger.info(f"Updated Arduino port to: {port}")
    
    def save_automation_config(self) -> None:
        """Save current automation configuration to file."""
        if not self.automation_config:
            raise ConfigurationError("No automation configuration to save")
        
        try:
            with open(self.automation_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.automation_config, f, indent=4, ensure_ascii=False)
            
            self.logger.info("Automation configuration saved successfully")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save automation config: {e}")
    
    def get_arduino_config(self) -> Dict[str, Any]:
        """Get Arduino-specific configuration."""
        if not self.automation_config:
            self.load_automation_config()
        
        return self.automation_config['arduino']
    
    def get_automation_config(self) -> Dict[str, Any]:
        """Get automation-specific configuration."""
        if not self.automation_config:
            self.load_automation_config()
        
        return self.automation_config['automation']
    
    def get_tesseract_config(self) -> Dict[str, Any]:
        """Get Tesseract OCR configuration."""
        if not self.automation_config:
            self.load_automation_config()
        
        return self.automation_config['tesseract_ocr']
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        if not self.automation_config:
            self.load_automation_config()
        
        return self.automation_config['database']
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        if not self.automation_config:
            self.load_automation_config()
        
        return self.automation_config.get('logging', {})
    
    def validate_configuration_readiness(self) -> Dict[str, Any]:
        """
        Validate that configuration is ready for production use.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'ready': True,
            'warnings': [],
            'errors': [],
            'placeholders_found': [],
            'arduino_connection': None
        }
        
        try:
            # Load configuration
            self.load_automation_config()
            
            # Check for placeholders
            placeholders = PlaceholderManager.find_placeholders(self.automation_config)
            if placeholders:
                results['placeholders_found'] = placeholders
                results['warnings'].append(f"Found {len(placeholders)} placeholders")
            
            # Test Arduino connection
            arduino_config = self.get_arduino_config()
            port = arduino_config.get('serial_port')
            
            if port and not port.startswith('PLACEHOLDER'):
                if ArduinoPortDetector.test_arduino_connection(port):
                    results['arduino_connection'] = 'success'
                else:
                    results['arduino_connection'] = 'failed'
                    results['warnings'].append(f"Cannot connect to Arduino on {port}")
            else:
                results['arduino_connection'] = 'not_configured'
                results['warnings'].append("Arduino port not configured")
            
            # Check database path
            db_config = self.get_database_config()
            db_path = db_config.get('db_path')
            if db_path and not os.path.exists(db_path):
                results['warnings'].append(f"Database path not found: {db_path}")
            
            # Determine overall readiness
            if results['errors']:
                results['ready'] = False
            
        except Exception as e:
            results['ready'] = False
            results['errors'].append(f"Configuration validation failed: {e}")
        
        return results
    
    def create_placeholder_replacement_guide(self) -> str:
        """
        Create a guide for replacing placeholders in configuration.
        
        Returns:
            Formatted guide string
        """
        guide = """
# Configuration Placeholder Replacement Guide

## Coordinates (pixels from top-left of screen)
- PLACEHOLDER_POINT1_X/Y: First click position for array processor
- PLACEHOLDER_POINT2_X/Y: Second click position for array processor  
- PLACEHOLDER_OCR_X/Y: Top-left corner of OCR monitoring region
- PLACEHOLDER_OCR_WIDTH/HEIGHT: Size of OCR monitoring region
- PLACEHOLDER_TARGET_AREA_X/Y: Base position for 9-step mouse pattern
- PLACEHOLDER_OFFSET_*_X/Y: Relative offsets for 9-step pattern

## Hotkeys
- PLACEHOLDER_MAIN_HOTKEY: Primary hotkey (e.g., F1, CTRL+C)
- PLACEHOLDER_SECONDARY_HOTKEY: Secondary hotkey
- PLACEHOLDER_CHAT_HOTKEY: Chat-related hotkey

## Names Array
- PLACEHOLDER_NAME_1-5: Names to process in array automation

## Example Values
```json
"point1": {"x": 100, "y": 200}
"main_hotkey": "F1"
"names_array": ["PlayerName1", "TargetName2"]
```

## Tools for Finding Coordinates
- Windows: Use built-in Screen Snipping Tool coordinates
- Third-party: Mouse position utilities
- Testing: Use Arduino CLICK commands to verify positions
"""
        
        return guide