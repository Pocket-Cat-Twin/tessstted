"""Audio capture service for dual microphone and system output recording."""

import threading
import queue
import time
import numpy as np
from typing import Optional, Callable, Dict, Any, List, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("PyAudio not available - audio capture will not work")

try:
    from ..config.settings import AudioSettings
    from ..core.event_bus import EventBus, EventType, get_event_bus
    from ..core.state_manager import StateManager, ComponentState, get_state_manager
    from ..utils.logger import AudioLogger, audio_logger
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config.settings import AudioSettings
    from core.event_bus import EventBus, EventType, get_event_bus
    from core.state_manager import StateManager, ComponentState, get_state_manager
    from utils.logger import AudioLogger, audio_logger

logger = logging.getLogger(__name__)


class AudioDeviceType(Enum):
    """Audio device types."""
    MICROPHONE = "microphone"
    SYSTEM_OUTPUT = "system_output"


@dataclass
class AudioDevice:
    """Audio device information."""
    index: int
    name: str
    device_type: AudioDeviceType
    channels: int
    sample_rate: int
    is_default: bool = False


@dataclass
class AudioFrame:
    """Audio frame data structure."""
    data: np.ndarray
    timestamp: float
    device_type: AudioDeviceType
    sample_rate: int
    channels: int
    frame_count: int


