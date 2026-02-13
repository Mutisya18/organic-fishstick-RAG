"""
Embedding Function Factory - Routes to the appropriate embedding provider.

This module provides a single entry point for getting embeddings, automatically
selecting between Ollama and Gemini based on configuration.
"""

from rag.config.provider_config import (
    ACTIVE_EMBEDDING_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    GEMINI_API_KEY,
    GEMINI_EMBED_MODEL,
    DEBUG_MODE,
)
from rag.models import (
    OllamaEmbeddingProvider,
    GeminiEmbeddingProvider,
)


def get_embedding_function():
    """
    Factory function that returns the configured embedding provider.
    
    Routes to either Ollama or Gemini based on ACTIVE_EMBEDDING_PROVIDER config.
    
    Returns:
        EmbeddingProvider: Ollama or Gemini embedding provider instance
    
    Raises:
        ValueError: If ACTIVE_EMBEDDING_PROVIDER is invalid
        ImportError: If required dependencies for chosen provider are missing
    """
    if DEBUG_MODE:
        print(f"[FACTORY] Building embedding provider: {ACTIVE_EMBEDDING_PROVIDER}")
    
    if ACTIVE_EMBEDDING_PROVIDER == "ollama":
        if DEBUG_MODE:
            print(f"[FACTORY]   base_url: {OLLAMA_BASE_URL}")
            print(f"[FACTORY]   model: {OLLAMA_EMBED_MODEL}")
        
        return OllamaEmbeddingProvider(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_EMBED_MODEL
        )
    
    elif ACTIVE_EMBEDDING_PROVIDER == "gemini":
        if DEBUG_MODE:
            print(f"[FACTORY]   model: {GEMINI_EMBED_MODEL}")
        
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY must be set to use Gemini embedding provider. "
                "Set GEMINI_API_KEY in your .env file."
            )
        
        return GeminiEmbeddingProvider(
            api_key=GEMINI_API_KEY,
            model=GEMINI_EMBED_MODEL
        )
    
    else:
        raise ValueError(
            f"Invalid ACTIVE_EMBEDDING_PROVIDER: {ACTIVE_EMBEDDING_PROVIDER}. "
            f"Must be 'ollama' or 'gemini'."
        )
