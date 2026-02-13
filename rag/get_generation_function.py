"""
Generation Function Factory - Routes to the appropriate generation provider.

This module provides a single entry point for getting text generation, automatically
selecting between Ollama and Gemini based on configuration.
"""

from rag.config.provider_config import (
    ACTIVE_GENERATION_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    GEMINI_API_KEY,
    GEMINI_CHAT_MODEL,
    GEMINI_THINKING_LEVEL,
    DEBUG_MODE,
)
from rag.models import (
    OllamaGenerationProvider,
    GeminiGenerationProvider,
)


def get_generation_function():
    """
    Factory function that returns the configured generation provider.
    
    Routes to either Ollama or Gemini based on ACTIVE_GENERATION_PROVIDER config.
    
    Returns:
        GenerationProvider: Ollama or Gemini generation provider instance
    
    Raises:
        ValueError: If ACTIVE_GENERATION_PROVIDER is invalid
        ImportError: If required dependencies for chosen provider are missing
    """
    if DEBUG_MODE:
        print(f"[FACTORY] Building generation provider: {ACTIVE_GENERATION_PROVIDER}")
    
    if ACTIVE_GENERATION_PROVIDER == "ollama":
        if DEBUG_MODE:
            print(f"[FACTORY]   base_url: {OLLAMA_BASE_URL}")
            print(f"[FACTORY]   model: {OLLAMA_CHAT_MODEL}")
        
        return OllamaGenerationProvider(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_CHAT_MODEL
        )
    
    elif ACTIVE_GENERATION_PROVIDER == "gemini":
        if DEBUG_MODE:
            print(f"[FACTORY]   model: {GEMINI_CHAT_MODEL}")
            print(f"[FACTORY]   thinking_level: {GEMINI_THINKING_LEVEL}")
        
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY must be set to use Gemini generation provider. "
                "Set GEMINI_API_KEY in your .env file."
            )
        
        return GeminiGenerationProvider(
            api_key=GEMINI_API_KEY,
            model=GEMINI_CHAT_MODEL,
            thinking_level=GEMINI_THINKING_LEVEL
        )
    
    else:
        raise ValueError(
            f"Invalid ACTIVE_GENERATION_PROVIDER: {ACTIVE_GENERATION_PROVIDER}. "
            f"Must be 'ollama' or 'gemini'."
        )
