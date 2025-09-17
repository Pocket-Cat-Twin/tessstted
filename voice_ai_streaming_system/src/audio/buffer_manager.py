"""Audio buffer management for Voice-to-AI system."""

import threading
import time
import numpy as np
from typing import Optional, List, Dict, Any, Callable
from collections import deque
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from .capture_service import AudioFrame, AudioDeviceType
    from ..utils.logger import audio_logger
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from audio.capture_service import AudioFrame, AudioDeviceType
    from utils.logger import audio_logger

logger = logging.getLogger(__name__)


class BufferMode(Enum):
    """Buffer operation modes."""
    CONTINUOUS = "continuous"  # Continuous recording, overwrite old data
    TRIGGERED = "triggered"    # Start/stop recording on command
    CIRCULAR = "circular"      # Circular buffer with fixed size


@dataclass
class BufferStats:
    """Buffer statistics."""
    total_frames: int = 0
    buffer_size_frames: int = 0
    buffer_size_seconds: float = 0.0
    oldest_timestamp: Optional[float] = None
    newest_timestamp: Optional[float] = None
    overruns: int = 0
    underruns: int = 0


class AudioBuffer:
    """Thread-safe audio buffer for a single device."""
    
    def __init__(
        self,
        device_type: AudioDeviceType,
        max_duration_seconds: float = 60.0,
        sample_rate: int = 16000,
        channels: int = 1
    ):
        self.device_type = device_type
        self.max_duration_seconds = max_duration_seconds
        self.sample_rate = sample_rate
        self.channels = channels
        
        # Calculate max frames
        self.max_frames = int(max_duration_seconds * sample_rate)
        
        # Buffer storage
        self._buffer: deque = deque(maxlen=self.max_frames)
        self._timestamps: deque = deque(maxlen=self.max_frames)
        
        # Buffer state
        self._is_recording = False
        self._recording_start_time: Optional[float] = None
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = BufferStats()
        
        logger.debug(f"AudioBuffer created for {device_type.value} - max {max_duration_seconds}s ({self.max_frames} frames)")
    
    def start_recording(self) -> None:
        """Start recording audio to buffer."""
        with self._lock:
            if not self._is_recording:
                self._is_recording = True
                self._recording_start_time = time.time()
                
                # Clear existing buffer
                self._buffer.clear()
                self._timestamps.clear()
                self._reset_stats()
                
                logger.debug(f"Started recording for {self.device_type.value}")
                audio_logger.capture_started(
                    f"{self.device_type.value}_buffer",
                    self.sample_rate,
                    self.channels
                )
    
    def stop_recording(self) -> float:
        """Stop recording and return duration.
        
        Returns:
            Recording duration in seconds
        """
        with self._lock:
            if self._is_recording:
                self._is_recording = False
                duration = time.time() - self._recording_start_time if self._recording_start_time else 0.0
                
                logger.debug(f"Stopped recording for {self.device_type.value} - duration: {duration:.2f}s")
                audio_logger.capture_stopped(f"{self.device_type.value}_buffer", duration)
                
                return duration
            return 0.0
    
    def add_frame(self, frame: AudioFrame) -> bool:
        """Add audio frame to buffer.
        
        Args:
            frame: Audio frame to add
            
        Returns:
            True if frame was added successfully
        """
        if frame.device_type != self.device_type:
            return False
        
        with self._lock:
            if not self._is_recording:
                return False
            
            try:
                # Add frame data to buffer
                for sample in frame.data:
                    self._buffer.append(sample)
                    self._timestamps.append(frame.timestamp)
                
                # Update statistics
                self._stats.total_frames += len(frame.data)
                self._stats.buffer_size_frames = len(self._buffer)
                self._stats.buffer_size_seconds = len(self._buffer) / self.sample_rate
                
                if self._stats.oldest_timestamp is None or frame.timestamp < self._stats.oldest_timestamp:
                    self._stats.oldest_timestamp = frame.timestamp
                
                if self._stats.newest_timestamp is None or frame.timestamp > self._stats.newest_timestamp:
                    self._stats.newest_timestamp = frame.timestamp
                
                # Check for buffer overrun
                if len(self._buffer) >= self.max_frames:
                    self._stats.overruns += 1
                
                return True
                
            except Exception as e:
                logger.error(f"Error adding frame to {self.device_type.value} buffer: {e}")
                return False
    
    def get_audio_data(self, start_seconds: float = 0.0, duration_seconds: Optional[float] = None) -> Optional[np.ndarray]:
        """Get audio data from buffer.
        
        Args:
            start_seconds: Start offset in seconds from beginning of recording
            duration_seconds: Duration to extract, None for all remaining data
            
        Returns:
            Audio data as numpy array or None if not available
        """
        with self._lock:
            if len(self._buffer) == 0:
                return None
            
            try:
                # Convert to numpy array
                audio_data = np.array(list(self._buffer), dtype=np.int16)
                
                # Calculate frame indices
                start_frame = int(start_seconds * self.sample_rate)
                
                if duration_seconds is not None:
                    end_frame = start_frame + int(duration_seconds * self.sample_rate)
                else:
                    end_frame = len(audio_data)
                
                # Validate indices
                start_frame = max(0, start_frame)
                end_frame = min(len(audio_data), end_frame)
                
                if start_frame >= end_frame:
                    return None
                
                return audio_data[start_frame:end_frame]
                
            except Exception as e:
                logger.error(f"Error getting audio data from {self.device_type.value} buffer: {e}")
                return None
    
    def get_latest_audio(self, duration_seconds: float) -> Optional[np.ndarray]:
        """Get the most recent audio data.
        
        Args:
            duration_seconds: Duration of recent audio to get
            
        Returns:
            Recent audio data as numpy array or None if not available
        """
        with self._lock:
            if len(self._buffer) == 0:
                return None
            
            try:
                # Calculate number of frames to get
                frames_needed = int(duration_seconds * self.sample_rate)
                frames_available = len(self._buffer)
                
                if frames_needed > frames_available:
                    frames_needed = frames_available
                
                # Get recent data
                recent_data = list(self._buffer)[-frames_needed:]
                return np.array(recent_data, dtype=np.int16)
                
            except Exception as e:
                logger.error(f"Error getting latest audio from {self.device_type.value} buffer: {e}")
                return None
    
    def clear_buffer(self) -> None:
        """Clear all buffer data."""
        with self._lock:
            self._buffer.clear()
            self._timestamps.clear()
            self._reset_stats()
            
            logger.debug(f"Cleared buffer for {self.device_type.value}")
    
    def is_recording(self) -> bool:
        """Check if buffer is currently recording."""
        return self._is_recording
    
    def get_recording_duration(self) -> float:
        """Get current recording duration in seconds."""
        with self._lock:
            if self._is_recording and self._recording_start_time:
                return time.time() - self._recording_start_time
            return 0.0
    
    def get_buffer_duration(self) -> float:
        """Get duration of data currently in buffer."""
        with self._lock:
            return len(self._buffer) / self.sample_rate if len(self._buffer) > 0 else 0.0
    
    def get_stats(self) -> BufferStats:
        """Get buffer statistics."""
        with self._lock:
            # Update current stats
            self._stats.buffer_size_frames = len(self._buffer)
            self._stats.buffer_size_seconds = len(self._buffer) / self.sample_rate
            return self._stats
    
    def _reset_stats(self) -> None:
        """Reset buffer statistics."""
        self._stats = BufferStats()


