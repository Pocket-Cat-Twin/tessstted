"""Voice Activity Detection for Voice-to-AI system."""

import numpy as np
import threading
import time
from typing import Optional, Callable, Dict, Any
import logging
from dataclasses import dataclass
from enum import Enum

try:
    import webrtcvad
    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False
    logging.warning("WebRTC VAD not available, using energy-based VAD")

try:
    from .capture_service import AudioFrame, AudioDeviceType
    from ..core.event_bus import EventBus, EventType, get_event_bus
    from ..config.settings import AudioSettings
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from audio.capture_service import AudioFrame, AudioDeviceType
    from core.event_bus import EventBus, EventType, get_event_bus
    from config.settings import AudioSettings

logger = logging.getLogger(__name__)


class VADMode(Enum):
    """Voice Activity Detection modes."""
    ENERGY_BASED = "energy_based"
    WEBRTC = "webrtc"
    HYBRID = "hybrid"


@dataclass
class VADResult:
    """Voice activity detection result."""
    has_voice: bool
    confidence: float
    energy_level: float
    timestamp: float
    device_type: AudioDeviceType


class EnergyBasedVAD:
    """Energy-based voice activity detector."""
    
    def __init__(
        self,
        energy_threshold: float = 0.01,
        min_voice_duration: float = 0.1,
        min_silence_duration: float = 0.3
    ):
        self.energy_threshold = energy_threshold
        self.min_voice_duration = min_voice_duration
        self.min_silence_duration = min_silence_duration
        
        # State tracking
        self._voice_start_time: Optional[float] = None
        self._silence_start_time: Optional[float] = None
        self._last_state = False
        self._energy_history = []
        self._history_size = 10
        
        logger.debug(f"EnergyBasedVAD initialized - threshold: {energy_threshold}")
    
    def process_frame(self, audio_data: np.ndarray, timestamp: float) -> VADResult:
        """Process audio frame and detect voice activity.
        
        Args:
            audio_data: Audio data as numpy array
            timestamp: Frame timestamp
            
        Returns:
            VAD result
        """
        try:
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            
            # Normalize energy (rough approximation)
            normalized_energy = energy / 32768.0  # int16 max value
            
            # Update energy history for adaptive threshold
            self._energy_history.append(normalized_energy)
            if len(self._energy_history) > self._history_size:
                self._energy_history.pop(0)
            
            # Calculate adaptive threshold
            avg_energy = np.mean(self._energy_history)
            adaptive_threshold = max(self.energy_threshold, avg_energy * 1.5)
            
            # Basic voice detection
            current_has_voice = normalized_energy > adaptive_threshold
            
            # Apply temporal filtering
            filtered_has_voice = self._apply_temporal_filter(
                current_has_voice, timestamp
            )
            
            # Calculate confidence based on energy ratio
            confidence = min(1.0, normalized_energy / adaptive_threshold) if adaptive_threshold > 0 else 0.0
            
            return VADResult(
                has_voice=filtered_has_voice,
                confidence=confidence,
                energy_level=normalized_energy,
                timestamp=timestamp,
                device_type=AudioDeviceType.MICROPHONE  # Default
            )
            
        except Exception as e:
            logger.error(f"Error in energy-based VAD: {e}")
            return VADResult(
                has_voice=False,
                confidence=0.0,
                energy_level=0.0,
                timestamp=timestamp,
                device_type=AudioDeviceType.MICROPHONE
            )
    
    def _apply_temporal_filter(self, has_voice: bool, timestamp: float) -> bool:
        """Apply temporal filtering to reduce false positives/negatives."""
        current_time = timestamp
        
        if has_voice and not self._last_state:
            # Potential voice start
            if self._voice_start_time is None:
                self._voice_start_time = current_time
            elif current_time - self._voice_start_time >= self.min_voice_duration:
                # Voice confirmed
                self._last_state = True
                self._silence_start_time = None
                return True
        elif not has_voice and self._last_state:
            # Potential voice end
            if self._silence_start_time is None:
                self._silence_start_time = current_time
            elif current_time - self._silence_start_time >= self.min_silence_duration:
                # Silence confirmed
                self._last_state = False
                self._voice_start_time = None
                return False
        elif has_voice and self._last_state:
            # Continue voice
            self._silence_start_time = None
            return True
        elif not has_voice and not self._last_state:
            # Continue silence
            self._voice_start_time = None
            return False
        
        return self._last_state


