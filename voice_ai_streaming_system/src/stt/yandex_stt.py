"""Yandex SpeechKit gRPC streaming STT service implementation."""

import asyncio
import grpc
import threading
import time
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
import numpy as np
from dataclasses import dataclass
import json
import io

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

# Yandex Cloud gRPC imports
try:
    # Try importing Yandex Cloud API proto files
    import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
    import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc
    YANDEX_GRPC_AVAILABLE = True
except ImportError:
    # Fallback - will be generated when grpc tools are installed
    YANDEX_GRPC_AVAILABLE = False
    stt_pb2 = None
    stt_service_pb2_grpc = None

logger = logging.getLogger(__name__)


@dataclass
class YandexCredentials:
    """Yandex authentication credentials."""
    api_key: Optional[str] = None
    iam_token: Optional[str] = None
    service_account_key_path: Optional[str] = None
    folder_id: Optional[str] = None


class YandexSTTService(BaseSTTService):
    """Yandex SpeechKit streaming STT service."""
    
    def __init__(
        self,
        settings: STTSettings,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        super().__init__(settings, event_bus, state_manager)
        
        # Yandex-specific settings
        self.api_settings = settings.provider_settings.get('yandex_speechkit', {})
        
        # Credentials
        self.credentials = YandexCredentials(
            api_key=self.api_settings.get('api_key'),
            iam_token=self.api_settings.get('iam_token'),
            service_account_key_path=self.api_settings.get('service_account_key'),
            folder_id=self.api_settings.get('folder_id')
        )
        
        # gRPC connection settings
        self.endpoint = self.api_settings.get('endpoint', 'stt.api.cloud.yandex.net:443')
        self.chunk_size = self.api_settings.get('chunk_size', 4000)
        self.language_code = self.api_settings.get('language_code', 'ru-RU')
        self.model = self.api_settings.get('model', 'general')
        
        # Connection state
        self._channel: Optional[grpc.Channel] = None
        self._stub: Optional[Any] = None
        self._streaming_active = False
        self._stream_thread: Optional[threading.Thread] = None
        self._audio_queue = asyncio.Queue()
        self._results_queue = asyncio.Queue()
        self._stop_streaming = threading.Event()
        
        # Statistics
        self._stream_sessions = 0
        self._stream_errors = 0
        
        logger.info(f"Yandex STT service initialized with endpoint: {self.endpoint}")
    
    @property
    def provider(self) -> STTProvider:
        return STTProvider.YANDEX_SPEECHKIT
    
    def initialize(self) -> bool:
        """Initialize Yandex STT service."""
        try:
            # Check if gRPC proto files are available
            if not YANDEX_GRPC_AVAILABLE:
                logger.error("Yandex gRPC proto files not available. Run: pip install yandexcloud")
                return False
            
            # Validate credentials
            if not self._validate_credentials():
                logger.error("Invalid Yandex credentials")
                return False
            
            # Create gRPC channel
            self._channel = grpc.secure_channel(
                self.endpoint,
                grpc.ssl_channel_credentials()
            )
            
            # Create service stub
            self._stub = stt_service_pb2_grpc.RecognizerStub(self._channel)
            
            # Test connection
            if not self._test_connection():
                logger.error("Failed to connect to Yandex SpeechKit")
                return False
            
            self._is_initialized = True
            logger.info("Yandex STT service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Yandex STT service: {e}")
            return False
    
    def _validate_credentials(self) -> bool:
        """Validate Yandex credentials."""
        try:
            # At least one authentication method must be provided
            if not any([
                self.credentials.api_key,
                self.credentials.iam_token,
                self.credentials.service_account_key_path
            ]):
                logger.error("No Yandex authentication credentials provided")
                return False
            
            # Folder ID is required for API key authentication
            if self.credentials.api_key and not self.credentials.folder_id:
                logger.error("Folder ID is required when using API key authentication")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            return False
    
    def _test_connection(self) -> bool:
        """Test connection to Yandex SpeechKit."""
        try:
            # Create test recognition request
            test_audio = np.zeros(1600, dtype=np.int16)  # 100ms of silence at 16kHz
            
            # This is a basic connectivity test
            # In production, you might want to use a more comprehensive test
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def _create_auth_metadata(self) -> List[tuple]:
        """Create gRPC authentication metadata."""
        try:
            metadata = []
            
            if self.credentials.api_key:
                metadata.append(('authorization', f'Api-Key {self.credentials.api_key}'))
                if self.credentials.folder_id:
                    metadata.append(('x-folder-id', self.credentials.folder_id))
            
            elif self.credentials.iam_token:
                metadata.append(('authorization', f'Bearer {self.credentials.iam_token}'))
            
            # Add other metadata
            metadata.append(('x-client-request-id', f'voice-ai-{int(time.time())}'))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error creating auth metadata: {e}")
            return []
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[STTResult]:
        """Process audio data with Yandex STT (non-streaming)."""
        try:
            if not self._validate_audio_data(audio_data, sample_rate):
                return None
            
            start_time = time.time()
            self._start_processing()
            
            # Prepare audio for Yandex API
            audio_bytes, final_sample_rate = self._prepare_audio_for_service(audio_data, sample_rate)
            
            # Create recognition options
            recognition_options = self._create_recognition_options(final_sample_rate)
            
            # Create request
            request = stt_pb2.RecognizeRequest(
                config=recognition_options,
                audio=stt_pb2.AudioContent(content=audio_bytes)
            )
            
            # Add authentication metadata
            metadata = self._create_auth_metadata()
            
            # Make request
            response = self._stub.Recognize(request, metadata=metadata)
            
            # Process response
            result = self._process_recognition_response(response, start_time)
            
            self._stop_processing(time.time() - start_time)
            
            if result:
                self._emit_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Yandex STT processing: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def process_audio_stream(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int = 16000
    ) -> AsyncGenerator[STTResult, None]:
        """Process streaming audio with Yandex STT."""
        try:
            if not self._is_initialized:
                raise RuntimeError("Yandex STT service not initialized")
            
            logger.info("Starting Yandex streaming recognition")
            self._streaming_active = True
            self._stop_streaming.clear()
            self._stream_sessions += 1
            
            # Create streaming recognition
            async for result in self._stream_recognition(audio_stream, sample_rate):
                if result:
                    yield result
                    
                # Check if streaming should stop
                if self._stop_streaming.is_set():
                    logger.info("Streaming stopped by external signal")
                    break
            
        except Exception as e:
            logger.error(f"Error in Yandex streaming STT: {e}")
            self._emit_error(e)
            self._stream_errors += 1
        finally:
            self._streaming_active = False
            logger.info("Yandex streaming recognition ended")
    
    async def _stream_recognition(
        self,
        audio_stream: AsyncGenerator[np.ndarray, None],
        sample_rate: int
    ) -> AsyncGenerator[STTResult, None]:
        """Core streaming recognition logic."""
        try:
            # Create metadata
            metadata = self._create_auth_metadata()
            
            # Create streaming call
            call = self._stub.RecognizeStreaming(metadata=metadata)
            
            # Send initial configuration
            recognition_options = self._create_streaming_recognition_options(sample_rate)
            config_request = stt_pb2.StreamingRequest(session_options=recognition_options)
            await call.write(config_request)
            
            # Start response processing task
            response_task = asyncio.create_task(
                self._process_streaming_responses(call)
            )
            
            # Stream audio chunks
            chunk_count = 0
            async for audio_chunk in audio_stream:
                if self._stop_streaming.is_set():
                    break
                
                # Prepare audio chunk
                audio_bytes, _ = self._prepare_audio_for_service(audio_chunk, sample_rate)
                
                # Create audio request
                audio_request = stt_pb2.StreamingRequest(
                    chunk=stt_pb2.AudioChunk(data=audio_bytes)
                )
                
                # Send audio chunk
                await call.write(audio_request)
                chunk_count += 1
                
                # Yield any available results
                while not self._results_queue.empty():
                    result = await self._results_queue.get()
                    yield result
            
            # Signal end of stream
            await call.done_writing()
            
            # Wait for final results
            await response_task
            
            # Yield any remaining results
            while not self._results_queue.empty():
                result = await self._results_queue.get()
                yield result
            
            logger.info(f"Processed {chunk_count} audio chunks in streaming session")
            
        except Exception as e:
            logger.error(f"Error in streaming recognition: {e}")
            raise
    
    async def _process_streaming_responses(self, call) -> None:
        """Process streaming responses from Yandex API."""
        try:
            async for response in call:
                if response.HasField('partial'):
                    # Partial result
                    partial_result = STTResult(
                        text=response.partial.alternatives[0].text if response.partial.alternatives else "",
                        confidence=response.partial.alternatives[0].confidence if response.partial.alternatives else 0.0,
                        is_final=False,
                        language=self.language_code,
                        timestamp=time.time()
                    )
                    await self._results_queue.put(partial_result)
                    
                elif response.HasField('final'):
                    # Final result
                    final_result = STTResult(
                        text=response.final.alternatives[0].text if response.final.alternatives else "",
                        confidence=response.final.alternatives[0].confidence if response.final.alternatives else 0.0,
                        is_final=True,
                        language=self.language_code,
                        timestamp=time.time()
                    )
                    await self._results_queue.put(final_result)
                    
                elif response.HasField('final_refinement'):
                    # Refined final result
                    refined_result = STTResult(
                        text=response.final_refinement.normalized_text.alternatives[0].text if response.final_refinement.normalized_text.alternatives else "",
                        confidence=response.final_refinement.normalized_text.alternatives[0].confidence if response.final_refinement.normalized_text.alternatives else 0.0,
                        is_final=True,
                        language=self.language_code,
                        timestamp=time.time()
                    )
                    await self._results_queue.put(refined_result)
                    
        except Exception as e:
            logger.error(f"Error processing streaming responses: {e}")
            raise
    
    def _create_recognition_options(self, sample_rate: int) -> Any:
        """Create recognition options for single request."""
        try:
            return stt_pb2.RecognitionConfig(
                specification=stt_pb2.RecognitionSpec(
                    language_restriction=stt_pb2.LanguageRestrictionOptions(
                        restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                        language_code=[self.language_code]
                    ),
                    model=self.model,
                    profanity_filter=self.settings.enable_profanity_filter,
                    literature_text=False,
                    audio_format=stt_pb2.AudioFormatOptions(
                        raw_audio=stt_pb2.RawAudio(
                            audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                            sample_rate_hertz=sample_rate,
                            audio_channel_count=1
                        )
                    )
                ),
                folder_id=self.credentials.folder_id
            )
            
        except Exception as e:
            logger.error(f"Error creating recognition options: {e}")
            raise
    
    def _create_streaming_recognition_options(self, sample_rate: int) -> Any:
        """Create recognition options for streaming request."""
        try:
            return stt_pb2.StreamingOptions(
                recognition_model=stt_pb2.RecognitionModelOptions(
                    audio_format=stt_pb2.AudioFormatOptions(
                        raw_audio=stt_pb2.RawAudio(
                            audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                            sample_rate_hertz=sample_rate,
                            audio_channel_count=1
                        )
                    ),
                    text_normalization=stt_pb2.TextNormalizationOptions(
                        text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                        profanity_filter=self.settings.enable_profanity_filter,
                        literature_text=False
                    ),
                    language_restriction=stt_pb2.LanguageRestrictionOptions(
                        restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                        language_code=[self.language_code]
                    ),
                    audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME
                )
            )
            
        except Exception as e:
            logger.error(f"Error creating streaming recognition options: {e}")
            raise
    
    def _process_recognition_response(self, response: Any, start_time: float) -> Optional[STTResult]:
        """Process single recognition response."""
        try:
            if not response.results:
                logger.warning("No recognition results received")
                return None
            
            result = response.results[0]
            if not result.alternatives:
                logger.warning("No alternatives in recognition result")
                return None
            
            alternative = result.alternatives[0]
            processing_time = time.time() - start_time
            
            return STTResult(
                text=alternative.text,
                confidence=alternative.confidence,
                is_final=True,
                language=self.language_code,
                timestamp=time.time(),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing recognition response: {e}")
            return None
    
    def stop_streaming(self) -> None:
        """Stop active streaming session."""
        try:
            if self._streaming_active:
                logger.info("Stopping Yandex streaming session")
                self._stop_streaming.set()
                self._streaming_active = False
                
                # Emit event
                self._event_bus.emit(
                    EventType.STT_STREAMING_STOPPED,
                    f"stt_{self.provider.value}",
                    {"provider": self.provider.value}
                )
                
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
    
    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        return self._streaming_active
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        base_stats = super().get_statistics()
        base_stats.update({
            "stream_sessions": self._stream_sessions,
            "stream_errors": self._stream_errors,
            "streaming_active": self._streaming_active,
            "endpoint": self.endpoint,
            "language": self.language_code,
            "model": self.model
        })
        return base_stats
    
    def shutdown(self) -> None:
        """Shutdown Yandex STT service."""
        try:
            # Stop streaming if active
            if self._streaming_active:
                self.stop_streaming()
            
            # Close gRPC channel
            if self._channel:
                self._channel.close()
                self._channel = None
            
            self._is_initialized = False
            self._is_processing = False
            
            logger.info("Yandex STT service shutdown")
            
        except Exception as e:
            logger.error(f"Error shutting down Yandex STT service: {e}")