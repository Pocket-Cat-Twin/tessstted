"""Configuration management system for Voice-to-AI application."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioSettings:
    """Audio capture and processing settings."""
    sample_rate: int = 16000
    buffer_size: int = 1024
    channels: int = 1
    format: str = "int16"
    microphone_device: Optional[str] = None
    system_output_device: Optional[str] = None
    vad_enabled: bool = True
    vad_aggressiveness: int = 2
    noise_reduction: bool = True
    auto_gain_control: bool = True


@dataclass
class HotkeySettings:
    """Global hotkey configuration."""
    start_recording: str = "ctrl+shift+f1"
    stop_recording: str = "ctrl+shift+f2"
    toggle_overlay: str = "ctrl+shift+f3"
    toggle_settings: str = "ctrl+shift+f4"
    emergency_stop: str = "ctrl+shift+esc"


@dataclass
class STTSettings:
    """Speech-to-Text service configuration."""
    primary_provider: str = "yandex_speechkit"
    fallback_provider: str = "whisperx"
    language_code: str = "ru-RU"
    alternative_language: str = "en-US"
    confidence_threshold: float = 0.7
    enable_profanity_filter: bool = False
    enable_word_time_offsets: bool = True
    max_alternatives: int = 1
    streaming_enabled: bool = True
    provider_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AISettings:
    """AI service configuration."""
    provider: str = "openrouter"
    model: str = "anthropic/claude-3-sonnet"
    fallback_model: str = "openai/gpt-4"
    max_tokens: int = 300
    temperature: float = 0.7
    stream_response: bool = True
    system_prompt: str = "You are a helpful AI assistant. Provide concise and relevant responses based on the conversation context."
    response_timeout: int = 30
    max_retries: int = 3
    provider_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OverlayPosition:
    """Overlay window position and size."""
    x: int = 100
    y: int = 100
    width: int = 400
    height: int = 200


@dataclass
class OverlayFont:
    """Overlay font settings."""
    family: str = "Arial"
    size: int = 12
    bold: bool = False
    italic: bool = False


@dataclass
class OverlayColors:
    """Overlay color scheme."""
    text: str = "#FFFFFF"
    background: str = "#000000"
    border: str = "#333333"


@dataclass
class OverlaySettings:
    """Overlay display configuration."""
    enabled: bool = True
    always_on_top: bool = True
    transparency: float = 0.9
    position: OverlayPosition = field(default_factory=OverlayPosition)
    font: OverlayFont = field(default_factory=OverlayFont)
    colors: OverlayColors = field(default_factory=OverlayColors)
    display_mode: str = "both"  # "questions", "answers", "both"
    auto_hide_delay: int = 10
    fade_animation: bool = True


@dataclass
class UISettings:
    """User interface configuration."""
    theme: str = "dark"
    language: str = "ru"
    show_system_tray: bool = True
    minimize_to_tray: bool = True
    start_minimized: bool = False
    show_notifications: bool = True
    notification_duration: int = 3


@dataclass
class LoggingSettings:
    """Logging configuration."""
    level: str = "INFO"
    file_enabled: bool = True
    console_enabled: bool = True
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    log_audio_events: bool = False
    log_api_calls: bool = True


@dataclass
class PerformanceSettings:
    """Performance optimization settings."""
    max_cpu_usage: int = 20
    max_memory_usage: int = 300  # MB
    enable_gpu_acceleration: bool = True
    thread_pool_size: int = 4
    audio_buffer_count: int = 3
    api_connection_pool_size: int = 5


@dataclass
class SecuritySettings:
    """Security and privacy settings."""
    encrypt_api_keys: bool = True
    auto_clear_recordings: bool = True
    recording_retention_seconds: int = 300
    disable_audio_logging: bool = True
    validate_certificates: bool = True


@dataclass
class APICredentials:
    """API service credentials."""
    google_cloud: Dict[str, Any] = field(default_factory=lambda: {
        "credentials_path": None,
        "project_id": None,
        "endpoint": "speech.googleapis.com"
    })
    azure_speech: Dict[str, Any] = field(default_factory=lambda: {
        "subscription_key": None,
        "region": "eastus",
        "endpoint": None
    })
    openai: Dict[str, Any] = field(default_factory=lambda: {
        "api_key": None,
        "organization": None,
        "base_url": "https://api.openai.com/v1"
    })
    anthropic: Dict[str, Any] = field(default_factory=lambda: {
        "api_key": None,
        "base_url": "https://api.anthropic.com"
    })


@dataclass
class Settings:
    """Complete application settings."""
    audio: AudioSettings = field(default_factory=AudioSettings)
    hotkeys: HotkeySettings = field(default_factory=HotkeySettings)
    stt: STTSettings = field(default_factory=STTSettings)
    ai: AISettings = field(default_factory=AISettings)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    ui: UISettings = field(default_factory=UISettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    apis: APICredentials = field(default_factory=APICredentials)


class ConfigManager:
    """Configuration manager for loading, saving, and validating settings."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Optional custom configuration directory
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Default to config directory relative to project root
            project_root = Path(__file__).parent.parent
            self.config_dir = project_root / "config"
        
        self.config_dir.mkdir(exist_ok=True)
        
        self.default_config_path = self.config_dir / "default_config.json"
        self.user_config_path = self.config_dir / "user_config.json"
        
        self._settings: Optional[Settings] = None
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load settings from configuration files."""
        try:
            # Load default settings
            default_config = self._load_json_config(self.default_config_path)
            
            # Load user overrides if they exist
            user_config = {}
            if self.user_config_path.exists():
                user_config = self._load_json_config(self.user_config_path)
            
            # Merge configurations
            merged_config = self._merge_configs(default_config, user_config)
            
            # Convert to Settings dataclass
            self._settings = self._dict_to_settings(merged_config)
            
            logger.info(f"Settings loaded successfully from {self.config_dir}")
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            # Fall back to default settings
            self._settings = Settings()
    
    def _load_json_config(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file {path}: {e}")
            return {}
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge user configuration over default configuration."""
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _dict_to_settings(self, config: Dict[str, Any]) -> Settings:
        """Convert configuration dictionary to Settings dataclass."""
        try:
            # Create nested dataclass instances
            audio = AudioSettings(**config.get("audio", {}))
            hotkeys = HotkeySettings(**config.get("hotkeys", {}))
            stt = STTSettings(**config.get("stt", {}))
            ai = AISettings(**config.get("ai", {}))
            
            # Handle nested overlay settings
            overlay_config = config.get("overlay", {})
            overlay_position = OverlayPosition(**overlay_config.get("position", {}))
            overlay_font = OverlayFont(**overlay_config.get("font", {}))
            overlay_colors = OverlayColors(**overlay_config.get("colors", {}))
            
            # Remove nested objects before creating OverlaySettings
            overlay_config_clean = {k: v for k, v in overlay_config.items() 
                                  if k not in ["position", "font", "colors"]}
            overlay = OverlaySettings(
                position=overlay_position,
                font=overlay_font,
                colors=overlay_colors,
                **overlay_config_clean
            )
            
            ui = UISettings(**config.get("ui", {}))
            logging_settings = LoggingSettings(**config.get("logging", {}))
            performance = PerformanceSettings(**config.get("performance", {}))
            security = SecuritySettings(**config.get("security", {}))
            apis = APICredentials(**config.get("apis", {}))
            
            return Settings(
                audio=audio,
                hotkeys=hotkeys,
                stt=stt,
                ai=ai,
                overlay=overlay,
                ui=ui,
                logging=logging_settings,
                performance=performance,
                security=security,
                apis=apis
            )
            
        except Exception as e:
            logger.error(f"Failed to convert config to Settings: {e}")
            return Settings()
    
    def get_settings(self) -> Settings:
        """Get current settings."""
        if self._settings is None:
            self._load_settings()
        return self._settings
    
    def save_user_settings(self, settings: Settings) -> bool:
        """Save user settings to user configuration file.
        
        Args:
            settings: Settings object to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Convert settings to dictionary
            settings_dict = asdict(settings)
            
            # Save to user config file
            with open(self.user_config_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
            
            # Update current settings
            self._settings = settings
            
            logger.info(f"User settings saved to {self.user_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user settings: {e}")
            return False
    
    def update_setting(self, path: str, value: Any) -> bool:
        """Update a specific setting by path.
        
        Args:
            path: Dot-separated path to setting (e.g., "audio.sample_rate")
            value: New value for the setting
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            settings = self.get_settings()
            settings_dict = asdict(settings)
            
            # Navigate to the setting using the path
            keys = path.split('.')
            current = settings_dict
            for key in keys[:-1]:
                if key not in current:
                    logger.error(f"Setting path not found: {path}")
                    return False
                current = current[key]
            
            # Update the value
            final_key = keys[-1]
            if final_key not in current:
                logger.error(f"Setting path not found: {path}")
                return False
            
            current[final_key] = value
            
            # Convert back to Settings and save
            updated_settings = self._dict_to_settings(settings_dict)
            return self.save_user_settings(updated_settings)
            
        except Exception as e:
            logger.error(f"Failed to update setting {path}: {e}")
            return False
    
    def get_setting(self, path: str, default: Any = None) -> Any:
        """Get a specific setting by path.
        
        Args:
            path: Dot-separated path to setting (e.g., "audio.sample_rate")
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        try:
            settings = self.get_settings()
            settings_dict = asdict(settings)
            
            # Navigate to the setting using the path
            current = settings_dict
            for key in path.split('.'):
                if key not in current:
                    return default
                current = current[key]
            
            return current
            
        except Exception as e:
            logger.error(f"Failed to get setting {path}: {e}")
            return default
    
    def validate_settings(self) -> bool:
        """Validate current settings for consistency and correctness.
        
        Returns:
            True if settings are valid, False otherwise
        """
        try:
            settings = self.get_settings()
            
            # Validate audio settings
            if settings.audio.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
                logger.warning(f"Unusual sample rate: {settings.audio.sample_rate}")
            
            if settings.audio.buffer_size not in [256, 512, 1024, 2048, 4096]:
                logger.warning(f"Unusual buffer size: {settings.audio.buffer_size}")
            
            # Validate overlay settings
            if not (0.0 <= settings.overlay.transparency <= 1.0):
                logger.error("Overlay transparency must be between 0.0 and 1.0")
                return False
            
            # Validate AI settings
            if not (0.0 <= settings.ai.temperature <= 2.0):
                logger.error("AI temperature must be between 0.0 and 2.0")
                return False
            
            if settings.ai.max_tokens < 1 or settings.ai.max_tokens > 4000:
                logger.error("AI max_tokens must be between 1 and 4000")
                return False
            
            # Validate STT settings
            if not (0.0 <= settings.stt.confidence_threshold <= 1.0):
                logger.error("STT confidence threshold must be between 0.0 and 1.0")
                return False
            
            logger.info("Settings validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Settings validation failed: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults.
        
        Returns:
            True if reset successfully, False otherwise
        """
        try:
            # Remove user config file
            if self.user_config_path.exists():
                self.user_config_path.unlink()
            
            # Reload settings (will use defaults only)
            self._load_settings()
            
            logger.info("Settings reset to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            return False
    
    def export_settings(self, export_path: Path) -> bool:
        """Export current settings to a file.
        
        Args:
            export_path: Path to export file
            
        Returns:
            True if exported successfully, False otherwise
        """
        try:
            settings = self.get_settings()
            settings_dict = asdict(settings)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Settings exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            return False
    
    def import_settings(self, import_path: Path) -> bool:
        """Import settings from a file.
        
        Args:
            import_path: Path to import file
            
        Returns:
            True if imported successfully, False otherwise
        """
        try:
            imported_config = self._load_json_config(import_path)
            
            # Validate imported settings
            imported_settings = self._dict_to_settings(imported_config)
            
            # Save as user settings
            success = self.save_user_settings(imported_settings)
            
            if success:
                logger.info(f"Settings imported from {import_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            return False


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config_from_file(file_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {file_path}: {e}")
        return {}