"""
Index Registry - Maps embedding spaces to Chroma collections.

Prevents "mixed embedding space" errors by maintaining a registry of which
collection corresponds to which embedding provider and model.

The key principle: Each embedding space (provider + model combo) has exactly one
Chroma collection. When you switch providers, you switch collections.
"""

from rag.config.provider_config import (
    CHROMA_PERSIST_DIR_OLLAMA,
    CHROMA_PERSIST_DIR_GEMINI,
    EMBEDDING_DIMENSIONALITY,
)

# ============================================================================
# EMBEDDING SPACE DEFINITIONS
# ============================================================================
# Each entry defines:
# - space_id: Unique identifier for the embedding space
# - collection_name: Name of the Chroma collection
# - chroma_path: Directory where Chroma persists this collection
# - dimensionality: Embedding vector dimension
PROVIDER_EMBEDDING_SPACE_MAP = {
    "ollama": {
        "space_id": f"ollama:nomic-embed-text:dim={EMBEDDING_DIMENSIONALITY}",
        "collection_name": "documents_ollama_nomic_768",
        "chroma_path": CHROMA_PERSIST_DIR_OLLAMA,
        "dimensionality": EMBEDDING_DIMENSIONALITY,
    },
    "gemini": {
        "space_id": f"gemini:gemini-embedding-001:dim=3072",
        "collection_name": "documents_gemini_embedding_3072",
        "chroma_path": CHROMA_PERSIST_DIR_GEMINI,
        "dimensionality": 3072,
    }
}


# ============================================================================
# ACCESSOR FUNCTIONS
# ============================================================================

def get_collection_name_for_provider(provider_name: str) -> str:
    """
    Get the Chroma collection name for a given embedding provider.
    
    Args:
        provider_name: "ollama" or "gemini"
    
    Returns:
        Collection name string (e.g., "documents_ollama_nomic_768")
    
    Raises:
        ValueError: If provider_name is invalid
    """
    if provider_name not in PROVIDER_EMBEDDING_SPACE_MAP:
        raise ValueError(
            f"Unknown embedding provider: {provider_name}. "
            f"Valid options: {list(PROVIDER_EMBEDDING_SPACE_MAP.keys())}"
        )
    return PROVIDER_EMBEDDING_SPACE_MAP[provider_name]["collection_name"]


def get_embedding_space_id(provider_name: str) -> str:
    """
    Get the unique embedding space ID for a given provider.
    
    This ID is stored in chunk metadata to detect mixed embedding spaces.
    
    Args:
        provider_name: "ollama" or "gemini"
    
    Returns:
        Space ID string (e.g., "ollama:nomic-embed-text:dim=768")
    
    Raises:
        ValueError: If provider_name is invalid
    """
    if provider_name not in PROVIDER_EMBEDDING_SPACE_MAP:
        raise ValueError(
            f"Unknown embedding provider: {provider_name}. "
            f"Valid options: {list(PROVIDER_EMBEDDING_SPACE_MAP.keys())}"
        )
    return PROVIDER_EMBEDDING_SPACE_MAP[provider_name]["space_id"]


def get_chroma_path_for_provider(provider_name: str) -> str:
    """
    Get the Chroma persistence directory for a given embedding provider.
    
    Args:
        provider_name: "ollama" or "gemini"
    
    Returns:
        Path string (e.g., "rag/chroma/ollama")
    
    Raises:
        ValueError: If provider_name is invalid
    """
    if provider_name not in PROVIDER_EMBEDDING_SPACE_MAP:
        raise ValueError(
            f"Unknown embedding provider: {provider_name}. "
            f"Valid options: {list(PROVIDER_EMBEDDING_SPACE_MAP.keys())}"
        )
    return PROVIDER_EMBEDDING_SPACE_MAP[provider_name]["chroma_path"]


def get_provider_info(provider_name: str) -> dict:
    """
    Get complete provider information.
    
    Args:
        provider_name: "ollama" or "gemini"
    
    Returns:
        Dict with all provider metadata
    """
    if provider_name not in PROVIDER_EMBEDDING_SPACE_MAP:
        raise ValueError(
            f"Unknown embedding provider: {provider_name}. "
            f"Valid options: {list(PROVIDER_EMBEDDING_SPACE_MAP.keys())}"
        )
    return PROVIDER_EMBEDDING_SPACE_MAP[provider_name].copy()


def validate_embedding_space_match(
    expected_space_id: str,
    document_space_id: str,
    strict: bool = True
) -> bool:
    """
    Validate that a document's embedding space matches expected space.
    
    This is a safety check to prevent querying with embeddings from a different
    provider than the documents were indexed with.
    
    Args:
        expected_space_id: The space_id of the active embedding provider
        document_space_id: The space_id stored in the document metadata
        strict: If True, raises error on mismatch; if False, returns False
    
    Returns:
        True if spaces match, False otherwise (only if strict=False)
    
    Raises:
        ValueError: If spaces don't match and strict=True
    """
    if expected_space_id != document_space_id:
        error_msg = (
            f"Embedding space mismatch detected! "
            f"Expected: {expected_space_id}, "
            f"Got document with: {document_space_id}. "
            f"This indicates mixed embedding providers in the same collection."
        )
        if strict:
            raise ValueError(error_msg)
        else:
            return False
    return True
