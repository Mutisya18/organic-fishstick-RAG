"""
Provider Configuration - Single source of truth for model selection and settings.

Controls which embedding and generation providers are active, along with all
model-specific configuration.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# PROVIDER SELECTION
# ============================================================================
# Choose which providers to use: "ollama" or "gemini"
ACTIVE_EMBEDDING_PROVIDER = os.getenv("ACTIVE_EMBEDDING_PROVIDER", "ollama")
ACTIVE_GENERATION_PROVIDER = os.getenv("ACTIVE_GENERATION_PROVIDER", "ollama")

# Validate provider selections
VALID_PROVIDERS = {"ollama", "gemini"}
assert ACTIVE_EMBEDDING_PROVIDER in VALID_PROVIDERS, \
    f"ACTIVE_EMBEDDING_PROVIDER must be one of {VALID_PROVIDERS}, got {ACTIVE_EMBEDDING_PROVIDER}"
assert ACTIVE_GENERATION_PROVIDER in VALID_PROVIDERS, \
    f"ACTIVE_GENERATION_PROVIDER must be one of {VALID_PROVIDERS}, got {ACTIVE_GENERATION_PROVIDER}"

# ============================================================================
# OLLAMA CONFIGURATION
# ============================================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2:3b")

# ============================================================================
# GEMINI CONFIGURATION
# ============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Use gemini-embedding-001 (only embedding model available in google.genai)
# Dimension: 3072
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low")

# Validate Gemini config if Gemini is enabled
if ACTIVE_EMBEDDING_PROVIDER == "gemini" or ACTIVE_GENERATION_PROVIDER == "gemini":
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY environment variable must be set when using Gemini provider"
        )

# ============================================================================
# INDEX STRATEGY
# ============================================================================
# "dual_collection": Maintain separate Chroma collections per embedding provider
# (Recommended - safest, allows A/B testing)
INDEX_STRATEGY = "dual_collection"

# ============================================================================
# EMBEDDING SETTINGS
# ============================================================================
EMBEDDING_DIMENSIONALITY = 768  # Fixed dimension for both Ollama and Gemini

# ============================================================================
# CHROMA SETTINGS
# ============================================================================
CHROMA_PERSIST_DIR_OLLAMA = os.getenv("CHROMA_PERSIST_DIR_OLLAMA", "rag/chroma/ollama")
CHROMA_PERSIST_DIR_GEMINI = os.getenv("CHROMA_PERSIST_DIR_GEMINI", "rag/chroma/gemini")
DATA_PATH = os.getenv("DATA_PATH", "rag/data")

# ============================================================================
# LOGGING AND DEBUGGING
# ============================================================================
# Enable detailed logging for provider initialization
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
