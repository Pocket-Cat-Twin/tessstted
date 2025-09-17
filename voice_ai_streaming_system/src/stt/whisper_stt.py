"""OpenAI Whisper local STT implementation."""

import time
import asyncio
import tempfile
import os
from typing import Optional, AsyncGenerator, Dict, Any
import logging
import numpy as np

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("OpenAI Whisper not available")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available - Whisper will use CPU only")

try:
    from .base_stt import BaseSTTService, STTResult, STTProvider
    from ..config.settings import STTSettings
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from stt.base_stt import BaseSTTService, STTResult, STTProvider
    from config.settings import STTSettings

logger = logging.getLogger(__name__)


class WhisperSTTService(BaseSTTService):
    """OpenAI Whisper local STT implementation."""
    
    def __init__(self, settings: STTSettings, **kwargs):
        super().__init__(settings, **kwargs)
        
        self._model: Optional[whisper.Whisper] = None
        self._model_name = "base"  # Default model
        self._device = "cpu"  # Default device
        
        # Whisper-specific settings
        self._temperature = 0.0  # For deterministic output
        self._no_speech_threshold = 0.6
        self._logprob_threshold = -1.0
        self._compression_ratio_threshold = 2.4
        
        # Supported models by size and performance
        self._available_models = {
            "tiny": {"size": "39 MB", "speed": "~32x", "accuracy": "lowest"},
            "base": {"size": "74 MB", "speed": "~16x", "accuracy": "low"},
            "small": {"size": "244 MB", "speed": "~6x", "accuracy": "medium"},
            "medium": {"size": "769 MB", "speed": "~2x", "accuracy": "high"},
            "large": {"size": "1550 MB", "speed": "~1x", "accuracy": "highest"},
            "large-v2": {"size": "1550 MB", "speed": "~1x", "accuracy": "highest"},
            "large-v3": {"size": "1550 MB", "speed": "~1x", "accuracy": "highest"}
        }
        
        logger.info("Whisper STT service created")
    
    @property
    def provider(self) -> STTProvider:
        return STTProvider.WHISPER_LOCAL
    
    def initialize(self) -> bool:
        """Initialize Whisper model."""
        try:
            if not WHISPER_AVAILABLE:
                logger.error("OpenAI Whisper not available")
                return False
            
            # Determine device
            if TORCH_AVAILABLE and torch.cuda.is_available():
                self._device = "cuda"
                logger.info("Using CUDA for Whisper")
            else:
                self._device = "cpu"
                logger.info("Using CPU for Whisper")
            
            # Load model
            logger.info(f"Loading Whisper model: {self._model_name}")
            self._model = whisper.load_model(self._model_name, device=self._device)
            
            # Test model with silence
            try:
                test_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
                result = self._model.transcribe(
                    test_audio,
                    language=self._get_whisper_language_code(),
                    temperature=self._temperature
                )
                logger.info("Whisper model test successful")
                
            except Exception as e:
                logger.warning(f"Whisper model test failed: {e}")
                # Continue anyway, might work with real audio
            
            self._is_initialized = True
            logger.info(f"Whisper STT service initialized successfully with {self._model_name} model")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Whisper STT service: {e}")
            self._emit_error(e)
            return False
    
    def set_model(self, model_name: str) -> bool:
        """Set Whisper model.
        
        Args:
            model_name: Model name (tiny, base, small, medium, large, large-v2, large-v3)
            
        Returns:
            True if model was set successfully
        """
        try:
            if model_name not in self._available_models:
                logger.error(f"Invalid Whisper model: {model_name}")
                return False
            
            if self._model_name == model_name and self._is_initialized:
                logger.info(f"Whisper model {model_name} already loaded")
                return True
            
            self._model_name = model_name
            
            # Reload model if already initialized
            if self._is_initialized:
                logger.info(f"Reloading Whisper model: {model_name}")
                self._model = whisper.load_model(model_name, device=self._device)
            
            logger.info(f"Whisper model set to: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Whisper model: {e}")
            return False
    
    def _get_whisper_language_code(self) -> Optional[str]:
        """Convert STT language code to Whisper language code."""
        # Whisper uses ISO 639-1 codes
        language_mapping = {
            'en-US': 'en', 'en-GB': 'en', 'en-AU': 'en', 'en-CA': 'en',
            'ru-RU': 'ru', 'ru': 'ru',
            'es-ES': 'es', 'es-US': 'es', 'es-MX': 'es',
            'fr-FR': 'fr', 'fr-CA': 'fr',
            'de-DE': 'de', 'de-AT': 'de', 'de-CH': 'de',
            'it-IT': 'it',
            'pt-BR': 'pt', 'pt-PT': 'pt',
            'ja-JP': 'ja',
            'ko-KR': 'ko',
            'zh-CN': 'zh', 'zh-TW': 'zh',
            'ar-EG': 'ar', 'ar-SA': 'ar',
            'hi-IN': 'hi',
            'th-TH': 'th',
            'tr-TR': 'tr',
            'pl-PL': 'pl',
            'nl-NL': 'nl',
            'sv-SE': 'sv',
            'da-DK': 'da',
            'no-NO': 'no', 'nb-NO': 'no',
            'fi-FI': 'fi'
        }
        
        language_code = self.settings.language_code
        return language_mapping.get(language_code, language_code.split('-')[0] if '-' in language_code else language_code)
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[STTResult]:
        """Process audio using Whisper."""
        try:
            if not self._is_initialized or not self._model:
                logger.error("Whisper STT service not initialized")
                return None
            
            if not self._validate_audio_data(audio_data, sample_rate):
                return None
            
            start_time = time.time()
            self._start_processing()
            
            # Prepare audio data for Whisper
            # Whisper expects float32 audio normalized to [-1, 1]
            if audio_data.dtype == np.int16:
                # Convert int16 to float32
                audio_float = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_float = audio_data.astype(np.float32) / 2147483648.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # Resample to 16kHz if needed (Whisper requirement)
            if sample_rate != 16000:
                audio_float = self._convert_audio_format(audio_float, 16000, sample_rate)
            
            # Get language code
            language = self._get_whisper_language_code()
            
            # Transcribe audio
            result = self._model.transcribe(
                audio_float,
                language=language,
                temperature=self._temperature,
                no_speech_threshold=self._no_speech_threshold,
                logprob_threshold=self._logprob_threshold,
                compression_ratio_threshold=self._compression_ratio_threshold,
                word_timestamps=self.settings.enable_word_time_offsets
            )
            
            processing_time = time.time() - start_time
            
            # Extract results
            text = result.get("text", "").strip()
            
            # Calculate confidence from segments if available
            confidence = 1.0
            if "segments" in result and result["segments"]:
                # Average confidence from segments
                segment_probs = []
                for segment in result["segments"]:
                    if "avg_logprob" in segment:
                        # Convert log probability to confidence (approximate)
                        prob = np.exp(segment["avg_logprob"])
                        segment_probs.append(prob)
                
                if segment_probs:
                    confidence = np.mean(segment_probs)
            
            # Extract word timestamps if requested
            word_timestamps = None
            if self.settings.enable_word_time_offsets and "segments" in result:
                word_timestamps = []
                for segment in result["segments"]:
                    if "words" in segment:
                        for word in segment["words"]:
                            word_timestamps.append({
                                "word": word.get("word", "").strip(),
                                "start_time": word.get("start", 0.0),
                                "end_time": word.get("end", 0.0)
                            })
            
            # Detect language if auto-detection was used
            detected_language = result.get("language", language or self.settings.language_code)
            
            stt_result = STTResult(
                text=text,
                confidence=confidence,
                is_final=True,
                language=detected_language,
                timestamp=time.time(),
                processing_time=processing_time,
                word_timestamps=word_timestamps
            )
            
            logger.debug(f"Whisper STT result: '{stt_result.text}' (confidence: {stt_result.confidence:.2f})")
            
            self._stop_processing(processing_time)
            self._emit_result(stt_result)
            
            return stt_result
            
        except Exception as e:
            logger.error(f"Error in Whisper STT processing: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def process_audio_stream(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int = 16000
    ) -> AsyncGenerator[STTResult, None]:
        """Process streaming audio using Whisper.
        
        Note: Whisper is not designed for real-time streaming, so this
        implementation buffers audio chunks and processes them in segments.
        """
        try:
            if not self._is_initialized or not self._model:
                logger.error("Whisper STT service not initialized")
                return
            
            logger.debug("Starting Whisper streaming recognition (buffered)")
            
            # Buffer settings
            buffer_duration = 5.0  # Process every 5 seconds
            buffer_size = int(buffer_duration * sample_rate)
            audio_buffer = []
            
            async for audio_chunk in audio_stream:
                if audio_chunk.size > 0:
                    # Add to buffer
                    audio_buffer.extend(audio_chunk.tolist())
                    
                    # Process when buffer is full
                    if len(audio_buffer) >= buffer_size:
                        # Convert buffer to numpy array
                        buffer_array = np.array(audio_buffer[:buffer_size], dtype=audio_chunk.dtype)
                        
                        # Process the buffer
                        result = self.process_audio(buffer_array, sample_rate)
                        if result and result.text.strip():
                            # Mark as partial result for streaming
                            result.is_final = False
                            logger.debug(f"Whisper streaming result: '{result.text}'")
                            yield result
                        
                        # Remove processed samples from buffer (with overlap)
                        overlap_size = buffer_size // 4  # 25% overlap
                        audio_buffer = audio_buffer[buffer_size - overlap_size:]
            
            # Process remaining buffer
            if len(audio_buffer) > sample_rate:  # At least 1 second of audio
                buffer_array = np.array(audio_buffer, dtype=np.float32)
                result = self.process_audio(buffer_array, sample_rate)
                if result and result.text.strip():
                    result.is_final = True  # Mark final result
                    logger.debug(f"Whisper final streaming result: '{result.text}'")
                    yield result
                    
        except Exception as e:
            logger.error(f"Error in Whisper STT streaming: {e}")
            self._emit_error(e)
    
    def transcribe_file(self, file_path: str) -> Optional[STTResult]:
        """Transcribe audio file directly.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            STT result or None if processing failed
        """
        try:
            if not self._is_initialized or not self._model:
                logger.error("Whisper STT service not initialized")
                return None
            
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found: {file_path}")
                return None
            
            start_time = time.time()
            self._start_processing()
            
            # Get language code
            language = self._get_whisper_language_code()
            
            # Transcribe file directly
            result = self._model.transcribe(
                file_path,
                language=language,
                temperature=self._temperature,
                word_timestamps=self.settings.enable_word_time_offsets
            )
            
            processing_time = time.time() - start_time
            
            # Process results (similar to process_audio)
            text = result.get("text", "").strip()
            
            # Calculate confidence
            confidence = 1.0
            if "segments" in result and result["segments"]:
                segment_probs = []
                for segment in result["segments"]:
                    if "avg_logprob" in segment:
                        prob = np.exp(segment["avg_logprob"])
                        segment_probs.append(prob)
                if segment_probs:
                    confidence = np.mean(segment_probs)
            
            # Extract word timestamps
            word_timestamps = None
            if self.settings.enable_word_time_offsets and "segments" in result:
                word_timestamps = []
                for segment in result["segments"]:
                    if "words" in segment:
                        for word in segment["words"]:
                            word_timestamps.append({
                                "word": word.get("word", "").strip(),
                                "start_time": word.get("start", 0.0),
                                "end_time": word.get("end", 0.0)
                            })
            
            detected_language = result.get("language", language or self.settings.language_code)
            
            stt_result = STTResult(
                text=text,
                confidence=confidence,
                is_final=True,
                language=detected_language,
                timestamp=time.time(),
                processing_time=processing_time,
                word_timestamps=word_timestamps
            )
            
            self._stop_processing(processing_time)
            self._emit_result(stt_result)
            
            logger.info(f"Whisper file transcription completed: {file_path}")
            return stt_result
            
        except Exception as e:
            logger.error(f"Error transcribing file with Whisper: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    def get_available_models(self) -> Dict[str, Dict[str, str]]:
        """Get available Whisper models.
        
        Returns:
            Dictionary of model names and their specifications
        """
        return self._available_models.copy()
    
    def get_current_model(self) -> str:
        """Get current model name."""
        return self._model_name
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes.
        
        Returns:
            List of supported language codes
        """
        # Whisper supports many languages
        return [
            'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl', 'ca', 'nl',
            'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 'he', 'uk', 'el', 'ms', 'cs', 'ro',
            'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy',
            'sk', 'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk', 'br', 'eu',
            'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw', 'gl', 'mr', 'pa', 'si', 'km',
            'sn', 'yo', 'so', 'af', 'oc', 'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo',
            'uz', 'fo', 'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg',
            'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su'
        ]
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities.
        
        Returns:
            Dictionary with service information
        """
        return {
            "provider": self.provider.value,
            "name": "OpenAI Whisper (Local)",
            "available": WHISPER_AVAILABLE,
            "initialized": self._is_initialized,
            "features": {
                "streaming": True,  # Buffered streaming
                "word_timestamps": True,
                "language_detection": True,
                "file_transcription": True,
                "offline": True,
                "multiple_models": True
            },
            "supported_formats": ["WAV", "MP3", "MP4", "FLAC", "M4A", "OGG"],
            "supported_sample_rates": "8kHz-48kHz (auto-converted to 16kHz)",
            "supported_languages": len(self.get_supported_languages()),
            "configuration": {
                "model": self._model_name,
                "device": self._device,
                "language": self.settings.language_code,
                "word_timestamps": self.settings.enable_word_time_offsets
            },
            "models": self._available_models
        }
    
    def shutdown(self) -> None:
        """Shutdown Whisper STT service."""
        try:
            self._is_initialized = False
            self._is_processing = False
            
            # Clear model from memory
            if self._model:
                del self._model
                self._model = None
                
                # Clear CUDA cache if using GPU
                if TORCH_AVAILABLE and self._device == "cuda":
                    torch.cuda.empty_cache()
            
            logger.info("Whisper STT service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during Whisper STT shutdown: {e}")