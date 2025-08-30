"""
High-Performance Hotkey Manager for Game Monitor System

Manages global hotkeys F1-F5 with asynchronous processing
and sub-second response times.
"""

import threading
import queue
import time
import logging
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class HotkeyType(Enum):
    """Hotkey types for different capture modes"""
    TRADER_LIST = "F1"        # Capture traders list + quantities  
    ITEM_SCAN = "F2"          # Capture item search results
    TRADER_INVENTORY = "F3"   # Capture opened trader inventory
    MANUAL_VERIFICATION = "F4" # Manual data verification
    EMERGENCY_STOP = "F5"     # Emergency system halt

@dataclass
class CaptureEvent:
    """Data structure for capture events"""
    hotkey_type: HotkeyType
    timestamp: float
    region: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None

class HotkeyManager:
    """Thread-safe hotkey manager with high-performance processing"""
    
    def __init__(self, max_queue_size: int = 100):
        self.max_queue_size = max_queue_size
        self.capture_queue = queue.Queue(maxsize=max_queue_size)
        self.processing_thread = None
        self.is_running = False
        self._lock = threading.Lock()
        
        # Callback functions for each hotkey type
        self._callbacks: Dict[HotkeyType, Callable] = {}
        
        # Performance tracking
        self.stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'avg_processing_time': 0.0,
            'last_capture_time': None
        }
        
        logger.info("HotkeyManager initialized")
    
    def register_callback(self, hotkey_type: HotkeyType, callback: Callable[[CaptureEvent], Any]):
        """Register callback function for specific hotkey type"""
        with self._lock:
            self._callbacks[hotkey_type] = callback
            logger.info(f"Registered callback for {hotkey_type.value}")
    
    def start(self):
        """Start the hotkey manager and processing thread"""
        if self.is_running:
            logger.warning("HotkeyManager already running")
            return
        
        with self._lock:
            self.is_running = True
            
            # Start processing thread
            self.processing_thread = threading.Thread(
                target=self._process_capture_queue,
                daemon=True,
                name="HotkeyProcessor"
            )
            self.processing_thread.start()
            
            # Try to register global hotkeys
            self._register_global_hotkeys()
            
            logger.info("HotkeyManager started successfully")
    
    def stop(self):
        """Stop the hotkey manager and cleanup"""
        if not self.is_running:
            return
        
        with self._lock:
            self.is_running = False
            
            # Stop processing thread
            if self.processing_thread and self.processing_thread.is_alive():
                # Add poison pill to queue to stop processing
                try:
                    self.capture_queue.put(None, timeout=1.0)
                except queue.Full:
                    pass
                
                self.processing_thread.join(timeout=2.0)
            
            # Unregister hotkeys
            self._unregister_global_hotkeys()
            
            logger.info("HotkeyManager stopped")
    
    def _register_global_hotkeys(self):
        """Register global hotkeys using available library"""
        try:
            # Try to import and use keyboard library
            import keyboard
            
            # Register hotkeys
            keyboard.add_hotkey('F1', lambda: self._on_hotkey_pressed(HotkeyType.TRADER_LIST))
            keyboard.add_hotkey('F2', lambda: self._on_hotkey_pressed(HotkeyType.ITEM_SCAN))
            keyboard.add_hotkey('F3', lambda: self._on_hotkey_pressed(HotkeyType.TRADER_INVENTORY))
            keyboard.add_hotkey('F4', lambda: self._on_hotkey_pressed(HotkeyType.MANUAL_VERIFICATION))
            keyboard.add_hotkey('F5', lambda: self._on_hotkey_pressed(HotkeyType.EMERGENCY_STOP))
            
            logger.info("Global hotkeys registered successfully")
            
        except ImportError:
            logger.warning("Keyboard library not available - using simulation mode")
            logger.info("Install 'keyboard' library for full hotkey support")
            # In development mode, provide manual trigger methods
            self._setup_simulation_mode()
        
        except Exception as e:
            logger.error(f"Failed to register hotkeys: {e}")
            self._setup_simulation_mode()
    
    def _unregister_global_hotkeys(self):
        """Unregister global hotkeys"""
        try:
            import keyboard
            keyboard.clear_all_hotkeys()
            logger.info("Global hotkeys unregistered")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error unregistering hotkeys: {e}")
    
    def _setup_simulation_mode(self):
        """Setup simulation mode for development/testing"""
        logger.info("Running in simulation mode - use trigger_* methods for testing")
    
    def _on_hotkey_pressed(self, hotkey_type: HotkeyType):
        """Handle hotkey press event"""
        if not self.is_running:
            return
        
        try:
            # Create capture event
            event = CaptureEvent(
                hotkey_type=hotkey_type,
                timestamp=time.time()
            )
            
            # Add to processing queue
            self.capture_queue.put(event, timeout=0.1)  # Fast timeout for responsiveness
            
            # Update stats
            with self._lock:
                self.stats['total_captures'] += 1
                self.stats['last_capture_time'] = event.timestamp
            
            logger.debug(f"Hotkey {hotkey_type.value} captured and queued")
            
        except queue.Full:
            logger.warning(f"Capture queue full, dropping {hotkey_type.value} event")
            with self._lock:
                self.stats['failed_captures'] += 1
        
        except Exception as e:
            logger.error(f"Error processing hotkey {hotkey_type.value}: {e}")
            with self._lock:
                self.stats['failed_captures'] += 1
    
    def _process_capture_queue(self):
        """Process capture events from queue"""
        logger.info("Capture processing thread started")
        
        while self.is_running:
            try:
                # Get event from queue with timeout
                event = self.capture_queue.get(timeout=1.0)
                
                # Check for poison pill (shutdown signal)
                if event is None:
                    break
                
                # Process event
                self._handle_capture_event(event)
                
            except queue.Empty:
                continue  # Timeout, check if still running
            
            except Exception as e:
                logger.error(f"Error in capture processing: {e}")
        
        logger.info("Capture processing thread stopped")
    
    def _handle_capture_event(self, event: CaptureEvent):
        """Handle individual capture event"""
        start_time = time.time()
        
        try:
            # Get callback for this hotkey type
            callback = self._callbacks.get(event.hotkey_type)
            
            if callback is None:
                logger.warning(f"No callback registered for {event.hotkey_type.value}")
                return
            
            # Execute callback
            result = callback(event)
            
            # Update stats
            processing_time = time.time() - start_time
            
            with self._lock:
                self.stats['successful_captures'] += 1
                
                # Update rolling average
                if self.stats['avg_processing_time'] == 0:
                    self.stats['avg_processing_time'] = processing_time
                else:
                    self.stats['avg_processing_time'] = (
                        self.stats['avg_processing_time'] * 0.9 + processing_time * 0.1
                    )
            
            logger.debug(f"Processed {event.hotkey_type.value} in {processing_time:.3f}s")
            
            # Performance warning if too slow
            if processing_time > 1.0:
                logger.warning(f"Slow capture processing: {processing_time:.3f}s for {event.hotkey_type.value}")
            
        except Exception as e:
            logger.error(f"Error handling capture event {event.hotkey_type.value}: {e}")
            with self._lock:
                self.stats['failed_captures'] += 1
    
    # Manual trigger methods for development/testing
    
    def trigger_trader_list_capture(self):
        """Manually trigger trader list capture (for testing)"""
        self._on_hotkey_pressed(HotkeyType.TRADER_LIST)
    
    def trigger_item_scan_capture(self):
        """Manually trigger item scan capture (for testing)"""
        self._on_hotkey_pressed(HotkeyType.ITEM_SCAN)
    
    def trigger_trader_inventory_capture(self):
        """Manually trigger trader inventory capture (for testing)"""
        self._on_hotkey_pressed(HotkeyType.TRADER_INVENTORY)
    
    def trigger_manual_verification(self):
        """Manually trigger manual verification (for testing)"""
        self._on_hotkey_pressed(HotkeyType.MANUAL_VERIFICATION)
    
    def trigger_emergency_stop(self):
        """Manually trigger emergency stop (for testing)"""
        self._on_hotkey_pressed(HotkeyType.EMERGENCY_STOP)
    
    # Statistics and monitoring
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            stats_copy = self.stats.copy()
        
        # Calculate success rate
        total = stats_copy['total_captures']
        if total > 0:
            stats_copy['success_rate'] = stats_copy['successful_captures'] / total
        else:
            stats_copy['success_rate'] = 0.0
        
        return stats_copy
    
    def reset_statistics(self):
        """Reset performance statistics"""
        with self._lock:
            self.stats = {
                'total_captures': 0,
                'successful_captures': 0,
                'failed_captures': 0,
                'avg_processing_time': 0.0,
                'last_capture_time': None
            }
        logger.info("Statistics reset")
    
    def is_queue_healthy(self) -> bool:
        """Check if capture queue is healthy (not too full)"""
        return self.capture_queue.qsize() < (self.max_queue_size * 0.8)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get capture queue status"""
        return {
            'queue_size': self.capture_queue.qsize(),
            'max_size': self.max_queue_size,
            'utilization': self.capture_queue.qsize() / self.max_queue_size,
            'is_healthy': self.is_queue_healthy()
        }

# Global instance for easy access
_hotkey_manager_instance = None
_hotkey_manager_lock = threading.Lock()

def get_hotkey_manager() -> HotkeyManager:
    """Get singleton hotkey manager instance"""
    global _hotkey_manager_instance
    if _hotkey_manager_instance is None:
        with _hotkey_manager_lock:
            if _hotkey_manager_instance is None:
                _hotkey_manager_instance = HotkeyManager()
    return _hotkey_manager_instance