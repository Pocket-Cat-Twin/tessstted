"""Overlay management and coordination."""

from typing import Optional, Dict, Any, Tuple
import threading
import time
from dataclasses import dataclass

from ..core.event_bus import EventBus, EventType
from ..core.state_manager import StateManager, OverlayState
from .invisible_window import InvisibleWindow, OverlayStyle


@dataclass
class OverlayConfig:
    """Overlay system configuration."""
    auto_show_on_response: bool = True
    auto_hide_timeout: float = 10.0  # seconds
    position: Tuple[int, int] = (100, 100)
    style: Optional[OverlayStyle] = None


class OverlayManager:
    """
    Manages overlay display and behavior.
    
    Coordinates overlay window, handles auto-show/hide logic,
    and manages overlay state and configuration.
    """
    
    def __init__(self, event_bus: EventBus, state_manager: StateManager, 
                 config: Optional[OverlayConfig] = None):
        """
        Initialize overlay manager.
        
        Args:
            event_bus: Event bus for communication
            state_manager: Global state manager
            config: Overlay configuration
        """
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.config = config or OverlayConfig()
        
        # Components
        self.overlay_window: Optional[InvisibleWindow] = None
        
        # State tracking
        self.is_running = False
        self.auto_hide_timer: Optional[threading.Timer] = None
        self.current_text = ""
        
        # Performance tracking
        self.stats = {
            'show_count': 0,
            'hide_count': 0,
            'text_updates': 0,
            'auto_hides': 0,
            'uptime_start': None
        }
        
        # Subscribe to events
        self._subscribe_to_events()
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        self.event_bus.subscribe(EventType.AI_RESPONSE_RECEIVED, self._handle_ai_response)
        self.event_bus.subscribe(EventType.AI_STREAM_START, self._handle_stream_start)
        self.event_bus.subscribe(EventType.AI_STREAM_TOKEN, self._handle_stream_token)
        self.event_bus.subscribe(EventType.AI_STREAM_END, self._handle_stream_end)
        self.event_bus.subscribe(EventType.STT_RESULT_RECEIVED, self._handle_stt_result)
        self.event_bus.subscribe(EventType.RECORDING_STOPPED, self._handle_recording_stopped)
        
        # Manual overlay controls
        self.event_bus.subscribe(EventType.OVERLAY_SHOW_REQUESTED, self._handle_manual_show)
        self.event_bus.subscribe(EventType.OVERLAY_HIDE_REQUESTED, self._handle_manual_hide)
        self.event_bus.subscribe(EventType.OVERLAY_TOGGLE_REQUESTED, self._handle_manual_toggle)
        self.event_bus.subscribe(EventType.OVERLAY_MOVE_REQUESTED, self._handle_manual_move)
        
        # Window events
        self.event_bus.subscribe(EventType.OVERLAY_SHOWN, self._handle_window_shown)
        self.event_bus.subscribe(EventType.OVERLAY_HIDDEN, self._handle_window_hidden)
        self.event_bus.subscribe(EventType.OVERLAY_MOVED, self._handle_window_moved)
    
    def start(self) -> bool:
        """
        Start overlay manager.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            return True
        
        try:
            # Create overlay window
            style = self.config.style or OverlayStyle()
            self.overlay_window = InvisibleWindow(self.event_bus, style)
            
            # Start overlay window
            if not self.overlay_window.start():
                self.event_bus.publish(EventType.ERROR_OCCURRED, {
                    'source': 'overlay_manager',
                    'error': 'Failed to start overlay window',
                    'severity': 'error'
                })
                return False
            
            # Set initial position
            self.overlay_window._move_window_safe(
                self.config.position[0], 
                self.config.position[1]
            )
            
            self.is_running = True
            self.stats['uptime_start'] = time.time()
            
            # Update state
            self.state_manager.update_overlay_state(
                OverlayState.READY,
                visible=False,
                position=self.config.position
            )
            
            self.event_bus.publish(EventType.OVERLAY_MANAGER_STARTED, {
                'config': self.config,
                'window_available': self.overlay_window.windows_available
            })
            
            return True
            
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'overlay_manager',
                'error': f'Failed to start overlay manager: {str(e)}',
                'severity': 'error'
            })
            return False
    
    def stop(self) -> None:
        """Stop overlay manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel auto-hide timer
        self._cancel_auto_hide_timer()
        
        # Stop overlay window
        if self.overlay_window:
            self.overlay_window.stop()
            self.overlay_window = None
        
        # Update state
        self.state_manager.update_overlay_state(OverlayState.STOPPED)
        
        self.event_bus.publish(EventType.OVERLAY_MANAGER_STOPPED, {
            'stats': self.get_statistics()
        })
    
    def _handle_ai_response(self, data: Dict[str, Any]) -> None:
        """Handle complete AI response."""
        response_text = data.get('response', '')
        
        if response_text and self.config.auto_show_on_response:
            self.show_text(response_text)
            self._start_auto_hide_timer()
    
    def _handle_stream_start(self, data: Dict[str, Any]) -> None:
        """Handle AI stream start."""
        if self.config.auto_show_on_response:
            self.clear_text()
            self.show()
    
    def _handle_stream_token(self, data: Dict[str, Any]) -> None:
        """Handle AI stream token."""
        token = data.get('token', '')
        
        if token and self.config.auto_show_on_response:
            self.append_text(token)
            self._restart_auto_hide_timer()
    
    def _handle_stream_end(self, data: Dict[str, Any]) -> None:
        """Handle AI stream end."""
        if self.config.auto_show_on_response:
            self._start_auto_hide_timer()
    
    def _handle_stt_result(self, data: Dict[str, Any]) -> None:
        """Handle STT result - could show transcription."""
        # Optional: Show transcription in overlay
        pass
    
    def _handle_recording_stopped(self, data: Dict[str, Any]) -> None:
        """Handle recording stopped - prepare for AI response."""
        if self.config.auto_show_on_response:
            self.show_text("Processing...")
    
    def _handle_manual_show(self, data: Dict[str, Any]) -> None:
        """Handle manual show request."""
        text = data.get('text', '')
        if text:
            self.show_text(text)
        else:
            self.show()
    
    def _handle_manual_hide(self, data: Dict[str, Any]) -> None:
        """Handle manual hide request."""
        self.hide()
    
    def _handle_manual_toggle(self, data: Dict[str, Any]) -> None:
        """Handle manual toggle request."""
        self.toggle()
    
    def _handle_manual_move(self, data: Dict[str, Any]) -> None:
        """Handle manual move request."""
        x = data.get('x', self.config.position[0])
        y = data.get('y', self.config.position[1])
        self.move(x, y)
    
    def _handle_window_shown(self, data: Dict[str, Any]) -> None:
        """Handle window shown event."""
        self.stats['show_count'] += 1
        self.state_manager.update_overlay_state(visible=True)
    
    def _handle_window_hidden(self, data: Dict[str, Any]) -> None:
        """Handle window hidden event."""
        self.stats['hide_count'] += 1
        self.state_manager.update_overlay_state(visible=False)
    
    def _handle_window_moved(self, data: Dict[str, Any]) -> None:
        """Handle window moved event."""
        x = data.get('x', 0)
        y = data.get('y', 0)
        self.config.position = (x, y)
        self.state_manager.update_overlay_state(position=(x, y))
    
    def show(self) -> None:
        """Show overlay window."""
        if not self.is_running or not self.overlay_window:
            return
        
        self.event_bus.publish(EventType.OVERLAY_SHOW, {})
        self._cancel_auto_hide_timer()
    
    def hide(self) -> None:
        """Hide overlay window."""
        if not self.is_running or not self.overlay_window:
            return
        
        self.event_bus.publish(EventType.OVERLAY_HIDE, {})
        self._cancel_auto_hide_timer()
    
    def toggle(self) -> None:
        """Toggle overlay visibility."""
        if not self.is_running or not self.overlay_window:
            return
        
        if self.overlay_window.is_visible:
            self.hide()
        else:
            self.show()
    
    def move(self, x: int, y: int) -> None:
        """Move overlay to position."""
        if not self.is_running or not self.overlay_window:
            return
        
        self.event_bus.publish(EventType.OVERLAY_MOVE, {'x': x, 'y': y})
    
    def show_text(self, text: str) -> None:
        """Show overlay with specific text."""
        if not self.is_running or not self.overlay_window:
            return
        
        self.current_text = text
        self.stats['text_updates'] += 1
        
        self.event_bus.publish(EventType.OVERLAY_UPDATE_TEXT, {
            'text': text,
            'append': False
        })
        
        self.show()
    
    def append_text(self, text: str) -> None:
        """Append text to current overlay content."""
        if not self.is_running or not self.overlay_window:
            return
        
        self.current_text += text
        self.stats['text_updates'] += 1
        
        self.event_bus.publish(EventType.OVERLAY_UPDATE_TEXT, {
            'text': text,
            'append': True
        })
    
    def clear_text(self) -> None:
        """Clear overlay text."""
        if not self.is_running or not self.overlay_window:
            return
        
        self.current_text = ""
        
        self.event_bus.publish(EventType.OVERLAY_UPDATE_TEXT, {
            'text': "",
            'append': False
        })
    
    def _start_auto_hide_timer(self) -> None:
        """Start auto-hide timer."""
        if self.config.auto_hide_timeout <= 0:
            return
        
        self._cancel_auto_hide_timer()
        
        self.auto_hide_timer = threading.Timer(
            self.config.auto_hide_timeout,
            self._auto_hide_timeout
        )
        self.auto_hide_timer.daemon = True
        self.auto_hide_timer.start()
    
    def _restart_auto_hide_timer(self) -> None:
        """Restart auto-hide timer."""
        if self.overlay_window and self.overlay_window.is_visible:
            self._start_auto_hide_timer()
    
    def _cancel_auto_hide_timer(self) -> None:
        """Cancel auto-hide timer."""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            self.auto_hide_timer = None
    
    def _auto_hide_timeout(self) -> None:
        """Handle auto-hide timeout."""
        self.stats['auto_hides'] += 1
        self.hide()
        
        self.event_bus.publish(EventType.OVERLAY_AUTO_HIDDEN, {})
    
    def set_config(self, config: OverlayConfig) -> None:
        """Update overlay configuration."""
        old_position = self.config.position
        self.config = config
        
        # Apply position change if needed
        if config.position != old_position and self.overlay_window:
            self.move(config.position[0], config.position[1])
        
        # Apply style changes if needed
        if config.style and self.overlay_window:
            self.overlay_window.set_style(config.style)
        
        self.event_bus.publish(EventType.OVERLAY_CONFIG_UPDATED, {
            'config': config
        })
    
    def get_current_text(self) -> str:
        """Get current overlay text."""
        return self.current_text
    
    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return (self.is_running and 
                self.overlay_window and 
                self.overlay_window.is_visible)
    
    def get_position(self) -> Tuple[int, int]:
        """Get current overlay position."""
        if self.overlay_window:
            return self.overlay_window.get_position()
        return self.config.position
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overlay statistics."""
        stats = self.stats.copy()
        
        if stats['uptime_start']:
            stats['uptime_seconds'] = time.time() - stats['uptime_start']
        else:
            stats['uptime_seconds'] = 0
        
        stats.update({
            'is_running': self.is_running,
            'is_visible': self.is_visible(),
            'current_text_length': len(self.current_text),
            'window_available': self.overlay_window.windows_available if self.overlay_window else False,
            'position': self.get_position(),
            'auto_hide_active': self.auto_hide_timer is not None
        })
        
        return stats