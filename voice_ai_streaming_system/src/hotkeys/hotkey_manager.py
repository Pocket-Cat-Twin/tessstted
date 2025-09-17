"""Global hotkey management for Voice-to-AI system."""

import threading
import time
from typing import Dict, Callable, Optional, Any, Set
import logging
from dataclasses import dataclass
from enum import Enum

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    logging.warning("keyboard library not available, hotkeys will not work")

try:
    from pynput import keyboard as pynput_keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput library not available")

try:
    from ..config.settings import HotkeySettings
    from ..core.event_bus import EventBus, EventType, get_event_bus
    from ..core.state_manager import StateManager, ComponentState, get_state_manager
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config.settings import HotkeySettings
    from core.event_bus import EventBus, EventType, get_event_bus
    from core.state_manager import StateManager, ComponentState, get_state_manager

logger = logging.getLogger(__name__)


class HotkeyBackend(Enum):
    """Hotkey backend implementations."""
    KEYBOARD = "keyboard"
    PYNPUT = "pynput"


@dataclass
class HotkeyBinding:
    """Hotkey binding information."""
    name: str
    key_combination: str
    callback: Callable[[], None]
    description: str
    enabled: bool = True
    last_triggered: Optional[float] = None
    trigger_count: int = 0


class HotkeyManager:
    """Global hotkey manager with multiple backend support."""
    
    def __init__(
        self,
        settings: HotkeySettings,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        self.settings = settings
        self._event_bus = event_bus or get_event_bus()
        self._state_manager = state_manager or get_state_manager()
        
        # Backend selection
        self._backend = self._select_backend()
        
        # Hotkey bindings
        self._bindings: Dict[str, HotkeyBinding] = {}
        self._registered_keys: Set[str] = set()
        
        # State
        self._enabled = True
        self._recording_active = False
        
        # Performance tracking
        self._debounce_time = 0.2  # 200ms debounce
        self._last_trigger_times: Dict[str, float] = {}
        
        # Threading
        self._lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # PynInput listener
        self._pynput_listener: Optional[pynput_keyboard.Listener] = None
        
        logger.info(f"HotkeyManager initialized with backend: {self._backend.value if self._backend else 'none'}")
    
    def _select_backend(self) -> Optional[HotkeyBackend]:
        """Select the best available hotkey backend."""
        if KEYBOARD_AVAILABLE:
            return HotkeyBackend.KEYBOARD
        elif PYNPUT_AVAILABLE:
            return HotkeyBackend.PYNPUT
        else:
            logger.error("No hotkey backend available")
            return None
    
    def initialize(self) -> bool:
        """Initialize hotkey system and register default hotkeys."""
        try:
            if not self._backend:
                logger.error("No hotkey backend available")
                return False
            
            # Register default hotkeys
            success = self._register_default_hotkeys()
            
            if success:
                # Start monitoring
                self._start_monitoring()
                
                # Update state
                self._state_manager.set_component_state("hotkey_manager", ComponentState.READY)
                
                logger.info("Hotkey system initialized successfully")
                return True
            else:
                logger.error("Failed to register default hotkeys")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize hotkey system: {e}")
            self._state_manager.record_error("hotkey_manager", str(e), critical=True)
            return False
    
    def _register_default_hotkeys(self) -> bool:
        """Register default system hotkeys."""
        try:
            # Start recording hotkey
            self.register_hotkey(
                "start_recording",
                self.settings.start_recording,
                self._on_start_recording,
                "Start voice recording"
            )
            
            # Stop recording hotkey
            self.register_hotkey(
                "stop_recording",
                self.settings.stop_recording,
                self._on_stop_recording,
                "Stop voice recording and process"
            )
            
            # Toggle overlay hotkey
            self.register_hotkey(
                "toggle_overlay",
                self.settings.toggle_overlay,
                self._on_toggle_overlay,
                "Toggle overlay visibility"
            )
            
            # Toggle settings hotkey
            self.register_hotkey(
                "toggle_settings",
                self.settings.toggle_settings,
                self._on_toggle_settings,
                "Toggle settings window"
            )
            
            # Emergency stop hotkey
            self.register_hotkey(
                "emergency_stop",
                self.settings.emergency_stop,
                self._on_emergency_stop,
                "Emergency stop all operations"
            )
            
            logger.info(f"Registered {len(self._bindings)} default hotkeys")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register default hotkeys: {e}")
            return False
    
    def register_hotkey(
        self,
        name: str,
        key_combination: str,
        callback: Callable[[], None],
        description: str = ""
    ) -> bool:
        """Register a new hotkey.
        
        Args:
            name: Unique hotkey name
            key_combination: Key combination string (e.g., "ctrl+shift+f1")
            callback: Function to call when hotkey is triggered
            description: Human-readable description
            
        Returns:
            True if hotkey was registered successfully
        """
        try:
            with self._lock:
                if name in self._bindings:
                    logger.warning(f"Hotkey {name} already registered, unregistering first")
                    self.unregister_hotkey(name)
                
                # Normalize key combination
                normalized_keys = self._normalize_key_combination(key_combination)
                
                # Check for conflicts
                if normalized_keys in self._registered_keys:
                    logger.error(f"Key combination {key_combination} already registered")
                    return False
                
                # Create binding
                binding = HotkeyBinding(
                    name=name,
                    key_combination=normalized_keys,
                    callback=callback,
                    description=description
                )
                
                # Register with backend
                if self._register_with_backend(binding):
                    self._bindings[name] = binding
                    self._registered_keys.add(normalized_keys)
                    
                    logger.info(f"Registered hotkey: {name} ({key_combination})")
                    return True
                else:
                    logger.error(f"Failed to register hotkey with backend: {name}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to register hotkey {name}: {e}")
            return False
    
    def unregister_hotkey(self, name: str) -> bool:
        """Unregister a hotkey.
        
        Args:
            name: Hotkey name to unregister
            
        Returns:
            True if hotkey was unregistered successfully
        """
        try:
            with self._lock:
                if name not in self._bindings:
                    logger.warning(f"Hotkey {name} not found")
                    return False
                
                binding = self._bindings[name]
                
                # Unregister with backend
                if self._unregister_with_backend(binding):
                    del self._bindings[name]
                    self._registered_keys.discard(binding.key_combination)
                    
                    logger.info(f"Unregistered hotkey: {name}")
                    return True
                else:
                    logger.error(f"Failed to unregister hotkey with backend: {name}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to unregister hotkey {name}: {e}")
            return False
    
    def _register_with_backend(self, binding: HotkeyBinding) -> bool:
        """Register hotkey with the selected backend."""
        try:
            if self._backend == HotkeyBackend.KEYBOARD and KEYBOARD_AVAILABLE:
                # Create wrapper callback with debouncing
                def debounced_callback():
                    self._trigger_hotkey(binding.name)
                
                # Register with keyboard library
                keyboard.add_hotkey(binding.key_combination, debounced_callback)
                return True
                
            elif self._backend == HotkeyBackend.PYNPUT and PYNPUT_AVAILABLE:
                # For pynput, we'll handle key combinations in the listener
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to register with backend: {e}")
            return False
    
    def _unregister_with_backend(self, binding: HotkeyBinding) -> bool:
        """Unregister hotkey with the selected backend."""
        try:
            if self._backend == HotkeyBackend.KEYBOARD and KEYBOARD_AVAILABLE:
                # Remove hotkey from keyboard library
                keyboard.remove_hotkey(binding.key_combination)
                return True
                
            elif self._backend == HotkeyBackend.PYNPUT and PYNPUT_AVAILABLE:
                # For pynput, we handle this in the listener
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister with backend: {e}")
            return False
    
    def _normalize_key_combination(self, key_combination: str) -> str:
        """Normalize key combination string."""
        # Convert to lowercase and standardize separators
        normalized = key_combination.lower().replace(" ", "").replace("-", "+")
        
        # Standardize modifier names
        replacements = {
            "control": "ctrl",
            "command": "cmd",
            "option": "alt",
            "windows": "win"
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _start_monitoring(self) -> None:
        """Start hotkey monitoring."""
        try:
            if self._backend == HotkeyBackend.PYNPUT and PYNPUT_AVAILABLE:
                # Start pynput listener
                self._pynput_listener = pynput_keyboard.Listener(
                    on_press=self._on_pynput_key_press,
                    on_release=self._on_pynput_key_release
                )
                self._pynput_listener.start()
                logger.debug("Started pynput keyboard listener")
            
            # Start monitoring thread for additional functionality
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="HotkeyMonitor",
                daemon=True
            )
            self._monitor_thread.start()
            
            logger.debug("Hotkey monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
    
    def _monitor_loop(self) -> None:
        """Monitor loop for additional hotkey functionality."""
        try:
            while not self._stop_event.wait(1.0):
                # Update state manager with hotkey status
                self._state_manager.update_audio_state(
                    # Could add hotkey-related state here
                )
                
                # Check for stuck keys or other issues
                # This is a placeholder for additional monitoring logic
                
        except Exception as e:
            logger.error(f"Error in hotkey monitor loop: {e}")
    
    def _on_pynput_key_press(self, key) -> None:
        """Handle pynput key press events."""
        # This is a simplified implementation
        # In a full implementation, you'd track modifier states
        # and match against registered key combinations
        pass
    
    def _on_pynput_key_release(self, key) -> None:
        """Handle pynput key release events."""
        pass
    
    def _trigger_hotkey(self, name: str) -> None:
        """Trigger a hotkey callback with debouncing."""
        try:
            with self._lock:
                if not self._enabled:
                    return
                
                if name not in self._bindings:
                    logger.warning(f"Unknown hotkey triggered: {name}")
                    return
                
                binding = self._bindings[name]
                
                if not binding.enabled:
                    logger.debug(f"Hotkey {name} is disabled")
                    return
                
                # Check debouncing
                current_time = time.time()
                last_trigger = self._last_trigger_times.get(name, 0)
                
                if current_time - last_trigger < self._debounce_time:
                    logger.debug(f"Hotkey {name} debounced")
                    return
                
                # Update trigger time and stats
                self._last_trigger_times[name] = current_time
                binding.last_triggered = current_time
                binding.trigger_count += 1
                
                logger.debug(f"Triggering hotkey: {name}")
                
                # Emit event
                self._event_bus.emit(
                    self._get_event_type_for_hotkey(name),
                    "hotkey_manager",
                    {
                        "hotkey_name": name,
                        "key_combination": binding.key_combination,
                        "timestamp": current_time
                    }
                )
                
                # Call callback
                try:
                    binding.callback()
                except Exception as e:
                    logger.error(f"Error in hotkey callback for {name}: {e}")
                
        except Exception as e:
            logger.error(f"Error triggering hotkey {name}: {e}")
    
    def _get_event_type_for_hotkey(self, name: str) -> EventType:
        """Get event type for hotkey name."""
        event_mapping = {
            "start_recording": EventType.HOTKEY_START_RECORDING,
            "stop_recording": EventType.HOTKEY_STOP_RECORDING,
            "toggle_overlay": EventType.HOTKEY_TOGGLE_OVERLAY,
            "toggle_settings": EventType.HOTKEY_TOGGLE_SETTINGS,
            "emergency_stop": EventType.HOTKEY_EMERGENCY_STOP
        }
        
        return event_mapping.get(name, EventType.APPLICATION_STARTED)  # Default event
    
    def _on_start_recording(self) -> None:
        """Handle start recording hotkey."""
        logger.info("Start recording hotkey triggered")
        
        if self._recording_active:
            logger.warning("Recording already active")
            return
        
        self._recording_active = True
        
        # Update state manager
        self._state_manager.update_recording_state(
            is_recording=True,
            start_time=time.time()
        )
    
    def _on_stop_recording(self) -> None:
        """Handle stop recording hotkey."""
        logger.info("Stop recording hotkey triggered")
        
        if not self._recording_active:
            logger.warning("No recording active")
            return
        
        self._recording_active = False
        
        # Update state manager
        self._state_manager.update_recording_state(
            is_recording=False
        )
    
    def _on_toggle_overlay(self) -> None:
        """Handle toggle overlay hotkey."""
        logger.info("Toggle overlay hotkey triggered")
        # Overlay toggle logic would be handled by overlay manager
        pass
    
    def _on_toggle_settings(self) -> None:
        """Handle toggle settings hotkey."""
        logger.info("Toggle settings hotkey triggered")
        # Settings window toggle logic would be handled by UI manager
        pass
    
    def _on_emergency_stop(self) -> None:
        """Handle emergency stop hotkey."""
        logger.warning("Emergency stop hotkey triggered")
        
        # Stop all operations
        self._recording_active = False
        
        # Update state manager
        self._state_manager.update_recording_state(is_recording=False)
        
        # Emit emergency stop event
        self._event_bus.emit(
            EventType.APPLICATION_ERROR,
            "hotkey_manager",
            {"reason": "emergency_stop", "timestamp": time.time()}
        )
    
    def enable_hotkey(self, name: str) -> bool:
        """Enable a specific hotkey."""
        with self._lock:
            if name in self._bindings:
                self._bindings[name].enabled = True
                logger.debug(f"Enabled hotkey: {name}")
                return True
            return False
    
    def disable_hotkey(self, name: str) -> bool:
        """Disable a specific hotkey."""
        with self._lock:
            if name in self._bindings:
                self._bindings[name].enabled = False
                logger.debug(f"Disabled hotkey: {name}")
                return True
            return False
    
    def enable_all_hotkeys(self) -> None:
        """Enable all hotkeys."""
        with self._lock:
            self._enabled = True
            for binding in self._bindings.values():
                binding.enabled = True
            logger.info("All hotkeys enabled")
    
    def disable_all_hotkeys(self) -> None:
        """Disable all hotkeys."""
        with self._lock:
            self._enabled = False
            for binding in self._bindings.values():
                binding.enabled = False
            logger.info("All hotkeys disabled")
    
    def is_recording_active(self) -> bool:
        """Check if recording is currently active."""
        return self._recording_active
    
    def get_hotkey_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific hotkey."""
        with self._lock:
            if name in self._bindings:
                binding = self._bindings[name]
                return {
                    "name": binding.name,
                    "key_combination": binding.key_combination,
                    "description": binding.description,
                    "enabled": binding.enabled,
                    "last_triggered": binding.last_triggered,
                    "trigger_count": binding.trigger_count
                }
            return None
    
    def get_all_hotkeys_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered hotkeys."""
        with self._lock:
            return {
                name: {
                    "name": binding.name,
                    "key_combination": binding.key_combination,
                    "description": binding.description,
                    "enabled": binding.enabled,
                    "last_triggered": binding.last_triggered,
                    "trigger_count": binding.trigger_count
                }
                for name, binding in self._bindings.items()
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hotkey system statistics."""
        with self._lock:
            total_triggers = sum(binding.trigger_count for binding in self._bindings.values())
            enabled_count = sum(1 for binding in self._bindings.values() if binding.enabled)
            
            return {
                "backend": self._backend.value if self._backend else "none",
                "enabled": self._enabled,
                "total_hotkeys": len(self._bindings),
                "enabled_hotkeys": enabled_count,
                "total_triggers": total_triggers,
                "recording_active": self._recording_active,
                "available_backends": {
                    "keyboard": KEYBOARD_AVAILABLE,
                    "pynput": PYNPUT_AVAILABLE
                }
            }
    
    def shutdown(self) -> None:
        """Shutdown hotkey manager."""
        logger.info("Shutting down HotkeyManager")
        
        try:
            # Stop monitoring
            self._stop_event.set()
            
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=2.0)
            
            # Stop pynput listener
            if self._pynput_listener:
                self._pynput_listener.stop()
                self._pynput_listener = None
            
            # Unregister all hotkeys
            with self._lock:
                hotkey_names = list(self._bindings.keys())
                for name in hotkey_names:
                    self.unregister_hotkey(name)
            
            # Clear keyboard library hotkeys if using keyboard backend
            if self._backend == HotkeyBackend.KEYBOARD and KEYBOARD_AVAILABLE:
                try:
                    keyboard.unhook_all()
                except Exception as e:
                    logger.warning(f"Error unhooking keyboard: {e}")
            
            # Update state
            self._state_manager.set_component_state("hotkey_manager", ComponentState.STOPPED)
            
            logger.info("HotkeyManager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during hotkey manager shutdown: {e}")