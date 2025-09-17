"""
Main Arduino Automation System Coordinator
Coordinates Arduino communication, database monitoring, array processing, and OCR
"""

import logging
import signal
import sys
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional
import threading

# Add current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager, ConfigurationError
from arduino_controller import ArduinoController
from database_integration import AutomationDatabaseManager
from tesseract_ocr import TesseractOCRManager
from database_monitor import DatabaseMonitorThread
from array_processor import ArrayProcessorThread


class AutomationSystemCoordinator:
    """
    Main coordinator for Arduino automation system.
    Manages all components and provides unified control interface.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize automation system coordinator.
        
        Args:
            config_dir: Optional path to configuration directory
        """
        # Setup logging first
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # System state
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # Configuration management
        self.config_manager = ConfigManager(config_dir)
        self.config: Optional[Dict[str, Any]] = None
        
        # Core components
        self.arduino_controller: Optional[ArduinoController] = None
        self.db_manager: Optional[AutomationDatabaseManager] = None
        self.ocr_manager: Optional[TesseractOCRManager] = None
        
        # Processing threads
        self.database_monitor: Optional[DatabaseMonitorThread] = None
        self.array_processor: Optional[ArrayProcessorThread] = None
        
        # System statistics
        self.start_time: Optional[float] = None
        self.stats = {
            'system_starts': 0,
            'total_uptime': 0.0,
            'last_error': None,
            'arduino_reconnects': 0
        }
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        self.logger.info("Arduino Automation System Coordinator initialized")
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Basic logging setup - will be updated with config later
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _update_logging_config(self) -> None:
        """Update logging configuration from loaded config."""
        try:
            log_config = self.config_manager.get_logging_config()
            
            # Get or create logger
            root_logger = logging.getLogger()
            
            # Set log level
            level_str = log_config.get('level', 'INFO')
            level = getattr(logging, level_str.upper(), logging.INFO)
            root_logger.setLevel(level)
            
            # Clear existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Create formatter
            log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            formatter = logging.Formatter(log_format)
            
            # Add console handler if enabled
            if log_config.get('console_output', True):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            # Add file handler if enabled
            if log_config.get('log_to_file', False):
                log_file = log_config.get('log_file', 'automation_system.log')
                
                # Create logs directory if needed
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                from logging.handlers import RotatingFileHandler
                max_size = log_config.get('max_log_size_mb', 50) * 1024 * 1024
                backup_count = log_config.get('backup_count', 3)
                
                file_handler = RotatingFileHandler(
                    log_file, maxBytes=max_size, backupCount=backup_count
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            
            self.logger.info("Logging configuration updated")
            
        except Exception as e:
            self.logger.error(f"Failed to update logging config: {e}")
    
    def load_configuration(self) -> None:
        """Load and validate system configuration."""
        try:
            self.logger.info("Loading configuration...")
            
            # Load main automation config
            self.config = self.config_manager.load_automation_config(validate=True)
            
            # Load Arduino setup config  
            self.config_manager.load_arduino_setup_config()
            
            # Update logging with config
            self._update_logging_config()
            
            # Auto-detect Arduino port if needed
            arduino_config = self.config_manager.get_arduino_config()
            port = arduino_config.get('serial_port')
            
            if arduino_config.get('auto_detect_port', True) and (not port or port.startswith('PLACEHOLDER')):
                detected_port = self.config_manager.auto_detect_arduino_port()
                if detected_port:
                    self.config_manager.update_arduino_port(detected_port)
                    self.logger.info(f"Auto-detected Arduino port: {detected_port}")
                else:
                    self.logger.warning("Arduino auto-detection failed")
            
            self.logger.info("Configuration loaded successfully")
            
        except ConfigurationError as e:
            self.logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def initialize_components(self) -> None:
        """Initialize all system components."""
        try:
            self.logger.info("Initializing system components...")
            
            # Initialize Arduino controller
            arduino_config = self.config_manager.get_arduino_config()
            self.arduino_controller = ArduinoController(
                port=arduino_config.get('serial_port', 'COM3'),
                baudrate=arduino_config.get('baudrate', 9600),
                timeout=arduino_config.get('connection_timeout', 5)
            )
            
            # Test Arduino connection
            if not self.arduino_controller.ping():
                self.logger.error("Arduino connection test failed")
                raise RuntimeError("Cannot connect to Arduino")
            
            self.logger.info("Arduino controller initialized")
            
            # Initialize database manager
            db_config = self.config_manager.get_database_config()
            db_path = db_config.get('db_path', 'automation.db')
            
            # Convert relative path to absolute if needed
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', db_path)
                db_path = os.path.abspath(db_path)
            
            self.db_manager = AutomationDatabaseManager(
                db_path=db_path,
                connection_timeout=db_config.get('connection_timeout', 30)
            )
            
            self.logger.info(f"Database manager initialized: {db_path}")
            
            # Initialize OCR manager
            ocr_config = self.config_manager.get_tesseract_config()
            self.ocr_manager = TesseractOCRManager(ocr_config)
            
            self.logger.info("OCR manager initialized")
            
            # Initialize processing threads
            threads_config = self.config_manager.get_automation_config().get('threads', {})
            
            if threads_config.get('main_thread_enabled', True):
                self.database_monitor = DatabaseMonitorThread(
                    self.arduino_controller,
                    self.db_manager,
                    self.ocr_manager,
                    self.config
                )
                self.logger.info("Database monitor thread initialized")
            
            if threads_config.get('secondary_thread_enabled', True):
                self.array_processor = ArrayProcessorThread(
                    self.arduino_controller,
                    self.db_manager,
                    self.config
                )
                self.logger.info("Array processor thread initialized")
            
            self.logger.info("All system components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    def start_system(self) -> None:
        """Start the automation system."""
        try:
            if self.is_running:
                self.logger.warning("System already running")
                return
            
            self.logger.info("Starting Arduino automation system...")
            
            self.is_running = True
            self.start_time = time.time()
            self.stats['system_starts'] += 1
            
            # Start processing threads
            threads_config = self.config_manager.get_automation_config().get('threads', {})
            startup_delay = threads_config.get('thread_startup_delay', 3)
            
            if self.database_monitor:
                self.database_monitor.start()
                self.logger.info("Database monitor thread started")
                
                if startup_delay > 0:
                    time.sleep(startup_delay)
            
            if self.array_processor:
                self.array_processor.start()
                self.logger.info("Array processor thread started")
            
            self.logger.info("Arduino automation system started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            self.stats['last_error'] = str(e)
            self.is_running = False
            raise
    
    def stop_system(self) -> None:
        """Stop the automation system."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping Arduino automation system...")
        
        try:
            # Stop processing threads
            if self.array_processor:
                self.array_processor.stop()
                self.logger.info("Array processor thread stopped")
            
            if self.database_monitor:
                self.database_monitor.stop()
                self.logger.info("Database monitor thread stopped")
            
            # Stop OCR monitoring
            if self.ocr_manager:
                self.ocr_manager.stop_all_monitors()
                self.logger.info("OCR monitoring stopped")
            
            # Close Arduino connection
            if self.arduino_controller:
                self.arduino_controller.close()
                self.logger.info("Arduino connection closed")
            
            # Close database connections
            if self.db_manager:
                self.db_manager.close_connection()
                self.logger.info("Database connections closed")
            
            # Update statistics
            if self.start_time:
                self.stats['total_uptime'] += time.time() - self.start_time
            
            self.is_running = False
            self.logger.info("Arduino automation system stopped")
            
        except Exception as e:
            self.logger.error(f"Error during system shutdown: {e}")
    
    def shutdown(self) -> None:
        """Graceful system shutdown."""
        self.logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()
        self.stop_system()
    
    def run(self) -> None:
        """Main run loop for the automation system."""
        try:
            # Load configuration
            self.load_configuration()
            
            # Validate configuration readiness
            validation = self.config_manager.validate_configuration_readiness()
            if not validation['ready']:
                self.logger.error("Configuration validation failed:")
                for error in validation['errors']:
                    self.logger.error(f"  - {error}")
                return
            
            if validation['warnings']:
                self.logger.warning("Configuration warnings:")
                for warning in validation['warnings']:
                    self.logger.warning(f"  - {warning}")
            
            # Initialize components
            self.initialize_components()
            
            # Start system
            self.start_system()
            
            # Main run loop
            self.logger.info("Entering main run loop...")
            
            monitoring_interval = self.config.get('monitoring', {}).get('health_check_interval', 30)
            
            while self.is_running and not self.shutdown_event.is_set():
                try:
                    # Health monitoring
                    self._perform_health_checks()
                    
                    # Wait for shutdown or next health check
                    if self.shutdown_event.wait(monitoring_interval):
                        break
                        
                except KeyboardInterrupt:
                    self.logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    self.stats['last_error'] = str(e)
                    time.sleep(5)  # Wait before continuing
            
        except Exception as e:
            self.logger.error(f"Critical system error: {e}")
            self.stats['last_error'] = str(e)
        finally:
            self.stop_system()
    
    def _perform_health_checks(self) -> None:
        """Perform periodic health checks."""
        try:
            # Check Arduino connection
            if self.arduino_controller and not self.arduino_controller.ping():
                self.logger.warning("Arduino connection lost, attempting reconnect...")
                if self.arduino_controller.reset_connection():
                    self.stats['arduino_reconnects'] += 1
                    self.logger.info("Arduino reconnection successful")
                else:
                    self.logger.error("Arduino reconnection failed")
            
            # Log system status
            if self.logger.isEnabledFor(logging.DEBUG):
                status = self.get_system_status()
                self.logger.debug(f"System status: {status}")
                
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary with system status information
        """
        status = {
            'running': self.is_running,
            'uptime_seconds': time.time() - self.start_time if self.start_time else 0,
            'statistics': self.stats.copy(),
            'arduino_status': None,
            'database_monitor_status': None,
            'array_processor_status': None,
            'ocr_status': None
        }
        
        # Arduino status
        if self.arduino_controller:
            status['arduino_status'] = self.arduino_controller.get_connection_status()
        
        # Database monitor status
        if self.database_monitor:
            status['database_monitor_status'] = self.database_monitor.get_status()
        
        # Array processor status
        if self.array_processor:
            status['array_processor_status'] = self.array_processor.get_status()
        
        # OCR status
        if self.ocr_manager:
            status['ocr_status'] = self.ocr_manager.get_statistics()
        
        return status
    
    def add_automation_target(self, target_name: str) -> int:
        """
        Add new automation target to database.
        
        Args:
            target_name: Name of target to add
            
        Returns:
            Target ID
        """
        if not self.db_manager:
            raise RuntimeError("Database manager not initialized")
        
        return self.db_manager.add_automation_target(target_name)
    
    def get_automation_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get automation statistics.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Statistics dictionary
        """
        if not self.db_manager:
            return {}
        
        return self.db_manager.get_automation_statistics(hours)


def main():
    """Main entry point for Arduino automation system."""
    print("Arduino Automation System")
    print("=" * 50)
    
    # Create system coordinator
    coordinator = AutomationSystemCoordinator()
    
    try:
        # Run the system
        coordinator.run()
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"System error: {e}")
        logging.getLogger().error(f"System error: {e}", exc_info=True)
    finally:
        print("Arduino automation system terminated")


if __name__ == "__main__":
    main()