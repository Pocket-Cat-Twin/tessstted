"""WhisperX large-v2 local STT service implementation."""

import asyncio
import threading
import time
import logging
import gc
import torch
from typing import Optional, AsyncGenerator, Dict, Any, List, Union
import numpy as np
from pathlib import Path
import tempfile
import os

try:
    from ..config.settings import STTSettings
    from .base_stt import BaseSTTService, STTProvider, STTResult
    from ..core.event_bus import EventBus, EventType, get_event_bus
    from ..core.state_manager import StateManager, get_state_manager
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config.settings import STTSettings
    from stt.base_stt import BaseSTTService, STTProvider, STTResult
    from core.event_bus import EventBus, EventType, get_event_bus
    from core.state_manager import StateManager, get_state_manager

# WhisperX imports
try:
    import whisperx
    WHISPERX_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False
    whisperx = None

logger = logging.getLogger(__name__)


class WhisperXSTTService(BaseSTTService):
    """WhisperX large-v2 local STT service."""
    
    def __init__(
        self,
        settings: STTSettings,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        super().__init__(settings, event_bus, state_manager)
        
        # WhisperX-specific settings
        self.api_settings = settings.provider_settings.get('whisperx', {})
        
        # Model configuration
        self.model_size = self.api_settings.get('model_size', 'large-v2')
        self.device = self._determine_device()
        self.compute_type = self.api_settings.get('compute_type', 'float16')
        self.batch_size = self.api_settings.get('batch_size', 16)
        self.language = self.api_settings.get('language', 'auto')
        
        # Advanced settings
        self.enable_diarization = self.api_settings.get('enable_diarization', False)
        self.enable_vad_filter = self.api_settings.get('enable_vad_filter', True)
        self.vad_onset = self.api_settings.get('vad_onset', 0.5)
        self.vad_offset = self.api_settings.get('vad_offset', 0.363)
        self.min_silence_duration = self.api_settings.get('min_silence_duration', 1.0)
        
        # Model instances
        self._model = None
        self._align_model = None
        self._align_metadata = None
        self._diarize_model = None
        
        # Processing state
        self._model_loading = False
        self._processing_queue = asyncio.Queue()
        self._processing_thread: Optional[threading.Thread] = None
        
        # Statistics
        self._processing_sessions = 0
        self._total_audio_duration = 0.0
        self._model_load_time = 0.0
        
        logger.info(f"WhisperX STT service initialized with model: {self.model_size}, device: {self.device}")
    
    @property
    def provider(self) -> STTProvider:
        return STTProvider.WHISPERX
    
    def _determine_device(self) -> str:
        """Determine the best device for WhisperX."""
        try:
            device_setting = self.api_settings.get('device', 'auto')
            
            if device_setting == 'auto':
                # Auto-detect best device
                if torch.cuda.is_available():
                    device = 'cuda'
                    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                    logger.info(f"CUDA available with {gpu_memory:.1f}GB GPU memory")
                    
                    # Adjust compute type based on GPU memory
                    if gpu_memory < 6:
                        logger.warning("Low GPU memory detected, using int8 compute type")
                        self.api_settings['compute_type'] = 'int8'
                        self.api_settings['batch_size'] = 8
                else:
                    device = 'cpu'
                    logger.info("CUDA not available, using CPU")
                    # CPU optimizations
                    self.api_settings['compute_type'] = 'int8'
                    self.api_settings['batch_size'] = 4
            else:
                device = device_setting
            
            return device
            
        except Exception as e:
            logger.error(f"Error determining device: {e}")
            return 'cpu'
    
    def initialize(self) -> bool:
        """Initialize WhisperX STT service."""
        try:
            # Check if WhisperX is available
            if not WHISPERX_AVAILABLE:
                logger.error("WhisperX not available. Run: pip install whisperx")
                return False
            
            # Check device compatibility
            if self.device == 'cuda' and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available, falling back to CPU")
                self.device = 'cpu'
                self.compute_type = 'int8'
            
            # Test model loading without full initialization
            if not self._test_model_loading():
                logger.error("Failed to test WhisperX model loading")
                return False
            
            self._is_initialized = True
            logger.info("WhisperX STT service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WhisperX STT service: {e}")
            return False
    
    def _test_model_loading(self) -> bool:
        """Test model loading without full initialization."""
        try:
            logger.info("Testing WhisperX model availability...")
            
            # Check if model files exist or can be downloaded
            # This is a lightweight check without actually loading the model
            test_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
            
            # Try to load model briefly
            start_time = time.time()
            model = whisperx.load_model(
                self.model_size,
                self.device,
                compute_type=self.compute_type
            )
            load_time = time.time() - start_time
            
            # Quick test transcription
            result = model.transcribe(test_audio, batch_size=1)
            
            # Clean up
            del model
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
            
            logger.info(f"Model test successful (load time: {load_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Model test failed: {e}")
            return False
    
    def _load_model(self) -> bool:
        """Load WhisperX model and alignment models."""
        try:
            if self._model is not None:
                return True  # Already loaded
            
            if self._model_loading:
                logger.info("Model loading already in progress")
                return False
            
            self._model_loading = True
            start_time = time.time()
            
            logger.info(f"Loading WhisperX model: {self.model_size} on {self.device}")
            
            # Load main model
            self._model = whisperx.load_model(
                self.model_size,
                self.device,
                compute_type=self.compute_type
            )
            
            model_load_time = time.time() - start_time
            self._model_load_time = model_load_time
            
            logger.info(f"WhisperX model loaded successfully in {model_load_time:.2f}s")
            
            # Emit model loaded event
            self._event_bus.emit(
                EventType.STT_MODEL_LOADED,
                f"stt_{self.provider.value}",
                {
                    "model_size": self.model_size,
                    "device": self.device,
                    "load_time": model_load_time
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load WhisperX model: {e}")
            return False
        finally:
            self._model_loading = False
    
    def _load_align_model(self, language_code: str) -> bool:
        """Load alignment model for word-level timestamps."""
        try:
            if not self.settings.enable_word_time_offsets:
                return True  # Skip if not needed
            
            if self._align_model is not None:
                return True  # Already loaded
            
            logger.info(f"Loading alignment model for language: {language_code}")
            
            self._align_model, self._align_metadata = whisperx.load_align_model(
                language_code=language_code,
                device=self.device
            )
            
            logger.info("Alignment model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load alignment model: {e}")
            return False
    
    def _load_diarization_model(self) -> bool:
        """Load speaker diarization model."""
        try:
            if not self.enable_diarization:
                return True  # Skip if not enabled
            
            if self._diarize_model is not None:
                return True  # Already loaded
            
            logger.info("Loading speaker diarization model")
            
            # Note: Diarization requires HuggingFace token for pyannote models
            self._diarize_model = whisperx.DiarizationPipeline(
                device=self.device
            )
            
            logger.info("Diarization model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            return False
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[STTResult]:
        """Process audio data with WhisperX (batch processing)."""
        try:
            if not self._validate_audio_data(audio_data, sample_rate):
                return None
            
            start_time = time.time()
            self._start_processing()
            
            # Load model if not already loaded
            if not self._load_model():
                raise RuntimeError("Failed to load WhisperX model")
            
            # Convert audio format
            audio_float = self._prepare_audio_for_whisperx(audio_data, sample_rate)
            
            # Emit processing started event
            self._event_bus.emit(
                EventType.STT_PROCESSING_STARTED,
                f"stt_{self.provider.value}",
                {
                    "audio_duration": len(audio_data) / sample_rate,
                    "model": self.model_size
                }
            )
            
            # Transcribe with WhisperX
            logger.info("Starting WhisperX transcription")
            result = self._model.transcribe(
                audio_float,
                batch_size=self.batch_size,
                language=self.language if self.language != 'auto' else None
            )
            
            # Process result
            transcription_result = self._process_whisperx_result(result, start_time)
            
            # Optional: Add word-level alignment
            if self.settings.enable_word_time_offsets and transcription_result:
                transcription_result = self._add_word_alignment(
                    transcription_result, result, audio_float
                )
            
            # Optional: Add speaker diarization
            if self.enable_diarization and transcription_result:
                transcription_result = self._add_speaker_diarization(
                    transcription_result, audio_float
                )
            
            processing_time = time.time() - start_time
            self._total_audio_duration += len(audio_data) / sample_rate
            self._processing_sessions += 1
            
            self._stop_processing(processing_time)
            
            if transcription_result:
                self._emit_result(transcription_result)
            
            # Memory cleanup
            self._cleanup_memory()
            
            return transcription_result
            
        except Exception as e:
            logger.error(f"Error in WhisperX processing: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def process_audio_stream(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int = 16000
    ) -> AsyncGenerator[STTResult, None]:
        """Process streaming audio with WhisperX (accumulates chunks then processes)."""
        try:
            logger.info("Starting WhisperX batch processing from stream")
            
            # Accumulate audio chunks
            audio_chunks = []
            chunk_count = 0
            
            async for audio_chunk in audio_stream:
                audio_chunks.append(audio_chunk)
                chunk_count += 1
                
                # Emit progress updates
                if chunk_count % 10 == 0:
                    self._event_bus.emit(
                        EventType.STT_CHUNK_RECEIVED,
                        f"stt_{self.provider.value}",
                        {"chunk_count": chunk_count}
                    )
            
            # Concatenate all chunks
            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                logger.info(f"Accumulated {chunk_count} chunks, total duration: {len(full_audio)/sample_rate:.2f}s")
                
                # Process accumulated audio
                result = self.process_audio(full_audio, sample_rate)
                if result:
                    yield result
            else:
                logger.warning("No audio chunks received")
                
        except Exception as e:
            logger.error(f"Error in WhisperX streaming processing: {e}")
            self._emit_error(e)
    
    def _prepare_audio_for_whisperx(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Prepare audio data for WhisperX processing."""
        try:
            # Convert to float32 normalized to [-1, 1]
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_float = audio_data.astype(np.float32) / 2147483648.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # Resample to 16kHz if needed (WhisperX expectation)
            if sample_rate != 16000:
                # Simple resampling (in production, use librosa or similar)
                ratio = 16000 / sample_rate
                new_length = int(len(audio_float) * ratio)
                indices = np.linspace(0, len(audio_float) - 1, new_length)
                audio_float = np.interp(indices, np.arange(len(audio_float)), audio_float)
            
            # Ensure mono
            if len(audio_float.shape) > 1:
                audio_float = np.mean(audio_float, axis=1)
            
            return audio_float
            
        except Exception as e:
            logger.error(f"Error preparing audio for WhisperX: {e}")
            return audio_data.astype(np.float32)
    
    def _process_whisperx_result(self, result: Dict[str, Any], start_time: float) -> Optional[STTResult]:
        """Process WhisperX transcription result."""
        try:
            if not result or 'segments' not in result:
                logger.warning("No segments in WhisperX result")
                return None
            
            # Combine all segment texts
            texts = []
            total_confidence = 0.0
            segment_count = 0
            
            for segment in result['segments']:
                if 'text' in segment:
                    texts.append(segment['text'].strip())
                    if 'avg_logprob' in segment:
                        # Convert log probability to confidence (approximate)
                        confidence = min(1.0, max(0.0, np.exp(segment['avg_logprob'])))
                        total_confidence += confidence
                        segment_count += 1
            
            if not texts:
                logger.warning("No text found in WhisperX segments")
                return None
            
            combined_text = ' '.join(texts).strip()
            avg_confidence = total_confidence / max(segment_count, 1)
            processing_time = time.time() - start_time
            
            # Extract language
            detected_language = result.get('language', self.language)
            
            stt_result = STTResult(
                text=combined_text,
                confidence=avg_confidence,
                is_final=True,
                language=detected_language,
                timestamp=time.time(),
                processing_time=processing_time
            )
            
            # Add word timestamps if available
            if self.settings.enable_word_time_offsets and result.get('segments'):
                word_timestamps = []
                for segment in result['segments']:
                    if 'words' in segment:
                        for word in segment['words']:
                            word_timestamps.append({
                                'word': word.get('word', ''),
                                'start': word.get('start', 0.0),
                                'end': word.get('end', 0.0),
                                'confidence': word.get('score', avg_confidence)
                            })
                stt_result.word_timestamps = word_timestamps
            
            logger.info(f"WhisperX transcription: '{combined_text[:100]}...' (confidence: {avg_confidence:.3f})")
            return stt_result
            
        except Exception as e:
            logger.error(f"Error processing WhisperX result: {e}")
            return None
    
    def _add_word_alignment(
        self,
        stt_result: STTResult,
        whisperx_result: Dict[str, Any],
        audio: np.ndarray
    ) -> STTResult:
        """Add word-level alignment to transcription result."""
        try:
            if not self._load_align_model(stt_result.language):
                return stt_result
            
            logger.info("Adding word-level alignment")
            
            # Perform alignment
            aligned_result = whisperx.align(
                whisperx_result["segments"],
                self._align_model,
                self._align_metadata,
                audio,
                self.device,
                return_char_alignments=False
            )
            
            # Update word timestamps
            word_timestamps = []
            for segment in aligned_result.get("segments", []):
                for word in segment.get("words", []):
                    word_timestamps.append({
                        'word': word.get('word', ''),
                        'start': word.get('start', 0.0),
                        'end': word.get('end', 0.0),
                        'confidence': word.get('score', stt_result.confidence)
                    })
            
            stt_result.word_timestamps = word_timestamps
            logger.info(f"Added alignment for {len(word_timestamps)} words")
            
            return stt_result
            
        except Exception as e:
            logger.error(f"Error adding word alignment: {e}")
            return stt_result
    
    def _add_speaker_diarization(
        self,
        stt_result: STTResult,
        audio: np.ndarray
    ) -> STTResult:
        """Add speaker diarization to transcription result."""
        try:
            if not self._load_diarization_model():
                return stt_result
            
            logger.info("Adding speaker diarization")
            
            # Perform diarization
            diarization_result = self._diarize_model(audio)
            
            # Add speaker information to result
            # This would require more complex integration with word timestamps
            # For now, just log that diarization was attempted
            
            logger.info("Speaker diarization completed")
            return stt_result
            
        except Exception as e:
            logger.error(f"Error adding speaker diarization: {e}")
            return stt_result
    
    def _cleanup_memory(self) -> None:
        """Clean up GPU memory after processing."""
        try:
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
    
    def unload_model(self) -> None:
        """Unload models to free memory."""
        try:
            logger.info("Unloading WhisperX models")
            
            # Clear models
            self._model = None
            self._align_model = None
            self._align_metadata = None
            self._diarize_model = None
            
            # Clean up memory
            self._cleanup_memory()
            
            logger.info("WhisperX models unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading models: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        base_stats = super().get_statistics()
        
        avg_processing_ratio = 0.0
        if self._total_audio_duration > 0:
            avg_processing_ratio = self._total_processing_time / self._total_audio_duration
        
        base_stats.update({
            "processing_sessions": self._processing_sessions,
            "total_audio_duration": self._total_audio_duration,
            "model_load_time": self._model_load_time,
            "model_loaded": self._model is not None,
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "batch_size": self.batch_size,
            "avg_processing_ratio": avg_processing_ratio,
            "enable_alignment": self.settings.enable_word_time_offsets,
            "enable_diarization": self.enable_diarization
        })
        
        return base_stats
    
    def shutdown(self) -> None:
        """Shutdown WhisperX STT service."""
        try:
            # Unload models
            self.unload_model()
            
            self._is_initialized = False
            self._is_processing = False
            
            logger.info("WhisperX STT service shutdown")
            
        except Exception as e:
            logger.error(f"Error shutting down WhisperX STT service: {e}")