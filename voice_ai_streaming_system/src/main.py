"""Main entry point for Voice-to-AI Streaming System."""

import sys
import os
import logging
from pathlib import Path
import signal
import time
from typing import Optional, Dict, Any

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import ConfigManager, Settings
from utils.logger import setup_logging, get_logger
from core.event_bus import get_event_bus, EventType, EventBus
from core.state_manager import get_state_manager, StateManager, SystemState
from core.thread_coordinator import get_thread_coordinator, ThreadCoordinator, ThreadType

logger = get_logger(__name__)


class VoiceAIApplication:
    """Main application class for Voice-to-AI Streaming System."""
    
    def __init__(self):
        self.config_manager: Optional[ConfigManager] = None
        self.settings: Optional[Settings] = None
        self.event_bus: Optional[EventBus] = None
        self.state_manager: Optional[StateManager] = None
        self.thread_coordinator: Optional[ThreadCoordinator] = None
        
        # Component instances
        self.audio_capture = None
        self.hotkey_manager = None
        self.stt_service = None
        self.ai_service = None
        self.overlay_manager = None
        self.settings_ui = None
        self.system_tray = None
        self.status_indicators = None
        
        self._shutdown_initiated = False
        
    def initialize(self) -> bool:
        """Initialize the application and all components."""
        try:
            logger.info("Initializing Voice-to-AI Streaming System")
            
            # Load configuration
            self.config_manager = ConfigManager()
            self.settings = self.config_manager.get_settings()
            
            # Setup logging with configuration
            setup_logging(self.settings.logging)
            logger.info("Configuration and logging initialized")
            
            # Initialize core systems
            self.event_bus = get_event_bus()
            self.state_manager = get_state_manager()
            self.thread_coordinator = get_thread_coordinator()
            
            # Start performance monitoring
            self.thread_coordinator.start_performance_monitoring()
            
            # Initialize components
            success = self._initialize_components()
            
            if success:
                self.state_manager.set_system_state(SystemState.READY)
                
                # Emit application started event
                self.event_bus.emit(
                    EventType.APPLICATION_STARTED,
                    "main_application",
                    {"version": "1.0.0", "components_initialized": True}
                )
                
                logger.info("Voice-to-AI Streaming System initialized successfully")
                return True
            else:
                logger.error("Failed to initialize all components")
                self.state_manager.set_system_state(SystemState.ERROR)
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            if self.state_manager:
                self.state_manager.set_system_state(SystemState.ERROR)
            return False
    
    def _initialize_components(self) -> bool:
        """Initialize all system components."""
        try:
            # Import and initialize actual components
            
            # Audio Capture Service
            from audio.capture_service import AudioCaptureService
            self.audio_capture = AudioCaptureService(
                self.event_bus, 
                self.state_manager, 
                self.settings.audio
            )
            logger.info("Audio capture service initialized")
            
            # Hotkey Manager
            from hotkeys.hotkey_manager import HotkeyManager
            self.hotkey_manager = HotkeyManager(
                self.event_bus,
                self.settings.hotkeys
            )
            logger.info("Hotkey manager initialized")
            
            # STT Service
            from stt.base_stt import create_stt_service
            self.stt_service = create_stt_service(
                self.settings.stt.provider,
                self.event_bus,
                self.settings.stt
            )
            logger.info(f"STT service initialized (provider: {self.settings.stt.provider})")
            
            # AI Service
            from ai.base_ai import create_ai_service
            self.ai_service = create_ai_service(
                self.settings.ai.provider,
                self.event_bus,
                self.settings.ai
            )
            logger.info(f"AI service initialized (provider: {self.settings.ai.provider})")
            
            # Overlay Manager
            from overlay.overlay_manager import OverlayManager, OverlayConfig
            from overlay.invisible_window import OverlayStyle
            
            overlay_config = OverlayConfig(
                auto_show_on_response=self.settings.overlay.auto_show_on_response,
                auto_hide_timeout=self.settings.overlay.auto_hide_timeout,
                position=tuple(self.settings.overlay.position),
                style=OverlayStyle(
                    font_family=self.settings.overlay.font_family,
                    font_size=self.settings.overlay.font_size,
                    text_color=self.settings.overlay.text_color,
                    background_color=self.settings.overlay.background_color,
                    background_alpha=self.settings.overlay.background_alpha,
                    max_width=self.settings.overlay.max_width,
                    max_height=self.settings.overlay.max_height
                )
            )
            
            self.overlay_manager = OverlayManager(
                self.event_bus,
                self.state_manager,
                overlay_config
            )
            logger.info("Overlay manager initialized")
            
            # Settings UI
            from ui.settings_window import SettingsWindow
            self.settings_ui = SettingsWindow(
                self.event_bus,
                self.config_manager
            )
            logger.info("Settings UI initialized")
            
            # System Tray (optional)
            from ui.system_tray import SystemTray, TrayConfig
            self.system_tray = SystemTray(
                self.event_bus,
                self.state_manager,
                TrayConfig(app_name="Voice-to-AI")
            )
            logger.info("System tray initialized")
            
            # Status Indicators (optional)
            from ui.status_indicators import StatusIndicators, IndicatorConfig
            self.status_indicators = StatusIndicators(
                self.event_bus,
                self.state_manager,
                IndicatorConfig(show_window=False)
            )
            logger.info("Status indicators initialized")
            
            # Subscribe to events for component coordination
            self._setup_event_handlers()
            
            # Start components
            self._start_components()
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers for component coordination."""
        # Handle recording workflow
        self.event_bus.subscribe(EventType.RECORDING_STOP_REQUESTED, self._handle_recording_stop)
        self.event_bus.subscribe(EventType.STT_RESULT_RECEIVED, self._handle_stt_result)
        self.event_bus.subscribe(EventType.AI_RESPONSE_RECEIVED, self._handle_ai_response)
        
        # Handle application control
        self.event_bus.subscribe(EventType.APPLICATION_EXIT_REQUESTED, self._handle_exit_request)
        self.event_bus.subscribe(EventType.SETTINGS_OPEN_REQUESTED, self._handle_settings_request)
        
        logger.info("Event handlers setup completed")
    
    def _start_components(self) -> None:
        """Start all components."""
        try:
            # Start audio capture
            if self.audio_capture:
                self.audio_capture.start()
            
            # Start hotkey manager
            if self.hotkey_manager:
                self.hotkey_manager.start()
            
            # Start overlay manager
            if self.overlay_manager:
                self.overlay_manager.start()
            
            # Start system tray
            if self.system_tray:
                self.system_tray.start()
            
            logger.info("All components started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start components: {e}")
    
    def _handle_recording_stop(self, data: Dict[str, Any]) -> None:
        """Handle recording stop and initiate audio processing."""
        audio_data = data.get('audio_data')
        if audio_data and self.stt_service:
            # Process audio with STT
            self.stt_service.process_audio(audio_data)
    
    def _handle_stt_result(self, data: Dict[str, Any]) -> None:
        """Handle STT result and send to AI."""
        text = data.get('text', '')
        if text and self.ai_service:
            # Send text to AI service
            self.ai_service.send_message(text)
    
    def _handle_ai_response(self, data: Dict[str, Any]) -> None:
        """Handle AI response."""
        response = data.get('response', '')
        if response:
            logger.info(f"AI response received: {len(response)} characters")
    
    def _handle_exit_request(self, data: Dict[str, Any]) -> None:
        """Handle application exit request."""
        logger.info("Exit requested, initiating shutdown")
        self.shutdown()
    
    def _handle_settings_request(self, data: Dict[str, Any]) -> None:
        """Handle settings window request."""
        if self.settings_ui:
            self.settings_ui.show()
    
    def run(self) -> None:
        """Run the main application loop."""
        try:
            logger.info("Starting main application loop")
            
            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Main event loop
            while not self._shutdown_initiated:
                try:
                    # Check system state
                    system_state = self.state_manager.get_system_state()
                    
                    if system_state == SystemState.ERROR:
                        logger.error("System in error state, initiating shutdown")
                        break
                    
                    if system_state == SystemState.STOPPED:
                        logger.info("System stopped, exiting main loop")
                        break
                    
                    # Sleep briefly to avoid busy waiting
                    time.sleep(0.1)
                    
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    self.state_manager.record_error("main_application", str(e), critical=True)
                    break
            
            logger.info("Main application loop ended")
            
        except Exception as e:
            logger.error(f"Fatal error in main application: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        if self._shutdown_initiated:
            return
        
        self._shutdown_initiated = True
        logger.info("Initiating application shutdown")
        
        try:
            # Emit shutdown event
            if self.event_bus:
                self.event_bus.emit(
                    EventType.APPLICATION_STOPPING,
                    "main_application",
                    {"reason": "shutdown_requested"}
                )
            
            # Update system state
            if self.state_manager:
                self.state_manager.set_system_state(SystemState.STOPPING)
            
            # Shutdown components in reverse order
            self._shutdown_components()
            
            # Shutdown core systems
            if self.thread_coordinator:
                self.thread_coordinator.shutdown()
            
            if self.state_manager:
                self.state_manager.set_system_state(SystemState.STOPPED)
                self.state_manager.shutdown()
            
            if self.event_bus:
                self.event_bus.shutdown()
            
            logger.info("Application shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _shutdown_components(self) -> None:
        """Shutdown all components."""
        try:
            components = [
                ("status_indicators", self.status_indicators),
                ("system_tray", self.system_tray),
                ("settings_ui", self.settings_ui),
                ("overlay_manager", self.overlay_manager),
                ("ai_service", self.ai_service),
                ("stt_service", self.stt_service),
                ("hotkey_manager", self.hotkey_manager),
                ("audio_capture", self.audio_capture)
            ]
            
            for component_name, component in components:
                if component:
                    try:
                        logger.debug(f"Shutting down {component_name}")
                        
                        # Use appropriate shutdown method based on component
                        if hasattr(component, 'stop'):
                            component.stop()
                        elif hasattr(component, 'shutdown'):
                            component.shutdown()
                        elif hasattr(component, 'hide'):
                            component.hide()
                        
                    except Exception as e:
                        logger.error(f"Error shutting down {component_name}: {e}")
            
            logger.info("All components shutdown completed")
            
        except Exception as e:
            logger.error(f"Error shutting down components: {e}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self.shutdown()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current application status."""
        if not self.state_manager:
            return {"status": "not_initialized"}
        
        return {
            "system_state": self.state_manager.get_system_state().value,
            "component_states": {
                name: state.value for name, state in 
                self.state_manager.get_state().component_states.items()
            },
            "performance": {
                "cpu_usage": self.state_manager.get_state().performance.cpu_usage,
                "memory_usage": self.state_manager.get_state().performance.memory_usage,
                "active_threads": self.state_manager.get_state().performance.active_threads
            },
            "errors": self.state_manager.get_active_errors()
        }


def main():
    """Main entry point."""
    try:
        # Create and initialize application
        app = VoiceAIApplication()
        
        if not app.initialize():
            logger.error("Failed to initialize application")
            sys.exit(1)
        
        # Run the application
        app.run()
        
        # Normal exit
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()