class WebRTCVAD:
    """WebRTC-based voice activity detector."""
    
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000):
        if not WEBRTC_VAD_AVAILABLE:
            raise RuntimeError("WebRTC VAD not available")
        
        self.aggressiveness = aggressiveness
        self.sample_rate = sample_rate
        self._vad = webrtcvad.Vad(aggressiveness)
        
        # WebRTC VAD requires specific sample rates
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Unsupported sample rate for WebRTC VAD: {sample_rate}")
        
        # Frame size requirements (10, 20, or 30 ms)
        self._frame_duration_ms = 20  # 20ms frames
        self._frame_size = int(sample_rate * self._frame_duration_ms / 1000)
        
        logger.debug(f"WebRTCVAD initialized - aggressiveness: {aggressiveness}, frame_size: {self._frame_size}")
    
    def process_frame(self, audio_data: np.ndarray, timestamp: float) -> VADResult:
        """Process audio frame with WebRTC VAD.
        
        Args:
            audio_data: Audio data as numpy array (int16)
            timestamp: Frame timestamp
            
        Returns:
            VAD result
        """
        try:
            # Ensure audio data is int16
            if audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            
            # WebRTC VAD requires specific frame sizes
            if len(audio_data) != self._frame_size:
                # Pad or truncate to required frame size
                if len(audio_data) < self._frame_size:
                    # Pad with zeros
                    padded_data = np.zeros(self._frame_size, dtype=np.int16)
                    padded_data[:len(audio_data)] = audio_data
                    audio_data = padded_data
                else:
                    # Truncate to frame size
                    audio_data = audio_data[:self._frame_size]
            
            # Convert to bytes
            audio_bytes = audio_data.tobytes()
            
            # Run VAD
            is_speech = self._vad.is_speech(audio_bytes, self.sample_rate)
            
            # Calculate energy for confidence
            energy = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2)) / 32768.0
            confidence = 0.8 if is_speech else 0.2  # WebRTC gives binary result
            
            return VADResult(
                has_voice=is_speech,
                confidence=confidence,
                energy_level=energy,
                timestamp=timestamp,
                device_type=AudioDeviceType.MICROPHONE
            )
            
        except Exception as e:
            logger.error(f"Error in WebRTC VAD: {e}")
            return VADResult(
                has_voice=False,
                confidence=0.0,
                energy_level=0.0,
                timestamp=timestamp,
                device_type=AudioDeviceType.MICROPHONE
            )