class AudioCaptureService:
    """Dual audio capture service for microphone and system output."""
    
    def __init__(
        self,
        settings: AudioSettings,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        self.settings = settings
        self._event_bus = event_bus or get_event_bus()
        self._state_manager = state_manager or get_state_manager()
        
        # PyAudio instance
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        
        # Audio streams
        self._microphone_stream: Optional[pyaudio.Stream] = None
        self._system_output_stream: Optional[pyaudio.Stream] = None
        
        # Capture state
        self._microphone_capturing = False
        self._system_output_capturing = False
        self._capture_threads: Dict[AudioDeviceType, threading.Thread] = {}
        self._stop_events: Dict[AudioDeviceType, threading.Event] = {}
        
        # Audio data queues
        self._microphone_queue = queue.Queue(maxsize=100)
        self._system_output_queue = queue.Queue(maxsize=100)
        
        # Device information
        self._available_devices: List[AudioDevice] = []
        self._selected_microphone: Optional[AudioDevice] = None
        self._selected_system_output: Optional[AudioDevice] = None
        
        # Callbacks
        self._audio_callback: Optional[Callable[[AudioFrame], None]] = None
        
        # Performance metrics
        self._frames_captured = 0
        self._frames_dropped = 0
        self._last_stats_time = time.time()
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("AudioCaptureService initialized")
    
    def initialize(self) -> bool:
        """Initialize audio system and enumerate devices."""
        try:
            with self._lock:
                # Initialize PyAudio
                self._pyaudio = pyaudio.PyAudio()
                
                # Enumerate audio devices
                self._enumerate_devices()
                
                # Select default devices
                self._select_default_devices()
                
                # Update state
                self._state_manager.set_component_state("audio_capture", ComponentState.READY)
                self._state_manager.update_audio_state(
                    sample_rate=self.settings.sample_rate,
                    buffer_size=self.settings.buffer_size
                )
                
                logger.info("Audio system initialized successfully")
                audio_logger.capture_started("system", self.settings.sample_rate, self.settings.channels)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize audio system: {e}")
            self._state_manager.record_error("audio_capture", str(e), critical=True)
            return False
    
    def _enumerate_devices(self) -> None:
        """Enumerate available audio devices."""
        try:
            self._available_devices.clear()
            device_count = self._pyaudio.get_device_count()
            
            for i in range(device_count):
                try:
                    device_info = self._pyaudio.get_device_info_by_index(i)
                    
                    # Check if device supports input
                    if device_info['maxInputChannels'] > 0:
                        # Determine device type
                        device_name = device_info['name'].lower()
                        
                        if any(keyword in device_name for keyword in ['microphone', 'mic', 'input']):
                            device_type = AudioDeviceType.MICROPHONE
                        elif any(keyword in device_name for keyword in ['speaker', 'output', 'stereo mix', 'what u hear']):
                            device_type = AudioDeviceType.SYSTEM_OUTPUT
                        else:
                            # Default to microphone for input devices
                            device_type = AudioDeviceType.MICROPHONE
                        
                        device = AudioDevice(
                            index=i,
                            name=device_info['name'],
                            device_type=device_type,
                            channels=min(device_info['maxInputChannels'], self.settings.channels),
                            sample_rate=int(device_info['defaultSampleRate']),
                            is_default=(i == self._pyaudio.get_default_input_device_info()['index'])
                        )
                        
                        self._available_devices.append(device)
                        
                        logger.debug(f"Found audio device: {device.name} (type: {device_type.value})")
                        
                except Exception as e:
                    logger.warning(f"Error getting info for device {i}: {e}")
            
            logger.info(f"Enumerated {len(self._available_devices)} audio devices")
            
        except Exception as e:
            logger.error(f"Failed to enumerate audio devices: {e}")
    
    def _select_default_devices(self) -> None:
        """Select default microphone and system output devices."""
        try:
            # Select microphone device
            microphone_devices = [d for d in self._available_devices if d.device_type == AudioDeviceType.MICROPHONE]
            if microphone_devices:
                # Prefer configured device or default
                if self.settings.microphone_device:
                    self._selected_microphone = next(
                        (d for d in microphone_devices if self.settings.microphone_device in d.name),
                        microphone_devices[0]
                    )
                else:
                    self._selected_microphone = next(
                        (d for d in microphone_devices if d.is_default),
                        microphone_devices[0]
                    )
                
                logger.info(f"Selected microphone: {self._selected_microphone.name}")
            
            # Select system output device
            system_output_devices = [d for d in self._available_devices if d.device_type == AudioDeviceType.SYSTEM_OUTPUT]
            if system_output_devices:
                if self.settings.system_output_device:
                    self._selected_system_output = next(
                        (d for d in system_output_devices if self.settings.system_output_device in d.name),
                        system_output_devices[0]
                    )
                else:
                    self._selected_system_output = system_output_devices[0]
                
                logger.info(f"Selected system output: {self._selected_system_output.name}")
            else:
                logger.warning("No system output devices found - system audio capture will not be available")
            
            # Update state manager
            self._state_manager.update_audio_state(
                microphone_device=self._selected_microphone.name if self._selected_microphone else None,
                system_output_device=self._selected_system_output.name if self._selected_system_output else None
            )
            
        except Exception as e:
            logger.error(f"Failed to select default devices: {e}")
    
    def get_available_devices(self) -> List[AudioDevice]:
        """Get list of available audio devices."""
        return self._available_devices.copy()
    
    def set_microphone_device(self, device_name: str) -> bool:
        """Set microphone device by name."""
        try:
            device = next(
                (d for d in self._available_devices 
                 if d.device_type == AudioDeviceType.MICROPHONE and device_name in d.name),
                None
            )
            
            if device:
                if self._microphone_capturing:
                    self.stop_microphone_capture()
                
                self._selected_microphone = device
                self._state_manager.update_audio_state(microphone_device=device.name)
                
                logger.info(f"Microphone device set to: {device.name}")
                return True
            else:
                logger.error(f"Microphone device not found: {device_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set microphone device: {e}")
            return False
    
    def set_system_output_device(self, device_name: str) -> bool:
        """Set system output device by name."""
        try:
            device = next(
                (d for d in self._available_devices 
                 if d.device_type == AudioDeviceType.SYSTEM_OUTPUT and device_name in d.name),
                None
            )
            
            if device:
                if self._system_output_capturing:
                    self.stop_system_output_capture()
                
                self._selected_system_output = device
                self._state_manager.update_audio_state(system_output_device=device.name)
                
                logger.info(f"System output device set to: {device.name}")
                return True
            else:
                logger.error(f"System output device not found: {device_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set system output device: {e}")
            return False
    
    def set_audio_callback(self, callback: Callable[[AudioFrame], None]) -> None:
        """Set callback function for audio data."""
        self._audio_callback = callback
        logger.debug("Audio callback registered")
    
    def start_microphone_capture(self) -> bool:
        """Start microphone audio capture."""
        try:
            with self._lock:
                if self._microphone_capturing:
                    logger.warning("Microphone capture already running")
                    return True
                
                if not self._selected_microphone:
                    logger.error("No microphone device selected")
                    return False
                
                # Create audio stream
                self._microphone_stream = self._pyaudio.open(
                    format=getattr(pyaudio, f"pa{self.settings.format.upper()}"),
                    channels=self.settings.channels,
                    rate=self.settings.sample_rate,
                    input=True,
                    input_device_index=self._selected_microphone.index,
                    frames_per_buffer=self.settings.buffer_size,
                    stream_callback=self._microphone_callback
                )
                
                # Start capture thread
                self._stop_events[AudioDeviceType.MICROPHONE] = threading.Event()
                self._capture_threads[AudioDeviceType.MICROPHONE] = threading.Thread(
                    target=self._capture_loop,
                    args=(AudioDeviceType.MICROPHONE,),
                    name="MicrophoneCapture",
                    daemon=True
                )
                
                self._microphone_capturing = True
                self._microphone_stream.start_stream()
                self._capture_threads[AudioDeviceType.MICROPHONE].start()
                
                # Update state
                self._state_manager.update_audio_state(microphone_capturing=True)
                
                # Emit event
                self._event_bus.emit(
                    EventType.AUDIO_CAPTURE_STARTED,
                    "audio_capture",
                    {
                        "device_type": "microphone",
                        "device_name": self._selected_microphone.name,
                        "sample_rate": self.settings.sample_rate,
                        "channels": self.settings.channels
                    }
                )
                
                audio_logger.capture_started(
                    self._selected_microphone.name,
                    self.settings.sample_rate,
                    self.settings.channels
                )
                
                logger.info("Microphone capture started")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start microphone capture: {e}")
            audio_logger.device_error(
                self._selected_microphone.name if self._selected_microphone else "unknown",
                str(e)
            )
            return False
    
    def start_system_output_capture(self) -> bool:
        """Start system output audio capture."""
        try:
            with self._lock:
                if self._system_output_capturing:
                    logger.warning("System output capture already running")
                    return True
                
                if not self._selected_system_output:
                    logger.error("No system output device selected")
                    return False
                
                # Create audio stream
                self._system_output_stream = self._pyaudio.open(
                    format=getattr(pyaudio, f"pa{self.settings.format.upper()}"),
                    channels=self.settings.channels,
                    rate=self.settings.sample_rate,
                    input=True,
                    input_device_index=self._selected_system_output.index,
                    frames_per_buffer=self.settings.buffer_size,
                    stream_callback=self._system_output_callback
                )
                
                # Start capture thread
                self._stop_events[AudioDeviceType.SYSTEM_OUTPUT] = threading.Event()
                self._capture_threads[AudioDeviceType.SYSTEM_OUTPUT] = threading.Thread(
                    target=self._capture_loop,
                    args=(AudioDeviceType.SYSTEM_OUTPUT,),
                    name="SystemOutputCapture",
                    daemon=True
                )
                
                self._system_output_capturing = True
                self._system_output_stream.start_stream()
                self._capture_threads[AudioDeviceType.SYSTEM_OUTPUT].start()
                
                # Update state
                self._state_manager.update_audio_state(system_output_capturing=True)
                
                # Emit event
                self._event_bus.emit(
                    EventType.AUDIO_CAPTURE_STARTED,
                    "audio_capture",
                    {
                        "device_type": "system_output",
                        "device_name": self._selected_system_output.name,
                        "sample_rate": self.settings.sample_rate,
                        "channels": self.settings.channels
                    }
                )
                
                audio_logger.capture_started(
                    self._selected_system_output.name,
                    self.settings.sample_rate,
                    self.settings.channels
                )
                
                logger.info("System output capture started")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start system output capture: {e}")
            audio_logger.device_error(
                self._selected_system_output.name if self._selected_system_output else "unknown",
                str(e)
            )
            return False
    
    def stop_microphone_capture(self) -> bool:
        """Stop microphone audio capture."""
        try:
            with self._lock:
                if not self._microphone_capturing:
                    return True
                
                # Stop capture
                self._microphone_capturing = False
                
                # Signal stop event
                if AudioDeviceType.MICROPHONE in self._stop_events:
                    self._stop_events[AudioDeviceType.MICROPHONE].set()
                
                # Stop and close stream
                if self._microphone_stream:
                    self._microphone_stream.stop_stream()
                    self._microphone_stream.close()
                    self._microphone_stream = None
                
                # Wait for thread to finish
                if AudioDeviceType.MICROPHONE in self._capture_threads:
                    self._capture_threads[AudioDeviceType.MICROPHONE].join(timeout=2.0)
                    del self._capture_threads[AudioDeviceType.MICROPHONE]
                
                # Update state
                self._state_manager.update_audio_state(microphone_capturing=False)
                
                # Emit event
                self._event_bus.emit(
                    EventType.AUDIO_CAPTURE_STOPPED,
                    "audio_capture",
                    {"device_type": "microphone"}
                )
                
                if self._selected_microphone:
                    audio_logger.capture_stopped(self._selected_microphone.name, 0.0)
                
                logger.info("Microphone capture stopped")
                return True
                
        except Exception as e:
            logger.error(f"Failed to stop microphone capture: {e}")
            return False
    
    def stop_system_output_capture(self) -> bool:
        """Stop system output audio capture."""
        try:
            with self._lock:
                if not self._system_output_capturing:
                    return True
                
                # Stop capture
                self._system_output_capturing = False
                
                # Signal stop event
                if AudioDeviceType.SYSTEM_OUTPUT in self._stop_events:
                    self._stop_events[AudioDeviceType.SYSTEM_OUTPUT].set()
                
                # Stop and close stream
                if self._system_output_stream:
                    self._system_output_stream.stop_stream()
                    self._system_output_stream.close()
                    self._system_output_stream = None
                
                # Wait for thread to finish
                if AudioDeviceType.SYSTEM_OUTPUT in self._capture_threads:
                    self._capture_threads[AudioDeviceType.SYSTEM_OUTPUT].join(timeout=2.0)
                    del self._capture_threads[AudioDeviceType.SYSTEM_OUTPUT]
                
                # Update state
                self._state_manager.update_audio_state(system_output_capturing=False)
                
                # Emit event
                self._event_bus.emit(
                    EventType.AUDIO_CAPTURE_STOPPED,
                    "audio_capture",
                    {"device_type": "system_output"}
                )
                
                if self._selected_system_output:
                    audio_logger.capture_stopped(self._selected_system_output.name, 0.0)
                
                logger.info("System output capture stopped")
                return True
                
        except Exception as e:
            logger.error(f"Failed to stop system output capture: {e}")
            return False
    
    def _microphone_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for microphone data."""
        if status:
            logger.warning(f"Microphone callback status: {status}")
        
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Create audio frame
            frame = AudioFrame(
                data=audio_data,
                timestamp=time.time(),
                device_type=AudioDeviceType.MICROPHONE,
                sample_rate=self.settings.sample_rate,
                channels=self.settings.channels,
                frame_count=frame_count
            )
            
            # Queue frame for processing
            try:
                self._microphone_queue.put_nowait(frame)
            except queue.Full:
                self._frames_dropped += 1
                audio_logger.buffer_overflow("microphone", 1)
            
        except Exception as e:
            logger.error(f"Error in microphone callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def _system_output_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for system output data."""
        if status:
            logger.warning(f"System output callback status: {status}")
        
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Create audio frame
            frame = AudioFrame(
                data=audio_data,
                timestamp=time.time(),
                device_type=AudioDeviceType.SYSTEM_OUTPUT,
                sample_rate=self.settings.sample_rate,
                channels=self.settings.channels,
                frame_count=frame_count
            )
            
            # Queue frame for processing
            try:
                self._system_output_queue.put_nowait(frame)
            except queue.Full:
                self._frames_dropped += 1
                audio_logger.buffer_overflow("system_output", 1)
            
        except Exception as e:
            logger.error(f"Error in system output callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def _capture_loop(self, device_type: AudioDeviceType) -> None:
        """Main capture loop for processing audio frames."""
        try:
            stop_event = self._stop_events[device_type]
            audio_queue = (self._microphone_queue if device_type == AudioDeviceType.MICROPHONE 
                          else self._system_output_queue)
            
            logger.debug(f"Capture loop started for {device_type.value}")
            
            while not stop_event.is_set():
                try:
                    # Get audio frame from queue
                    frame = audio_queue.get(timeout=0.1)
                    
                    # Process frame
                    self._process_audio_frame(frame)
                    self._frames_captured += 1
                    
                    # Update performance stats
                    current_time = time.time()
                    if current_time - self._last_stats_time >= 5.0:
                        self._log_performance_stats()
                        self._last_stats_time = current_time
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing audio frame for {device_type.value}: {e}")
            
            logger.debug(f"Capture loop ended for {device_type.value}")
            
        except Exception as e:
            logger.error(f"Fatal error in capture loop for {device_type.value}: {e}")
    
    def _process_audio_frame(self, frame: AudioFrame) -> None:
        """Process an audio frame."""
        try:
            # Emit audio data event
            self._event_bus.emit(
                EventType.AUDIO_DATA_AVAILABLE,
                "audio_capture",
                {
                    "device_type": frame.device_type.value,
                    "timestamp": frame.timestamp,
                    "frame_count": frame.frame_count,
                    "sample_rate": frame.sample_rate,
                    "channels": frame.channels
                }
            )
            
            # Call registered callback
            if self._audio_callback:
                self._audio_callback(frame)
                
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
    
    def _log_performance_stats(self) -> None:
        """Log performance statistics."""
        try:
            frames_per_second = self._frames_captured / 5.0 if self._frames_captured > 0 else 0
            dropped_percentage = (self._frames_dropped / max(self._frames_captured, 1)) * 100
            
            logger.debug(f"Audio performance: {frames_per_second:.1f} fps, {dropped_percentage:.1f}% dropped")
            
            # Reset counters
            self._frames_captured = 0
            self._frames_dropped = 0
            
        except Exception as e:
            logger.error(f"Error logging performance stats: {e}")
    
    def is_capturing(self, device_type: Optional[AudioDeviceType] = None) -> bool:
        """Check if audio capture is active."""
        if device_type == AudioDeviceType.MICROPHONE:
            return self._microphone_capturing
        elif device_type == AudioDeviceType.SYSTEM_OUTPUT:
            return self._system_output_capturing
        else:
            return self._microphone_capturing or self._system_output_capturing
    
    def get_capture_status(self) -> Dict[str, Any]:
        """Get current capture status."""
        return {
            "microphone_capturing": self._microphone_capturing,
            "system_output_capturing": self._system_output_capturing,
            "microphone_device": self._selected_microphone.name if self._selected_microphone else None,
            "system_output_device": self._selected_system_output.name if self._selected_system_output else None,
            "frames_captured": self._frames_captured,
            "frames_dropped": self._frames_dropped,
            "sample_rate": self.settings.sample_rate,
            "buffer_size": self.settings.buffer_size,
            "channels": self.settings.channels
        }
    
    def shutdown(self) -> None:
        """Shutdown audio capture service."""
        logger.info("Shutting down audio capture service")
        
        try:
            # Stop all captures
            self.stop_microphone_capture()
            self.stop_system_output_capture()
            
            # Cleanup PyAudio
            if self._pyaudio:
                self._pyaudio.terminate()
                self._pyaudio = None
            
            # Update state
            self._state_manager.set_component_state("audio_capture", ComponentState.STOPPED)
            
            logger.info("Audio capture service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during audio capture shutdown: {e}")