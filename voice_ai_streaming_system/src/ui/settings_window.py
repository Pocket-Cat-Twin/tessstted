"""Settings configuration window."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, Optional, Callable
import json
import threading

from ..core.event_bus import EventBus, EventType
from ..config.settings import ConfigManager, AudioConfig, HotkeyConfig, STTConfig, AIConfig, OverlayConfig


class SettingsWindow:
    """
    Settings configuration window.
    
    Provides GUI interface for configuring all system settings including
    audio devices, hotkeys, STT/AI providers, and overlay appearance.
    """
    
    def __init__(self, event_bus: EventBus, config_manager: ConfigManager):
        """
        Initialize settings window.
        
        Args:
            event_bus: Event bus for communication
            config_manager: Configuration manager
        """
        self.event_bus = event_bus
        self.config_manager = config_manager
        
        # Window state
        self.window: Optional[tk.Toplevel] = None
        self.is_open = False
        self.config_changed = False
        
        # Widget references
        self.widgets = {}
        self.current_config = self.config_manager.get_config().copy()
        
        # Validation callbacks
        self.validators = {}
        
        # Subscribe to events
        self._subscribe_to_events()
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        self.event_bus.subscribe(EventType.CONFIG_UPDATED, self._handle_config_updated)
        self.event_bus.subscribe(EventType.SETTINGS_OPEN_REQUESTED, self._handle_open_request)
        self.event_bus.subscribe(EventType.AUDIO_DEVICES_UPDATED, self._handle_audio_devices_updated)
    
    def show(self) -> None:
        """Show settings window."""
        if self.is_open and self.window:
            # Bring to front if already open
            self.window.lift()
            self.window.focus_set()
            return
        
        self._create_window()
        self.is_open = True
        
        self.event_bus.publish(EventType.SETTINGS_WINDOW_OPENED, {})
    
    def hide(self) -> None:
        """Hide settings window."""
        if self.window:
            self.window.destroy()
            self.window = None
            self.is_open = False
            
            self.event_bus.publish(EventType.SETTINGS_WINDOW_CLOSED, {
                'config_changed': self.config_changed
            })
    
    def _create_window(self) -> None:
        """Create the settings window."""
        # Create window
        self.window = tk.Toplevel()
        self.window.title("Voice-to-AI Settings")
        self.window.geometry("600x500")
        self.window.resizable(True, True)
        
        # Configure window properties
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Create main layout
        self._create_layout()
        
        # Load current settings
        self._load_settings()
        
        # Center window
        self._center_window()
    
    def _create_layout(self) -> None:
        """Create window layout and widgets."""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self._create_audio_tab(notebook)
        self._create_hotkey_tab(notebook)
        self._create_stt_tab(notebook)
        self._create_ai_tab(notebook)
        self._create_overlay_tab(notebook)
        
        # Create button frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Create buttons
        self._create_buttons(button_frame)
    
    def _create_audio_tab(self, notebook: ttk.Notebook) -> None:
        """Create audio configuration tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Audio")
        
        # Microphone device
        ttk.Label(frame, text="Microphone Device:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        mic_combo = ttk.Combobox(frame, width=40)
        mic_combo.grid(row=0, column=1, padx=5, pady=5)
        self.widgets['microphone_device'] = mic_combo
        
        # System output device
        ttk.Label(frame, text="System Output Device:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        output_combo = ttk.Combobox(frame, width=40)
        output_combo.grid(row=1, column=1, padx=5, pady=5)
        self.widgets['output_device'] = output_combo
        
        # Sample rate
        ttk.Label(frame, text="Sample Rate:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        sample_combo = ttk.Combobox(frame, values=["16000", "44100", "48000"], width=40)
        sample_combo.grid(row=2, column=1, padx=5, pady=5)
        self.widgets['sample_rate'] = sample_combo
        
        # Buffer size
        ttk.Label(frame, text="Buffer Size:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        buffer_combo = ttk.Combobox(frame, values=["512", "1024", "2048"], width=40)
        buffer_combo.grid(row=3, column=1, padx=5, pady=5)
        self.widgets['buffer_size'] = buffer_combo
        
        # VAD threshold
        ttk.Label(frame, text="Voice Detection Threshold:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        vad_scale = ttk.Scale(frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL)
        vad_scale.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        self.widgets['vad_threshold'] = vad_scale
        
        # Test buttons
        ttk.Button(frame, text="Test Microphone", command=self._test_microphone).grid(row=5, column=0, padx=5, pady=10)
        ttk.Button(frame, text="Test Output", command=self._test_output).grid(row=5, column=1, padx=5, pady=10)
        
        # Refresh devices button
        ttk.Button(frame, text="Refresh Devices", command=self._refresh_audio_devices).grid(row=6, column=0, columnspan=2, pady=10)
    
    def _create_hotkey_tab(self, notebook: ttk.Notebook) -> None:
        """Create hotkey configuration tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Hotkeys")
        
        # Start recording hotkey
        ttk.Label(frame, text="Start Recording:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        start_entry = ttk.Entry(frame, width=40)
        start_entry.grid(row=0, column=1, padx=5, pady=5)
        self.widgets['start_recording_hotkey'] = start_entry
        
        # Stop recording hotkey
        ttk.Label(frame, text="Stop Recording:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        stop_entry = ttk.Entry(frame, width=40)
        stop_entry.grid(row=1, column=1, padx=5, pady=5)
        self.widgets['stop_recording_hotkey'] = stop_entry
        
        # Show/hide overlay hotkey
        ttk.Label(frame, text="Toggle Overlay:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        overlay_entry = ttk.Entry(frame, width=40)
        overlay_entry.grid(row=2, column=1, padx=5, pady=5)
        self.widgets['toggle_overlay_hotkey'] = overlay_entry
        
        # Settings hotkey
        ttk.Label(frame, text="Open Settings:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        settings_entry = ttk.Entry(frame, width=40)
        settings_entry.grid(row=3, column=1, padx=5, pady=5)
        self.widgets['settings_hotkey'] = settings_entry
        
        # Debounce time
        ttk.Label(frame, text="Debounce Time (ms):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        debounce_spin = ttk.Spinbox(frame, from_=100, to=2000, width=40)
        debounce_spin.grid(row=4, column=1, padx=5, pady=5)
        self.widgets['debounce_time'] = debounce_spin
        
        # Instructions
        instructions = ttk.Label(frame, text="Format: ctrl+shift+f1, alt+space, etc.", font=("Arial", 8))
        instructions.grid(row=5, column=0, columnspan=2, pady=10)
    
    def _create_stt_tab(self, notebook: ttk.Notebook) -> None:
        """Create STT configuration tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Speech-to-Text")
        
        # Provider selection
        ttk.Label(frame, text="STT Provider:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        provider_combo = ttk.Combobox(frame, values=["google", "azure", "whisper", "mock"], width=40)
        provider_combo.grid(row=0, column=1, padx=5, pady=5)
        self.widgets['stt_provider'] = provider_combo
        
        # Language
        ttk.Label(frame, text="Language:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        lang_combo = ttk.Combobox(frame, values=["ru-RU", "en-US", "en-GB"], width=40)
        lang_combo.grid(row=1, column=1, padx=5, pady=5)
        self.widgets['stt_language'] = lang_combo
        
        # API key
        ttk.Label(frame, text="API Key:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        api_key_entry = ttk.Entry(frame, width=40, show="*")
        api_key_entry.grid(row=2, column=1, padx=5, pady=5)
        self.widgets['stt_api_key'] = api_key_entry
        
        # Confidence threshold
        ttk.Label(frame, text="Confidence Threshold:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        conf_scale = ttk.Scale(frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL)
        conf_scale.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        self.widgets['stt_confidence_threshold'] = conf_scale
        
        # Enable streaming
        streaming_var = tk.BooleanVar()
        streaming_check = ttk.Checkbutton(frame, text="Enable Streaming STT", variable=streaming_var)
        streaming_check.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        self.widgets['stt_streaming'] = streaming_var
        
        # Test button
        ttk.Button(frame, text="Test STT", command=self._test_stt).grid(row=5, column=0, columnspan=2, pady=10)
    
    def _create_ai_tab(self, notebook: ttk.Notebook) -> None:
        """Create AI configuration tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="AI Provider")
        
        # Provider selection
        ttk.Label(frame, text="AI Provider:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ai_combo = ttk.Combobox(frame, values=["openai", "anthropic", "mock"], width=40)
        ai_combo.grid(row=0, column=1, padx=5, pady=5)
        self.widgets['ai_provider'] = ai_combo
        
        # Model
        ttk.Label(frame, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        model_combo = ttk.Combobox(frame, values=["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"], width=40)
        model_combo.grid(row=1, column=1, padx=5, pady=5)
        self.widgets['ai_model'] = model_combo
        
        # API key
        ttk.Label(frame, text="API Key:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ai_key_entry = ttk.Entry(frame, width=40, show="*")
        ai_key_entry.grid(row=2, column=1, padx=5, pady=5)
        self.widgets['ai_api_key'] = ai_key_entry
        
        # Max tokens
        ttk.Label(frame, text="Max Tokens:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        tokens_spin = ttk.Spinbox(frame, from_=100, to=4000, width=40)
        tokens_spin.grid(row=3, column=1, padx=5, pady=5)
        self.widgets['ai_max_tokens'] = tokens_spin
        
        # Temperature
        ttk.Label(frame, text="Temperature:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        temp_scale = ttk.Scale(frame, from_=0.0, to=2.0, orient=tk.HORIZONTAL)
        temp_scale.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        self.widgets['ai_temperature'] = temp_scale
        
        # System prompt
        ttk.Label(frame, text="System Prompt:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        prompt_text = tk.Text(frame, height=4, width=50)
        prompt_text.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
        self.widgets['ai_system_prompt'] = prompt_text
        
        # Enable streaming
        ai_streaming_var = tk.BooleanVar()
        ai_streaming_check = ttk.Checkbutton(frame, text="Enable Streaming Responses", variable=ai_streaming_var)
        ai_streaming_check.grid(row=7, column=0, columnspan=2, padx=5, pady=5)
        self.widgets['ai_streaming'] = ai_streaming_var
        
        # Test button
        ttk.Button(frame, text="Test AI", command=self._test_ai).grid(row=8, column=0, columnspan=2, pady=10)
    
    def _create_overlay_tab(self, notebook: ttk.Notebook) -> None:
        """Create overlay configuration tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Overlay")
        
        # Position
        ttk.Label(frame, text="Position X:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        pos_x_spin = ttk.Spinbox(frame, from_=0, to=2000, width=20)
        pos_x_spin.grid(row=0, column=1, padx=5, pady=5)
        self.widgets['overlay_x'] = pos_x_spin
        
        ttk.Label(frame, text="Position Y:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        pos_y_spin = ttk.Spinbox(frame, from_=0, to=2000, width=20)
        pos_y_spin.grid(row=0, column=3, padx=5, pady=5)
        self.widgets['overlay_y'] = pos_y_spin
        
        # Size
        ttk.Label(frame, text="Max Width:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        width_spin = ttk.Spinbox(frame, from_=200, to=800, width=20)
        width_spin.grid(row=1, column=1, padx=5, pady=5)
        self.widgets['overlay_width'] = width_spin
        
        ttk.Label(frame, text="Max Height:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        height_spin = ttk.Spinbox(frame, from_=100, to=600, width=20)
        height_spin.grid(row=1, column=3, padx=5, pady=5)
        self.widgets['overlay_height'] = height_spin
        
        # Font
        ttk.Label(frame, text="Font Family:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        font_combo = ttk.Combobox(frame, values=["Arial", "Times New Roman", "Calibri"], width=20)
        font_combo.grid(row=2, column=1, padx=5, pady=5)
        self.widgets['overlay_font'] = font_combo
        
        ttk.Label(frame, text="Font Size:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        font_size_spin = ttk.Spinbox(frame, from_=8, to=24, width=20)
        font_size_spin.grid(row=2, column=3, padx=5, pady=5)
        self.widgets['overlay_font_size'] = font_size_spin
        
        # Colors
        ttk.Label(frame, text="Text Color:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        text_color_entry = ttk.Entry(frame, width=20)
        text_color_entry.grid(row=3, column=1, padx=5, pady=5)
        self.widgets['overlay_text_color'] = text_color_entry
        
        ttk.Label(frame, text="Background Color:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)
        bg_color_entry = ttk.Entry(frame, width=20)
        bg_color_entry.grid(row=3, column=3, padx=5, pady=5)
        self.widgets['overlay_bg_color'] = bg_color_entry
        
        # Transparency
        ttk.Label(frame, text="Transparency:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        alpha_scale = ttk.Scale(frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL)
        alpha_scale.grid(row=4, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        self.widgets['overlay_alpha'] = alpha_scale
        
        # Auto-hide
        ttk.Label(frame, text="Auto-hide (seconds):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        autohide_spin = ttk.Spinbox(frame, from_=0, to=60, width=20)
        autohide_spin.grid(row=5, column=1, padx=5, pady=5)
        self.widgets['overlay_autohide'] = autohide_spin
        
        # Test overlay button
        ttk.Button(frame, text="Test Overlay", command=self._test_overlay).grid(row=6, column=0, columnspan=4, pady=10)
    
    def _create_buttons(self, frame: ttk.Frame) -> None:
        """Create action buttons."""
        # Save button
        save_btn = ttk.Button(frame, text="Save", command=self._save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = ttk.Button(frame, text="Cancel", command=self._cancel_settings)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Apply button
        apply_btn = ttk.Button(frame, text="Apply", command=self._apply_settings)
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
        # Reset to defaults button
        reset_btn = ttk.Button(frame, text="Reset to Defaults", command=self._reset_defaults)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Export/Import buttons
        export_btn = ttk.Button(frame, text="Export Config", command=self._export_config)
        export_btn.pack(side=tk.LEFT, padx=5)
        
        import_btn = ttk.Button(frame, text="Import Config", command=self._import_config)
        import_btn.pack(side=tk.LEFT, padx=5)
    
    def _load_settings(self) -> None:
        """Load current settings into widgets."""
        config = self.config_manager.get_config()
        
        # Audio settings
        if 'microphone_device' in self.widgets:
            self.widgets['microphone_device'].set(config.audio.microphone_device_name or "")
        if 'output_device' in self.widgets:
            self.widgets['output_device'].set(config.audio.output_device_name or "")
        if 'sample_rate' in self.widgets:
            self.widgets['sample_rate'].set(str(config.audio.sample_rate))
        if 'buffer_size' in self.widgets:
            self.widgets['buffer_size'].set(str(config.audio.buffer_size))
        if 'vad_threshold' in self.widgets:
            self.widgets['vad_threshold'].set(config.audio.vad_threshold)
        
        # Hotkey settings
        if 'start_recording_hotkey' in self.widgets:
            self.widgets['start_recording_hotkey'].set(config.hotkeys.start_recording)
        if 'stop_recording_hotkey' in self.widgets:
            self.widgets['stop_recording_hotkey'].set(config.hotkeys.stop_recording)
        if 'toggle_overlay_hotkey' in self.widgets:
            self.widgets['toggle_overlay_hotkey'].set(config.hotkeys.toggle_overlay)
        if 'settings_hotkey' in self.widgets:
            self.widgets['settings_hotkey'].set(config.hotkeys.show_settings)
        if 'debounce_time' in self.widgets:
            self.widgets['debounce_time'].set(str(config.hotkeys.debounce_time))
        
        # STT settings
        if 'stt_provider' in self.widgets:
            self.widgets['stt_provider'].set(config.stt.provider)
        if 'stt_language' in self.widgets:
            self.widgets['stt_language'].set(config.stt.language)
        if 'stt_api_key' in self.widgets:
            self.widgets['stt_api_key'].set(config.stt.api_key or "")
        if 'stt_confidence_threshold' in self.widgets:
            self.widgets['stt_confidence_threshold'].set(config.stt.confidence_threshold)
        if 'stt_streaming' in self.widgets:
            self.widgets['stt_streaming'].set(config.stt.enable_streaming)
        
        # AI settings
        if 'ai_provider' in self.widgets:
            self.widgets['ai_provider'].set(config.ai.provider)
        if 'ai_model' in self.widgets:
            self.widgets['ai_model'].set(config.ai.model)
        if 'ai_api_key' in self.widgets:
            self.widgets['ai_api_key'].set(config.ai.api_key or "")
        if 'ai_max_tokens' in self.widgets:
            self.widgets['ai_max_tokens'].set(str(config.ai.max_tokens))
        if 'ai_temperature' in self.widgets:
            self.widgets['ai_temperature'].set(config.ai.temperature)
        if 'ai_system_prompt' in self.widgets:
            self.widgets['ai_system_prompt'].insert('1.0', config.ai.system_prompt)
        if 'ai_streaming' in self.widgets:
            self.widgets['ai_streaming'].set(config.ai.enable_streaming)
        
        # Overlay settings
        if 'overlay_x' in self.widgets:
            self.widgets['overlay_x'].set(str(config.overlay.position[0]))
        if 'overlay_y' in self.widgets:
            self.widgets['overlay_y'].set(str(config.overlay.position[1]))
        if 'overlay_width' in self.widgets:
            self.widgets['overlay_width'].set(str(config.overlay.max_width))
        if 'overlay_height' in self.widgets:
            self.widgets['overlay_height'].set(str(config.overlay.max_height))
        if 'overlay_font' in self.widgets:
            self.widgets['overlay_font'].set(config.overlay.font_family)
        if 'overlay_font_size' in self.widgets:
            self.widgets['overlay_font_size'].set(str(config.overlay.font_size))
        if 'overlay_text_color' in self.widgets:
            self.widgets['overlay_text_color'].set(config.overlay.text_color)
        if 'overlay_bg_color' in self.widgets:
            self.widgets['overlay_bg_color'].set(config.overlay.background_color)
        if 'overlay_alpha' in self.widgets:
            self.widgets['overlay_alpha'].set(config.overlay.background_alpha)
        if 'overlay_autohide' in self.widgets:
            self.widgets['overlay_autohide'].set(str(config.overlay.auto_hide_timeout))
    
    def _save_settings(self) -> None:
        """Save settings and close window."""
        if self._apply_settings():
            self.hide()
    
    def _cancel_settings(self) -> None:
        """Cancel settings changes and close window."""
        self.hide()
    
    def _apply_settings(self) -> bool:
        """Apply current settings."""
        try:
            # Build new configuration
            new_config = self._build_config_from_widgets()
            
            # Validate configuration
            if not self._validate_config(new_config):
                return False
            
            # Apply configuration
            self.config_manager.update_config(new_config)
            self.config_changed = True
            
            messagebox.showinfo("Settings", "Settings applied successfully!")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings: {str(e)}")
            return False
    
    def _build_config_from_widgets(self) -> Dict[str, Any]:
        """Build configuration dictionary from widget values."""
        config = self.current_config.copy()
        
        # Audio configuration
        if 'microphone_device' in self.widgets:
            config['audio']['microphone_device_name'] = self.widgets['microphone_device'].get()
        if 'output_device' in self.widgets:
            config['audio']['output_device_name'] = self.widgets['output_device'].get()
        if 'sample_rate' in self.widgets:
            config['audio']['sample_rate'] = int(self.widgets['sample_rate'].get())
        if 'buffer_size' in self.widgets:
            config['audio']['buffer_size'] = int(self.widgets['buffer_size'].get())
        if 'vad_threshold' in self.widgets:
            config['audio']['vad_threshold'] = float(self.widgets['vad_threshold'].get())
        
        # Hotkey configuration
        if 'start_recording_hotkey' in self.widgets:
            config['hotkeys']['start_recording'] = self.widgets['start_recording_hotkey'].get()
        if 'stop_recording_hotkey' in self.widgets:
            config['hotkeys']['stop_recording'] = self.widgets['stop_recording_hotkey'].get()
        if 'toggle_overlay_hotkey' in self.widgets:
            config['hotkeys']['toggle_overlay'] = self.widgets['toggle_overlay_hotkey'].get()
        if 'settings_hotkey' in self.widgets:
            config['hotkeys']['show_settings'] = self.widgets['settings_hotkey'].get()
        if 'debounce_time' in self.widgets:
            config['hotkeys']['debounce_time'] = int(self.widgets['debounce_time'].get())
        
        # STT configuration
        if 'stt_provider' in self.widgets:
            config['stt']['provider'] = self.widgets['stt_provider'].get()
        if 'stt_language' in self.widgets:
            config['stt']['language'] = self.widgets['stt_language'].get()
        if 'stt_api_key' in self.widgets:
            config['stt']['api_key'] = self.widgets['stt_api_key'].get()
        if 'stt_confidence_threshold' in self.widgets:
            config['stt']['confidence_threshold'] = float(self.widgets['stt_confidence_threshold'].get())
        if 'stt_streaming' in self.widgets:
            config['stt']['enable_streaming'] = self.widgets['stt_streaming'].get()
        
        # AI configuration
        if 'ai_provider' in self.widgets:
            config['ai']['provider'] = self.widgets['ai_provider'].get()
        if 'ai_model' in self.widgets:
            config['ai']['model'] = self.widgets['ai_model'].get()
        if 'ai_api_key' in self.widgets:
            config['ai']['api_key'] = self.widgets['ai_api_key'].get()
        if 'ai_max_tokens' in self.widgets:
            config['ai']['max_tokens'] = int(self.widgets['ai_max_tokens'].get())
        if 'ai_temperature' in self.widgets:
            config['ai']['temperature'] = float(self.widgets['ai_temperature'].get())
        if 'ai_system_prompt' in self.widgets:
            config['ai']['system_prompt'] = self.widgets['ai_system_prompt'].get('1.0', tk.END).strip()
        if 'ai_streaming' in self.widgets:
            config['ai']['enable_streaming'] = self.widgets['ai_streaming'].get()
        
        # Overlay configuration
        if 'overlay_x' in self.widgets and 'overlay_y' in self.widgets:
            config['overlay']['position'] = [
                int(self.widgets['overlay_x'].get()),
                int(self.widgets['overlay_y'].get())
            ]
        if 'overlay_width' in self.widgets:
            config['overlay']['max_width'] = int(self.widgets['overlay_width'].get())
        if 'overlay_height' in self.widgets:
            config['overlay']['max_height'] = int(self.widgets['overlay_height'].get())
        if 'overlay_font' in self.widgets:
            config['overlay']['font_family'] = self.widgets['overlay_font'].get()
        if 'overlay_font_size' in self.widgets:
            config['overlay']['font_size'] = int(self.widgets['overlay_font_size'].get())
        if 'overlay_text_color' in self.widgets:
            config['overlay']['text_color'] = self.widgets['overlay_text_color'].get()
        if 'overlay_bg_color' in self.widgets:
            config['overlay']['background_color'] = self.widgets['overlay_bg_color'].get()
        if 'overlay_alpha' in self.widgets:
            config['overlay']['background_alpha'] = float(self.widgets['overlay_alpha'].get())
        if 'overlay_autohide' in self.widgets:
            config['overlay']['auto_hide_timeout'] = float(self.widgets['overlay_autohide'].get())
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration values."""
        # Add validation logic here
        return True
    
    def _reset_defaults(self) -> None:
        """Reset settings to defaults."""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            default_config = self.config_manager.get_default_config()
            self.current_config = default_config
            self._load_settings()
    
    def _export_config(self) -> None:
        """Export configuration to file."""
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                config = self.config_manager.get_config()
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                messagebox.showinfo("Export", "Configuration exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")
    
    def _import_config(self) -> None:
        """Import configuration from file."""
        filename = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    config = json.load(f)
                
                # Validate and apply configuration
                self.config_manager.update_config(config)
                self.current_config = config
                self._load_settings()
                
                messagebox.showinfo("Import", "Configuration imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import configuration: {str(e)}")
    
    def _test_microphone(self) -> None:
        """Test microphone recording."""
        self.event_bus.publish(EventType.AUDIO_TEST_REQUESTED, {'device_type': 'microphone'})
    
    def _test_output(self) -> None:
        """Test output device recording."""
        self.event_bus.publish(EventType.AUDIO_TEST_REQUESTED, {'device_type': 'output'})
    
    def _test_stt(self) -> None:
        """Test STT service."""
        self.event_bus.publish(EventType.STT_TEST_REQUESTED, {})
    
    def _test_ai(self) -> None:
        """Test AI service."""
        self.event_bus.publish(EventType.AI_TEST_REQUESTED, {})
    
    def _test_overlay(self) -> None:
        """Test overlay display."""
        self.event_bus.publish(EventType.OVERLAY_TEST_REQUESTED, {})
    
    def _refresh_audio_devices(self) -> None:
        """Refresh audio device list."""
        self.event_bus.publish(EventType.AUDIO_DEVICES_REFRESH_REQUESTED, {})
    
    def _center_window(self) -> None:
        """Center window on screen."""
        if self.window:
            self.window.update_idletasks()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            x = (self.window.winfo_screenwidth() // 2) - (width // 2)
            y = (self.window.winfo_screenheight() // 2) - (height // 2)
            self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def _on_window_close(self) -> None:
        """Handle window close event."""
        if self.config_changed:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?"
            )
            if result is True:  # Yes - save and close
                self._save_settings()
            elif result is False:  # No - discard and close
                self.hide()
            # Cancel - don't close
        else:
            self.hide()
    
    def _handle_config_updated(self, data: Dict[str, Any]) -> None:
        """Handle configuration update event."""
        if self.is_open:
            # Reload settings if window is open
            self._load_settings()
    
    def _handle_open_request(self, data: Dict[str, Any]) -> None:
        """Handle settings window open request."""
        self.show()
    
    def _handle_audio_devices_updated(self, data: Dict[str, Any]) -> None:
        """Handle audio devices update."""
        devices = data.get('devices', {})
        
        # Update microphone device list
        if 'microphone_device' in self.widgets and 'microphone' in devices:
            combo = self.widgets['microphone_device']
            combo['values'] = [d['name'] for d in devices['microphone']]
        
        # Update output device list
        if 'output_device' in self.widgets and 'output' in devices:
            combo = self.widgets['output_device']
            combo['values'] = [d['name'] for d in devices['output']]