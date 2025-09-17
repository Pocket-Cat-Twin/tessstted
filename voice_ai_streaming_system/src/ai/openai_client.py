"""OpenAI API client for Voice-to-AI system."""

import time
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
import logging

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available")

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


class OpenAIClient(BaseAIService):
    """OpenAI API client implementation."""
    
    def __init__(self, settings: AISettings, **kwargs):
        super().__init__(settings, **kwargs)
        
        self._client: Optional[openai.OpenAI] = None
        self._api_key: Optional[str] = None
        self._organization: Optional[str] = None
        self._base_url: Optional[str] = None
        
        # Model settings
        self._model = self.settings.model
        self._max_tokens = self.settings.max_tokens
        self._temperature = self.settings.temperature
        self._stream_response = self.settings.stream_response
        
        # Rate limiting
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests
        
        logger.info("OpenAI client created")
    
    @property
    def provider(self) -> AIProvider:
        return AIProvider.OPENAI
    
    def initialize(self) -> bool:
        """Initialize OpenAI client."""
        try:
            if not OPENAI_AVAILABLE:
                logger.error("OpenAI library not available")
                return False
            
            # Get credentials from configuration
            # These should be set in the config system
            self._api_key = getattr(self.settings, 'openai_api_key', None)
            self._organization = getattr(self.settings, 'openai_organization', None)
            self._base_url = getattr(self.settings, 'openai_base_url', None)
            
            if not self._api_key:
                logger.error("OpenAI API key not configured")
                return False
            
            # Initialize client
            client_kwargs = {
                "api_key": self._api_key
            }
            
            if self._organization:
                client_kwargs["organization"] = self._organization
            
            if self._base_url:
                client_kwargs["base_url"] = self._base_url
            
            self._client = openai.OpenAI(**client_kwargs)
            
            # Test connection with a simple request
            try:
                # Get available models to test connection
                models = self._client.models.list()
                available_models = [model.id for model in models.data]
                
                if self._model not in available_models:
                    logger.warning(f"Model {self._model} not found in available models")
                    # Use a default model that should be available
                    if "gpt-3.5-turbo" in available_models:
                        self._model = "gpt-3.5-turbo"
                        logger.info(f"Switched to model: {self._model}")
                    else:
                        logger.warning("No suitable model found, using configured model anyway")
                
                logger.info("OpenAI API connection test successful")
                
            except Exception as e:
                logger.warning(f"OpenAI API connection test failed: {e}")
                # Continue anyway, might work with actual requests
            
            self._is_initialized = True
            logger.info("OpenAI client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self._emit_error(e)
            return False
    
    def generate_response(self, prompt: str, context: Optional[str] = None) -> Optional[AIResponse]:
        """Generate AI response using OpenAI API."""
        try:
            if not self._is_initialized or not self._client:
                logger.error("OpenAI client not initialized")
                return None
            
            # Rate limiting
            self._enforce_rate_limit()
            
            start_time = time.time()
            self._start_processing(prompt)
            
            # Build messages for chat completion
            messages = self._build_messages(prompt, context)
            
            # Make API request
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                stream=False
            )
            
            processing_time = time.time() - start_time
            
            # Extract response
            if response.choices:
                choice = response.choices[0]
                response_text = choice.message.content.strip()
                finish_reason = choice.finish_reason
                
                # Extract usage statistics
                usage_stats = None
                if hasattr(response, 'usage') and response.usage:
                    usage_stats = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                    self._total_tokens_used += response.usage.total_tokens
                
                ai_response = AIResponse(
                    text=response_text,
                    is_complete=True,
                    tokens_used=response.usage.total_tokens if hasattr(response, 'usage') and response.usage else None,
                    model=self._model,
                    processing_time=processing_time,
                    finish_reason=finish_reason,
                    usage_stats=usage_stats
                )
                
                # Add to conversation history
                self.add_to_conversation(prompt, response_text)
                
                logger.debug(f"OpenAI response: '{response_text[:100]}...' (tokens: {ai_response.tokens_used})")
                
            else:
                # No response generated
                ai_response = AIResponse(
                    text="",
                    is_complete=True,
                    model=self._model,
                    processing_time=processing_time,
                    finish_reason="no_response"
                )
                
                logger.warning("OpenAI API returned no response")
            
            self._stop_processing(processing_time)
            self._emit_response(ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error in OpenAI response generation: {e}")
            self._emit_error(e)
            self._stop_processing()
            return None
    
    async def stream_response(
        self,
        prompt: str,
        context: Optional[str] = None
    ) -> AsyncGenerator[AIResponse, None]:
        """Generate streaming AI response using OpenAI API."""
        try:
            if not self._is_initialized or not self._client:
                logger.error("OpenAI client not initialized")
                return
            
            # Rate limiting
            self._enforce_rate_limit()
            
            logger.debug("Starting OpenAI streaming response")
            
            start_time = time.time()
            self._start_processing(prompt)
            
            # Build messages for chat completion
            messages = self._build_messages(prompt, context)
            
            # Make streaming API request
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                stream=True
            )
            
            accumulated_text = ""
            total_tokens = 0
            
            for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    
                    # Get delta content
                    delta_content = ""
                    if hasattr(choice, 'delta') and choice.delta and hasattr(choice.delta, 'content'):
                        delta_content = choice.delta.content or ""
                    
                    if delta_content:
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
                    
                    # Check if response is complete
                    if hasattr(choice, 'finish_reason') and choice.finish_reason:
                        processing_time = time.time() - start_time
                        
                        # Create final response
                        final_response = AIResponse(
                            text="",  # Empty for final marker
                            is_complete=True,
                            tokens_used=total_tokens,
                            model=self._model,
                            processing_time=processing_time,
                            finish_reason=choice.finish_reason
                        )
                        
                        # Add to conversation history
                        self.add_to_conversation(prompt, accumulated_text)
                        
                        # Update total token count
                        self._total_tokens_used += total_tokens
                        
                        self._stop_processing(processing_time)
                        self._emit_response(final_response)
                        
                        logger.debug(f"OpenAI streaming completed: {len(accumulated_text)} chars, {total_tokens} tokens")
                        yield final_response
                        break
                        
        except Exception as e:
            logger.error(f"Error in OpenAI streaming response: {e}")
            self._emit_error(e)
            self._stop_processing()
    
    def _build_messages(self, prompt: str, context: Optional[str] = None) -> list[Dict[str, str]]:
        """Build messages list for OpenAI chat completion.
        
        Args:
            prompt: User prompt
            context: Additional context
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Add system message
        if self.settings.system_prompt:
            messages.append({
                "role": "system",
                "content": self.settings.system_prompt
            })
        
        # Add conversation history
        for msg in self._conversation_history:
            messages.append(msg)
        
        # Add context if provided
        if context:
            messages.append({
                "role": "system",
                "content": f"Additional context: {context}"
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def set_model(self, model: str) -> bool:
        """Set OpenAI model.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            
        Returns:
            True if model was set successfully
        """
        try:
            # Common OpenAI models
            valid_models = [
                "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
                "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
                "gpt-4-32k", "gpt-4-0613", "gpt-4-1106-preview"
            ]
            
            if model not in valid_models:
                logger.warning(f"Model {model} not in known valid models, setting anyway")
            
            self._model = model
            self.settings.model = model
            
            logger.info(f"OpenAI model set to: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set OpenAI model: {e}")
            return False
    
    def set_temperature(self, temperature: float) -> bool:
        """Set response temperature.
        
        Args:
            temperature: Temperature value (0.0-2.0)
            
        Returns:
            True if temperature was set successfully
        """
        try:
            if not (0.0 <= temperature <= 2.0):
                logger.error(f"Invalid temperature: {temperature} (must be 0.0-2.0)")
                return False
            
            self._temperature = temperature
            self.settings.temperature = temperature
            
            logger.info(f"OpenAI temperature set to: {temperature}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set OpenAI temperature: {e}")
            return False
    
    def set_max_tokens(self, max_tokens: int) -> bool:
        """Set maximum tokens for response.
        
        Args:
            max_tokens: Maximum number of tokens
            
        Returns:
            True if max_tokens was set successfully
        """
        try:
            if max_tokens < 1 or max_tokens > 4000:
                logger.error(f"Invalid max_tokens: {max_tokens} (must be 1-4000)")
                return False
            
            self._max_tokens = max_tokens
            self.settings.max_tokens = max_tokens
            
            logger.info(f"OpenAI max_tokens set to: {max_tokens}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set OpenAI max_tokens: {e}")
            return False
    
    def get_available_models(self) -> list[str]:
        """Get list of available OpenAI models.
        
        Returns:
            List of available model names
        """
        try:
            if self._client:
                models = self._client.models.list()
                return [model.id for model in models.data if "gpt" in model.id]
            else:
                # Return common models if client not initialized
                return [
                    "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
                    "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
                ]
                
        except Exception as e:
            logger.error(f"Failed to get OpenAI models: {e}")
            return []
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities.
        
        Returns:
            Dictionary with service information
        """
        return {
            "provider": self.provider.value,
            "name": "OpenAI GPT",
            "available": OPENAI_AVAILABLE,
            "initialized": self._is_initialized,
            "features": {
                "chat_completion": True,
                "streaming": True,
                "conversation_history": True,
                "system_prompts": True,
                "temperature_control": True,
                "token_usage_tracking": True
            },
            "models": self.get_available_models(),
            "limits": {
                "max_tokens": 4000,
                "temperature_range": "0.0-2.0",
                "context_length": "4K-32K (model dependent)"
            },
            "configuration": {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "stream_response": self._stream_response
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown OpenAI client."""
        try:
            self._is_initialized = False
            self._is_processing = False
            
            # Clear client reference
            self._client = None
            
            logger.info("OpenAI client shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during OpenAI client shutdown: {e}")