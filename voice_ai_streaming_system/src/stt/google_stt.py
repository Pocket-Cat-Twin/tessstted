"""Google Cloud Speech-to-Text service implementation."""

import time
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
import logging
import numpy as np

try:
    from google.cloud import speech
    from google.cloud.speech import RecognitionConfig, StreamingRecognitionConfig
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False
    logging.warning("Google Cloud Speech not available")

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


class GoogleSTTService(BaseSTTService):
    """Google Cloud Speech-to-Text service."""
    
    def __init__(self, settings: STTSettings, **kwargs):
        super().__init__(settings, **kwargs)
        
        self._client: Optional[speech.SpeechClient] = None
        self._streaming_config: Optional[StreamingRecognitionConfig] = None
        self._recognition_config: Optional[RecognitionConfig] = None
        
        # API settings
        self._max_alternatives = self.settings.max_alternatives
        self._enable_word_time_offsets = self.settings.enable_word_time_offsets
        self._enable_profanity_filter = self.settings.enable_profanity_filter
        
        logger.info("Google STT service created")
    
    @property
    def provider(self) -> STTProvider:
        return STTProvider.GOOGLE_CLOUD
    
    def initialize(self) -> bool:
        """Initialize Google Cloud Speech client."""
        try:
            if not GOOGLE_SPEECH_AVAILABLE:
                logger.error("Google Cloud Speech library not available")
                return False
            
            # Initialize client
            self._client = speech.SpeechClient()
            
            # Setup recognition config
            self._recognition_config = RecognitionConfig(
                encoding=RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,  # Standard rate for most applications
                language_code=self.settings.language_code,
                max_alternatives=self._max_alternatives,
                enable_word_time_offsets=self._enable_word_time_offsets,
                profanity_filter=self._enable_profanity_filter,
                enable_automatic_punctuation=True,
                use_enhanced=True,  # Use enhanced model if available
                model='latest_long'  # Use latest long-form model
            )
            
            # Setup streaming config
            self._streaming_config = StreamingRecognitionConfig(
                config=self._recognition_config,
                interim_results=True,
                single_utterance=False
            )
            
            # Test connection
            try:
                # Simple test to verify credentials and connection
                test_audio = np.zeros(1600, dtype=np.int16)  # 0.1s of silence at 16kHz
                test_bytes = test_audio.tobytes()
                
                audio = speech.RecognitionAudio(content=test_bytes)
                response = self._client.recognize(
                    config=self._recognition_config,
                    audio=audio
                )
                
                logger.info("Google Cloud Speech connection test successful")
                
            except Exception as e:
                logger.warning(f"Google Cloud Speech connection test failed: {e}")
                # Continue anyway, might work with real audio
            
            self._is_initialized = True
            logger.info("Google STT service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Google STT service: {e}")
            self._emit_error(e)
            return False
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[STTResult]:
        """Process audio using Google Cloud Speech."""
        try:
            if not self._is_initialized or not self._client:
                logger.error("Google STT service not initialized")
                return None
            
            if not self._validate_audio_data(audio_data, sample_rate):
                return None
            
            start_time = time.time()
            self._start_processing()
            
            # Prepare audio data
            audio_bytes, final_sample_rate = self._prepare_audio_for_service(audio_data, sample_rate)
            
            # Update config sample rate if needed
            if final_sample_rate != self._recognition_config.sample_rate_hertz:
                config = RecognitionConfig(
                    encoding=RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=final_sample_rate,
                    language_code=self.settings.language_code,
                    max_alternatives=self._max_alternatives,
                    enable_word_time_offsets=self._enable_word_time_offsets,
                    profanity_filter=self._enable_profanity_filter,
                    enable_automatic_punctuation=True,
                    use_enhanced=True,
                    model='latest_long'
                )
            else:
                config = self._recognition_config
            
            # Create recognition request
            audio = speech.RecognitionAudio(content=audio_bytes)
            
            # Perform recognition
            response = self._client.recognize(config=config, audio=audio)
            
            processing_time = time.time() - start_time
            
            # Process results
            if response.results:
                # Get best result
                best_result = response.results[0]
                alternative = best_result.alternatives[0]
                
                # Extract word timestamps if available
                word_timestamps = []
                if self._enable_word_time_offsets and hasattr(alternative, 'words'):
                    for word in alternative.words:
                        word_timestamps.append({
                            'word': word.word,
                            'start_time': word.start_time.total_seconds(),
                            'end_time': word.end_time.total_seconds()
                        })
                
                # Extract alternatives
                alternatives = []
                if len(best_result.alternatives) > 1:
                    alternatives = [alt.transcript for alt in best_result.alternatives[1:]]
                
                result = STTResult(
                    text=alternative.transcript.strip(),
                    confidence=alternative.confidence,
                    is_final=True,
                    language=self.settings.language_code,
                    timestamp=time.time(),
                    processing_time=processing_time,
                    alternatives=alternatives if alternatives else None,
                    word_timestamps=word_timestamps if word_timestamps else None
                )
                
                logger.debug(f"Google STT result: '{result.text}' (confidence: {result.confidence:.2f})")
                
            else:
                # No results - return empty result
                result = STTResult(
                    text="",
                    confidence=0.0,
                    is_final=True,
                    language=self.settings.language_code,
                    timestamp=time.time(),
                    processing_time=processing_time
                )
                
                logger.debug("Google STT: No speech detected")
            
            self._stop_processing(processing_time)
            self._emit_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Google STT processing: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def process_audio_stream(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int = 16000
    ) -> AsyncGenerator[STTResult, None]:
        """Process streaming audio using Google Cloud Speech."""
        try:
            if not self._is_initialized or not self._client:
                logger.error("Google STT service not initialized")
                return
            
            logger.debug("Starting Google Cloud Speech streaming recognition")
            
            # Create streaming recognition request generator
            async def request_generator():
                # First request with config
                yield speech.StreamingRecognizeRequest(
                    streaming_config=self._streaming_config
                )
                
                # Stream audio data
                async for audio_chunk in audio_stream:
                    if audio_chunk.size > 0:
                        audio_bytes, _ = self._prepare_audio_for_service(audio_chunk, sample_rate)
                        yield speech.StreamingRecognizeRequest(audio_content=audio_bytes)
            
            # Process streaming requests
            try:
                responses = self._client.streaming_recognize(request_generator())
                
                for response in responses:
                    # Check for errors
                    if response.error:
                        logger.error(f"Google STT streaming error: {response.error}")
                        continue
                    
                    # Process results
                    for result in response.results:
                        if result.alternatives:
                            alternative = result.alternatives[0]
                            
                            # Extract word timestamps for final results
                            word_timestamps = []
                            if (result.is_final and self._enable_word_time_offsets 
                                and hasattr(alternative, 'words')):
                                for word in alternative.words:
                                    word_timestamps.append({
                                        'word': word.word,
                                        'start_time': word.start_time.total_seconds(),
                                        'end_time': word.end_time.total_seconds()
                                    })
                            
                            # Create STT result
                            stt_result = STTResult(
                                text=alternative.transcript.strip(),
                                confidence=alternative.confidence,
                                is_final=result.is_final,
                                language=self.settings.language_code,
                                timestamp=time.time(),
                                word_timestamps=word_timestamps if word_timestamps else None
                            )
                            
                            logger.debug(
                                f"Google STT streaming result: '{stt_result.text}' "
                                f"(final: {stt_result.is_final}, confidence: {stt_result.confidence:.2f})"
                            )
                            
                            yield stt_result
                            self._emit_result(stt_result)
                
            except Exception as e:
                logger.error(f"Error in Google STT streaming: {e}")
                self._emit_error(e)
                
        except Exception as e:
            logger.error(f"Error setting up Google STT streaming: {e}")
            self._emit_error(e)
    
    def set_language(self, language_code: str) -> bool:
        """Set recognition language.
        
        Args:
            language_code: Language code (e.g., 'en-US', 'ru-RU')
            
        Returns:
            True if language was set successfully
        """
        try:
            # Update settings
            self.settings.language_code = language_code
            
            # Update recognition config
            if self._recognition_config:
                self._recognition_config.language_code = language_code
            
            # Update streaming config
            if self._streaming_config and self._recognition_config:
                self._streaming_config.config = self._recognition_config
            
            logger.info(f"Google STT language set to: {language_code}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Google STT language: {e}")
            return False
    
    def set_model(self, model: str) -> bool:
        """Set recognition model.
        
        Args:
            model: Model name (e.g., 'latest_long', 'latest_short', 'phone_call')
            
        Returns:
            True if model was set successfully
        """
        try:
            if self._recognition_config:
                self._recognition_config.model = model
                
                # Update streaming config
                if self._streaming_config:
                    self._streaming_config.config = self._recognition_config
                
                logger.info(f"Google STT model set to: {model}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to set Google STT model: {e}")
            return False
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes.
        
        Returns:
            List of supported language codes
        """
        # Common Google Cloud Speech supported languages
        return [
            'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-IN',
            'ru-RU', 'ru', 
            'es-ES', 'es-US', 'es-MX',
            'fr-FR', 'fr-CA',
            'de-DE', 'de-AT', 'de-CH',
            'it-IT',
            'pt-BR', 'pt-PT',
            'ja-JP',
            'ko-KR',
            'zh-CN', 'zh-TW',
            'ar-EG', 'ar-SA',
            'hi-IN',
            'th-TH',
            'tr-TR',
            'pl-PL',
            'nl-NL',
            'sv-SE',
            'da-DK',
            'no-NO',
            'fi-FI'
        ]
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities.
        
        Returns:
            Dictionary with service information
        """
        return {
            "provider": self.provider.value,
            "name": "Google Cloud Speech-to-Text",
            "available": GOOGLE_SPEECH_AVAILABLE,
            "initialized": self._is_initialized,
            "features": {
                "streaming": True,
                "word_timestamps": True,
                "multiple_alternatives": True,
                "punctuation": True,
                "profanity_filter": True,
                "enhanced_models": True,
                "real_time": True
            },
            "supported_formats": ["LINEAR16", "FLAC", "MULAW", "AMR", "AMR_WB"],
            "supported_sample_rates": [8000, 16000, 22050, 32000, 44100, 48000],
            "supported_languages": len(self.get_supported_languages()),
            "configuration": {
                "language": self.settings.language_code,
                "max_alternatives": self._max_alternatives,
                "word_time_offsets": self._enable_word_time_offsets,
                "profanity_filter": self._enable_profanity_filter
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown Google STT service."""
        try:
            self._is_initialized = False
            self._is_processing = False
            
            # Close client connections
            if self._client:
                # Google client doesn't have explicit close method
                self._client = None
            
            self._recognition_config = None
            self._streaming_config = None
            
            logger.info("Google STT service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during Google STT shutdown: {e}")