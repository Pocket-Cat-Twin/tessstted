"""Status indicators and visual feedback system."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Tuple
import threading
import time
import math
from enum import Enum
from dataclasses import dataclass

from ..core.event_bus import EventBus, EventType
from ..core.state_manager import StateManager, SystemState


class IndicatorType(Enum):
    """Status indicator types."""
    SYSTEM = "system"
    RECORDING = "recording"
    STT = "stt"
    AI = "ai"
    OVERLAY = "overlay"
    AUDIO = "audio"
    HOTKEYS = "hotkeys"


class IndicatorState(Enum):
    """Indicator states."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class IndicatorConfig:
    """Status indicator configuration."""
    show_window: bool = True
    window_title: str = "Voice-to-AI Status"
    window_size: Tuple[int, int] = (300, 200)
    window_position: Tuple[int, int] = (10, 10)
    always_on_top: bool = True
    auto_hide: bool = False
    auto_hide_delay: float = 5.0


class StatusIndicators:
    """
    Status indicators and visual feedback system.
    
    Provides visual status indicators for all system components
    including recording, STT, AI processing, and system health.
    """
    
    def __init__(self, event_bus: EventBus, state_manager: StateManager,
                 config: Optional[IndicatorConfig] = None):
        """
        Initialize status indicators.
        
        Args:
            event_bus: Event bus for communication
            state_manager: Global state manager
            config: Indicator configuration
        """
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.config = config or IndicatorConfig()
        
        # UI components
        self.window: Optional[tk.Toplevel] = None
        self.indicators: Dict[IndicatorType, Dict[str, Any]] = {}
        self.is_visible = False
        
        # Animation state
        self.animation_active = False
        self.animation_thread: Optional[threading.Thread] = None
        
        # Auto-hide timer
        self.auto_hide_timer: Optional[threading.Timer] = None
        
        # Initialize indicators
        self._initialize_indicators()
        
        # Subscribe to events
        self._subscribe_to_events()
    
    def _initialize_indicators(self) -> None:
        """Initialize status indicators."""
        indicator_configs = {
            IndicatorType.SYSTEM: {
                'label': 'System',
                'state': IndicatorState.INACTIVE,
                'description': 'Overall system status'
            },
            IndicatorType.RECORDING: {
                'label': 'Recording',
                'state': IndicatorState.INACTIVE,
                'description': 'Audio recording status'
            },
            IndicatorType.STT: {
                'label': 'Speech-to-Text',
                'state': IndicatorState.INACTIVE,
                'description': 'STT processing status'
            },
            IndicatorType.AI: {
                'label': 'AI Processing',
                'state': IndicatorState.INACTIVE,
                'description': 'AI response generation'
            },
            IndicatorType.OVERLAY: {
                'label': 'Overlay',
                'state': IndicatorState.INACTIVE,
                'description': 'Overlay display status'
            },
            IndicatorType.AUDIO: {
                'label': 'Audio System',
                'state': IndicatorState.INACTIVE,
                'description': 'Audio capture system'
            },
            IndicatorType.HOTKEYS: {
                'label': 'Hotkeys',
                'state': IndicatorState.INACTIVE,
                'description': 'Global hotkey system'
            }
        }
        
        for indicator_type, config in indicator_configs.items():
            self.indicators[indicator_type] = {
                **config,
                'widget': None,
                'status_widget': None,
                'last_update': time.time()
            }
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        # System events
        self.event_bus.subscribe(EventType.SYSTEM_STATE_CHANGED, self._handle_system_state)
        self.event_bus.subscribe(EventType.APPLICATION_STARTED, self._handle_app_started)
        self.event_bus.subscribe(EventType.APPLICATION_STOPPING, self._handle_app_stopping)
        
        # Recording events
        self.event_bus.subscribe(EventType.RECORDING_STARTED, self._handle_recording_started)
        self.event_bus.subscribe(EventType.RECORDING_STOPPED, self._handle_recording_stopped)
        
        # STT events
        self.event_bus.subscribe(EventType.STT_PROCESSING_STARTED, self._handle_stt_started)
        self.event_bus.subscribe(EventType.STT_RESULT_RECEIVED, self._handle_stt_result)
        
        # AI events
        self.event_bus.subscribe(EventType.AI_REQUEST_SENT, self._handle_ai_started)
        self.event_bus.subscribe(EventType.AI_RESPONSE_RECEIVED, self._handle_ai_response)
        self.event_bus.subscribe(EventType.AI_STREAM_START, self._handle_ai_stream_start)
        self.event_bus.subscribe(EventType.AI_STREAM_END, self._handle_ai_stream_end)
        
        # Overlay events
        self.event_bus.subscribe(EventType.OVERLAY_SHOWN, self._handle_overlay_shown)
        self.event_bus.subscribe(EventType.OVERLAY_HIDDEN, self._handle_overlay_hidden)
        
        # Component events
        self.event_bus.subscribe(EventType.AUDIO_SERVICE_STARTED, self._handle_audio_started)
        self.event_bus.subscribe(EventType.AUDIO_SERVICE_STOPPED, self._handle_audio_stopped)
        self.event_bus.subscribe(EventType.HOTKEY_SERVICE_STARTED, self._handle_hotkeys_started)
        self.event_bus.subscribe(EventType.HOTKEY_SERVICE_STOPPED, self._handle_hotkeys_stopped)
        
        # Error events
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, self._handle_error)
        
        # Manual control
        self.event_bus.subscribe(EventType.STATUS_INDICATORS_SHOW_REQUESTED, self._handle_show_request)
        self.event_bus.subscribe(EventType.STATUS_INDICATORS_HIDE_REQUESTED, self._handle_hide_request)
    
    def show(self) -> None:
        """Show status indicators window."""
        if self.is_visible and self.window:
            # Bring to front if already visible
            self.window.lift()
            return
        
        self._create_window()
        self.is_visible = True
        
        if self.config.auto_hide:
            self._start_auto_hide_timer()
        
        self.event_bus.publish(EventType.STATUS_INDICATORS_SHOWN, {})
    
    def hide(self) -> None:
        """Hide status indicators window."""
        if self.window:
            self.window.destroy()
            self.window = None
            self.is_visible = False
            
            self._cancel_auto_hide_timer()
            
            self.event_bus.publish(EventType.STATUS_INDICATORS_HIDDEN, {})
    
    def toggle(self) -> None:
        """Toggle status indicators visibility."""
        if self.is_visible:
            self.hide()
        else:
            self.show()
    
    def _create_window(self) -> None:
        """Create status indicators window."""
        # Create window
        self.window = tk.Toplevel()
        self.window.title(self.config.window_title)
        self.window.geometry(f"{self.config.window_size[0]}x{self.config.window_size[1]}+"
                           f"{self.config.window_position[0]}+{self.config.window_position[1]}")
        
        # Configure window properties
        if self.config.always_on_top:
            self.window.attributes('-topmost', True)
        
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Create main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create indicators
        self._create_indicator_widgets(main_frame)
        
        # Update all indicators
        self._update_all_indicators()
    
    def _create_indicator_widgets(self, parent: ttk.Frame) -> None:
        """Create indicator widgets."""
        for i, (indicator_type, indicator) in enumerate(self.indicators.items()):
            # Create frame for indicator
            frame = ttk.Frame(parent)
            frame.grid(row=i, column=0, sticky=tk.EW, pady=2)
            parent.grid_columnconfigure(0, weight=1)
            
            # Label
            label = ttk.Label(frame, text=indicator['label'], width=15)
            label.grid(row=0, column=0, sticky=tk.W)
            
            # Status indicator (colored circle)
            status_frame = tk.Frame(frame, width=20, height=20)
            status_frame.grid(row=0, column=1, padx=5)
            status_frame.grid_propagate(False)
            
            canvas = tk.Canvas(status_frame, width=16, height=16, highlightthickness=0)
            canvas.pack(expand=True)
            
            # Description label
            desc_label = ttk.Label(frame, text=indicator['description'], 
                                 font=("Arial", 8), foreground="#666666")
            desc_label.grid(row=0, column=2, sticky=tk.W, padx=10)
            
            # Store widget references
            indicator['widget'] = frame
            indicator['status_widget'] = canvas
            indicator['label_widget'] = label
            indicator['desc_widget'] = desc_label
        
        # Add control buttons
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=len(self.indicators), column=0, pady=10, sticky=tk.EW)
        
        ttk.Button(button_frame, text="Hide", command=self.hide).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self._update_all_indicators).pack(side=tk.RIGHT, padx=5)
    
    def _update_indicator(self, indicator_type: IndicatorType, state: IndicatorState, 
                         description: Optional[str] = None) -> None:
        """Update specific indicator."""
        if indicator_type not in self.indicators:
            return
        
        indicator = self.indicators[indicator_type]
        indicator['state'] = state
        indicator['last_update'] = time.time()
        
        if description:
            indicator['description'] = description
        
        # Update widget if visible
        if self.is_visible and indicator['status_widget']:
            self._update_indicator_widget(indicator)
        
        # Restart auto-hide timer if needed
        if self.config.auto_hide and self.is_visible:
            self._start_auto_hide_timer()
    
    def _update_indicator_widget(self, indicator: Dict[str, Any]) -> None:
        """Update indicator widget appearance."""
        canvas = indicator['status_widget']
        state = indicator['state']
        
        if not canvas:
            return
        
        # Clear canvas
        canvas.delete("all")
        
        # Define colors for states
        colors = {
            IndicatorState.INACTIVE: '#808080',    # Gray
            IndicatorState.ACTIVE: '#4CAF50',      # Green
            IndicatorState.PROCESSING: '#FF9800',  # Orange
            IndicatorState.ERROR: '#F44336',       # Red
            IndicatorState.WARNING: '#FFC107'      # Yellow
        }
        
        color = colors.get(state, '#808080')
        
        # Draw status circle
        canvas.create_oval(2, 2, 14, 14, fill=color, outline='#FFFFFF', width=1)
        
        # Add animation for processing state
        if state == IndicatorState.PROCESSING:
            self._start_processing_animation(canvas)
        
        # Update description if widget exists
        if 'desc_widget' in indicator:
            indicator['desc_widget'].config(text=indicator['description'])
    
    def _start_processing_animation(self, canvas: tk.Canvas) -> None:
        """Start processing animation for indicator."""
        def animate():
            if not self.animation_active:
                return
            
            try:
                # Simple pulsing animation
                current_time = time.time()
                alpha = (1 + math.sin(current_time * 4)) / 2  # Pulse between 0 and 1
                
                # Update canvas (simplified - tkinter doesn't support alpha directly)
                canvas.after(100, animate)
                
            except tk.TclError:
                # Widget destroyed
                pass
        
        if not self.animation_active:
            self.animation_active = True
            animate()
    
    def _update_all_indicators(self) -> None:
        """Update all indicators based on current state."""
        if not self.is_visible:
            return
        
        for indicator_type, indicator in self.indicators.items():
            self._update_indicator_widget(indicator)
    
    def _start_auto_hide_timer(self) -> None:
        """Start auto-hide timer."""
        self._cancel_auto_hide_timer()
        
        if self.config.auto_hide and self.config.auto_hide_delay > 0:
            self.auto_hide_timer = threading.Timer(
                self.config.auto_hide_delay,
                self.hide
            )
            self.auto_hide_timer.daemon = True
            self.auto_hide_timer.start()
    
    def _cancel_auto_hide_timer(self) -> None:
        """Cancel auto-hide timer."""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            self.auto_hide_timer = None
    
    # Event handlers
    def _handle_system_state(self, data: Dict[str, Any]) -> None:
        """Handle system state change."""
        new_state = data.get('new_state')
        
        if new_state == SystemState.READY:
            self._update_indicator(IndicatorType.SYSTEM, IndicatorState.ACTIVE, "System ready")
        elif new_state == SystemState.RECORDING:
            self._update_indicator(IndicatorType.SYSTEM, IndicatorState.PROCESSING, "Recording active")
        elif new_state == SystemState.PROCESSING:
            self._update_indicator(IndicatorType.SYSTEM, IndicatorState.PROCESSING, "Processing audio")
        elif new_state == SystemState.ERROR:
            self._update_indicator(IndicatorType.SYSTEM, IndicatorState.ERROR, "System error")
        else:
            self._update_indicator(IndicatorType.SYSTEM, IndicatorState.INACTIVE, "System stopped")
    
    def _handle_app_started(self, data: Dict[str, Any]) -> None:
        """Handle application started."""
        self._update_indicator(IndicatorType.SYSTEM, IndicatorState.ACTIVE, "System started")
    
    def _handle_app_stopping(self, data: Dict[str, Any]) -> None:
        """Handle application stopping."""
        self._update_indicator(IndicatorType.SYSTEM, IndicatorState.INACTIVE, "System stopping")
    
    def _handle_recording_started(self, data: Dict[str, Any]) -> None:
        """Handle recording started."""
        device = data.get('device', 'Unknown')
        self._update_indicator(IndicatorType.RECORDING, IndicatorState.ACTIVE, 
                             f"Recording from {device}")
    
    def _handle_recording_stopped(self, data: Dict[str, Any]) -> None:
        """Handle recording stopped."""
        self._update_indicator(IndicatorType.RECORDING, IndicatorState.INACTIVE, "Recording stopped")
    
    def _handle_stt_started(self, data: Dict[str, Any]) -> None:
        """Handle STT processing started."""
        provider = data.get('provider', 'Unknown')
        self._update_indicator(IndicatorType.STT, IndicatorState.PROCESSING, 
                             f"Processing with {provider}")
    
    def _handle_stt_result(self, data: Dict[str, Any]) -> None:
        """Handle STT result received."""
        confidence = data.get('confidence', 0)
        self._update_indicator(IndicatorType.STT, IndicatorState.ACTIVE, 
                             f"Transcribed ({confidence:.1%} confidence)")
    
    def _handle_ai_started(self, data: Dict[str, Any]) -> None:
        """Handle AI processing started."""
        provider = data.get('provider', 'Unknown')
        self._update_indicator(IndicatorType.AI, IndicatorState.PROCESSING, 
                             f"Processing with {provider}")
    
    def _handle_ai_response(self, data: Dict[str, Any]) -> None:
        """Handle AI response received."""
        tokens = data.get('usage', {}).get('total_tokens', 0)
        self._update_indicator(IndicatorType.AI, IndicatorState.ACTIVE, 
                             f"Response received ({tokens} tokens)")
    
    def _handle_ai_stream_start(self, data: Dict[str, Any]) -> None:
        """Handle AI stream start."""
        self._update_indicator(IndicatorType.AI, IndicatorState.PROCESSING, "Streaming response")
    
    def _handle_ai_stream_end(self, data: Dict[str, Any]) -> None:
        """Handle AI stream end."""
        self._update_indicator(IndicatorType.AI, IndicatorState.ACTIVE, "Stream completed")
    
    def _handle_overlay_shown(self, data: Dict[str, Any]) -> None:
        """Handle overlay shown."""
        self._update_indicator(IndicatorType.OVERLAY, IndicatorState.ACTIVE, "Overlay visible")
    
    def _handle_overlay_hidden(self, data: Dict[str, Any]) -> None:
        """Handle overlay hidden."""
        self._update_indicator(IndicatorType.OVERLAY, IndicatorState.INACTIVE, "Overlay hidden")
    
    def _handle_audio_started(self, data: Dict[str, Any]) -> None:
        """Handle audio service started."""
        self._update_indicator(IndicatorType.AUDIO, IndicatorState.ACTIVE, "Audio system ready")
    
    def _handle_audio_stopped(self, data: Dict[str, Any]) -> None:
        """Handle audio service stopped."""
        self._update_indicator(IndicatorType.AUDIO, IndicatorState.INACTIVE, "Audio system stopped")
    
    def _handle_hotkeys_started(self, data: Dict[str, Any]) -> None:
        """Handle hotkey service started."""
        backend = data.get('backend', 'Unknown')
        self._update_indicator(IndicatorType.HOTKEYS, IndicatorState.ACTIVE, 
                             f"Hotkeys active ({backend})")
    
    def _handle_hotkeys_stopped(self, data: Dict[str, Any]) -> None:
        """Handle hotkey service stopped."""
        self._update_indicator(IndicatorType.HOTKEYS, IndicatorState.INACTIVE, "Hotkeys inactive")
    
    def _handle_error(self, data: Dict[str, Any]) -> None:
        """Handle error occurred."""
        source = data.get('source', 'Unknown')
        severity = data.get('severity', 'error')
        
        # Map source to indicator type
        source_mapping = {
            'audio': IndicatorType.AUDIO,
            'hotkeys': IndicatorType.HOTKEYS,
            'stt': IndicatorType.STT,
            'ai': IndicatorType.AI,
            'overlay': IndicatorType.OVERLAY
        }
        
        indicator_type = source_mapping.get(source, IndicatorType.SYSTEM)
        state = IndicatorState.ERROR if severity == 'error' else IndicatorState.WARNING
        
        error_msg = data.get('error', 'Unknown error')[:50]
        self._update_indicator(indicator_type, state, f"Error: {error_msg}")
    
    def _handle_show_request(self, data: Dict[str, Any]) -> None:
        """Handle show request."""
        self.show()
    
    def _handle_hide_request(self, data: Dict[str, Any]) -> None:
        """Handle hide request."""
        self.hide()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all indicators."""
        status = {
            'is_visible': self.is_visible,
            'indicators': {}
        }
        
        for indicator_type, indicator in self.indicators.items():
            status['indicators'][indicator_type.value] = {
                'state': indicator['state'].value,
                'description': indicator['description'],
                'last_update': indicator['last_update']
            }
        
        return status
    
    def set_config(self, config: IndicatorConfig) -> None:
        """Update indicator configuration."""
        self.config = config
        
        # Apply changes to existing window if visible
        if self.is_visible and self.window:
            if config.always_on_top:
                self.window.attributes('-topmost', True)
            else:
                self.window.attributes('-topmost', False)
            
            if config.auto_hide:
                self._start_auto_hide_timer()
            else:
                self._cancel_auto_hide_timer()