"""Global state management for Voice-to-AI system."""

import threading
from typing import Any, Dict, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

from .event_bus import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """Overall system states."""
    STARTING = "starting"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ComponentState(Enum):
    """Individual component states."""
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class AudioState:
    """Audio system state."""
    microphone_capturing: bool = False
    system_output_capturing: bool = False
    microphone_device: Optional[str] = None
    system_output_device: Optional[str] = None
    sample_rate: int = 16000
    buffer_size: int = 1024
    voice_activity_detected: bool = False
    recording_duration: float = 0.0
    last_audio_data_time: Optional[datetime] = None


@dataclass
class RecordingState:
    """Recording session state."""
    is_recording: bool = False
    start_time: Optional[datetime] = None
    duration: float = 0.0
    audio_data_size: int = 0
    voice_segments: int = 0


@dataclass
class STTState:
    """Speech-to-Text state."""
    active_provider: Optional[str] = None
    is_processing: bool = False
    current_text: str = ""
    confidence: float = 0.0
    language: str = "ru-RU"
    processing_time: float = 0.0
    last_result_time: Optional[datetime] = None


@dataclass
class AIState:
    """AI service state."""
    active_provider: Optional[str] = None
    is_processing: bool = False
    current_request: Optional[str] = None
    current_response: str = ""
    response_streaming: bool = False
    tokens_received: int = 0
    processing_time: float = 0.0
    last_response_time: Optional[datetime] = None


@dataclass
class OverlayState:
    """Overlay display state."""
    visible: bool = False
    position: Dict[str, int] = field(default_factory=lambda: {"x": 100, "y": 100, "width": 400, "height": 200})
    transparency: float = 0.9
    current_text: str = ""
    display_mode: str = "both"  # "questions", "answers", "both"
    always_on_top: bool = True


@dataclass
class HotkeyState:
    """Hotkey system state."""
    registered_hotkeys: Set[str] = field(default_factory=set)
    active_hotkeys: Dict[str, str] = field(default_factory=dict)
    last_hotkey_time: Optional[datetime] = None
    last_hotkey: Optional[str] = None


@dataclass
class PerformanceState:
    """System performance metrics."""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_threads: int = 0
    audio_latency: float = 0.0
    stt_latency: float = 0.0
    ai_latency: float = 0.0
    overlay_fps: float = 0.0
    last_performance_update: Optional[datetime] = None


@dataclass
class ErrorState:
    """Error tracking state."""
    last_error: Optional[str] = None
    error_count: int = 0
    last_error_time: Optional[datetime] = None
    critical_errors: int = 0
    component_errors: Dict[str, int] = field(default_factory=dict)


@dataclass
class GlobalState:
    """Complete system state."""
    system_state: SystemState = SystemState.STARTING
    component_states: Dict[str, ComponentState] = field(default_factory=dict)
    audio: AudioState = field(default_factory=AudioState)
    recording: RecordingState = field(default_factory=RecordingState)
    stt: STTState = field(default_factory=STTState)
    ai: AIState = field(default_factory=AIState)
    overlay: OverlayState = field(default_factory=OverlayState)
    hotkeys: HotkeyState = field(default_factory=HotkeyState)
    performance: PerformanceState = field(default_factory=PerformanceState)
    errors: ErrorState = field(default_factory=ErrorState)
    last_updated: datetime = field(default_factory=datetime.now)


StateChangeCallback = Callable[[str, Any, Any], None]


