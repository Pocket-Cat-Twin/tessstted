"""
Main application entry point for market monitoring system.
Initializes and manages all system components.
"""

import sys
import signal
import logging
import threading
from pathlib import Path
from typing import Optional
import time

# Add src directory to Python path for proper imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import SettingsManager, ConfigurationError
from utils.logger import setup_logging, LoggerManager  
from utils.file_utils import FileUtils
from core.database_manager import DatabaseManager
from core.screenshot_capture import ScreenshotCapture
from core.image_processor import ImageProcessor
from core.ocr_client import YandexOCRClient
from core.ocr_queue import OCRQueue
from core.text_parser import TextParser
from core.monitoring_engine import MonitoringEngine
from utils.scheduler import TaskScheduler


class MarketMonitoringSystem:
    """
    Main application class for the market monitoring system.
    Manages initialization, startup, and shutdown of all components.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the market monitoring system.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file
        self.logger: Optional[logging.Logger] = None
        self.logger_manager: Optional[LoggerManager] = None
        
        # System components
        self.settings: Optional[SettingsManager] = None
        self.file_utils: Optional[FileUtils] = None
        self.database: Optional[DatabaseManager] = None
        self.screenshot_capture: Optional[ScreenshotCapture] = None
        self.image_processor: Optional[ImageProcessor] = None
        self.ocr_client: Optional[YandexOCRClient] = None
        self.ocr_queue: Optional[OCRQueue] = None
        self.text_parser: Optional[TextParser] = None
        self.monitoring_engine: Optional[MonitoringEngine] = None
        self.scheduler: Optional[TaskScheduler] = None
        
        # System state
        self._is_running = False
        self._shutdown_event = threading.Event()
        self._initialization_error = None
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            if self.logger:
                self.logger.info(f"Received {signal_name}, initiating shutdown...")
            else:
                print(f"Received {signal_name}, initiating shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def initialize(self) -> bool:
        """
        Initialize all system components.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            print("Initializing Market Monitoring System...")
            
            # Step 1: Load configuration
            print("Loading configuration...")
            self.settings = SettingsManager(self.config_file)
            
            # Step 2: Initialize logging
            print("Setting up logging...")
            self.logger_manager = LoggerManager({
                'logs_dir': str(self.settings.paths.logs),
                'level': self.settings.logging.level,
                'console_output': self.settings.logging.console_output,
                'max_log_size_mb': self.settings.logging.max_log_size_mb,
                'backup_count': self.settings.logging.backup_count
            })
            self.logger = self.logger_manager.get_logger(__name__)
            
            self.logger.info("=== Market Monitoring System Starting ===")
            self.logger.info(f"Configuration loaded from: {self.settings.config_file}")
            
            # Step 3: Initialize file utilities
            self.logger.info("Initializing file utilities...")
            self.file_utils = FileUtils()
            
            # Step 4: Initialize database
            self.logger.info("Initializing database...")
            self.database = DatabaseManager(
                str(self.settings.paths.database),
                self.settings.database.connection_timeout
            )
            
            # Step 5: Initialize core processing components
            self.logger.info("Initializing image processor...")
            self.image_processor = ImageProcessor(self.settings)
            
            self.logger.info("Initializing OCR client...")
            self.ocr_client = YandexOCRClient(self.settings)
            
            self.logger.info("Initializing OCR queue...")
            self.ocr_queue = OCRQueue(
                ocr_client=self.ocr_client,
                num_workers=2,
                max_queue_size=100
            )
            
            self.logger.info("Initializing text parser...")
            self.text_parser = TextParser()
            
            self.logger.info("Initializing monitoring engine...")
            self.monitoring_engine = MonitoringEngine(self.database, self.settings)
            
            # Step 6: Initialize screenshot capture (requires GUI dependencies)
            self.logger.info("Initializing screenshot capture...")
            try:
                self.screenshot_capture = ScreenshotCapture(self.settings)
            except Exception as e:
                self.logger.error(f"Failed to initialize screenshot capture: {e}")
                self.logger.warning("Screenshot capture disabled - system will run in processing-only mode")
                self.screenshot_capture = None
            
            # Step 7: Initialize scheduler
            self.logger.info("Initializing task scheduler...")
            self.scheduler = TaskScheduler(
                settings_manager=self.settings,
                database_manager=self.database,
                image_processor=self.image_processor,
                ocr_queue=self.ocr_queue,
                text_parser=self.text_parser,
                monitoring_engine=self.monitoring_engine
            )
            
            # Step 8: Perform system health checks
            self.logger.info("Performing system health checks...")
            health_ok = self._perform_health_checks()
            
            if not health_ok:
                self.logger.error("System health checks failed")
                return False
            
            self.logger.info("System initialization completed successfully")
            return True
            
        except ConfigurationError as e:
            error_msg = f"Configuration error: {e}"
            print(error_msg)
            if self.logger:
                self.logger.error(error_msg)
            self._initialization_error = error_msg
            return False
            
        except Exception as e:
            error_msg = f"Initialization failed: {e}"
            print(error_msg)
            if self.logger:
                self.logger.error(error_msg)
            self._initialization_error = error_msg
            return False
    
    def _perform_health_checks(self) -> bool:
        """
        Perform system health checks.
        
        Returns:
            True if all health checks pass
        """
        health_ok = True
        
        try:
            # Check database connectivity
            self.logger.info("Checking database connectivity...")
            try:
                stats = self.database.get_monitoring_status_summary()
                self.logger.info(f"Database check passed - status summary: {stats}")
            except Exception as e:
                self.logger.error(f"Database health check failed: {e}")
                health_ok = False
            
            # Check OCR API connectivity (if configured)
            self.logger.info("Checking OCR API connectivity...")
            try:
                if self.ocr_client.test_api_connection():
                    self.logger.info("OCR API check passed")
                else:
                    self.logger.warning("OCR API check failed - OCR functionality may not work")
                    # Don't fail initialization for OCR issues
            except Exception as e:
                self.logger.warning(f"OCR API check error: {e}")
            
            # Check file system permissions
            self.logger.info("Checking file system permissions...")
            try:
                # Test writing to logs directory
                test_file = self.settings.paths.logs / "health_check.tmp"
                test_file.write_text("health check", encoding='utf-8')
                test_file.unlink()
                
                # Test writing to temp directories
                for path in [self.settings.paths.temp_screenshots, self.settings.paths.temp_merged]:
                    path.mkdir(parents=True, exist_ok=True)
                    test_file = path / "health_check.tmp"
                    test_file.write_text("health check", encoding='utf-8')
                    test_file.unlink()
                
                self.logger.info("File system check passed")
                
            except Exception as e:
                self.logger.error(f"File system check failed: {e}")
                health_ok = False
            
            # Check configuration completeness
            self.logger.info("Checking configuration completeness...")
            enabled_hotkeys = self.settings.get_enabled_hotkeys()
            if not enabled_hotkeys:
                self.logger.warning("No enabled hotkeys found - screenshot capture will not work")
            else:
                self.logger.info(f"Configuration check passed - {len(enabled_hotkeys)} enabled hotkeys")
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            health_ok = False
        
        return health_ok
    
    def start(self) -> bool:
        """
        Start the market monitoring system.
        
        Returns:
            True if startup was successful
        """
        try:
            if self._is_running:
                self.logger.warning("System is already running")
                return True
            
            self.logger.info("Starting Market Monitoring System...")
            
            # Start OCR queue
            self.logger.info("Starting OCR processing queue...")
            self.ocr_queue.start()
            
            # Start screenshot capture if available
            if self.screenshot_capture:
                self.logger.info("Starting screenshot capture system...")
                self.screenshot_capture.start_monitoring()
            else:
                self.logger.info("Screenshot capture not available - skipping")
            
            # Start task scheduler
            self.logger.info("Starting task scheduler...")
            self.scheduler.start_monitoring()
            
            self._is_running = True
            
            # Log startup information
            config_summary = self.settings.get_config_summary()
            self.logger.info(f"System started successfully with configuration: {config_summary}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            self.shutdown()  # Cleanup on failure
            return False
    
    def shutdown(self) -> None:
        """Shutdown the system gracefully."""
        try:
            if not self._is_running:
                return
            
            self.logger.info("Shutting down Market Monitoring System...")
            self._shutdown_event.set()
            
            # Stop components in reverse order of initialization
            if self.scheduler:
                self.logger.info("Stopping task scheduler...")
                self.scheduler.stop_monitoring()
            
            if self.screenshot_capture:
                self.logger.info("Stopping screenshot capture...")
                self.screenshot_capture.stop_monitoring()
            
            if self.ocr_queue:
                self.logger.info("Stopping OCR queue...")
                self.ocr_queue.stop()
            
            if self.ocr_client:
                self.logger.info("Closing OCR client...")
                self.ocr_client.close()
            
            if self.database:
                self.logger.info("Closing database connections...")
                self.database.close_connection()
            
            self._is_running = False
            self.logger.info("System shutdown completed")
            
        except Exception as e:
            error_msg = f"Error during shutdown: {e}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(error_msg)
    
    def run_forever(self) -> None:
        """Run the system until shutdown signal is received."""
        try:
            if not self._is_running:
                self.logger.error("System is not running")
                return
            
            self.logger.info("Market Monitoring System is running. Press Ctrl+C to stop.")
            
            # Main loop - wait for shutdown signal
            while self._is_running and not self._shutdown_event.is_set():
                try:
                    # Sleep in small intervals to allow for responsive shutdown
                    time.sleep(1.0)
                    
                    # Periodic health checks
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        self._periodic_health_check()
                        
                except KeyboardInterrupt:
                    break
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.shutdown()
    
    def _periodic_health_check(self) -> None:
        """Perform periodic health checks while running."""
        try:
            # Check monitoring engine health
            if self.monitoring_engine:
                health = self.monitoring_engine.get_system_health()
                if health['status'] != 'healthy':
                    self.logger.warning(f"Monitoring engine health issues: {health['issues']}")
            
            # Check scheduler status
            if self.scheduler:
                status = self.scheduler.get_scheduler_status()
                if not status['is_running']:
                    self.logger.error("Task scheduler is not running")
            
        except Exception as e:
            self.logger.warning(f"Periodic health check failed: {e}")
    
    def get_system_status(self) -> dict:
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary with system status information
        """
        status = {
            'is_running': self._is_running,
            'initialization_error': self._initialization_error,
            'components': {}
        }
        
        if self.settings:
            status['configuration'] = self.settings.get_config_summary()
        
        if self.database:
            try:
                status['components']['database'] = self.database.get_monitoring_status_summary()
            except Exception as e:
                status['components']['database'] = {'error': str(e)}
        
        if self.scheduler:
            try:
                status['components']['scheduler'] = self.scheduler.get_scheduler_status()
            except Exception as e:
                status['components']['scheduler'] = {'error': str(e)}
        
        if self.screenshot_capture:
            try:
                status['components']['screenshot_capture'] = self.screenshot_capture.get_system_status()
            except Exception as e:
                status['components']['screenshot_capture'] = {'error': str(e)}
        
        if self.monitoring_engine:
            try:
                status['components']['monitoring_engine'] = self.monitoring_engine.get_monitoring_statistics()
            except Exception as e:
                status['components']['monitoring_engine'] = {'error': str(e)}
        
        return status
    
    def __enter__(self):
        """Context manager entry."""
        if self.initialize() and self.start():
            return self
        else:
            raise RuntimeError(f"Failed to initialize system: {self._initialization_error}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Market Monitoring System')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--test-only', action='store_true', help='Run initialization test only')
    parser.add_argument('--status', action='store_true', help='Show system status and exit')
    
    args = parser.parse_args()
    
    # Create and initialize system
    system = MarketMonitoringSystem(args.config)
    
    if args.test_only:
        print("Running initialization test...")
        if system.initialize():
            print("✓ Initialization test passed")
            return 0
        else:
            print("✗ Initialization test failed")
            return 1
    
    if args.status:
        print("Getting system status...")
        if system.initialize():
            status = system.get_system_status()
            print(f"System Status: {status}")
            return 0
        else:
            print("Failed to initialize system for status check")
            return 1
    
    # Normal operation
    try:
        with system:
            system.run_forever()
        return 0
    except Exception as e:
        print(f"System failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())