"""Base speech-to-text service interface."""

import abc
import time
import threading
from typing import Optional, Callable, Dict, Any, List, AsyncGenerator, Union
import logging
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    from ..config.settings import STTSettings
    from ..core.event_bus import EventBus, EventType, get_event_bus
    from ..core.state_manager import StateManager, get_state_manager
    from ..audio.capture_service import AudioFrame
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config.settings import STTSettings
    from core.event_bus import EventBus, EventType, get_event_bus
    from core.state_manager import StateManager, get_state_manager
    from audio.capture_service import AudioFrame

logger = logging.getLogger(__name__)


class STTProvider(Enum):
    """STT service providers."""
    YANDEX_SPEECHKIT = "yandex_speechkit"
    WHISPERX = "whisperx"
    MOCK = "mock"  # For testing


@dataclass
class STTResult:
    """Speech-to-text result."""
    text: str
    confidence: float
    is_final: bool
    language: str
    timestamp: float
    processing_time: Optional[float] = None
    alternatives: Optional[List[str]] = None
    word_timestamps: Optional[List[Dict[str, Any]]] = None


class BaseSTTService(abc.ABC):
    """Abstract base class for STT services."""
    
    def __init__(
        self,
        settings: STTSettings,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        self.settings = settings
        self._event_bus = event_bus or get_event_bus()
        self._state_manager = state_manager or get_state_manager()
        
        # Service state
        self._is_initialized = False
        self._is_processing = False
        self._current_session_id: Optional[str] = None
        
        # Callbacks
        self._result_callback: Optional[Callable[[STTResult], None]] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        
        # Performance tracking
        self._requests_count = 0
        self._total_processing_time = 0.0
        self._errors_count = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(f"STT service {self.get_provider()} initialized")
    
    @property
    @abc.abstractmethod
    def provider(self) -> STTProvider:
        """Get the STT provider type."""
        pass
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize the STT service.
        
        Returns:
            True if initialization successful
        """
        pass
    
    @abc.abstractmethod
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[STTResult]:
        """Process audio data and return transcription.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Audio sample rate
            
        Returns:
            STT result or None if processing failed
        """
        pass
    
    @abc.abstractmethod
    def process_audio_stream(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int = 16000
    ) -> AsyncGenerator[STTResult, None]:
        """Process streaming audio data.
        
        Args:
            audio_stream: Stream of audio data chunks
            sample_rate: Audio sample rate
            
        Yields:
            STT results as they become available
        """
        pass
    
    @abc.abstractmethod
    def shutdown(self) -> None:
        """Shutdown the STT service."""
        pass
    
    def get_provider(self) -> STTProvider:
        """Get the provider type."""
        return self.provider
    
    def set_result_callback(self, callback: Callable[[STTResult], None]) -> None:
        """Set callback for STT results."""
        self._result_callback = callback
        logger.debug("STT result callback registered")
    
    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Set callback for STT errors."""
        self._error_callback = callback
        logger.debug("STT error callback registered")
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._is_initialized
    
    def is_processing(self) -> bool:
        """Check if service is currently processing."""
        return self._is_processing
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        with self._lock:
            avg_processing_time = (
                self._total_processing_time / max(self._requests_count, 1)
            )
            
            return {
                "provider": self.provider.value,
                "initialized": self._is_initialized,
                "processing": self._is_processing,
                "requests_count": self._requests_count,
                "errors_count": self._errors_count,
                "average_processing_time": avg_processing_time,
                "error_rate": self._errors_count / max(self._requests_count, 1)
            }
    
    def reset_statistics(self) -> None:
        """Reset service statistics."""
        with self._lock:
            self._requests_count = 0
            self._total_processing_time = 0.0
            self._errors_count = 0
            logger.debug("STT statistics reset")
    
    def _emit_result(self, result: STTResult) -> None:
        """Emit STT result via event bus and callback."""
        try:
            # Emit event
            self._event_bus.emit(
                EventType.STT_FINAL_RESULT if result.is_final else EventType.STT_PARTIAL_RESULT,
                f"stt_{self.provider.value}",
                {
                    "text": result.text,
                    "confidence": result.confidence,
                    "is_final": result.is_final,
                    "language": result.language,
                    "processing_time": result.processing_time
                }
            )
            
            # Update state manager
            self._state_manager.update_stt_state(
                current_text=result.text,
                confidence=result.confidence,
                processing_time=result.processing_time or 0.0,
                last_result_time=time.time()
            )
            
            # Call callback
            if self._result_callback:
                try:
                    self._result_callback(result)
                except Exception as e:
                    logger.error(f"Error in STT result callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error emitting STT result: {e}")
    
    def _emit_error(self, error: Exception) -> None:
        """Emit STT error via event bus and callback."""
        try:
            # Update error count
            with self._lock:
                self._errors_count += 1
            
            # Emit event
            self._event_bus.emit(
                EventType.STT_ERROR,
                f"stt_{self.provider.value}",
                {
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "provider": self.provider.value
                }
            )
            
            # Record error in state manager
            self._state_manager.record_error(
                f"stt_{self.provider.value}",
                str(error),
                critical=False
            )
            
            # Call callback
            if self._error_callback:
                try:
                    self._error_callback(error)
                except Exception as e:
                    logger.error(f"Error in STT error callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error emitting STT error: {e}")
    
    def _start_processing(self) -> None:
        """Mark processing as started."""
        with self._lock:
            self._is_processing = True
            self._requests_count += 1
        
        # Update state manager
        self._state_manager.update_stt_state(is_processing=True)
        
        # Emit event
        self._event_bus.emit(
            EventType.STT_PROCESSING_STARTED,
            f"stt_{self.provider.value}",
            {"provider": self.provider.value}
        )
    
    def _stop_processing(self, processing_time: Optional[float] = None) -> None:
        """Mark processing as stopped."""
        with self._lock:
            self._is_processing = False
            if processing_time:
                self._total_processing_time += processing_time
        
        # Update state manager
        self._state_manager.update_stt_state(is_processing=False)
    
    def _validate_audio_data(self, audio_data: np.ndarray, sample_rate: int) -> bool:
        """Validate audio data format."""
        try:
            if not isinstance(audio_data, np.ndarray):
                logger.error("Audio data must be numpy array")
                return False
            
            if audio_data.size == 0:
                logger.warning("Empty audio data")
                return False
            
            if sample_rate <= 0:
                logger.error(f"Invalid sample rate: {sample_rate}")
                return False
            
            # Check supported sample rates (most STT services)
            supported_rates = [8000, 16000, 22050, 32000, 44100, 48000]
            if sample_rate not in supported_rates:
                logger.warning(f"Unusual sample rate: {sample_rate}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating audio data: {e}")
            return False
    
    def _convert_audio_format(
        self,
        audio_data: np.ndarray,
        target_sample_rate: int,
        current_sample_rate: int
    ) -> np.ndarray:
        """Convert audio format if needed."""
        try:
            # Simple resampling using scipy if available
            if target_sample_rate != current_sample_rate:
                logger.debug(f"Resampling from {current_sample_rate} to {target_sample_rate}")
                
                # Simple decimation/interpolation for now
                ratio = target_sample_rate / current_sample_rate
                new_length = int(len(audio_data) * ratio)
                
                # Linear interpolation
                indices = np.linspace(0, len(audio_data) - 1, new_length)
                resampled = np.interp(indices, np.arange(len(audio_data)), audio_data)
                
                return resampled.astype(audio_data.dtype)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error converting audio format: {e}")
            return audio_data
    
    def _prepare_audio_for_service(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> tuple[bytes, int]:
        """Prepare audio data for STT service.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Current sample rate
            
        Returns:
            Tuple of (audio_bytes, final_sample_rate)
        """
        try:
            # Convert to target sample rate if needed
            target_rate = 16000  # Most STT services prefer 16kHz
            converted_audio = self._convert_audio_format(audio_data, target_rate, sample_rate)
            
            # Ensure correct format (int16)
            if converted_audio.dtype != np.int16:
                # Normalize to int16 range
                if converted_audio.dtype == np.float32 or converted_audio.dtype == np.float64:
                    # Assume float audio is in range [-1, 1]
                    converted_audio = (converted_audio * 32767).astype(np.int16)
                else:
                    converted_audio = converted_audio.astype(np.int16)
            
            # Convert to bytes
            audio_bytes = converted_audio.tobytes()
            
            return audio_bytes, target_rate
            
        except Exception as e:
            logger.error(f"Error preparing audio for service: {e}")
            # Return original data as fallback
            return audio_data.tobytes(), sample_rate


class MockSTTService(BaseSTTService):
    """Mock STT service for testing."""
    
    @property
    def provider(self) -> STTProvider:
        return STTProvider.MOCK
    
    def initialize(self) -> bool:
        """Initialize mock service."""
        try:
            self._is_initialized = True
            logger.info("Mock STT service initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize mock STT service: {e}")
            return False
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[STTResult]:
        """Process audio with mock transcription."""
        try:
            if not self._validate_audio_data(audio_data, sample_rate):
                return None
            
            start_time = time.time()
            self._start_processing()
            
            # Mock processing delay
            time.sleep(0.1)
            
            # Generate mock result
            duration = len(audio_data) / sample_rate
            mock_text = f"Mock transcription for {duration:.1f}s audio"
            
            processing_time = time.time() - start_time
            
            result = STTResult(
                text=mock_text,
                confidence=0.95,
                is_final=True,
                language=self.settings.language_code,
                timestamp=time.time(),
                processing_time=processing_time
            )
            
            self._stop_processing(processing_time)
            self._emit_result(result)
            
            return result
            
        except Exception as e:
            self._emit_error(e)
            return None
    
    async def process_audio_stream(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int = 16000
    ) -> AsyncGenerator[STTResult, None]:
        """Process streaming audio with mock transcription."""
        try:
            chunk_count = 0
            async for audio_chunk in audio_stream:
                chunk_count += 1
                
                # Mock partial results
                if chunk_count % 3 == 0:  # Every 3rd chunk
                    partial_result = STTResult(
                        text=f"Partial transcription chunk {chunk_count}",
                        confidence=0.8,
                        is_final=False,
                        language=self.settings.language_code,
                        timestamp=time.time()
                    )
                    yield partial_result
                
                # Mock final result every 10 chunks
                if chunk_count % 10 == 0:
                    final_result = STTResult(
                        text=f"Final transcription for chunks 1-{chunk_count}",
                        confidence=0.95,
                        is_final=True,
                        language=self.settings.language_code,
                        timestamp=time.time()
                    )
                    yield final_result
                    
        except Exception as e:
            logger.error(f"Error in mock streaming STT: {e}")
            self._emit_error(e)
    
    def shutdown(self) -> None:
        """Shutdown mock service."""
        self._is_initialized = False
        self._is_processing = False
        logger.info("Mock STT service shutdown")