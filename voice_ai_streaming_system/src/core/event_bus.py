"""Event bus system for inter-component communication."""

import threading
import weakref
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EventType(Enum):
    """System event types."""
    
    # Audio events
    AUDIO_CAPTURE_STARTED = "audio_capture_started"
    AUDIO_CAPTURE_STOPPED = "audio_capture_stopped"
    AUDIO_DATA_AVAILABLE = "audio_data_available"
    AUDIO_DEVICE_ERROR = "audio_device_error"
    VOICE_ACTIVITY_DETECTED = "voice_activity_detected"
    VOICE_ACTIVITY_ENDED = "voice_activity_ended"
    
    # Hotkey events
    HOTKEY_START_RECORDING = "hotkey_start_recording"
    HOTKEY_STOP_RECORDING = "hotkey_stop_recording"
    HOTKEY_TOGGLE_OVERLAY = "hotkey_toggle_overlay"
    HOTKEY_TOGGLE_SETTINGS = "hotkey_toggle_settings"
    HOTKEY_EMERGENCY_STOP = "hotkey_emergency_stop"
    
    # Recording events
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    RECORDING_DATA_READY = "recording_data_ready"
    RECORDING_ERROR = "recording_error"
    
    # STT events
    STT_PROCESSING_STARTED = "stt_processing_started"
    STT_PARTIAL_RESULT = "stt_partial_result"
    STT_FINAL_RESULT = "stt_final_result"
    STT_ERROR = "stt_error"
    STT_SERVICE_CHANGED = "stt_service_changed"
    
    # AI events
    AI_REQUEST_STARTED = "ai_request_started"
    AI_RESPONSE_CHUNK = "ai_response_chunk"
    AI_RESPONSE_COMPLETED = "ai_response_completed"
    AI_REQUEST_ERROR = "ai_request_error"
    AI_SERVICE_CHANGED = "ai_service_changed"
    
    # Overlay events
    OVERLAY_SHOW = "overlay_show"
    OVERLAY_HIDE = "overlay_hide"
    OVERLAY_UPDATE_TEXT = "overlay_update_text"
    OVERLAY_POSITION_CHANGED = "overlay_position_changed"
    OVERLAY_SETTINGS_CHANGED = "overlay_settings_changed"
    
    # UI events
    SETTINGS_WINDOW_OPENED = "settings_window_opened"
    SETTINGS_WINDOW_CLOSED = "settings_window_closed"
    SETTINGS_CHANGED = "settings_changed"
    SYSTEM_TRAY_CLICKED = "system_tray_clicked"
    
    # System events
    APPLICATION_STARTED = "application_started"
    APPLICATION_STOPPING = "application_stopping"
    APPLICATION_ERROR = "application_error"
    CONFIGURATION_LOADED = "configuration_loaded"
    CONFIGURATION_SAVED = "configuration_saved"
    
    # Performance events
    PERFORMANCE_WARNING = "performance_warning"
    RESOURCE_USAGE_HIGH = "resource_usage_high"
    LATENCY_THRESHOLD_EXCEEDED = "latency_threshold_exceeded"


@dataclass
class Event:
    """Event data structure."""
    
    event_type: EventType
    source: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


EventHandler = Callable[[Event], None]


