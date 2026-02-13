"""
Embedding Provider Implementations - Abstractions for different embedding services.

Provides a unified interface for embeddings from Ollama and Google Gemini,
ensuring consistent dimensionality and metadata.
"""

import time
from typing import List, Dict, Any
from langchain_ollama import OllamaEmbeddings

from rag.config.provider_config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    GEMINI_EMBED_MODEL,
    EMBEDDING_DIMENSIONALITY,
)
from rag.config.index_registry import get_embedding_space_id


# ============================================================================
# EMBEDDING PROVIDER BASE INTERFACE (Conceptual)
# ============================================================================

class EmbeddingProvider:
    """
    Base interface for embedding providers.
    
    All embedding providers must implement these methods to ensure consistent
    behavior and interchangeability.
    """
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        raise NotImplementedError
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple document strings."""
        raise NotImplementedError
    
    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        raise NotImplementedError


# ============================================================================
# OLLAMA EMBEDDING PROVIDER
# ============================================================================

class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Wrapper around LangChain's OllamaEmbeddings.
    
    Handles embedding requests to a local or remote Ollama instance.
    """
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_EMBED_MODEL):
        """
        Initialize Ollama embedding provider.
        
        Args:
            base_url: Ollama server URL (local or ngrok)
            model: Model name (e.g., "nomic-embed-text")
        """
        self.base_url = base_url
        self.model = model
        self._embedding_function = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the underlying OllamaEmbeddings object."""
        try:
            print(f"[INIT] Initializing OllamaEmbeddingProvider")
            print(f"[INIT]   base_url: {self.base_url}")
            print(f"[INIT]   model: {self.model}")
            self._embedding_function = OllamaEmbeddings(
                model=self.model,
                base_url=self.base_url
            )
            print(f"[INIT] OllamaEmbeddingProvider initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize OllamaEmbeddingProvider: {str(e)}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        return self._embedding_function.embed_query(text)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        return self._embedding_function.embed_documents(texts)
    
    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        return {
            "provider": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "space_id": get_embedding_space_id("ollama"),
            "dimensionality": EMBEDDING_DIMENSIONALITY,
        }


# ============================================================================
# GEMINI EMBEDDING PROVIDER
# ============================================================================

class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Wrapper around Google Gemini's embeddings API.
    
    Handles embedding requests using the Gemini embeddings model.
    Requires GOOGLE_API_KEY environment variable.
    """
    
    def __init__(self, api_key: str, model: str = GEMINI_EMBED_MODEL):
        """
        Initialize Gemini embedding provider.
        
        Args:
            api_key: Google API key for Gemini access
            model: Model name (e.g., "text-embedding-004")
        """
        self.api_key = api_key
        self.model = model
        self._client = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the Gemini client using the new google-genai package."""
        try:
            print(f"[INIT] Initializing GeminiEmbeddingProvider")
            print(f"[INIT]   model: {self.model}")
            
            # Use the new google-genai package (google.generativeai is deprecated)
            import google.genai as genai
            
            # Create a client with the API key (new package uses Client pattern)
            self._client = genai.Client(api_key=self.api_key)
            
            print(f"[INIT] GeminiEmbeddingProvider initialized successfully")
        except ImportError as e:
            raise ImportError(
                f"google-genai package required for Gemini embeddings. "
                f"Install with: pip install --upgrade google-genai langchain-google-genai\n{str(e)}"
            )
        except Exception as e:
            print(f"[ERROR] Failed to initialize GeminiEmbeddingProvider: {str(e)}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query using Gemini.
        
        Uses the new google-genai API.
        Returns a 3072-dimensional embedding.
        """
        try:
            response = self._client.models.embed_content(
                model=self.model,
                contents=text,
            )
            # Extract the embedding vector from response
            return response.embeddings[0].values
        except Exception as e:
            print(f"[ERROR] Failed to embed query with Gemini: {str(e)}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents using Gemini.
        
        Uses the new google-genai API.
        Returns 3072-dimensional embeddings.
        """
        embeddings = []
        try:
            for idx, text in enumerate(texts):
                response = self._client.models.embed_content(
                    model=self.model,
                    contents=text,
                )
                # Extract the embedding vector from response
                embeddings.append(response.embeddings[0].values)
                
                # Log progress every 100 documents
                if (idx + 1) % 100 == 0:
                    print(f"[PROGRESS] Embedded {idx + 1}/{len(texts)} documents")
            
            return embeddings
        except Exception as e:
            print(f"[ERROR] Failed to embed documents with Gemini: {str(e)}")
            raise
    
    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        return {
            "provider": "gemini",
            "model": self.model,
            "space_id": get_embedding_space_id("gemini"),
            "dimensionality": EMBEDDING_DIMENSIONALITY,
            "task_types_supported": ["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"],
        }
