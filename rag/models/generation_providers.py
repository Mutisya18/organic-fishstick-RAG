"""
Generation Provider Implementations - Abstractions for different LLM services.

Provides a unified interface for text generation from Ollama and Google Gemini,
ensuring consistent response formats and metadata.
"""

import time
from typing import Dict, Any, Optional
from langchain_ollama import OllamaLLM

from rag.config.provider_config import (
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    GEMINI_CHAT_MODEL,
    GEMINI_THINKING_LEVEL,
)


# ============================================================================
# GENERATION PROVIDER BASE INTERFACE (Conceptual)
# ============================================================================

class GenerationProvider:
    """
    Base interface for generation providers.
    
    All generation providers must implement these methods to ensure consistent
    behavior and interchangeability.
    """
    
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate text from a prompt.
        
        Returns:
            Dict with keys:
            - text: Generated response text
            - usage: Token usage info
            - latency_ms: Response time in milliseconds
            - metadata: Provider-specific metadata
        """
        raise NotImplementedError
    
    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        raise NotImplementedError


# ============================================================================
# OLLAMA GENERATION PROVIDER
# ============================================================================

class OllamaGenerationProvider(GenerationProvider):
    """
    Wrapper around LangChain's OllamaLLM.
    
    Handles text generation requests to a local or remote Ollama instance.
    """
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_CHAT_MODEL):
        """
        Initialize Ollama generation provider.
        
        Args:
            base_url: Ollama server URL
            model: Model name (e.g., "llama3.2:3b")
        """
        self.base_url = base_url
        self.model = model
        self._model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the OllamaLLM object."""
        try:
            print(f"[INIT] Initializing OllamaGenerationProvider")
            print(f"[INIT]   base_url: {self.base_url}")
            print(f"[INIT]   model: {self.model}")
            self._model = OllamaLLM(
                model=self.model,
                base_url=self.base_url
            )
            print(f"[INIT] OllamaGenerationProvider initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize OllamaGenerationProvider: {str(e)}")
            raise
    
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate text using Ollama.
        
        Note: Ollama's LangChain integration doesn't directly support system
        instructions, so we prepend them to the prompt.
        """
        start_time = time.time()
        
        try:
            # Combine system instruction with prompt if provided
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"
            
            # Generate response
            response_text = self._model.invoke(full_prompt)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimate tokens (rough approximation)
            estimated_prompt_tokens = len(full_prompt.split()) * 1.3
            estimated_completion_tokens = len(response_text.split()) * 1.3
            
            return {
                "text": response_text,
                "usage": {
                    "prompt_tokens": int(estimated_prompt_tokens),
                    "completion_tokens": int(estimated_completion_tokens),
                    "total_tokens": int(estimated_prompt_tokens + estimated_completion_tokens),
                },
                "latency_ms": latency_ms,
                "metadata": {
                    "model": self.model,
                    "provider": "ollama",
                }
            }
        except Exception as e:
            print(f"[ERROR] Failed to generate with Ollama: {str(e)}")
            raise
    
    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        return {
            "provider": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "supports_streaming": False,
            "supports_thinking": False,
        }


# ============================================================================
# GEMINI GENERATION PROVIDER
# ============================================================================

class GeminiGenerationProvider(GenerationProvider):
    """
    Wrapper around Google Gemini's generation API.
    
    Handles text generation requests using Gemini with optional thinking mode.
    Requires GOOGLE_API_KEY environment variable.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = GEMINI_CHAT_MODEL,
        thinking_level: str = GEMINI_THINKING_LEVEL
    ):
        """
        Initialize Gemini generation provider.
        
        Args:
            api_key: Google API key for Gemini access
            model: Model name (e.g., "gemini-2.0-flash")
            thinking_level: Thinking mode ("off", "low", "medium", "high")
        """
        self.api_key = api_key
        self.model = model
        self.thinking_level = thinking_level
        self._client = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the Gemini client using google.genai."""
        try:
            print(f"[INIT] Initializing GeminiGenerationProvider")
            print(f"[INIT]   model: {self.model}")
            print(f"[INIT]   thinking_level: {self.thinking_level}")
            
            # Use the new google-genai package
            import google.genai as genai
            
            # Create a client with the API key (new package uses Client pattern)
            self._client = genai.Client(api_key=self.api_key)
            
            print(f"[INIT] GeminiGenerationProvider initialized successfully")
        except ImportError as e:
            raise ImportError(
                f"google-genai package required for Gemini generation. "
                f"Install with: pip install --upgrade google-genai\n{str(e)}"
            )
        except Exception as e:
            print(f"[ERROR] Failed to initialize GeminiGenerationProvider: {str(e)}")
            raise
    
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate text using Gemini via google.genai.
        
        Args:
            prompt: The prompt text
            system_instruction: System instruction for the model
            config: Optional config dict with keys like 'thinking_level'
        
        Returns:
            Dict with text, usage, latency_ms, metadata
        """
        start_time = time.time()
        
        try:
            from google.genai import types
            
            # Use config thinking level if provided, else use default
            thinking_level = "off"
            if config and "thinking_level" in config:
                thinking_level = config["thinking_level"]
            elif self.thinking_level != "off":
                thinking_level = self.thinking_level
            
            # Build generation config for google.genai
            generation_config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
                system_instruction=system_instruction if system_instruction else None,
            )
            
            # Add thinking config if not "off" (if supported)
            if thinking_level != "off":
                try:
                    # Try to set thinking mode if supported
                    generation_config.thinking = types.ThinkingConfig(
                        type_=thinking_level.upper()  # expected: "DISABLED", "LOW", "MEDIUM", "HIGH"
                    )
                except:
                    # If thinking not supported, just proceed without it
                    print(f"[WARNING] Thinking mode '{thinking_level}' not supported in this model")
            
            # Generate response using google.genai API
            response = self._client.models.generate_content(
                model=self.model,  # No "models/" prefix
                contents=prompt,
                config=generation_config,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract results
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Try to get token counts if available
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, 'usage_metadata'):
                prompt_tokens = response.usage_metadata.prompt_token_count if hasattr(response.usage_metadata, 'prompt_token_count') else 0
                completion_tokens = response.usage_metadata.candidates_token_count if hasattr(response.usage_metadata, 'candidates_token_count') else 0
            
            return {
                "text": response_text,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                "latency_ms": latency_ms,
                "metadata": {
                    "model": self.model,
                    "provider": "gemini",
                    "thinking_level": thinking_level,
                }
            }
        except Exception as e:
            print(f"[ERROR] Failed to generate with Gemini: {str(e)}")
            raise
    
    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        return {
            "provider": "gemini",
            "model": self.model,
            "thinking_level": self.thinking_level,
            "supports_streaming": True,
            "supports_thinking": True,
            "thinking_modes_available": ["off", "low", "medium", "high"],
        }