class EventBus:
    """Central event bus for system-wide communication."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[weakref.ref]] = {}
        self._global_handlers: List[weakref.ref] = []
        self._lock = threading.RLock()
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        self._enabled = True
        
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """Subscribe to specific event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to handle events
            
        Returns:
            True if subscription successful
        """
        try:
            with self._lock:
                if event_type not in self._handlers:
                    self._handlers[event_type] = []
                
                # Use weak reference to prevent memory leaks
                handler_ref = weakref.ref(handler, self._cleanup_handler)
                self._handlers[event_type].append(handler_ref)
                
                logger.debug(f"Subscribed to {event_type.value} - Total handlers: {len(self._handlers[event_type])}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to subscribe to {event_type.value}: {e}")
            return False
    
    def subscribe_global(self, handler: EventHandler) -> bool:
        """Subscribe to all events.
        
        Args:
            handler: Callback function to handle all events
            
        Returns:
            True if subscription successful
        """
        try:
            with self._lock:
                handler_ref = weakref.ref(handler, self._cleanup_global_handler)
                self._global_handlers.append(handler_ref)
                
                logger.debug(f"Global subscription added - Total global handlers: {len(self._global_handlers)}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to subscribe globally: {e}")
            return False
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """Unsubscribe from specific event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
            
        Returns:
            True if unsubscription successful
        """
        try:
            with self._lock:
                if event_type not in self._handlers:
                    return False
                
                # Find and remove handler reference
                handlers_to_remove = []
                for handler_ref in self._handlers[event_type]:
                    if handler_ref() is handler:
                        handlers_to_remove.append(handler_ref)
                
                for handler_ref in handlers_to_remove:
                    self._handlers[event_type].remove(handler_ref)
                
                logger.debug(f"Unsubscribed from {event_type.value} - Remaining handlers: {len(self._handlers[event_type])}")
                return len(handlers_to_remove) > 0
                
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {event_type.value}: {e}")
            return False
    
    def unsubscribe_global(self, handler: EventHandler) -> bool:
        """Unsubscribe from all events.
        
        Args:
            handler: Handler function to remove
            
        Returns:
            True if unsubscription successful
        """
        try:
            with self._lock:
                handlers_to_remove = []
                for handler_ref in self._global_handlers:
                    if handler_ref() is handler:
                        handlers_to_remove.append(handler_ref)
                
                for handler_ref in handlers_to_remove:
                    self._global_handlers.remove(handler_ref)
                
                logger.debug(f"Global unsubscription - Remaining global handlers: {len(self._global_handlers)}")
                return len(handlers_to_remove) > 0
                
        except Exception as e:
            logger.error(f"Failed to unsubscribe globally: {e}")
            return False
    
    def publish(self, event: Event) -> bool:
        """Publish event to all subscribers.
        
        Args:
            event: Event to publish
            
        Returns:
            True if event was published successfully
        """
        if not self._enabled:
            return False
        
        try:
            with self._lock:
                # Add to history
                self._add_to_history(event)
                
                # Notify specific event handlers
                handlers_called = 0
                if event.event_type in self._handlers:
                    dead_refs = []
                    for handler_ref in self._handlers[event.event_type]:
                        handler = handler_ref()
                        if handler is None:
                            dead_refs.append(handler_ref)
                        else:
                            try:
                                handler(event)
                                handlers_called += 1
                            except Exception as e:
                                logger.error(f"Error in event handler for {event.event_type.value}: {e}")
                    
                    # Clean up dead references
                    for dead_ref in dead_refs:
                        self._handlers[event.event_type].remove(dead_ref)
                
                # Notify global handlers
                dead_refs = []
                for handler_ref in self._global_handlers:
                    handler = handler_ref()
                    if handler is None:
                        dead_refs.append(handler_ref)
                    else:
                        try:
                            handler(event)
                            handlers_called += 1
                        except Exception as e:
                            logger.error(f"Error in global event handler for {event.event_type.value}: {e}")
                
                # Clean up dead references
                for dead_ref in dead_refs:
                    self._global_handlers.remove(dead_ref)
                
                logger.debug(f"Published {event.event_type.value} from {event.source} to {handlers_called} handlers")
                return True
                
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type.value}: {e}")
            return False
    
    def emit(self, event_type: EventType, source: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Convenience method to create and publish an event.
        
        Args:
            event_type: Type of event
            source: Source component name
            data: Optional event data
            
        Returns:
            True if event was published successfully
        """
        event = Event(event_type=event_type, source=source, data=data)
        return self.publish(event)
    
    def get_event_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get recent event history.
        
        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        with self._lock:
            events = self._event_history.copy()
            
            # Filter by event type if specified
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Return most recent events
            return events[-limit:] if limit else events
    
    def clear_history(self) -> None:
        """Clear event history."""
        with self._lock:
            self._event_history.clear()
            logger.debug("Event history cleared")
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics.
        
        Returns:
            Dictionary with subscription statistics
        """
        with self._lock:
            stats = {
                "total_event_types": len(self._handlers),
                "total_handlers": sum(len(handlers) for handlers in self._handlers.values()),
                "global_handlers": len(self._global_handlers),
                "event_history_size": len(self._event_history),
                "event_types": {}
            }
            
            for event_type, handlers in self._handlers.items():
                stats["event_types"][event_type.value] = len(handlers)
            
            return stats
    
    def enable(self) -> None:
        """Enable event bus."""
        self._enabled = True
        logger.info("EventBus enabled")
    
    def disable(self) -> None:
        """Disable event bus (events will be ignored)."""
        self._enabled = False
        logger.info("EventBus disabled")
    
    def is_enabled(self) -> bool:
        """Check if event bus is enabled."""
        return self._enabled
    
    def _add_to_history(self, event: Event) -> None:
        """Add event to history with size limit."""
        self._event_history.append(event)
        
        # Maintain history size limit
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]
    
    def _cleanup_handler(self, handler_ref: weakref.ref) -> None:
        """Cleanup dead handler reference."""
        with self._lock:
            for handlers_list in self._handlers.values():
                if handler_ref in handlers_list:
                    handlers_list.remove(handler_ref)
    
    def _cleanup_global_handler(self, handler_ref: weakref.ref) -> None:
        """Cleanup dead global handler reference."""
        with self._lock:
            if handler_ref in self._global_handlers:
                self._global_handlers.remove(handler_ref)
    
    def shutdown(self) -> None:
        """Shutdown event bus and cleanup resources."""
        logger.info("EventBus shutting down")
        
        with self._lock:
            self._enabled = False
            self._handlers.clear()
            self._global_handlers.clear()
            self._event_history.clear()
        
        logger.info("EventBus shutdown complete")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def subscribe(event_type: EventType, handler: EventHandler) -> bool:
    """Convenience function to subscribe to events."""
    return get_event_bus().subscribe(event_type, handler)


def subscribe_global(handler: EventHandler) -> bool:
    """Convenience function to subscribe to all events."""
    return get_event_bus().subscribe_global(handler)


def unsubscribe(event_type: EventType, handler: EventHandler) -> bool:
    """Convenience function to unsubscribe from events."""
    return get_event_bus().unsubscribe(event_type, handler)


def publish(event: Event) -> bool:
    """Convenience function to publish events."""
    return get_event_bus().publish(event)


def emit(event_type: EventType, source: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """Convenience function to emit events."""
    return get_event_bus().emit(event_type, source, data)