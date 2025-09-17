"""Anthropic Claude API client for Voice-to-AI system."""

import time
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
import logging

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic library not available")

try:
    from .base_ai import BaseAIService, AIResponse, AIProvider
    from ..config.settings import AISettings
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from ai.base_ai import BaseAIService, AIResponse, AIProvider
    from config.settings import AISettings

logger = logging.getLogger(__name__)


class AnthropicClient(BaseAIService):
    """Anthropic Claude API client implementation."""
    
    def __init__(self, settings: AISettings, **kwargs):
        super().__init__(settings, **kwargs)
        
        self._client: Optional[anthropic.Anthropic] = None
        self._api_key: Optional[str] = None
        self._base_url: Optional[str] = None
        
        # Model settings
        self._model = "claude-3-sonnet-20240229"  # Default Claude model
        self._max_tokens = self.settings.max_tokens
        self._temperature = self.settings.temperature
        self._stream_response = self.settings.stream_response
        
        # Claude-specific settings
        self._top_p = 0.9  # Nucleus sampling parameter
        self._top_k = 40   # Top-k sampling parameter
        
        # Rate limiting
        self._last_request_time = 0.0
        self._min_request_interval = 0.2  # 200ms between requests
        
        logger.info("Anthropic client created")
    
    @property
    def provider(self) -> AIProvider:
        return AIProvider.ANTHROPIC
    
    def initialize(self) -> bool:
        """Initialize Anthropic client."""
        try:
            if not ANTHROPIC_AVAILABLE:
                logger.error("Anthropic library not available")
                return False
            
            # Get credentials from configuration
            self._api_key = getattr(self.settings, 'anthropic_api_key', None)
            self._base_url = getattr(self.settings, 'anthropic_base_url', None)
            
            if not self._api_key:
                logger.error("Anthropic API key not configured")
                return False
            
            # Initialize client
            client_kwargs = {
                "api_key": self._api_key
            }
            
            if self._base_url:
                client_kwargs["base_url"] = self._base_url
            
            self._client = anthropic.Anthropic(**client_kwargs)
            
            # Test connection with a simple request
            try:
                # Make a minimal test request
                test_response = self._client.messages.create(
                    model=self._model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                
                logger.info("Anthropic API connection test successful")
                
            except Exception as e:
                logger.warning(f"Anthropic API connection test failed: {e}")
                # Continue anyway, might work with actual requests
            
            self._is_initialized = True
            logger.info("Anthropic client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            self._emit_error(e)
            return False
    
    def generate_response(self, prompt: str, context: Optional[str] = None) -> Optional[AIResponse]:
        """Generate AI response using Anthropic Claude API."""
        try:
            if not self._is_initialized or not self._client:
                logger.error("Anthropic client not initialized")
                return None
            
            # Rate limiting
            self._enforce_rate_limit()
            
            start_time = time.time()
            self._start_processing(prompt)
            
            # Build messages for Claude
            messages = self._build_messages(prompt, context)
            
            # Build system message
            system_message = self._build_system_message(context)
            
            # Make API request
            request_kwargs = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "messages": messages
            }
            
            if system_message:
                request_kwargs["system"] = system_message
            
            response = self._client.messages.create(**request_kwargs)
            
            processing_time = time.time() - start_time
            
            # Extract response
            if response.content:
                # Claude returns content as a list of blocks
                response_text = ""
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        response_text += content_block.text
                
                response_text = response_text.strip()
                
                # Extract usage statistics
                usage_stats = None
                tokens_used = None
                if hasattr(response, 'usage') and response.usage:
                    usage_stats = {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    }
                    tokens_used = usage_stats["total_tokens"]
                    self._total_tokens_used += tokens_used
                
                ai_response = AIResponse(
                    text=response_text,
                    is_complete=True,
                    tokens_used=tokens_used,
                    model=self._model,
                    processing_time=processing_time,
                    finish_reason=getattr(response, 'stop_reason', 'completed'),
                    usage_stats=usage_stats
                )
                
                # Add to conversation history
                self.add_to_conversation(prompt, response_text)
                
                logger.debug(f"Anthropic response: '{response_text[:100]}...' (tokens: {tokens_used})")
                
            else:
                # No response generated
                ai_response = AIResponse(
                    text="",
                    is_complete=True,
                    model=self._model,
                    processing_time=processing_time,
                    finish_reason="no_response"
                )
                
                logger.warning("Anthropic API returned no response")
            
            self._stop_processing(processing_time)
            self._emit_response(ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error in Anthropic response generation: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def stream_response(
        self,
        prompt: str,
        context: Optional[str] = None
    ) -> AsyncGenerator[AIResponse, None]:
        """Generate streaming AI response using Anthropic Claude API."""
        try:
            if not self._is_initialized or not self._client:
                logger.error("Anthropic client not initialized")
                return
            
            # Rate limiting
            self._enforce_rate_limit()
            
            logger.debug("Starting Anthropic streaming response")
            
            start_time = time.time()
            self._start_processing(prompt)
            
            # Build messages for Claude
            messages = self._build_messages(prompt, context)
            
            # Build system message
            system_message = self._build_system_message(context)
            
            # Make streaming API request
            request_kwargs = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "messages": messages,
                "stream": True
            }
            
            if system_message:
                request_kwargs["system"] = system_message
            
            stream = self._client.messages.create(**request_kwargs)
            
            accumulated_text = ""
            total_tokens = 0
            
            for event in stream:
                if hasattr(event, 'type'):
                    if event.type == "content_block_delta":
                        # Get delta content
                        if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                            delta_content = event.delta.text
                            
                            accumulated_text += delta_content
                            total_tokens += 1  # Approximate token count
                            
                            # Create streaming response
                            ai_response = AIResponse(
                                text=delta_content,
                                is_complete=False,
                                tokens_used=1,
                                model=self._model
                            )
                            
                            self._emit_response(ai_response)
                            yield ai_response
                    
                    elif event.type == "message_stop":
                        # Response is complete
                        processing_time = time.time() - start_time
                        
                        # Create final response
                        final_response = AIResponse(
                            text="",  # Empty for final marker
                            is_complete=True,
                            tokens_used=total_tokens,
                            model=self._model,
                            processing_time=processing_time,
                            finish_reason="completed"
                        )
                        
                        # Add to conversation history
                        self.add_to_conversation(prompt, accumulated_text)
                        
                        # Update total token count
                        self._total_tokens_used += total_tokens
                        
                        self._stop_processing(processing_time)
                        self._emit_response(final_response)
                        
                        logger.debug(f"Anthropic streaming completed: {len(accumulated_text)} chars, {total_tokens} tokens")
                        yield final_response
                        break
                        
        except Exception as e:
            logger.error(f"Error in Anthropic streaming response: {e}")
            self._emit_error(e)
            self._stop_processing()
    
    def _build_messages(self, prompt: str, context: Optional[str] = None) -> list[Dict[str, str]]:
        """Build messages list for Anthropic Claude.
        
        Args:
            prompt: User prompt
            context: Additional context
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Add conversation history (excluding system messages)
        for msg in self._conversation_history:
            if msg["role"] in ["user", "assistant"]:
                messages.append(msg)
        
        # Add current user message
        user_content = prompt
        if context:
            user_content = f"Context: {context}\n\nUser: {prompt}"
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages
    
    def _build_system_message(self, context: Optional[str] = None) -> Optional[str]:
        """Build system message for Claude.
        
        Args:
            context: Additional context
            
        Returns:
            System message string or None
        """
        parts = []
        
        # Add system prompt
        if self.settings.system_prompt:
            parts.append(self.settings.system_prompt)
        
        # Add context if provided and not already in user message
        if context and len(self._conversation_history) > 0:
            parts.append(f"Additional context: {context}")
        
        return "\n\n".join(parts) if parts else None
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def set_model(self, model: str) -> bool:
        """Set Anthropic model.
        
        Args:
            model: Model name (e.g., 'claude-3-sonnet-20240229', 'claude-3-opus-20240229')
            
        Returns:
            True if model was set successfully
        """
        try:
            # Common Claude models
            valid_models = [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229", 
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
            
            if model not in valid_models:
                logger.warning(f"Model {model} not in known valid models, setting anyway")
            
            self._model = model
            
            logger.info(f"Anthropic model set to: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Anthropic model: {e}")
            return False
    
    def set_temperature(self, temperature: float) -> bool:
        """Set response temperature.
        
        Args:
            temperature: Temperature value (0.0-1.0 for Claude)
            
        Returns:
            True if temperature was set successfully
        """
        try:
            if not (0.0 <= temperature <= 1.0):
                logger.error(f"Invalid temperature: {temperature} (must be 0.0-1.0 for Claude)")
                return False
            
            self._temperature = temperature
            self.settings.temperature = temperature
            
            logger.info(f"Anthropic temperature set to: {temperature}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Anthropic temperature: {e}")
            return False
    
    def set_max_tokens(self, max_tokens: int) -> bool:
        """Set maximum tokens for response.
        
        Args:
            max_tokens: Maximum number of tokens
            
        Returns:
            True if max_tokens was set successfully
        """
        try:
            if max_tokens < 1 or max_tokens > 100000:  # Claude has higher limits
                logger.error(f"Invalid max_tokens: {max_tokens} (must be 1-100000)")
                return False
            
            self._max_tokens = max_tokens
            self.settings.max_tokens = max_tokens
            
            logger.info(f"Anthropic max_tokens set to: {max_tokens}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Anthropic max_tokens: {e}")
            return False
    
    def get_available_models(self) -> list[str]:
        """Get list of available Anthropic models.
        
        Returns:
            List of available model names
        """
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307", 
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities.
        
        Returns:
            Dictionary with service information
        """
        return {
            "provider": self.provider.value,
            "name": "Anthropic Claude",
            "available": ANTHROPIC_AVAILABLE,
            "initialized": self._is_initialized,
            "features": {
                "chat_completion": True,
                "streaming": True,
                "conversation_history": True,
                "system_prompts": True,
                "temperature_control": True,
                "token_usage_tracking": True,
                "large_context": True
            },
            "models": self.get_available_models(),
            "limits": {
                "max_tokens": 100000,
                "temperature_range": "0.0-1.0",
                "context_length": "200K tokens (model dependent)"
            },
            "configuration": {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "stream_response": self._stream_response,
                "top_p": self._top_p,
                "top_k": self._top_k
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown Anthropic client."""
        try:
            self._is_initialized = False
            self._is_processing = False
            
            # Clear client reference
            self._client = None
            
            logger.info("Anthropic client shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during Anthropic client shutdown: {e}")