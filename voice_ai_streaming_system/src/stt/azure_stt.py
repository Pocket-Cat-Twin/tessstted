"""Azure Speech Services STT implementation."""

import time
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
import logging
import numpy as np

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    AZURE_SPEECH_AVAILABLE = False
    logging.warning("Azure Speech SDK not available")

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


class AzureSTTService(BaseSTTService):
    """Azure Speech Services STT implementation."""
    
    def __init__(self, settings: STTSettings, **kwargs):
        super().__init__(settings, **kwargs)
        
        self._speech_config: Optional[speechsdk.SpeechConfig] = None
        self._audio_config: Optional[speechsdk.AudioConfig] = None
        self._speech_recognizer: Optional[speechsdk.SpeechRecognizer] = None
        
        # API credentials (should be set in configuration)
        self._subscription_key: Optional[str] = None
        self._region: Optional[str] = None
        self._endpoint: Optional[str] = None
        
        # Recognition settings
        self._continuous_recognition = False
        
        logger.info("Azure STT service created")
    
    @property
    def provider(self) -> STTProvider:
        return STTProvider.AZURE_SPEECH
    
    def initialize(self) -> bool:
        """Initialize Azure Speech service."""
        try:
            if not AZURE_SPEECH_AVAILABLE:
                logger.error("Azure Speech SDK not available")
                return False
            
            # Get credentials from configuration
            # These should be set in the config system
            self._subscription_key = getattr(self.settings, 'azure_subscription_key', None)
            self._region = getattr(self.settings, 'azure_region', 'eastus')
            self._endpoint = getattr(self.settings, 'azure_endpoint', None)
            
            if not self._subscription_key:
                logger.error("Azure subscription key not configured")
                return False
            
            # Create speech config
            if self._endpoint:
                self._speech_config = speechsdk.SpeechConfig(
                    subscription=self._subscription_key,
                    endpoint=self._endpoint
                )
            else:
                self._speech_config = speechsdk.SpeechConfig(
                    subscription=self._subscription_key,
                    region=self._region
                )
            
            # Configure speech settings
            self._speech_config.speech_recognition_language = self.settings.language_code
            self._speech_config.enable_dictation()
            
            # Set output format
            self._speech_config.output_format = speechsdk.OutputFormat.Detailed
            
            # Enable profanity filter if configured
            if self.settings.enable_profanity_filter:
                self._speech_config.set_profanity(speechsdk.ProfanityOption.Masked)
            else:
                self._speech_config.set_profanity(speechsdk.ProfanityOption.Raw)
            
            # Test connection with a simple recognition
            try:
                # Create a simple audio config for testing
                test_audio_config = speechsdk.AudioConfig(use_default_microphone=True)
                test_recognizer = speechsdk.SpeechRecognizer(
                    speech_config=self._speech_config,
                    audio_config=test_audio_config
                )
                
                # This doesn't actually start recognition, just validates config
                logger.info("Azure Speech configuration validated")
                
            except Exception as e:
                logger.warning(f"Azure Speech configuration test failed: {e}")
                # Continue anyway, might work with actual audio
            
            self._is_initialized = True
            logger.info("Azure STT service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure STT service: {e}")
            self._emit_error(e)
            return False
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[STTResult]:
        """Process audio using Azure Speech Services."""
        try:
            if not self._is_initialized or not self._speech_config:
                logger.error("Azure STT service not initialized")
                return None
            
            if not self._validate_audio_data(audio_data, sample_rate):
                return None
            
            start_time = time.time()
            self._start_processing()
            
            # Prepare audio data
            audio_bytes, final_sample_rate = self._prepare_audio_for_service(audio_data, sample_rate)
            
            # Create audio stream from bytes
            audio_stream = speechsdk.audio.PullAudioInputStream(
                pull_stream_callback=None,
                stream_format=speechsdk.audio.AudioStreamFormat(
                    samples_per_second=final_sample_rate,
                    bits_per_sample=16,
                    channels=1
                )
            )
            
            # Write audio data to stream
            audio_stream.write(audio_bytes)
            audio_stream.close()
            
            # Create audio config from stream
            audio_config = speechsdk.AudioConfig(stream=audio_stream)
            
            # Create recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self._speech_config,
                audio_config=audio_config
            )
            
            # Perform recognition
            result = recognizer.recognize_once()
            
            processing_time = time.time() - start_time
            
            # Process result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Get detailed results if available
                confidence = 1.0  # Azure doesn't always provide confidence in simple recognition
                
                # Try to extract confidence from detailed results
                if hasattr(result, 'json') and result.json:
                    try:
                        import json
                        detailed = json.loads(result.json)
                        if 'NBest' in detailed and detailed['NBest']:
                            confidence = detailed['NBest'][0].get('Confidence', 1.0)
                    except Exception as e:
                        logger.debug(f"Could not parse detailed results: {e}")
                
                stt_result = STTResult(
                    text=result.text.strip(),
                    confidence=confidence,
                    is_final=True,
                    language=self.settings.language_code,
                    timestamp=time.time(),
                    processing_time=processing_time
                )
                
                logger.debug(f"Azure STT result: '{stt_result.text}' (confidence: {stt_result.confidence:.2f})")
                
            elif result.reason == speechsdk.ResultReason.NoMatch:
                # No speech detected
                stt_result = STTResult(
                    text="",
                    confidence=0.0,
                    is_final=True,
                    language=self.settings.language_code,
                    timestamp=time.time(),
                    processing_time=processing_time
                )
                
                logger.debug("Azure STT: No speech detected")
                
            else:
                # Error occurred
                error_msg = f"Azure STT recognition failed: {result.reason}"
                if hasattr(result, 'error_details'):
                    error_msg += f" - {result.error_details}"
                
                logger.error(error_msg)
                raise Exception(error_msg)
            
            self._stop_processing(processing_time)
            self._emit_result(stt_result)
            
            return stt_result
            
        except Exception as e:
            logger.error(f"Error in Azure STT processing: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def process_audio_stream(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int = 16000
    ) -> AsyncGenerator[STTResult, None]:
        """Process streaming audio using Azure Speech Services."""
        try:
            if not self._is_initialized or not self._speech_config:
                logger.error("Azure STT service not initialized")
                return
            
            logger.debug("Starting Azure Speech streaming recognition")
            
            # Create push audio input stream
            push_stream = speechsdk.audio.PushAudioInputStream(
                stream_format=speechsdk.audio.AudioStreamFormat(
                    samples_per_second=16000,  # Azure prefers 16kHz
                    bits_per_sample=16,
                    channels=1
                )
            )
            
            audio_config = speechsdk.AudioConfig(stream=push_stream)
            
            # Create recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self._speech_config,
                audio_config=audio_config
            )
            
            # Setup event handlers
            results_queue = asyncio.Queue()
            
            def recognized_handler(evt):
                """Handle recognized speech events."""
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    result = STTResult(
                        text=evt.result.text.strip(),
                        confidence=1.0,  # Azure doesn't provide confidence in streaming
                        is_final=True,
                        language=self.settings.language_code,
                        timestamp=time.time()
                    )
                    asyncio.create_task(results_queue.put(result))
            
            def recognizing_handler(evt):
                """Handle partial recognition events."""
                if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
                    result = STTResult(
                        text=evt.result.text.strip(),
                        confidence=0.5,  # Lower confidence for partial results
                        is_final=False,
                        language=self.settings.language_code,
                        timestamp=time.time()
                    )
                    asyncio.create_task(results_queue.put(result))
            
            def error_handler(evt):
                """Handle error events."""
                logger.error(f"Azure STT streaming error: {evt}")
            
            # Connect event handlers
            recognizer.recognized.connect(recognized_handler)
            recognizer.recognizing.connect(recognizing_handler)
            recognizer.session_stopped.connect(error_handler)
            recognizer.canceled.connect(error_handler)
            
            # Start continuous recognition
            recognizer.start_continuous_recognition()
            
            try:
                # Process audio stream
                async def audio_feeder():
                    """Feed audio data to the push stream."""
                    async for audio_chunk in audio_stream:
                        if audio_chunk.size > 0:
                            audio_bytes, _ = self._prepare_audio_for_service(audio_chunk, sample_rate)
                            push_stream.write(audio_bytes)
                
                # Start audio feeding task
                audio_task = asyncio.create_task(audio_feeder())
                
                # Yield results as they come
                while not audio_task.done():
                    try:
                        # Wait for result with timeout
                        result = await asyncio.wait_for(results_queue.get(), timeout=0.1)
                        
                        logger.debug(
                            f"Azure STT streaming result: '{result.text}' "
                            f"(final: {result.is_final}, confidence: {result.confidence:.2f})"
                        )
                        
                        yield result
                        self._emit_result(result)
                        
                    except asyncio.TimeoutError:
                        # No result available, continue
                        continue
                
                # Wait for audio feeding to complete
                await audio_task
                
                # Get any remaining results
                while not results_queue.empty():
                    result = await results_queue.get()
                    yield result
                    self._emit_result(result)
                    
            finally:
                # Stop recognition and close stream
                recognizer.stop_continuous_recognition()
                push_stream.close()
                
        except Exception as e:
            logger.error(f"Error in Azure STT streaming: {e}")
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
            
            # Update speech config
            if self._speech_config:
                self._speech_config.speech_recognition_language = language_code
            
            logger.info(f"Azure STT language set to: {language_code}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Azure STT language: {e}")
            return False
    
    def set_endpoint_id(self, endpoint_id: str) -> bool:
        """Set custom speech endpoint ID.
        
        Args:
            endpoint_id: Custom endpoint ID for specialized models
            
        Returns:
            True if endpoint was set successfully
        """
        try:
            if self._speech_config:
                self._speech_config.endpoint_id = endpoint_id
                logger.info(f"Azure STT endpoint ID set to: {endpoint_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to set Azure STT endpoint ID: {e}")
            return False
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes.
        
        Returns:
            List of supported language codes
        """
        # Common Azure Speech Services supported languages
        return [
            'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-IN', 'en-NZ', 'en-ZA',
            'ru-RU',
            'es-ES', 'es-US', 'es-MX', 'es-AR', 'es-CL', 'es-CO',
            'fr-FR', 'fr-CA', 'fr-CH', 'fr-BE',
            'de-DE', 'de-AT', 'de-CH',
            'it-IT',
            'pt-BR', 'pt-PT',
            'ja-JP',
            'ko-KR',
            'zh-CN', 'zh-TW', 'zh-HK',
            'ar-EG', 'ar-SA', 'ar-AE', 'ar-BH', 'ar-DZ', 'ar-IQ', 'ar-JO',
            'hi-IN',
            'th-TH',
            'tr-TR',
            'pl-PL',
            'nl-NL', 'nl-BE',
            'sv-SE',
            'da-DK',
            'nb-NO',
            'fi-FI',
            'he-IL',
            'hu-HU',
            'cs-CZ',
            'sk-SK',
            'sl-SI',
            'hr-HR',
            'bg-BG',
            'ro-RO',
            'uk-UA',
            'vi-VN',
            'id-ID',
            'ms-MY',
            'ta-IN',
            'te-IN',
            'mr-IN',
            'gu-IN',
            'bn-IN'
        ]
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities.
        
        Returns:
            Dictionary with service information
        """
        return {
            "provider": self.provider.value,
            "name": "Azure Speech Services",
            "available": AZURE_SPEECH_AVAILABLE,
            "initialized": self._is_initialized,
            "features": {
                "streaming": True,
                "continuous_recognition": True,
                "custom_models": True,
                "punctuation": True,
                "profanity_filter": True,
                "dictation_mode": True,
                "real_time": True
            },
            "supported_formats": ["PCM", "WAV", "OGG", "FLAC"],
            "supported_sample_rates": [8000, 16000, 22050, 24000, 44100, 48000],
            "supported_languages": len(self.get_supported_languages()),
            "configuration": {
                "language": self.settings.language_code,
                "region": self._region,
                "profanity_filter": self.settings.enable_profanity_filter
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown Azure STT service."""
        try:
            self._is_initialized = False
            self._is_processing = False
            
            # Stop any active recognition
            if self._speech_recognizer:
                try:
                    self._speech_recognizer.stop_continuous_recognition()
                except:
                    pass
                self._speech_recognizer = None
            
            # Clear configurations
            self._speech_config = None
            self._audio_config = None
            
            logger.info("Azure STT service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during Azure STT shutdown: {e}")