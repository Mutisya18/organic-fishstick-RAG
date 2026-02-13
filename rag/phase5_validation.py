#!/usr/bin/env python3
"""
Phase 5: Validation & Testing Execution

Quick validation script to test all components of the dual-provider architecture
without hitting external services. Tests provider config, routing, and metadata.

Usage:
    python rag/phase5_validation.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from rag.config.provider_config import (
    ACTIVE_EMBEDDING_PROVIDER,
    ACTIVE_GENERATION_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_CHAT_MODEL,
    GEMINI_API_KEY,
    GEMINI_EMBED_MODEL,
    GEMINI_CHAT_MODEL,
    GEMINI_THINKING_LEVEL,
    DEBUG_MODE,
)
from rag.config.index_registry import (
    get_collection_name_for_provider,
    get_embedding_space_id,
    get_chroma_path_for_provider,
    PROVIDER_EMBEDDING_SPACE_MAP,
)
from rag.get_embedding_function import get_embedding_function
from rag.get_generation_function import get_generation_function

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def test_header(title: str):
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}{title:^70}{RESET}")
    print(f"{CYAN}{'='*70}{RESET}")


def test_result(passed: bool, message: str):
    symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    print(f"{symbol} {message}")
    return passed


def test_1_config_loading():
    """Test 1: Configuration loads without errors"""
    test_header("1. Configuration Loading")
    results = []
    
    try:
        results.append(test_result(True, f"Active embedding provider: {ACTIVE_EMBEDDING_PROVIDER}"))
        results.append(test_result(True, f"Active generation provider: {ACTIVE_GENERATION_PROVIDER}"))
        results.append(test_result(True, f"Ollama base URL: {OLLAMA_BASE_URL}"))
        results.append(test_result(True, f"Debug mode: {DEBUG_MODE}"))
    except Exception as e:
        results.append(test_result(False, f"Failed to load config: {str(e)}"))
    
    return all(results)


def test_2_index_registry():
    """Test 2: Index registry mappings are correct"""
    test_header("2. Index Registry Mappings")
    results = []
    
    try:
        # Ollama mappings
        ollama_collection = get_collection_name_for_provider("ollama")
        results.append(test_result(
            ollama_collection == "documents_ollama_nomic_768",
            f"Ollama collection: {ollama_collection}"
        ))
        
        ollama_space = get_embedding_space_id("ollama")
        results.append(test_result(
            "ollama" in ollama_space.lower(),
            f"Ollama embedding space ID: {ollama_space}"
        ))
        
        ollama_path = get_chroma_path_for_provider("ollama")
        results.append(test_result(
            "ollama" in ollama_path,
            f"Ollama Chroma path: {ollama_path}"
        ))
        
        # Gemini mappings
        gemini_collection = get_collection_name_for_provider("gemini")
        results.append(test_result(
            gemini_collection == "documents_gemini_embedding_768",
            f"Gemini collection: {gemini_collection}"
        ))
        
        gemini_space = get_embedding_space_id("gemini")
        results.append(test_result(
            "gemini" in gemini_space.lower(),
            f"Gemini embedding space ID: {gemini_space}"
        ))
        
        gemini_path = get_chroma_path_for_provider("gemini")
        results.append(test_result(
            "gemini" in gemini_path,
            f"Gemini Chroma path: {gemini_path}"
        ))
        
    except Exception as e:
        results.append(test_result(False, f"Index registry error: {str(e)}"))
    
    return all(results)


def test_3_provider_space_map():
    """Test 3: Provider embedding space map is complete"""
    test_header("3. Provider Embedding Space Map")
    results = []
    
    try:
        required_keys = {"ollama", "gemini"}
        available_keys = set(PROVIDER_EMBEDDING_SPACE_MAP.keys())
        
        results.append(test_result(
            required_keys == available_keys,
            f"Required providers available: {available_keys}"
        ))
        
        for provider, config in PROVIDER_EMBEDDING_SPACE_MAP.items():
            required_fields = {"space_id", "collection_name", "chroma_path", "dimensionality"}
            available_fields = set(config.keys())
            
            results.append(test_result(
                required_fields <= available_fields,
                f"Provider '{provider}' has all required fields: {list(config.keys())}"
            ))
    
    except Exception as e:
        results.append(test_result(False, f"Space map error: {str(e)}"))
    
    return all(results)


def test_4_embedding_provider_factory():
    """Test 4: Embedding provider factory creates correct provider"""
    test_header("4. Embedding Provider Factory")
    results = []
    
    try:
        provider = get_embedding_function()
        info = provider.get_info()
        
        expected_provider = ACTIVE_EMBEDDING_PROVIDER
        actual_provider = info.get("provider")
        
        results.append(test_result(
            actual_provider == expected_provider,
            f"Provider type: {actual_provider} (expected: {expected_provider})"
        ))
        
        results.append(test_result(
            "space_id" in info,
            f"Provider has space_id: {info.get('space_id')}"
        ))
        
        results.append(test_result(
            info.get("dimensionality") == 768,
            f"Dimensionality is 768: {info.get('dimensionality')}"
        ))
        
        results.append(test_result(
            hasattr(provider, 'embed_query'),
            f"Provider has embed_query method"
        ))
        
        results.append(test_result(
            hasattr(provider, 'embed_documents'),
            f"Provider has embed_documents method"
        ))
        
    except Exception as e:
        results.append(test_result(False, f"Embedding factory error: {str(e)}"))
    
    return all(results)


def test_5_generation_provider_factory():
    """Test 5: Generation provider factory creates correct provider"""
    test_header("5. Generation Provider Factory")
    results = []
    
    try:
        provider = get_generation_function()
        info = provider.get_info()
        
        expected_provider = ACTIVE_GENERATION_PROVIDER
        actual_provider = info.get("provider")
        
        results.append(test_result(
            actual_provider == expected_provider,
            f"Provider type: {actual_provider} (expected: {expected_provider})"
        ))
        
        results.append(test_result(
            "model" in info,
            f"Provider has model: {info.get('model')}"
        ))
        
        results.append(test_result(
            hasattr(provider, 'generate'),
            f"Provider has generate method"
        ))
        
        results.append(test_result(
            hasattr(provider, 'get_info'),
            f"Provider has get_info method"
        ))
        
        # If Ollama, check for expected model
        if ACTIVE_GENERATION_PROVIDER == "ollama":
            results.append(test_result(
                "llama" in info.get("model", "").lower(),
                f"Ollama model is llama variant: {info.get('model')}"
            ))
        
        # If Gemini, check for thinking support
        if ACTIVE_GENERATION_PROVIDER == "gemini":
            results.append(test_result(
                info.get("supports_thinking") == True,
                f"Gemini supports thinking mode"
            ))
        
    except Exception as e:
        results.append(test_result(False, f"Generation factory error: {str(e)}"))
    
    return all(results)


def test_6_chroma_directories():
    """Test 6: Chroma directories exist"""
    test_header("6. Chroma Directory Structure")
    results = []
    
    try:
        ollama_path = Path("rag/chroma/ollama")
        gemini_path = Path("rag/chroma/gemini")
        
        results.append(test_result(
            ollama_path.exists(),
            f"Ollama collection directory exists: {ollama_path}"
        ))
        
        results.append(test_result(
            gemini_path.exists(),
            f"Gemini collection directory exists: {gemini_path}"
        ))
        
        # Check if Ollama has Chroma database
        ollama_has_db = any(ollama_path.glob("*.sqlite3")) or any(ollama_path.glob("*.parquet"))
        if ollama_has_db:
            results.append(test_result(
                True,
                f"Ollama collection has database files"
            ))
        else:
            results.append(test_result(
                True,
                f"Ollama collection directory is empty (expected for new setup)"
            ))
        
    except Exception as e:
        results.append(test_result(False, f"Directory check error: {str(e)}"))
    
    return all(results)


def test_7_environment_variables():
    """Test 7: All required environment variables are set"""
    test_header("7. Environment Variables")
    results = []
    
    try:
        # Basic requirements
        results.append(test_result(
            ACTIVE_EMBEDDING_PROVIDER in ["ollama", "gemini"],
            f"ACTIVE_EMBEDDING_PROVIDER is valid: {ACTIVE_EMBEDDING_PROVIDER}"
        ))
        
        results.append(test_result(
            ACTIVE_GENERATION_PROVIDER in ["ollama", "gemini"],
            f"ACTIVE_GENERATION_PROVIDER is valid: {ACTIVE_GENERATION_PROVIDER}"
        ))
        
        # Ollama variables
        if ACTIVE_EMBEDDING_PROVIDER == "ollama":
            results.append(test_result(
                OLLAMA_EMBED_MODEL != "",
                f"OLLAMA_EMBED_MODEL is set: {OLLAMA_EMBED_MODEL}"
            ))
        
        if ACTIVE_GENERATION_PROVIDER == "ollama":
            results.append(test_result(
                OLLAMA_CHAT_MODEL != "",
                f"OLLAMA_CHAT_MODEL is set: {OLLAMA_CHAT_MODEL}"
            ))
        
        # Gemini variables
        if ACTIVE_EMBEDDING_PROVIDER == "gemini" or ACTIVE_GENERATION_PROVIDER == "gemini":
            has_api_key = bool(GEMINI_API_KEY)
            results.append(test_result(
                has_api_key,
                f"GEMINI_API_KEY is set"
            ))
            
            if has_api_key:
                results.append(test_result(
                    GEMINI_EMBED_MODEL != "",
                    f"GEMINI_EMBED_MODEL is set: {GEMINI_EMBED_MODEL}"
                ))
                
                results.append(test_result(
                    GEMINI_CHAT_MODEL != "",
                    f"GEMINI_CHAT_MODEL is set: {GEMINI_CHAT_MODEL}"
                ))
                
                results.append(test_result(
                    GEMINI_THINKING_LEVEL in ["off", "low", "medium", "high"],
                    f"GEMINI_THINKING_LEVEL is valid: {GEMINI_THINKING_LEVEL}"
                ))
    
    except Exception as e:
        results.append(test_result(False, f"Environment variable error: {str(e)}"))
    
    return all(results)


def main():
    """Run all validation tests"""
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}PHASE 5: VALIDATION & TESTING EXECUTION{RESET}")
    print(f"{CYAN}{'='*70}{RESET}")
    print(f"{YELLOW}Configuration:{RESET}")
    print(f"  Embedding Provider: {ACTIVE_EMBEDDING_PROVIDER}")
    print(f"  Generation Provider: {ACTIVE_GENERATION_PROVIDER}")
    print(f"  Debug Mode: {DEBUG_MODE}")
    
    test_results = []
    
    # Run all tests
    test_results.append(test_1_config_loading())
    test_results.append(test_2_index_registry())
    test_results.append(test_3_provider_space_map())
    test_results.append(test_4_embedding_provider_factory())
    test_results.append(test_5_generation_provider_factory())
    test_results.append(test_6_chroma_directories())
    test_results.append(test_7_environment_variables())
    
    # Summary
    test_header("VALIDATION SUMMARY")
    passed = sum(test_results)
    total = len(test_results)
    all_passed = all(test_results)
    
    status = f"{GREEN}ALL TESTS PASSED ✓{RESET}" if all_passed else f"{RED}SOME TESTS FAILED ✗{RESET}"
    print(f"\n{status}")
    print(f"Passed: {passed}/{total} test groups")
    
    if all_passed:
        print(f"\n{GREEN}Phase 5 Validation Complete!{RESET}")
        print(f"{GREEN}The dual-provider architecture is ready for use.{RESET}")
        print(f"\n{YELLOW}Next steps:{RESET}")
        print(f"  1. Run: python rag/populate_database.py (to ingest documents)")
        print(f"  2. Run: python rag/query_data.py '<your-question>'")
        print(f"  3. To switch providers, edit .env and change ACTIVE_EMBEDDING_PROVIDER/ACTIVE_GENERATION_PROVIDER")
    else:
        print(f"\n{RED}Please fix the failing tests before proceeding.{RESET}")
        return 1
    
    print(f"{CYAN}{'='*70}{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