class AudioBufferManager:
    """Manager for multiple audio buffers."""
    
    def __init__(
        self,
        max_duration_seconds: float = 60.0,
        sample_rate: int = 16000,
        channels: int = 1
    ):
        self.max_duration_seconds = max_duration_seconds
        self.sample_rate = sample_rate
        self.channels = channels
        
        # Audio buffers for each device type
        self._buffers: Dict[AudioDeviceType, AudioBuffer] = {}
        
        # Recording state
        self._recording_mode = BufferMode.TRIGGERED
        self._is_recording = False
        self._recording_start_time: Optional[float] = None
        
        # Callbacks
        self._recording_started_callback: Optional[Callable[[], None]] = None
        self._recording_stopped_callback: Optional[Callable[[float], None]] = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize buffers
        self._initialize_buffers()
        
        logger.info("AudioBufferManager initialized")
    
    def _initialize_buffers(self) -> None:
        """Initialize audio buffers for all device types."""
        for device_type in AudioDeviceType:
            self._buffers[device_type] = AudioBuffer(
                device_type=device_type,
                max_duration_seconds=self.max_duration_seconds,
                sample_rate=self.sample_rate,
                channels=self.channels
            )
    
    def set_recording_mode(self, mode: BufferMode) -> None:
        """Set recording mode."""
        with self._lock:
            self._recording_mode = mode
            logger.debug(f"Recording mode set to: {mode.value}")
    
    def set_recording_callbacks(
        self,
        started_callback: Optional[Callable[[], None]] = None,
        stopped_callback: Optional[Callable[[float], None]] = None
    ) -> None:
        """Set callbacks for recording events."""
        self._recording_started_callback = started_callback
        self._recording_stopped_callback = stopped_callback
        logger.debug("Recording callbacks registered")
    
    def start_recording(self, device_types: Optional[List[AudioDeviceType]] = None) -> bool:
        """Start recording for specified device types.
        
        Args:
            device_types: List of device types to record, None for all
            
        Returns:
            True if recording started successfully
        """
        with self._lock:
            if self._is_recording:
                logger.warning("Recording already in progress")
                return False
            
            try:
                # Default to all device types
                if device_types is None:
                    device_types = list(AudioDeviceType)
                
                # Start recording for each device type
                for device_type in device_types:
                    if device_type in self._buffers:
                        self._buffers[device_type].start_recording()
                
                self._is_recording = True
                self._recording_start_time = time.time()
                
                # Call callback
                if self._recording_started_callback:
                    try:
                        self._recording_started_callback()
                    except Exception as e:
                        logger.error(f"Error in recording started callback: {e}")
                
                logger.info(f"Started recording for device types: {[dt.value for dt in device_types]}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                return False
    
    def stop_recording(self) -> float:
        """Stop recording for all device types.
        
        Returns:
            Total recording duration in seconds
        """
        with self._lock:
            if not self._is_recording:
                logger.warning("No recording in progress")
                return 0.0
            
            try:
                # Stop recording for all buffers
                total_duration = 0.0
                for buffer in self._buffers.values():
                    duration = buffer.stop_recording()
                    total_duration = max(total_duration, duration)
                
                self._is_recording = False
                
                # Calculate actual duration
                if self._recording_start_time:
                    actual_duration = time.time() - self._recording_start_time
                    total_duration = max(total_duration, actual_duration)
                
                # Call callback
                if self._recording_stopped_callback:
                    try:
                        self._recording_stopped_callback(total_duration)
                    except Exception as e:
                        logger.error(f"Error in recording stopped callback: {e}")
                
                logger.info(f"Stopped recording - duration: {total_duration:.2f}s")
                return total_duration
                
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")
                return 0.0
    
    def add_audio_frame(self, frame: AudioFrame) -> bool:
        """Add audio frame to appropriate buffer.
        
        Args:
            frame: Audio frame to add
            
        Returns:
            True if frame was added successfully
        """
        if frame.device_type in self._buffers:
            return self._buffers[frame.device_type].add_frame(frame)
        return False
    
    def get_recorded_audio(self, device_type: AudioDeviceType, start_seconds: float = 0.0, duration_seconds: Optional[float] = None) -> Optional[np.ndarray]:
        """Get recorded audio data for a device type.
        
        Args:
            device_type: Device type to get audio from
            start_seconds: Start offset in seconds
            duration_seconds: Duration to extract, None for all
            
        Returns:
            Audio data as numpy array or None if not available
        """
        if device_type in self._buffers:
            return self._buffers[device_type].get_audio_data(start_seconds, duration_seconds)
        return None
    
    def get_latest_audio(self, device_type: AudioDeviceType, duration_seconds: float) -> Optional[np.ndarray]:
        """Get latest audio data for a device type.
        
        Args:
            device_type: Device type to get audio from
            duration_seconds: Duration of recent audio to get
            
        Returns:
            Recent audio data as numpy array or None if not available
        """
        if device_type in self._buffers:
            return self._buffers[device_type].get_latest_audio(duration_seconds)
        return None
    
    def is_recording(self) -> bool:
        """Check if any recording is active."""
        return self._is_recording
    
    def get_recording_duration(self) -> float:
        """Get current recording duration."""
        with self._lock:
            if self._is_recording and self._recording_start_time:
                return time.time() - self._recording_start_time
            return 0.0
    
    def get_buffer_info(self, device_type: AudioDeviceType) -> Optional[Dict[str, Any]]:
        """Get buffer information for a device type.
        
        Args:
            device_type: Device type to get info for
            
        Returns:
            Buffer information dictionary or None if not found
        """
        if device_type in self._buffers:
            buffer = self._buffers[device_type]
            stats = buffer.get_stats()
            
            return {
                "device_type": device_type.value,
                "is_recording": buffer.is_recording(),
                "recording_duration": buffer.get_recording_duration(),
                "buffer_duration": buffer.get_buffer_duration(),
                "max_duration": buffer.max_duration_seconds,
                "sample_rate": buffer.sample_rate,
                "channels": buffer.channels,
                "stats": {
                    "total_frames": stats.total_frames,
                    "buffer_size_frames": stats.buffer_size_frames,
                    "buffer_size_seconds": stats.buffer_size_seconds,
                    "overruns": stats.overruns,
                    "underruns": stats.underruns
                }
            }
        return None
    
    def get_all_buffer_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information for all buffers.
        
        Returns:
            Dictionary mapping device type to buffer info
        """
        info = {}
        for device_type in self._buffers:
            buffer_info = self.get_buffer_info(device_type)
            if buffer_info:
                info[device_type.value] = buffer_info
        return info
    
    def clear_all_buffers(self) -> None:
        """Clear all audio buffers."""
        with self._lock:
            for buffer in self._buffers.values():
                buffer.clear_buffer()
            
            logger.info("All audio buffers cleared")
    
    def get_total_memory_usage(self) -> int:
        """Get total memory usage of all buffers in bytes.
        
        Returns:
            Total memory usage in bytes
        """
        total_bytes = 0
        for buffer in self._buffers.values():
            # Each sample is 2 bytes (int16)
            total_bytes += len(buffer._buffer) * 2
        
        return total_bytes
    
    def shutdown(self) -> None:
        """Shutdown buffer manager."""
        logger.info("Shutting down AudioBufferManager")
        
        with self._lock:
            # Stop any active recordings
            if self._is_recording:
                self.stop_recording()
            
            # Clear all buffers
            self.clear_all_buffers()
            
            logger.info("AudioBufferManager shutdown complete")