class VoiceActivityDetector:
    """Main voice activity detector with multiple detection modes."""
    
    def __init__(
        self,
        settings: AudioSettings,
        event_bus: Optional[EventBus] = None
    ):
        self.settings = settings
        self._event_bus = event_bus or get_event_bus()
        
        # Detection mode
        self._vad_mode = VADMode.WEBRTC if WEBRTC_VAD_AVAILABLE else VADMode.ENERGY_BASED
        
        # VAD instances
        self._energy_vad: Optional[EnergyBasedVAD] = None
        self._webrtc_vad: Optional[WebRTCVAD] = None
        
        # State tracking
        self._current_voice_state = False
        self._voice_start_time: Optional[float] = None
        self._voice_end_time: Optional[float] = None
        
        # Callbacks
        self._voice_started_callback: Optional[Callable[[float], None]] = None
        self._voice_ended_callback: Optional[Callable[[float], None]] = None
        
        # Performance tracking
        self._frames_processed = 0
        self._voice_segments = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize VAD instances
        self._initialize_vad()
        
        logger.info(f"VoiceActivityDetector initialized with mode: {self._vad_mode.value}")
    
    def _initialize_vad(self) -> None:
        """Initialize VAD instances based on settings."""
        try:
            # Always initialize energy-based VAD as fallback
            self._energy_vad = EnergyBasedVAD(
                energy_threshold=0.01,
                min_voice_duration=0.1,
                min_silence_duration=0.3
            )
            
            # Initialize WebRTC VAD if available and enabled
            if WEBRTC_VAD_AVAILABLE and self.settings.vad_enabled:
                try:
                    self._webrtc_vad = WebRTCVAD(
                        aggressiveness=self.settings.vad_aggressiveness,
                        sample_rate=self.settings.sample_rate
                    )
                    self._vad_mode = VADMode.WEBRTC
                    logger.info("WebRTC VAD initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize WebRTC VAD: {e}, falling back to energy-based")
                    self._vad_mode = VADMode.ENERGY_BASED
            else:
                self._vad_mode = VADMode.ENERGY_BASED
            
        except Exception as e:
            logger.error(f"Failed to initialize VAD: {e}")
            self._vad_mode = VADMode.ENERGY_BASED
    
    def set_voice_callbacks(
        self,
        voice_started: Optional[Callable[[float], None]] = None,
        voice_ended: Optional[Callable[[float], None]] = None
    ) -> None:
        """Set callbacks for voice activity events.
        
        Args:
            voice_started: Callback for voice activity start (timestamp)
            voice_ended: Callback for voice activity end (duration)
        """
        self._voice_started_callback = voice_started
        self._voice_ended_callback = voice_ended
        logger.debug("Voice activity callbacks registered")
    
    def process_audio_frame(self, frame: AudioFrame) -> VADResult:
        """Process audio frame for voice activity detection.
        
        Args:
            frame: Audio frame to process
            
        Returns:
            VAD result
        """
        with self._lock:
            try:
                # Select VAD method
                if self._vad_mode == VADMode.WEBRTC and self._webrtc_vad:
                    result = self._webrtc_vad.process_frame(frame.data, frame.timestamp)
                else:
                    result = self._energy_vad.process_frame(frame.data, frame.timestamp)
                
                # Update device type
                result.device_type = frame.device_type
                
                # Process voice state changes
                self._process_voice_state_change(result)
                
                # Update performance tracking
                self._frames_processed += 1
                
                return result
                
            except Exception as e:
                logger.error(f"Error processing audio frame for VAD: {e}")
                return VADResult(
                    has_voice=False,
                    confidence=0.0,
                    energy_level=0.0,
                    timestamp=frame.timestamp,
                    device_type=frame.device_type
                )
    
    def _process_voice_state_change(self, result: VADResult) -> None:
        """Process voice state changes and emit events."""
        try:
            # Check for voice activity start
            if result.has_voice and not self._current_voice_state:
                self._current_voice_state = True
                self._voice_start_time = result.timestamp
                self._voice_segments += 1
                
                # Emit event
                self._event_bus.emit(
                    EventType.VOICE_ACTIVITY_DETECTED,
                    "vad_detector",
                    {
                        "timestamp": result.timestamp,
                        "confidence": result.confidence,
                        "energy_level": result.energy_level,
                        "device_type": result.device_type.value
                    }
                )
                
                # Call callback
                if self._voice_started_callback:
                    try:
                        self._voice_started_callback(result.timestamp)
                    except Exception as e:
                        logger.error(f"Error in voice started callback: {e}")
                
                logger.debug(f"Voice activity started - confidence: {result.confidence:.2f}")
            
            # Check for voice activity end
            elif not result.has_voice and self._current_voice_state:
                self._current_voice_state = False
                self._voice_end_time = result.timestamp
                
                # Calculate voice duration
                voice_duration = 0.0
                if self._voice_start_time:
                    voice_duration = self._voice_end_time - self._voice_start_time
                
                # Emit event
                self._event_bus.emit(
                    EventType.VOICE_ACTIVITY_ENDED,
                    "vad_detector",
                    {
                        "timestamp": result.timestamp,
                        "duration": voice_duration,
                        "device_type": result.device_type.value
                    }
                )
                
                # Call callback
                if self._voice_ended_callback:
                    try:
                        self._voice_ended_callback(voice_duration)
                    except Exception as e:
                        logger.error(f"Error in voice ended callback: {e}")
                
                logger.debug(f"Voice activity ended - duration: {voice_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing voice state change: {e}")
    
    def is_voice_active(self) -> bool:
        """Check if voice activity is currently detected."""
        return self._current_voice_state
    
    def get_current_voice_duration(self) -> float:
        """Get duration of current voice activity."""
        if self._current_voice_state and self._voice_start_time:
            return time.time() - self._voice_start_time
        return 0.0
    
    def get_vad_mode(self) -> VADMode:
        """Get current VAD mode."""
        return self._vad_mode
    
    def set_vad_mode(self, mode: VADMode) -> bool:
        """Set VAD mode.
        
        Args:
            mode: VAD mode to set
            
        Returns:
            True if mode was set successfully
        """
        try:
            if mode == VADMode.WEBRTC and not WEBRTC_VAD_AVAILABLE:
                logger.warning("WebRTC VAD not available")
                return False
            
            if mode == VADMode.WEBRTC and not self._webrtc_vad:
                try:
                    self._webrtc_vad = WebRTCVAD(
                        aggressiveness=self.settings.vad_aggressiveness,
                        sample_rate=self.settings.sample_rate
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize WebRTC VAD: {e}")
                    return False
            
            self._vad_mode = mode
            logger.info(f"VAD mode set to: {mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set VAD mode: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get VAD statistics.
        
        Returns:
            Dictionary with VAD statistics
        """
        with self._lock:
            return {
                "vad_mode": self._vad_mode.value,
                "frames_processed": self._frames_processed,
                "voice_segments": self._voice_segments,
                "current_voice_active": self._current_voice_state,
                "current_voice_duration": self.get_current_voice_duration(),
                "webrtc_available": WEBRTC_VAD_AVAILABLE
            }
    
    def reset_statistics(self) -> None:
        """Reset VAD statistics."""
        with self._lock:
            self._frames_processed = 0
            self._voice_segments = 0
            logger.debug("VAD statistics reset")
    
    def shutdown(self) -> None:
        """Shutdown voice activity detector."""
        logger.info("Shutting down VoiceActivityDetector")
        
        with self._lock:
            # Reset state
            self._current_voice_state = False
            self._voice_start_time = None
            self._voice_end_time = None
            
            # Clear callbacks
            self._voice_started_callback = None
            self._voice_ended_callback = None
            
            logger.info("VoiceActivityDetector shutdown complete")