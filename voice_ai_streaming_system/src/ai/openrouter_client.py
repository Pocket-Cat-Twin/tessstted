"""OpenRouter AI service implementation."""

import asyncio
import time
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
import json

try:
    from ..config.settings import AISettings
    from .base_ai import BaseAIService, AIProvider, AIResponse
    from ..core.event_bus import EventBus, EventType, get_event_bus
    from ..core.state_manager import StateManager, get_state_manager
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config.settings import AISettings
    from ai.base_ai import BaseAIService, AIProvider, AIResponse
    from core.event_bus import EventBus, EventType, get_event_bus
    from core.state_manager import StateManager, get_state_manager

# OpenAI client (OpenRouter compatible)
try:
    from openai import OpenAI
    OPENAI_CLIENT_AVAILABLE = True
except ImportError:
    OPENAI_CLIENT_AVAILABLE = False
    OpenAI = None

logger = logging.getLogger(__name__)


class OpenRouterAIService(BaseAIService):
    """OpenRouter AI service implementation."""
    
    def __init__(
        self,
        settings: AISettings,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        super().__init__(settings, event_bus, state_manager)
        
        # OpenRouter-specific settings
        self.api_settings = settings.provider_settings.get('openrouter', {})
        
        # API configuration
        self.api_key = self.api_settings.get('api_key')
        self.base_url = self.api_settings.get('base_url', 'https://openrouter.ai/api/v1')
        self.site_url = self.api_settings.get('site_url')
        self.app_name = self.api_settings.get('app_name', 'Voice AI Streaming System')
        self.http_referer = self.api_settings.get('http_referer', 'http://localhost:5000')
        
        # Model configuration
        self.model = settings.model
        self.fallback_model = getattr(settings, 'fallback_model', None)
        
        # Client instance
        self._client: Optional[OpenAI] = None
        
        # Request tracking
        self._active_requests = 0
        self._max_retries = settings.max_retries
        self._timeout = settings.response_timeout
        
        logger.info(f"OpenRouter AI service initialized with model: {self.model}")
    
    @property
    def provider(self) -> AIProvider:
        return AIProvider.OPENROUTER
    
    def initialize(self) -> bool:
        """Initialize OpenRouter AI service."""
        try:
            # Check if OpenAI client is available
            if not OPENAI_CLIENT_AVAILABLE:
                logger.error("OpenAI client not available. Run: pip install openai>=1.12.0")
                return False
            
            # Validate API key
            if not self.api_key:
                logger.error("OpenRouter API key not provided")
                return False
            
            # Create OpenAI client with OpenRouter endpoint
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self._timeout,
                max_retries=self._max_retries,
                default_headers=self._create_default_headers()
            )
            
            # Test connection
            if not self._test_connection():
                logger.error("Failed to connect to OpenRouter")
                return False
            
            self._is_initialized = True
            logger.info("OpenRouter AI service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter AI service: {e}")
            return False
    
    def _create_default_headers(self) -> Dict[str, str]:
        """Create default headers for OpenRouter requests."""
        headers = {}
        
        # HTTP-Referer is required by OpenRouter
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        
        # X-Title header for better request tracking
        if self.app_name:
            headers["X-Title"] = self.app_name
        
        return headers
    
    def _test_connection(self) -> bool:
        """Test connection to OpenRouter."""
        try:
            # Make a simple request to test connectivity
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                stream=False
            )
            
            if response and response.choices:
                logger.info("OpenRouter connection test successful")
                return True
            else:
                logger.error("OpenRouter connection test failed: no response")
                return False
                
        except Exception as e:
            logger.error(f"OpenRouter connection test failed: {e}")
            return False
    
    def generate_response(self, prompt: str, context: Optional[str] = None) -> Optional[AIResponse]:
        """Generate AI response using OpenRouter."""
        try:
            if not self._is_initialized:
                raise RuntimeError("OpenRouter AI service not initialized")
            
            start_time = time.time()
            self._start_processing(prompt)
            self._active_requests += 1
            
            # Build messages
            messages = self._build_messages(prompt, context)
            
            # Make request
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.settings.max_tokens,
                temperature=self.settings.temperature,
                stream=False
            )
            
            # Process response
            ai_response = self._process_completion_response(response, start_time)
            
            # Add to conversation history
            if ai_response:
                self.add_to_conversation(prompt, ai_response.text)
            
            processing_time = time.time() - start_time
            self._stop_processing(processing_time)
            
            if ai_response:
                self._emit_response(ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error in OpenRouter completion: {e}")
            
            # Try fallback model if available
            if self.fallback_model and self.fallback_model != self.model:
                logger.info(f"Retrying with fallback model: {self.fallback_model}")
                return self._generate_with_fallback(prompt, context)
            
            self._emit_error(e)
            self._stop_processing()
            return None
        finally:
            self._active_requests = max(0, self._active_requests - 1)
    
    async def stream_response(
        self,
        prompt: str,
        context: Optional[str] = None
    ) -> AsyncGenerator[AIResponse, None]:
        """Generate streaming AI response using OpenRouter."""
        try:
            if not self._is_initialized:
                raise RuntimeError("OpenRouter AI service not initialized")
            
            start_time = time.time()
            self._start_processing(prompt)
            self._active_requests += 1
            
            # Build messages
            messages = self._build_messages(prompt, context)
            
            logger.info(f"Starting OpenRouter streaming request with model: {self.model}")
            
            # Make streaming request
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.settings.max_tokens,
                temperature=self.settings.temperature,
                stream=True
            )
            
            # Process streaming response
            accumulated_text = ""
            chunk_count = 0
            
            for chunk in stream:
                chunk_count += 1
                
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    accumulated_text += content
                    
                    # Create chunk response
                    chunk_response = AIResponse(
                        text=content,
                        is_complete=False,
                        tokens_used=1,  # Approximate
                        model=self.model,
                        timestamp=time.time()
                    )
                    
                    self._emit_response(chunk_response)
                    yield chunk_response
                
                # Check for completion
                if chunk.choices and chunk.choices[0].finish_reason:
                    processing_time = time.time() - start_time
                    
                    # Create final response
                    final_response = AIResponse(
                        text=accumulated_text,
                        is_complete=True,
                        tokens_used=chunk_count,  # Approximate
                        model=self.model,
                        timestamp=time.time(),
                        processing_time=processing_time,
                        finish_reason=chunk.choices[0].finish_reason
                    )
                    
                    # Add to conversation history
                    self.add_to_conversation(prompt, accumulated_text)
                    
                    self._emit_response(final_response)
                    yield final_response
                    break
            
            self._stop_processing(time.time() - start_time)
            logger.info(f"Streaming completed: {chunk_count} chunks, {len(accumulated_text)} chars")
            
        except Exception as e:
            logger.error(f"Error in OpenRouter streaming: {e}")
            
            # Try fallback model if available
            if self.fallback_model and self.fallback_model != self.model:
                logger.info(f"Retrying streaming with fallback model: {self.fallback_model}")
                async for response in self._stream_with_fallback(prompt, context):
                    yield response
            else:
                self._emit_error(e)
                self._stop_processing()
        finally:
            self._active_requests = max(0, self._active_requests - 1)
    
    def _build_messages(self, prompt: str, context: Optional[str] = None) -> List[Dict[str, str]]:
        """Build messages array for OpenRouter API."""
        messages = []
        
        # Add system prompt
        if self.settings.system_prompt:
            messages.append({
                "role": "system",
                "content": self.settings.system_prompt
            })
        
        # Add conversation history
        messages.extend(self._conversation_history)
        
        # Add context if provided
        if context:
            messages.append({
                "role": "user",
                "content": f"Context: {context}"
            })
        
        # Add current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    def _process_completion_response(self, response: Any, start_time: float) -> Optional[AIResponse]:
        """Process completion response from OpenRouter."""
        try:
            if not response.choices:
                logger.warning("No choices in OpenRouter response")
                return None
            
            choice = response.choices[0]
            content = choice.message.content if choice.message else ""
            
            # Extract usage information
            usage = response.usage if hasattr(response, 'usage') else None
            tokens_used = usage.total_tokens if usage else len(content.split())
            
            processing_time = time.time() - start_time
            
            # Update statistics
            self._total_tokens_used += tokens_used
            
            return AIResponse(
                text=content,
                is_complete=True,
                tokens_used=tokens_used,
                model=response.model if hasattr(response, 'model') else self.model,
                timestamp=time.time(),
                processing_time=processing_time,
                finish_reason=choice.finish_reason if hasattr(choice, 'finish_reason') else "completed",
                usage_stats={
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else tokens_used,
                    "total_tokens": tokens_used
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing completion response: {e}")
            return None
    
    def _generate_with_fallback(self, prompt: str, context: Optional[str] = None) -> Optional[AIResponse]:
        """Generate response with fallback model."""
        try:
            logger.info(f"Using fallback model: {self.fallback_model}")
            
            # Temporarily switch model
            original_model = self.model
            self.model = self.fallback_model
            
            # Build messages
            messages = self._build_messages(prompt, context)
            
            # Make request with fallback model
            response = self._client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                max_tokens=self.settings.max_tokens,
                temperature=self.settings.temperature,
                stream=False
            )
            
            # Restore original model
            self.model = original_model
            
            # Process response
            start_time = time.time()
            ai_response = self._process_completion_response(response, start_time)
            
            if ai_response:
                self.add_to_conversation(prompt, ai_response.text)
                self._emit_response(ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Fallback model also failed: {e}")
            self.model = original_model  # Restore original model
            return None
    
    async def _stream_with_fallback(
        self,
        prompt: str,
        context: Optional[str] = None
    ) -> AsyncGenerator[AIResponse, None]:
        """Stream response with fallback model."""
        try:
            logger.info(f"Streaming with fallback model: {self.fallback_model}")
            
            # Temporarily switch model
            original_model = self.model
            self.model = self.fallback_model
            
            # Stream with fallback model
            async for response in self.stream_response(prompt, context):
                yield response
                
        except Exception as e:
            logger.error(f"Fallback streaming also failed: {e}")
        finally:
            # Restore original model
            self.model = original_model
    
    def set_model(self, model: str) -> None:
        """Set the model to use for requests."""
        self.model = model
        logger.info(f"OpenRouter model changed to: {model}")
    
    def set_fallback_model(self, fallback_model: str) -> None:
        """Set the fallback model."""
        self.fallback_model = fallback_model
        logger.info(f"OpenRouter fallback model set to: {fallback_model}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from OpenRouter."""
        try:
            if not self._is_initialized:
                return []
            
            # OpenRouter provides model information through their API
            # This is a simplified implementation
            return [
                "anthropic/claude-3-sonnet",
                "anthropic/claude-3-opus",
                "anthropic/claude-3-haiku",
                "openai/gpt-4",
                "openai/gpt-4-turbo",
                "openai/gpt-3.5-turbo",
                "google/gemini-pro",
                "meta-llama/llama-2-70b-chat",
                "mistralai/mistral-7b-instruct"
            ]
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        base_stats = super().get_statistics()
        base_stats.update({
            "model": self.model,
            "fallback_model": self.fallback_model,
            "active_requests": self._active_requests,
            "base_url": self.base_url,
            "app_name": self.app_name
        })
        return base_stats
    
    def shutdown(self) -> None:
        """Shutdown OpenRouter AI service."""
        try:
            # Wait for active requests to complete
            if self._active_requests > 0:
                logger.info(f"Waiting for {self._active_requests} active requests to complete")
                # In a real implementation, you might want to add a timeout here
            
            # Close client
            if self._client:
                # OpenAI client doesn't have explicit close method
                self._client = None
            
            self._is_initialized = False
            self._is_processing = False
            
            logger.info("OpenRouter AI service shutdown")
            
        except Exception as e:
            logger.error(f"Error shutting down OpenRouter AI service: {e}")