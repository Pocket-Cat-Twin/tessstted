"""System tray integration for Voice-to-AI system."""

import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from ..core.event_bus import EventBus, EventType
from ..core.state_manager import StateManager, SystemState


@dataclass
class TrayConfig:
    """System tray configuration."""
    app_name: str = "Voice-to-AI"
    tooltip: str = "Voice-to-AI Streaming System"
    icon_size: int = 64
    show_notifications: bool = True


class SystemTray:
    """
    System tray integration.
    
    Provides system tray icon with context menu and status notifications.
    Allows control of the application from the system tray.
    """
    
    def __init__(self, event_bus: EventBus, state_manager: StateManager, 
                 config: Optional[TrayConfig] = None):
        """
        Initialize system tray.
        
        Args:
            event_bus: Event bus for communication
            state_manager: Global state manager
            config: Tray configuration
        """
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.config = config or TrayConfig()
        
        # System tray components
        self.tray_icon: Optional['pystray.Icon'] = None
        self.tray_thread: Optional[threading.Thread] = None
        
        # State tracking
        self.is_running = False
        self.current_status = "stopped"
        self.recording_active = False
        
        # Check availability
        self.available = TRAY_AVAILABLE
        if not self.available:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'system_tray',
                'error': 'System tray requires pystray and PIL libraries',
                'severity': 'warning'
            })
        
        # Subscribe to events
        self._subscribe_to_events()
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        self.event_bus.subscribe(EventType.SYSTEM_STATE_CHANGED, self._handle_system_state_changed)
        self.event_bus.subscribe(EventType.RECORDING_STARTED, self._handle_recording_started)
        self.event_bus.subscribe(EventType.RECORDING_STOPPED, self._handle_recording_stopped)
        self.event_bus.subscribe(EventType.AI_RESPONSE_RECEIVED, self._handle_ai_response)
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, self._handle_error)
        self.event_bus.subscribe(EventType.APPLICATION_STARTED, self._handle_app_started)
        self.event_bus.subscribe(EventType.APPLICATION_STOPPING, self._handle_app_stopping)
    
    def start(self) -> bool:
        """
        Start system tray.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self.available:
            return False
        
        if self.is_running:
            return True
        
        try:
            # Create tray icon
            self.tray_icon = pystray.Icon(
                name=self.config.app_name,
                icon=self._create_icon("stopped"),
                title=self.config.tooltip,
                menu=self._create_menu()
            )
            
            # Start tray in separate thread
            self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
            self.tray_thread.start()
            
            self.is_running = True
            
            self.event_bus.publish(EventType.SYSTEM_TRAY_STARTED, {
                'available': self.available
            })
            
            return True
            
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'system_tray',
                'error': f'Failed to start system tray: {str(e)}',
                'severity': 'error'
            })
            return False
    
    def stop(self) -> None:
        """Stop system tray."""
        if not self.is_running or not self.tray_icon:
            return
        
        self.is_running = False
        
        try:
            self.tray_icon.stop()
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'system_tray',
                'error': f'Error stopping system tray: {str(e)}',
                'severity': 'warning'
            })
        
        if self.tray_thread and self.tray_thread.is_alive():
            self.tray_thread.join(timeout=2.0)
        
        self.tray_icon = None
        self.tray_thread = None
        
        self.event_bus.publish(EventType.SYSTEM_TRAY_STOPPED, {})
    
    def _run_tray(self) -> None:
        """Run the system tray."""
        try:
            if self.tray_icon:
                self.tray_icon.run()
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'system_tray',
                'error': f'System tray error: {str(e)}',
                'severity': 'error'
            })
    
    def _create_icon(self, status: str) -> 'Image.Image':
        """
        Create tray icon based on status.
        
        Args:
            status: Current system status
            
        Returns:
            PIL Image for tray icon
        """
        size = self.config.icon_size
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Define colors based on status
        colors = {
            'stopped': '#808080',     # Gray
            'ready': '#4CAF50',       # Green
            'recording': '#FF5722',   # Red
            'processing': '#FF9800',  # Orange
            'error': '#F44336'        # Dark red
        }
        
        color = colors.get(status, '#808080')
        
        # Draw circle icon
        margin = size // 8
        draw.ellipse([margin, margin, size - margin, size - margin], 
                    fill=color, outline='#FFFFFF', width=2)
        
        # Add status indicator
        if status == 'recording':
            # Add recording dot
            dot_size = size // 4
            dot_x = size - dot_size - margin // 2
            dot_y = margin // 2
            draw.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size],
                        fill='#FFFFFF')
        
        elif status == 'processing':
            # Add processing animation (simplified)
            center = size // 2
            radius = size // 6
            for i in range(3):
                angle_offset = i * 120
                x = center + radius * 0.7
                y = center
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill='#FFFFFF')
        
        return image
    
    def _create_menu(self) -> 'pystray.Menu':
        """Create context menu for tray icon."""
        return pystray.Menu(
            pystray.MenuItem(
                "Start Recording",
                self._menu_start_recording,
                enabled=lambda item: not self.recording_active
            ),
            pystray.MenuItem(
                "Stop Recording", 
                self._menu_stop_recording,
                enabled=lambda item: self.recording_active
            ),
            pystray.MenuItem("", None),  # Separator
            
            pystray.MenuItem("Show Overlay", self._menu_show_overlay),
            pystray.MenuItem("Hide Overlay", self._menu_hide_overlay),
            pystray.MenuItem("", None),  # Separator
            
            pystray.MenuItem("Settings", self._menu_show_settings),
            pystray.MenuItem("Statistics", self._menu_show_statistics),
            pystray.MenuItem("", None),  # Separator
            
            pystray.MenuItem("Exit", self._menu_exit)
        )
    
    def _menu_start_recording(self, icon, item) -> None:
        """Handle start recording menu item."""
        self.event_bus.publish(EventType.RECORDING_START_REQUESTED, {
            'source': 'system_tray'
        })
    
    def _menu_stop_recording(self, icon, item) -> None:
        """Handle stop recording menu item."""
        self.event_bus.publish(EventType.RECORDING_STOP_REQUESTED, {
            'source': 'system_tray'
        })
    
    def _menu_show_overlay(self, icon, item) -> None:
        """Handle show overlay menu item."""
        self.event_bus.publish(EventType.OVERLAY_SHOW_REQUESTED, {
            'source': 'system_tray'
        })
    
    def _menu_hide_overlay(self, icon, item) -> None:
        """Handle hide overlay menu item."""
        self.event_bus.publish(EventType.OVERLAY_HIDE_REQUESTED, {
            'source': 'system_tray'
        })
    
    def _menu_show_settings(self, icon, item) -> None:
        """Handle show settings menu item."""
        self.event_bus.publish(EventType.SETTINGS_OPEN_REQUESTED, {
            'source': 'system_tray'
        })
    
    def _menu_show_statistics(self, icon, item) -> None:
        """Handle show statistics menu item."""
        self.event_bus.publish(EventType.STATISTICS_SHOW_REQUESTED, {
            'source': 'system_tray'
        })
    
    def _menu_exit(self, icon, item) -> None:
        """Handle exit menu item."""
        self.event_bus.publish(EventType.APPLICATION_EXIT_REQUESTED, {
            'source': 'system_tray'
        })
    
    def _handle_system_state_changed(self, data: Dict[str, Any]) -> None:
        """Handle system state change."""
        new_state = data.get('new_state')
        
        if new_state == SystemState.READY:
            self._update_status("ready")
        elif new_state == SystemState.RECORDING:
            self._update_status("recording")
        elif new_state == SystemState.PROCESSING:
            self._update_status("processing")
        elif new_state == SystemState.ERROR:
            self._update_status("error")
        else:
            self._update_status("stopped")
    
    def _handle_recording_started(self, data: Dict[str, Any]) -> None:
        """Handle recording started."""
        self.recording_active = True
        self._update_status("recording")
        
        if self.config.show_notifications:
            self._show_notification("Recording Started", "Voice recording is now active")
    
    def _handle_recording_stopped(self, data: Dict[str, Any]) -> None:
        """Handle recording stopped."""
        self.recording_active = False
        self._update_status("processing")
        
        if self.config.show_notifications:
            self._show_notification("Recording Stopped", "Processing audio...")
    
    def _handle_ai_response(self, data: Dict[str, Any]) -> None:
        """Handle AI response received."""
        self._update_status("ready")
        
        if self.config.show_notifications:
            response = data.get('response', '')
            preview = response[:50] + "..." if len(response) > 50 else response
            self._show_notification("AI Response", preview)
    
    def _handle_error(self, data: Dict[str, Any]) -> None:
        """Handle error occurred."""
        severity = data.get('severity', 'error')
        
        if severity == 'error':
            self._update_status("error")
            
            if self.config.show_notifications:
                error_msg = data.get('error', 'Unknown error')
                self._show_notification("Error", error_msg)
    
    def _handle_app_started(self, data: Dict[str, Any]) -> None:
        """Handle application started."""
        self._update_status("ready")
        
        if self.config.show_notifications:
            self._show_notification("Voice-to-AI", "System started successfully")
    
    def _handle_app_stopping(self, data: Dict[str, Any]) -> None:
        """Handle application stopping."""
        self._update_status("stopped")
    
    def _update_status(self, status: str) -> None:
        """Update tray icon status."""
        if not self.tray_icon or not self.is_running:
            return
        
        self.current_status = status
        
        try:
            # Update icon
            new_icon = self._create_icon(status)
            self.tray_icon.icon = new_icon
            
            # Update tooltip
            status_text = {
                'stopped': 'Stopped',
                'ready': 'Ready',
                'recording': 'Recording...',
                'processing': 'Processing...',
                'error': 'Error'
            }.get(status, 'Unknown')
            
            self.tray_icon.title = f"{self.config.app_name} - {status_text}"
            
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'system_tray',
                'error': f'Failed to update tray icon: {str(e)}',
                'severity': 'warning'
            })
    
    def _show_notification(self, title: str, message: str) -> None:
        """Show system notification."""
        if not self.tray_icon or not self.is_running or not self.config.show_notifications:
            return
        
        try:
            self.tray_icon.notify(message, title)
        except Exception as e:
            # Notifications might not be supported on all systems
            pass
    
    def update_tooltip(self, tooltip: str) -> None:
        """Update tray icon tooltip."""
        if self.tray_icon and self.is_running:
            self.tray_icon.title = tooltip
    
    def show_notification(self, title: str, message: str) -> None:
        """Show custom notification."""
        self._show_notification(title, message)
    
    def set_notifications_enabled(self, enabled: bool) -> None:
        """Enable/disable notifications."""
        self.config.show_notifications = enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get current tray status."""
        return {
            'is_running': self.is_running,
            'available': self.available,
            'current_status': self.current_status,
            'recording_active': self.recording_active,
            'notifications_enabled': self.config.show_notifications
        }