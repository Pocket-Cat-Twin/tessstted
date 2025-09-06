"""
Screenshot capture module for market monitoring system.
Handles global hotkey registration and screen capture functionality.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Callable, Tuple, List
import uuid

try:
    import keyboard
    import mss
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    IMPORT_ERROR = str(e)

from config.settings import SettingsManager, HotkeyConfig


class ScreenshotCaptureError(Exception):
    """Exception raised for screenshot capture errors."""
    pass


class ScreenshotCapture:
    """
    Handles global hotkey registration and screen capture functionality.
    Thread-safe with proper error handling and resource management.
    """
    
    def __init__(self, settings_manager: SettingsManager):
        """
        Initialize screenshot capture system.
        
        Args:
            settings_manager: Configuration manager instance
        """
        if not DEPENDENCIES_AVAILABLE:
            raise ScreenshotCaptureError(f"Required dependencies not available: {IMPORT_ERROR}")
        
        self.settings = settings_manager
        self.logger = logging.getLogger(__name__)
        
        # State management
        self._is_running = False
        self._hotkey_handlers: Dict[str, Callable] = {}
        self._capture_stats: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
        # Screenshot engine
        self._mss_instance: Optional[mss.mss] = None
        
        # Initialize capture statistics
        self._initialize_stats()
        
    def _initialize_stats(self) -> None:
        """Initialize capture statistics for enabled hotkeys."""
        for hotkey in self.settings.get_enabled_hotkeys():
            self._capture_stats[hotkey] = {
                'total_captures': 0,
                'successful_captures': 0,
                'failed_captures': 0,
                'last_capture_time': None,
                'last_capture_duration': 0.0,
                'average_capture_time': 0.0
            }
    
    def _get_mss_instance(self) -> mss.mss:
        """Get or create MSS instance with thread safety."""
        with self._lock:
            if self._mss_instance is None:
                try:
                    self._mss_instance = mss.mss()
                    self.logger.debug("Created new MSS instance")
                except Exception as e:
                    self.logger.error(f"Failed to create MSS instance: {e}")
                    raise ScreenshotCaptureError(f"MSS initialization failed: {e}")
            return self._mss_instance
    
    def _recreate_mss_instance(self) -> None:
        """Force recreation of MSS instance after error."""
        with self._lock:
            if self._mss_instance:
                try:
                    self._mss_instance.close()
                except Exception as e:
                    self.logger.warning(f"Error closing corrupted MSS instance: {e}")
                finally:
                    self._mss_instance = None
                    self.logger.debug("MSS instance cleared for recreation")
    
    def _cleanup_mss_instance(self) -> None:
        """Clean up MSS instance with proper error handling."""
        with self._lock:
            if self._mss_instance:
                try:
                    self._mss_instance.close()
                    self.logger.debug("MSS instance closed successfully")
                except Exception as e:
                    self.logger.error(f"Error closing MSS instance: {e}")
                finally:
                    self._mss_instance = None
    
    def register_global_hotkeys(self) -> None:
        """Register global hotkeys for all enabled configurations."""
        if not DEPENDENCIES_AVAILABLE:
            raise ScreenshotCaptureError("Keyboard library not available")
        
        try:
            enabled_hotkeys = self.settings.get_enabled_hotkeys()
            
            if not enabled_hotkeys:
                self.logger.warning("No enabled hotkeys found in configuration")
                return
            
            # Clear existing hotkey handlers
            self._clear_hotkey_handlers()
            
            # Register each enabled hotkey
            for hotkey_name, config in enabled_hotkeys.items():
                self._register_single_hotkey(hotkey_name, config)
            
            self.logger.info(f"Registered {len(enabled_hotkeys)} global hotkeys")
            
        except Exception as e:
            raise ScreenshotCaptureError(f"Failed to register global hotkeys: {e}")
    
    def _register_single_hotkey(self, hotkey_name: str, config: HotkeyConfig) -> None:
        """
        Register a single hotkey.
        
        Args:
            hotkey_name: Name of the hotkey (e.g., 'F1')
            config: Hotkey configuration
        """
        try:
            # Create handler function for this hotkey
            def handler():
                self._handle_hotkey_press(hotkey_name, config)
            
            # Register with keyboard library
            keyboard.add_hotkey(hotkey_name.lower(), handler, suppress=False)
            self._hotkey_handlers[hotkey_name] = handler
            
            self.logger.info(f"Registered hotkey {hotkey_name} for {config.description}")
            
        except Exception as e:
            self.logger.error(f"Failed to register hotkey {hotkey_name}: {e}")
            raise
    
    def _clear_hotkey_handlers(self) -> None:
        """Clear all registered hotkey handlers."""
        try:
            keyboard.clear_all_hotkeys()
            self._hotkey_handlers.clear()
            self.logger.debug("Cleared all hotkey handlers")
            
        except Exception as e:
            self.logger.error(f"Failed to clear hotkey handlers: {e}")
    
    def _handle_hotkey_press(self, hotkey_name: str, config: HotkeyConfig) -> None:
        """
        Handle hotkey press event.
        
        Args:
            hotkey_name: Name of the pressed hotkey
            config: Hotkey configuration
        """
        try:
            with self._lock:
                # Update statistics
                self._capture_stats[hotkey_name]['total_captures'] += 1
            
            self.logger.info(f"Hotkey {hotkey_name} pressed - capturing screenshot")
            
            # Capture screenshot
            success = self.capture_area(
                coordinates=config.area,
                hotkey_name=hotkey_name,
                description=config.description
            )
            
            # Update statistics
            with self._lock:
                if success:
                    self._capture_stats[hotkey_name]['successful_captures'] += 1
                else:
                    self._capture_stats[hotkey_name]['failed_captures'] += 1
            
        except Exception as e:
            self.logger.error(f"Error handling hotkey {hotkey_name}: {e}")
            with self._lock:
                self._capture_stats[hotkey_name]['failed_captures'] += 1
    
    def capture_area(self, coordinates: Tuple[int, int, int, int], 
                     hotkey_name: str, description: str = "") -> bool:
        """
        Capture specified screen area and save to file.
        
        Args:
            coordinates: Screen area coordinates (x1, y1, x2, y2)
            hotkey_name: Name of the hotkey that triggered capture
            description: Optional description for logging
            
        Returns:
            True if capture was successful, False otherwise
        """
        start_time = time.time()
        
        try:
            # Validate coordinates
            x1, y1, x2, y2 = coordinates
            if x1 >= x2 or y1 >= y2:
                raise ScreenshotCaptureError(f"Invalid coordinates: {coordinates}")
            
            # Get screenshot path
            screenshot_path = self._get_screenshot_path(hotkey_name)
            if not screenshot_path:
                raise ScreenshotCaptureError(f"Could not determine screenshot path for {hotkey_name}")
            
            # Ensure directory exists
            screenshot_path.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            filename = f"{hotkey_name}_{timestamp}_{uuid.uuid4().hex[:8]}.png"
            filepath = screenshot_path / filename
            
            # Capture screenshot with proper resource management
            monitor = {
                "top": y1,
                "left": x1,
                "width": x2 - x1,
                "height": y2 - y1
            }
            
            screenshot = None
            try:
                # Get MSS instance with thread safety
                mss_instance = self._get_mss_instance()
                screenshot = mss_instance.grab(monitor)
                
                # Save to file
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=str(filepath))
                
            except Exception as e:
                # Re-create MSS instance on error as it might be corrupted
                self._recreate_mss_instance()
                raise e
            finally:
                # Clean up screenshot object if it exists
                if screenshot:
                    del screenshot
            
            # Calculate capture duration
            capture_duration = time.time() - start_time
            
            # Update statistics
            with self._lock:
                stats = self._capture_stats[hotkey_name]
                stats['last_capture_time'] = datetime.now().isoformat()
                stats['last_capture_duration'] = capture_duration
                
                # Update average capture time
                successful_count = stats['successful_captures']
                if successful_count > 0:
                    current_avg = stats['average_capture_time']
                    stats['average_capture_time'] = (
                        (current_avg * (successful_count - 1) + capture_duration) / successful_count
                    )
            
            self.logger.info(
                f"Screenshot captured successfully: {filepath.name} "
                f"({x2-x1}x{y2-y1}) in {capture_duration:.3f}s"
            )
            
            return True
            
        except Exception as e:
            capture_duration = time.time() - start_time
            self.logger.error(
                f"Failed to capture screenshot for {hotkey_name}: {e} "
                f"(failed after {capture_duration:.3f}s)"
            )
            return False
    
    def _get_screenshot_path(self, hotkey_name: str) -> Optional[Path]:
        """
        Get screenshot directory path for specified hotkey.
        
        Args:
            hotkey_name: Name of the hotkey
            
        Returns:
            Path to screenshot directory or None
        """
        return self.settings.get_screenshot_path(hotkey_name)
    
    def cleanup_old_screenshots(self, hotkey_name: Optional[str] = None, 
                               max_age_minutes: int = 60) -> int:
        """
        Clean up old screenshot files.
        
        Args:
            hotkey_name: Specific hotkey to clean (None for all)
            max_age_minutes: Maximum age of files to keep
            
        Returns:
            Number of files deleted
        """
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        deleted_count = 0
        
        try:
            # Determine hotkeys to process
            if hotkey_name:
                hotkeys_to_clean = [hotkey_name] if hotkey_name in self.settings.hotkeys else []
            else:
                hotkeys_to_clean = list(self.settings.get_enabled_hotkeys().keys())
            
            for hk in hotkeys_to_clean:
                screenshot_path = self._get_screenshot_path(hk)
                if not screenshot_path or not screenshot_path.exists():
                    continue
                
                # Find and delete old files
                for file_path in screenshot_path.glob(f"{hk}_*.png"):
                    try:
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_time:
                            file_path.unlink()
                            deleted_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to delete {file_path}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old screenshot files")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error during screenshot cleanup: {e}")
            return 0
    
    def get_screenshot_files(self, hotkey_name: str, 
                           max_files: Optional[int] = None) -> List[Path]:
        """
        Get list of screenshot files for specified hotkey.
        
        Args:
            hotkey_name: Name of the hotkey
            max_files: Maximum number of files to return (most recent first)
            
        Returns:
            List of screenshot file paths
        """
        try:
            screenshot_path = self._get_screenshot_path(hotkey_name)
            if not screenshot_path or not screenshot_path.exists():
                return []
            
            # Get all screenshot files for this hotkey
            files = list(screenshot_path.glob(f"{hotkey_name}_*.png"))
            
            # Sort by modification time (newest first)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Limit number of files if specified
            if max_files is not None:
                files = files[:max_files]
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to get screenshot files for {hotkey_name}: {e}")
            return []
    
    def start_monitoring(self) -> None:
        """Start the screenshot capture system."""
        try:
            if self._is_running:
                self.logger.warning("Screenshot capture system is already running")
                return
            
            # Register global hotkeys
            self.register_global_hotkeys()
            
            self._is_running = True
            self.logger.info("Screenshot capture system started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start screenshot capture system: {e}")
            raise ScreenshotCaptureError(f"Failed to start capture system: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop the screenshot capture system."""
        try:
            if not self._is_running:
                return
            
            # Clear hotkey handlers
            self._clear_hotkey_handlers()
            
            # Close MSS instance with proper cleanup
            self._cleanup_mss_instance()
            
            self._is_running = False
            self.logger.info("Screenshot capture system stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping screenshot capture system: {e}")
            # Force cleanup MSS instance even if error occurred
            self._cleanup_mss_instance()
    
    def get_capture_statistics(self) -> Dict[str, Dict]:
        """
        Get capture statistics for all hotkeys.
        
        Returns:
            Dictionary with capture statistics
        """
        with self._lock:
            return {
                hotkey: stats.copy() 
                for hotkey, stats in self._capture_stats.items()
            }
    
    def get_system_status(self) -> Dict[str, any]:
        """
        Get system status information.
        
        Returns:
            Dictionary with system status
        """
        enabled_hotkeys = self.settings.get_enabled_hotkeys()
        
        return {
            'is_running': self._is_running,
            'dependencies_available': DEPENDENCIES_AVAILABLE,
            'registered_hotkeys': list(self._hotkey_handlers.keys()),
            'enabled_hotkeys': list(enabled_hotkeys.keys()),
            'mss_instance_active': self._mss_instance is not None,
            'capture_statistics': self.get_capture_statistics()
        }
    
    def test_capture(self, hotkey_name: str) -> bool:
        """
        Test screenshot capture for specified hotkey.
        
        Args:
            hotkey_name: Name of the hotkey to test
            
        Returns:
            True if test capture was successful
        """
        try:
            config = self.settings.get_hotkey_config(hotkey_name)
            if not config:
                self.logger.error(f"No configuration found for hotkey {hotkey_name}")
                return False
            
            self.logger.info(f"Testing capture for hotkey {hotkey_name}")
            
            return self.capture_area(
                coordinates=config.area,
                hotkey_name=hotkey_name,
                description=f"Test capture for {config.description}"
            )
            
        except Exception as e:
            self.logger.error(f"Test capture failed for {hotkey_name}: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()