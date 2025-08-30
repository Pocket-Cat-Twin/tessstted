"""
High-Performance Hotkey Manager for Game Monitor System

Manages global hotkeys F1-F5 with asynchronous processing
and sub-second response times.
"""

import threading
import queue
import time
import logging
import sys
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .advanced_logger import get_hotkey_logger
from .error_tracker import ErrorTracker
from .performance_logger import PerformanceMonitor

logger = logging.getLogger(__name__)  # Keep for compatibility

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
        init_start = time.time()
        
        # Basic initialization
        self.max_queue_size = max_queue_size
        self.capture_queue = queue.Queue(maxsize=max_queue_size)
        self.processing_thread = None
        self.is_running = False
        self._lock = threading.Lock()
        
        # Advanced logging and monitoring
        self.advanced_logger = get_hotkey_logger()
        self.error_tracker = ErrorTracker()
        self.performance_monitor = PerformanceMonitor()
        
        with self.advanced_logger.operation_context('hotkey_manager', 'initialization'):
            try:
                self.advanced_logger.info(
                    "Starting HotkeyManager initialization",
                    extra_data={
                        'max_queue_size': max_queue_size,
                        'python_version': sys.version,
                        'initialization_started': datetime.now().isoformat()
                    }
                )
                
                # Initialize callback functions for each hotkey type
                callback_start = time.time()
                self._callbacks: Dict[HotkeyType, Callable] = {}
                callback_time = time.time() - callback_start
                
                self.advanced_logger.debug(
                    "Callback registry initialized",
                    extra_data={
                        'callback_registry_init_time_ms': callback_time * 1000,
                        'supported_hotkeys': [hk.value for hk in HotkeyType]
                    }
                )
                
                # Performance tracking initialization
                stats_start = time.time()
                self.stats = {
                    'total_captures': 0,
                    'successful_captures': 0,
                    'failed_captures': 0,
                    'avg_processing_time': 0.0,
                    'last_capture_time': None
                }
                stats_time = time.time() - stats_start
                
                self.advanced_logger.debug(
                    "Performance statistics initialized",
                    extra_data={
                        'stats_init_time_ms': stats_time * 1000,
                        'stats_fields': list(self.stats.keys())
                    }
                )
                
                init_time = time.time() - init_start
                
                # Final initialization log
                self.advanced_logger.info(
                    f"HotkeyManager initialized successfully in {init_time*1000:.2f}ms",
                    extra_data={
                        'total_initialization_time_ms': init_time * 1000,
                        'timing_breakdown': {
                            'callbacks_ms': callback_time * 1000,
                            'stats_ms': stats_time * 1000
                        },
                        'system_ready': True,
                        'queue_capacity': max_queue_size,
                        'supported_hotkey_count': len(HotkeyType)
                    }
                )
                
                logger.info("HotkeyManager initialized")
                
            except Exception as e:
                # Log initialization failure
                init_time = time.time() - init_start
                
                self.advanced_logger.error(
                    f"HotkeyManager initialization failed: {str(e)}",
                    error=e,
                    extra_data={
                        'initialization_time_ms': init_time * 1000,
                        'initialization_stage': 'unknown'
                    }
                )
                
                # Record initialization error
                self.error_tracker.record_error(
                    'hotkey_manager', 'initialization', e,
                    context={'max_queue_size': max_queue_size}
                )
                
                raise
    
    def register_callback(self, hotkey_type: HotkeyType, callback: Callable[[CaptureEvent], Any]):
        """Register callback function for specific hotkey type with comprehensive logging"""
        with self.advanced_logger.operation_context('hotkey_manager', 'register_callback'):
            start_time = time.time()
            
            try:
                # Log callback registration attempt
                self.advanced_logger.info(
                    f"Registering callback for hotkey {hotkey_type.value}",
                    extra_data={
                        'hotkey_type': hotkey_type.value,
                        'callback_name': getattr(callback, '__name__', 'anonymous'),
                        'callback_module': getattr(callback, '__module__', 'unknown'),
                        'existing_callbacks': list(self._callbacks.keys()),
                        'is_replacement': hotkey_type in self._callbacks
                    }
                )
                
                # Check if replacing existing callback
                replacing_existing = hotkey_type in self._callbacks
                if replacing_existing:
                    old_callback = self._callbacks[hotkey_type]
                    self.advanced_logger.warning(
                        f"Replacing existing callback for {hotkey_type.value}",
                        extra_data={
                            'old_callback_name': getattr(old_callback, '__name__', 'anonymous'),
                            'new_callback_name': getattr(callback, '__name__', 'anonymous')
                        }
                    )
                
                # Register the callback
                with self._lock:
                    self._callbacks[hotkey_type] = callback
                
                registration_time = time.time() - start_time
                
                # Log successful registration
                self.advanced_logger.info(
                    f"Successfully registered callback for {hotkey_type.value}",
                    extra_data={
                        'registration_time_ms': registration_time * 1000,
                        'total_registered_callbacks': len(self._callbacks),
                        'registered_hotkey_types': [hk.value for hk in self._callbacks.keys()],
                        'was_replacement': replacing_existing
                    }
                )
                
                logger.info(f"Registered callback for {hotkey_type.value}")
                
            except Exception as e:
                # Comprehensive error logging
                registration_time = time.time() - start_time
                
                self.advanced_logger.error(
                    f"Failed to register callback for {hotkey_type.value}: {str(e)}",
                    error=e,
                    extra_data={
                        'hotkey_type': hotkey_type.value,
                        'callback_name': getattr(callback, '__name__', 'anonymous'),
                        'elapsed_time_ms': registration_time * 1000,
                        'existing_callbacks_count': len(self._callbacks)
                    }
                )
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'hotkey_manager', 'register_callback', e,
                    context={
                        'hotkey_type': hotkey_type.value,
                        'callback_available': callback is not None
                    }
                )
                
                raise
    
    def start(self):
        """Start the hotkey manager and processing thread with comprehensive logging"""
        # Start performance tracking for startup
        trace_id = self.performance_monitor.start_operation(
            'hotkey_manager', 'start',
            context={'currently_running': self.is_running}
        )
        
        with self.advanced_logger.operation_context('hotkey_manager', 'start'):
            start_time = time.time()
            
            try:
                # Check if already running
                if self.is_running:
                    self.advanced_logger.warning(
                        "HotkeyManager start requested but already running",
                        extra_data={
                            'current_state': 'running',
                            'thread_alive': self.processing_thread.is_alive() if self.processing_thread else False,
                            'registered_callbacks': len(self._callbacks)
                        }
                    )
                    logger.warning("HotkeyManager already running")
                    
                    # Finish performance tracking - not an error but no action taken
                    self.performance_monitor.finish_operation(trace_id, success=True, operation_data={'already_running': True})
                    return
                
                self.advanced_logger.info(
                    "Starting HotkeyManager system",
                    extra_data={
                        'registered_callbacks': len(self._callbacks),
                        'callback_types': [hk.value for hk in self._callbacks.keys()],
                        'queue_capacity': self.max_queue_size,
                        'current_queue_size': self.capture_queue.qsize()
                    }
                )
                
                # Stage 1: Update running state
                state_start = time.time()
                with self._lock:
                    self.is_running = True
                state_time = time.time() - state_start
                
                self.advanced_logger.debug(
                    f"System state updated to running in {state_time*1000:.2f}ms",
                    extra_data={'state_update_time_ms': state_time * 1000}
                )
                
                # Stage 2: Start processing thread
                thread_start = time.time()
                self.processing_thread = threading.Thread(
                    target=self._process_capture_queue,
                    daemon=True,
                    name="HotkeyProcessor"
                )
                self.processing_thread.start()
                thread_time = time.time() - thread_start
                
                self.advanced_logger.info(
                    f"Processing thread started in {thread_time*1000:.2f}ms",
                    extra_data={
                        'thread_start_time_ms': thread_time * 1000,
                        'thread_name': self.processing_thread.name,
                        'thread_daemon': self.processing_thread.daemon,
                        'thread_alive': self.processing_thread.is_alive()
                    }
                )
                
                # Stage 3: Register global hotkeys
                hotkey_start = time.time()
                self._register_global_hotkeys()
                hotkey_time = time.time() - hotkey_start
                
                self.advanced_logger.debug(
                    f"Hotkey registration completed in {hotkey_time*1000:.2f}ms",
                    extra_data={'hotkey_registration_time_ms': hotkey_time * 1000}
                )
                
                total_time = time.time() - start_time
                
                # Log successful startup
                self.advanced_logger.info(
                    f"HotkeyManager started successfully in {total_time*1000:.2f}ms",
                    extra_data={
                        'total_startup_time_ms': total_time * 1000,
                        'timing_breakdown': {
                            'state_update_ms': state_time * 1000,
                            'thread_start_ms': thread_time * 1000,
                            'hotkey_registration_ms': hotkey_time * 1000
                        },
                        'system_status': 'operational',
                        'thread_status': 'running',
                        'registered_callbacks': len(self._callbacks)
                    }
                )
                
                # Finish performance tracking
                self.performance_monitor.finish_operation(
                    trace_id, success=True,
                    operation_data={
                        'startup_time_ms': total_time * 1000,
                        'callbacks_registered': len(self._callbacks),
                        'thread_started': self.processing_thread.is_alive()
                    }
                )
                
                logger.info("HotkeyManager started successfully")
                
            except Exception as e:
                # Comprehensive error logging
                total_time = time.time() - start_time
                
                self.advanced_logger.error(
                    f"HotkeyManager startup failed: {str(e)}",
                    error=e,
                    extra_data={
                        'startup_time_ms': total_time * 1000,
                        'registered_callbacks': len(self._callbacks),
                        'thread_created': self.processing_thread is not None,
                        'current_state': 'failed_startup'
                    }
                )
                
                # Reset state on failure
                with self._lock:
                    self.is_running = False
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'hotkey_manager', 'start', e,
                    context={
                        'callbacks_count': len(self._callbacks),
                        'queue_size': self.capture_queue.qsize()
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                raise
    
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
        """Handle hotkey press event with comprehensive logging"""
        # Start performance tracking for hotkey processing
        trace_id = self.performance_monitor.start_operation(
            'hotkey_manager', 'hotkey_press',
            context={
                'hotkey': hotkey_type.value,
                'system_running': self.is_running
            }
        )
        
        with self.advanced_logger.operation_context('hotkey_manager', 'hotkey_press'):
            press_time = time.time()
            
            try:
                # Check if system is running
                if not self.is_running:
                    self.advanced_logger.warning(
                        f"Hotkey {hotkey_type.value} pressed but system not running",
                        extra_data={
                            'hotkey_type': hotkey_type.value,
                            'system_state': 'stopped',
                            'action_taken': 'ignored'
                        }
                    )
                    
                    # Finish tracking - not an error but no action taken
                    self.performance_monitor.finish_operation(trace_id, success=True, operation_data={'system_not_running': True})
                    return
                
                # Log hotkey press with system context
                self.advanced_logger.info(
                    f"Hotkey {hotkey_type.value} pressed - processing event",
                    extra_data={
                        'hotkey_type': hotkey_type.value,
                        'press_timestamp': press_time,
                        'queue_size_before': self.capture_queue.qsize(),
                        'queue_capacity': self.max_queue_size,
                        'queue_utilization': self.capture_queue.qsize() / self.max_queue_size,
                        'total_captures_so_far': self.stats['total_captures']
                    }
                )
                
                # Create capture event
                event_creation_start = time.time()
                event = CaptureEvent(
                    hotkey_type=hotkey_type,
                    timestamp=press_time
                )
                event_creation_time = time.time() - event_creation_start
                
                self.advanced_logger.debug(
                    f"Capture event created in {event_creation_time*1000:.2f}ms",
                    extra_data={
                        'event_creation_time_ms': event_creation_time * 1000,
                        'event_timestamp': event.timestamp
                    }
                )
                
                # Add to processing queue with detailed logging
                queue_start = time.time()
                self.capture_queue.put(event, timeout=0.1)  # Fast timeout for responsiveness
                queue_time = time.time() - queue_start
                
                # Update stats
                with self._lock:
                    self.stats['total_captures'] += 1
                    self.stats['last_capture_time'] = event.timestamp
                
                total_processing_time = time.time() - press_time
                
                # Log successful queuing
                self.advanced_logger.info(
                    f"Hotkey {hotkey_type.value} successfully queued in {total_processing_time*1000:.2f}ms",
                    extra_data={
                        'total_processing_time_ms': total_processing_time * 1000,
                        'timing_breakdown': {
                            'event_creation_ms': event_creation_time * 1000,
                            'queue_insertion_ms': queue_time * 1000
                        },
                        'queue_size_after': self.capture_queue.qsize(),
                        'updated_stats': {
                            'total_captures': self.stats['total_captures'],
                            'last_capture_time': self.stats['last_capture_time']
                        }
                    }
                )
                
                # Performance warning if too slow
                if total_processing_time > 0.01:  # 10ms threshold for hotkey responsiveness
                    self.advanced_logger.warning(
                        f"Slow hotkey processing: {total_processing_time*1000:.2f}ms for {hotkey_type.value}",
                        extra_data={'performance_threshold_ms': 10}
                    )
                
                # Finish performance tracking
                self.performance_monitor.finish_operation(
                    trace_id, success=True,
                    operation_data={
                        'processing_time_ms': total_processing_time * 1000,
                        'queue_size_after': self.capture_queue.qsize(),
                        'hotkey_type': hotkey_type.value
                    }
                )
                
                logger.debug(f"Hotkey {hotkey_type.value} captured and queued")
                
            except queue.Full:
                # Queue full - detailed error logging
                total_time = time.time() - press_time
                
                self.advanced_logger.error(
                    f"Capture queue full, dropping {hotkey_type.value} event",
                    extra_data={
                        'hotkey_type': hotkey_type.value,
                        'queue_size': self.capture_queue.qsize(),
                        'max_queue_size': self.max_queue_size,
                        'queue_utilization': 1.0,
                        'processing_time_ms': total_time * 1000,
                        'action_taken': 'event_dropped'
                    }
                )
                
                # Update failed captures stat
                with self._lock:
                    self.stats['failed_captures'] += 1
                
                # Record queue full error
                self.error_tracker.record_error(
                    'hotkey_manager', 'hotkey_press_queue_full', 
                    Exception(f"Queue full for {hotkey_type.value}"),
                    context={
                        'hotkey_type': hotkey_type.value,
                        'queue_size': self.capture_queue.qsize(),
                        'max_queue_size': self.max_queue_size
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                logger.warning(f"Capture queue full, dropping {hotkey_type.value} event")
            
            except Exception as e:
                # General error handling with comprehensive logging
                total_time = time.time() - press_time
                
                self.advanced_logger.error(
                    f"Error processing hotkey {hotkey_type.value}: {str(e)}",
                    error=e,
                    extra_data={
                        'hotkey_type': hotkey_type.value,
                        'processing_time_ms': total_time * 1000,
                        'queue_size': self.capture_queue.qsize(),
                        'system_running': self.is_running,
                        'action_taken': 'event_failed'
                    }
                )
                
                # Update failed captures stat
                with self._lock:
                    self.stats['failed_captures'] += 1
                
                # Record general processing error
                self.error_tracker.record_error(
                    'hotkey_manager', 'hotkey_press_error', e,
                    context={
                        'hotkey_type': hotkey_type.value,
                        'system_state': 'running' if self.is_running else 'stopped'
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                logger.error(f"Error processing hotkey {hotkey_type.value}: {e}")
    
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