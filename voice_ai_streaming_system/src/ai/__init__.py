"""AI response services for Voice-to-AI system."""

from .base_ai import BaseAIService, AIResponse, AIProvider, MockAIService
from .openrouter_client import OpenRouterAIService

# AI Service Factory
def create_ai_service(provider: AIProvider, settings) -> BaseAIService:
    """Create AI service instance based on provider."""
    if provider == AIProvider.OPENROUTER:
        return OpenRouterAIService(settings)
    elif provider == AIProvider.MOCK:
        return MockAIService(settings)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")

__all__ = [
    "BaseAIService", "AIResponse", "AIProvider",
    "MockAIService", "OpenRouterAIService",
    "create_ai_service"
]
