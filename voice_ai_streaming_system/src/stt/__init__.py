"""Speech-to-Text services for Voice-to-AI system."""

from .base_stt import BaseSTTService, STTResult, STTProvider, MockSTTService
from .yandex_stt import YandexSTTService
from .whisperx_stt import WhisperXSTTService

# STT Service Factory
def create_stt_service(provider: STTProvider, settings) -> BaseSTTService:
    """Create STT service instance based on provider."""
    if provider == STTProvider.YANDEX_SPEECHKIT:
        return YandexSTTService(settings)
    elif provider == STTProvider.WHISPERX:
        return WhisperXSTTService(settings)
    elif provider == STTProvider.MOCK:
        return MockSTTService(settings)
    else:
        raise ValueError(f"Unknown STT provider: {provider}")

__all__ = [
    "BaseSTTService", "STTResult", "STTProvider",
    "MockSTTService", "YandexSTTService", "WhisperXSTTService",
    "create_stt_service"
]