class StateManager:
    """Global state manager with thread-safe operations."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._state = GlobalState()
        self._lock = threading.RLock()
        self._event_bus = event_bus or get_event_bus()
        self._callbacks: Dict[str, Set[StateChangeCallback]] = {}
        
        # Initialize component states
        self._initialize_component_states()
        
        logger.info("StateManager initialized")
    
    def _initialize_component_states(self) -> None:
        """Initialize component states."""
        components = [
            "audio_capture",
            "hotkey_manager", 
            "stt_service",
            "ai_service",
            "overlay_manager",
            "settings_ui",
            "system_tray"
        ]
        
        with self._lock:
            for component in components:
                self._state.component_states[component] = ComponentState.INITIALIZING
    
    def get_state(self) -> GlobalState:
        """Get a copy of the current global state."""
        with self._lock:
            # Create a deep copy to prevent external modifications
            import copy
            return copy.deepcopy(self._state)
    
    def get_system_state(self) -> SystemState:
        """Get current system state."""
        with self._lock:
            return self._state.system_state
    
    def set_system_state(self, state: SystemState) -> None:
        """Set system state and notify subscribers."""
        with self._lock:
            old_state = self._state.system_state
            self._state.system_state = state
            self._state.last_updated = datetime.now()
        
        self._notify_state_change("system_state", old_state, state)
        self._event_bus.emit(
            EventType.CONFIGURATION_LOADED if state == SystemState.READY else EventType.APPLICATION_STOPPING,
            "state_manager",
            {"old_state": old_state.value, "new_state": state.value}
        )
        
        logger.info(f"System state changed: {old_state.value} -> {state.value}")
    
    def get_component_state(self, component: str) -> ComponentState:
        """Get state of a specific component."""
        with self._lock:
            return self._state.component_states.get(component, ComponentState.STOPPED)
    
    def set_component_state(self, component: str, state: ComponentState) -> None:
        """Set component state and notify subscribers."""
        with self._lock:
            old_state = self._state.component_states.get(component, ComponentState.STOPPED)
            self._state.component_states[component] = state
            self._state.last_updated = datetime.now()
        
        self._notify_state_change(f"component_state.{component}", old_state, state)
        
        logger.debug(f"Component {component} state: {old_state.value} -> {state.value}")
        
        # Update system state based on component states
        self._update_system_state_from_components()
    
    def update_audio_state(self, **kwargs) -> None:
        """Update audio state fields."""
        with self._lock:
            old_audio = self._state.audio
            for key, value in kwargs.items():
                if hasattr(self._state.audio, key):
                    setattr(self._state.audio, key, value)
            self._state.last_updated = datetime.now()
        
        self._notify_state_change("audio_state", old_audio, self._state.audio)
    
    def update_recording_state(self, **kwargs) -> None:
        """Update recording state fields."""
        with self._lock:
            old_recording = self._state.recording
            for key, value in kwargs.items():
                if hasattr(self._state.recording, key):
                    setattr(self._state.recording, key, value)
            self._state.last_updated = datetime.now()
        
        self._notify_state_change("recording_state", old_recording, self._state.recording)
    
    def update_stt_state(self, **kwargs) -> None:
        """Update STT state fields."""
        with self._lock:
            old_stt = self._state.stt
            for key, value in kwargs.items():
                if hasattr(self._state.stt, key):
                    setattr(self._state.stt, key, value)
            self._state.last_updated = datetime.now()
        
        self._notify_state_change("stt_state", old_stt, self._state.stt)
    
    def update_ai_state(self, **kwargs) -> None:
        """Update AI state fields."""
        with self._lock:
            old_ai = self._state.ai
            for key, value in kwargs.items():
                if hasattr(self._state.ai, key):
                    setattr(self._state.ai, key, value)
            self._state.last_updated = datetime.now()
        
        self._notify_state_change("ai_state", old_ai, self._state.ai)
    
    def update_overlay_state(self, **kwargs) -> None:
        """Update overlay state fields."""
        with self._lock:
            old_overlay = self._state.overlay
            for key, value in kwargs.items():
                if hasattr(self._state.overlay, key):
                    setattr(self._state.overlay, key, value)
            self._state.last_updated = datetime.now()
        
        self._notify_state_change("overlay_state", old_overlay, self._state.overlay)
    
    def update_performance_state(self, **kwargs) -> None:
        """Update performance metrics."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state.performance, key):
                    setattr(self._state.performance, key, value)
            self._state.performance.last_performance_update = datetime.now()
            self._state.last_updated = datetime.now()
    
    def record_error(self, component: str, error: str, critical: bool = False) -> None:
        """Record an error in the state."""
        with self._lock:
            self._state.errors.last_error = error
            self._state.errors.error_count += 1
            self._state.errors.last_error_time = datetime.now()
            
            if critical:
                self._state.errors.critical_errors += 1
            
            if component not in self._state.errors.component_errors:
                self._state.errors.component_errors[component] = 0
            self._state.errors.component_errors[component] += 1
            
            self._state.last_updated = datetime.now()
        
        logger.error(f"Error recorded for {component}: {error}")
        
        self._event_bus.emit(
            EventType.APPLICATION_ERROR,
            "state_manager",
            {
                "component": component,
                "error": error,
                "critical": critical,
                "total_errors": self._state.errors.error_count
            }
        )
    
    def is_system_ready(self) -> bool:
        """Check if system is ready for operation."""
        with self._lock:
            return self._state.system_state == SystemState.READY
    
    def is_recording_active(self) -> bool:
        """Check if recording is currently active."""
        with self._lock:
            return self._state.recording.is_recording
    
    def is_processing_active(self) -> bool:
        """Check if any processing is active."""
        with self._lock:
            return (self._state.stt.is_processing or 
                   self._state.ai.is_processing or
                   self._state.system_state == SystemState.PROCESSING)
    
    def get_active_errors(self) -> Dict[str, Any]:
        """Get current error information."""
        with self._lock:
            return {
                "last_error": self._state.errors.last_error,
                "error_count": self._state.errors.error_count,
                "last_error_time": self._state.errors.last_error_time,
                "critical_errors": self._state.errors.critical_errors,
                "component_errors": self._state.errors.component_errors.copy()
            }
    
    def register_state_callback(self, state_path: str, callback: StateChangeCallback) -> None:
        """Register callback for state changes.
        
        Args:
            state_path: Path to state field (e.g., "system_state", "audio_state.microphone_capturing")
            callback: Function to call when state changes
        """
        with self._lock:
            if state_path not in self._callbacks:
                self._callbacks[state_path] = set()
            self._callbacks[state_path].add(callback)
        
        logger.debug(f"Registered state callback for {state_path}")
    
    def unregister_state_callback(self, state_path: str, callback: StateChangeCallback) -> None:
        """Unregister state change callback."""
        with self._lock:
            if state_path in self._callbacks:
                self._callbacks[state_path].discard(callback)
                if not self._callbacks[state_path]:
                    del self._callbacks[state_path]
        
        logger.debug(f"Unregistered state callback for {state_path}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current state for debugging/monitoring."""
        with self._lock:
            return {
                "system_state": self._state.system_state.value,
                "component_states": {k: v.value for k, v in self._state.component_states.items()},
                "recording_active": self._state.recording.is_recording,
                "processing_active": self._state.stt.is_processing or self._state.ai.is_processing,
                "overlay_visible": self._state.overlay.visible,
                "error_count": self._state.errors.error_count,
                "last_updated": self._state.last_updated.isoformat(),
                "performance": {
                    "cpu_usage": self._state.performance.cpu_usage,
                    "memory_usage": self._state.performance.memory_usage,
                    "active_threads": self._state.performance.active_threads
                }
            }
    
    def _update_system_state_from_components(self) -> None:
        """Update system state based on component states."""
        component_states = list(self._state.component_states.values())
        
        # Check if any components are in error state
        if ComponentState.ERROR in component_states:
            if self._state.system_state != SystemState.ERROR:
                self.set_system_state(SystemState.ERROR)
            return
        
        # Check if all components are ready
        if all(state in [ComponentState.READY, ComponentState.IDLE] for state in component_states):
            if self._state.system_state not in [SystemState.READY, SystemState.RECORDING, SystemState.PROCESSING]:
                self.set_system_state(SystemState.READY)
            return
        
        # Check if any components are still initializing
        if ComponentState.INITIALIZING in component_states:
            if self._state.system_state != SystemState.STARTING:
                self.set_system_state(SystemState.STARTING)
            return
        
        # Check if any components are stopping
        if ComponentState.STOPPING in component_states:
            if self._state.system_state != SystemState.STOPPING:
                self.set_system_state(SystemState.STOPPING)
            return
        
        # Check if all components are stopped
        if all(state == ComponentState.STOPPED for state in component_states):
            if self._state.system_state != SystemState.STOPPED:
                self.set_system_state(SystemState.STOPPED)
            return
    
    def _notify_state_change(self, state_path: str, old_value: Any, new_value: Any) -> None:
        """Notify registered callbacks of state changes."""
        if state_path in self._callbacks:
            for callback in self._callbacks[state_path].copy():
                try:
                    callback(state_path, old_value, new_value)
                except Exception as e:
                    logger.error(f"Error in state change callback for {state_path}: {e}")
    
    def shutdown(self) -> None:
        """Shutdown state manager."""
        logger.info("StateManager shutting down")
        
        with self._lock:
            self._callbacks.clear()
            self.set_system_state(SystemState.STOPPED)
        
        logger.info("StateManager shutdown complete")


# Global state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager