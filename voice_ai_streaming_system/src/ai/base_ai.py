"""Base AI service interface for Voice-to-AI system."""

import abc
import time
import asyncio
from typing import Optional, Callable, Dict, Any, List, AsyncGenerator, Union
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from ..config.settings import AISettings
    from ..core.event_bus import EventBus, EventType, get_event_bus
    from ..core.state_manager import StateManager, get_state_manager
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config.settings import AISettings
    from core.event_bus import EventBus, EventType, get_event_bus
    from core.state_manager import StateManager, get_state_manager

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI service providers."""
    OPENROUTER = "openrouter"
    MOCK = "mock"  # For testing


@dataclass
class AIResponse:
    """AI response data structure."""
    text: str
    is_complete: bool
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    timestamp: float = None
    processing_time: Optional[float] = None
    finish_reason: Optional[str] = None
    usage_stats: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BaseAIService(abc.ABC):
    """Abstract base class for AI services."""
    
    def __init__(
        self,
        settings: AISettings,
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
        
        # Conversation context
        self._conversation_history: List[Dict[str, str]] = []
        self._max_history_length = 10  # Keep last 10 exchanges
        
        # Callbacks
        self._response_callback: Optional[Callable[[AIResponse], None]] = None
        self._chunk_callback: Optional[Callable[[str], None]] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        
        # Performance tracking
        self._requests_count = 0
        self._total_processing_time = 0.0
        self._total_tokens_used = 0
        self._errors_count = 0
        
        logger.info(f"AI service {self.get_provider()} initialized")
    
    @property
    @abc.abstractmethod
    def provider(self) -> AIProvider:
        """Get the AI provider type."""
        pass
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize the AI service.
        
        Returns:
            True if initialization successful
        """
        pass
    
    @abc.abstractmethod
    def generate_response(self, prompt: str, context: Optional[str] = None) -> Optional[AIResponse]:
        """Generate AI response for given prompt.
        
        Args:
            prompt: User prompt/question
            context: Optional context information
            
        Returns:
            AI response or None if generation failed
        """
        pass
    
    @abc.abstractmethod
    def stream_response(
        self,
        prompt: str,
        context: Optional[str] = None
    ) -> AsyncGenerator[AIResponse, None]:
        """Generate streaming AI response.
        
        Args:
            prompt: User prompt/question
            context: Optional context information
            
        Yields:
            AI response chunks as they become available
        """
        pass
    
    @abc.abstractmethod
    def shutdown(self) -> None:
        """Shutdown the AI service."""
        pass
    
    def get_provider(self) -> AIProvider:
        """Get the provider type."""
        return self.provider
    
    def set_response_callback(self, callback: Callable[[AIResponse], None]) -> None:
        """Set callback for AI responses."""
        self._response_callback = callback
        logger.debug("AI response callback registered")
    
    def set_chunk_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for streaming chunks."""
        self._chunk_callback = callback
        logger.debug("AI chunk callback registered")
    
    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Set callback for AI errors."""
        self._error_callback = callback
        logger.debug("AI error callback registered")
    
    def add_to_conversation(self, user_input: str, ai_response: str) -> None:
        """Add exchange to conversation history.
        
        Args:
            user_input: User's input
            ai_response: AI's response
        """
        self._conversation_history.append({
            "role": "user",
            "content": user_input
        })
        self._conversation_history.append({
            "role": "assistant",
            "content": ai_response
        })
        
        # Trim history if too long
        if len(self._conversation_history) > self._max_history_length * 2:
            # Remove oldest exchange (user + assistant)
            self._conversation_history = self._conversation_history[2:]
        
        logger.debug(f"Added to conversation history (total: {len(self._conversation_history)} messages)")
    
    def get_conversation_context(self) -> str:
        """Get conversation context as formatted string.
        
        Returns:
            Formatted conversation history
        """
        if not self._conversation_history:
            return ""
        
        context_parts = []
        for i in range(0, len(self._conversation_history), 2):
            if i + 1 < len(self._conversation_history):
                user_msg = self._conversation_history[i]["content"]
                ai_msg = self._conversation_history[i + 1]["content"]
                context_parts.append(f"User: {user_msg}")
                context_parts.append(f"Assistant: {ai_msg}")
        
        return "\n".join(context_parts)
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
        logger.debug("Conversation history cleared")
    
    def set_system_prompt(self, system_prompt: str) -> None:
        """Set system prompt for AI responses.
        
        Args:
            system_prompt: System prompt to use
        """
        self.settings.system_prompt = system_prompt
        logger.info("System prompt updated")
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._is_initialized
    
    def is_processing(self) -> bool:
        """Check if service is currently processing."""
        return self._is_processing
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        avg_processing_time = (
            self._total_processing_time / max(self._requests_count, 1)
        )
        avg_tokens_per_request = (
            self._total_tokens_used / max(self._requests_count, 1)
        )
        
        return {
            "provider": self.provider.value,
            "initialized": self._is_initialized,
            "processing": self._is_processing,
            "requests_count": self._requests_count,
            "errors_count": self._errors_count,
            "total_tokens_used": self._total_tokens_used,
            "average_processing_time": avg_processing_time,
            "average_tokens_per_request": avg_tokens_per_request,
            "error_rate": self._errors_count / max(self._requests_count, 1),
            "conversation_length": len(self._conversation_history)
        }
    
    def reset_statistics(self) -> None:
        """Reset service statistics."""
        self._requests_count = 0
        self._total_processing_time = 0.0
        self._total_tokens_used = 0
        self._errors_count = 0
        logger.debug("AI statistics reset")
    
    def _emit_response(self, response: AIResponse) -> None:
        """Emit AI response via event bus and callback."""
        try:
            # Emit event
            self._event_bus.emit(
                EventType.AI_RESPONSE_COMPLETED if response.is_complete else EventType.AI_RESPONSE_CHUNK,
                f"ai_{self.provider.value}",
                {
                    "text": response.text,
                    "is_complete": response.is_complete,
                    "tokens_used": response.tokens_used,
                    "model": response.model,
                    "processing_time": response.processing_time
                }
            )
            
            # Update state manager
            self._state_manager.update_ai_state(
                current_response=response.text if response.is_complete else self._state_manager.get_state().ai.current_response + response.text,
                tokens_received=self._state_manager.get_state().ai.tokens_received + (response.tokens_used or 0),
                processing_time=response.processing_time or 0.0,
                last_response_time=time.time()
            )
            
            # Call callbacks
            if response.is_complete and self._response_callback:
                try:
                    self._response_callback(response)
                except Exception as e:
                    logger.error(f"Error in AI response callback: {e}")
            
            if not response.is_complete and self._chunk_callback:
                try:
                    self._chunk_callback(response.text)
                except Exception as e:
                    logger.error(f"Error in AI chunk callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error emitting AI response: {e}")
    
    def _emit_error(self, error: Exception) -> None:
        """Emit AI error via event bus and callback."""
        try:
            # Update error count
            self._errors_count += 1
            
            # Emit event
            self._event_bus.emit(
                EventType.AI_REQUEST_ERROR,
                f"ai_{self.provider.value}",
                {
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "provider": self.provider.value
                }
            )
            
            # Record error in state manager
            self._state_manager.record_error(
                f"ai_{self.provider.value}",
                str(error),
                critical=False
            )
            
            # Call callback
            if self._error_callback:
                try:
                    self._error_callback(error)
                except Exception as e:
                    logger.error(f"Error in AI error callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error emitting AI error: {e}")
    
    def _start_processing(self, request: str) -> None:
        """Mark processing as started."""
        self._is_processing = True
        self._requests_count += 1
        
        # Update state manager
        self._state_manager.update_ai_state(
            is_processing=True,
            current_request=request,
            current_response=""
        )
        
        # Emit event
        self._event_bus.emit(
            EventType.AI_REQUEST_STARTED,
            f"ai_{self.provider.value}",
            {"provider": self.provider.value, "request": request}
        )
    
    def _stop_processing(self, processing_time: Optional[float] = None) -> None:
        """Mark processing as stopped."""
        self._is_processing = False
        
        if processing_time:
            self._total_processing_time += processing_time
        
        # Update state manager
        self._state_manager.update_ai_state(is_processing=False)
    
    def _build_prompt_with_context(self, prompt: str, context: Optional[str] = None) -> str:
        """Build complete prompt with system prompt and context.
        
        Args:
            prompt: User prompt
            context: Additional context
            
        Returns:
            Complete prompt string
        """
        parts = []
        
        # Add system prompt
        if self.settings.system_prompt:
            parts.append(f"System: {self.settings.system_prompt}")
        
        # Add conversation history
        conversation_context = self.get_conversation_context()
        if conversation_context:
            parts.append("Previous conversation:")
            parts.append(conversation_context)
        
        # Add additional context
        if context:
            parts.append(f"Context: {context}")
        
        # Add current prompt
        parts.append(f"User: {prompt}")
        parts.append("Assistant:")
        
        return "\n\n".join(parts)


class MockAIService(BaseAIService):
    """Mock AI service for testing."""
    
    @property
    def provider(self) -> AIProvider:
        return AIProvider.MOCK
    
    def initialize(self) -> bool:
        """Initialize mock service."""
        try:
            self._is_initialized = True
            logger.info("Mock AI service initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize mock AI service: {e}")
            return False
    
    def generate_response(self, prompt: str, context: Optional[str] = None) -> Optional[AIResponse]:
        """Generate mock AI response."""
        try:
            start_time = time.time()
            self._start_processing(prompt)
            
            # Mock processing delay
            time.sleep(0.2)
            
            # Generate mock response
            processing_time = time.time() - start_time
            
            mock_text = f"Mock AI response to: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'"
            if context:
                mock_text += f" (with context: {len(context)} chars)"
            
            response = AIResponse(
                text=mock_text,
                is_complete=True,
                tokens_used=len(mock_text.split()),
                model="mock-model",
                processing_time=processing_time,
                finish_reason="completed"
            )
            
            # Add to conversation
            self.add_to_conversation(prompt, response.text)
            
            self._stop_processing(processing_time)
            self._emit_response(response)
            
            return response
            
        except Exception as e:
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def stream_response(
        self,
        prompt: str,
        context: Optional[str] = None
    ) -> AsyncGenerator[AIResponse, None]:
        """Generate streaming mock AI response."""
        try:
            start_time = time.time()
            self._start_processing(prompt)
            
            # Mock streaming response
            full_response = f"Streaming mock response to: '{prompt[:30]}...'"
            words = full_response.split()
            
            accumulated_text = ""
            
            for i, word in enumerate(words):
                accumulated_text += (word + " ")
                
                # Mock streaming delay
                await asyncio.sleep(0.1)
                
                is_complete = (i == len(words) - 1)
                processing_time = time.time() - start_time if is_complete else None
                
                response = AIResponse(
                    text=word + " ",
                    is_complete=is_complete,
                    tokens_used=1,
                    model="mock-streaming-model",
                    processing_time=processing_time,
                    finish_reason="completed" if is_complete else None
                )
                
                self._emit_response(response)
                yield response
            
            # Add final response to conversation
            self.add_to_conversation(prompt, accumulated_text.strip())
            self._stop_processing(time.time() - start_time)
            
        except Exception as e:
            logger.error(f"Error in mock streaming AI: {e}")
            self._emit_error(e)
            self._stop_processing()
    
    def shutdown(self) -> None:
        """Shutdown mock service."""
        self._is_initialized = False
        self._is_processing = False
        logger.info("Mock AI service shutdown")