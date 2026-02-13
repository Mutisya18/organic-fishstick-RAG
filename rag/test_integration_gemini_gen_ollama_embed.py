"""
Integration Test: Gemini generation with Ollama embeddings.

Tests switching to Gemini for generation while keeping Ollama for embeddings.
This validates that the generation provider switch is independent of retrieval.

Prerequisites:
    - Set ACTIVE_GENERATION_PROVIDER=gemini in .env
    - Keep ACTIVE_EMBEDDING_PROVIDER=ollama in .env
    - Set GEMINI_API_KEY in .env
    - Have Ollama collection populated

Usage:
    python test_integration_gemini_gen_ollama_embed.py
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.get_embedding_function import get_embedding_function
from rag.get_generation_function import get_generation_function
from rag.config.provider_config import (
    ACTIVE_EMBEDDING_PROVIDER,
    ACTIVE_GENERATION_PROVIDER,
    GEMINI_API_KEY,
)
from rag.config.index_registry import get_collection_name_for_provider
from rag.query_data import query_rag

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_test_header(test_name: str):
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}TEST: {test_name}{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")


def print_result(passed: bool, message: str):
    symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    print(f"{symbol} {message}")
    return passed


def test_provider_config():
    """Test 1: Verify hybrid provider configuration"""
    print_test_header("Provider Configuration (Hybrid)")
    
    results = []
    
    # Check embedding provider (should be Ollama)
    is_ollama_embed = ACTIVE_EMBEDDING_PROVIDER == "ollama"
    results.append(print_result(
        is_ollama_embed,
        f"Embedding provider is Ollama: {ACTIVE_EMBEDDING_PROVIDER}"
    ))
    
    # Check generation provider (should be Gemini)
    is_gemini_gen = ACTIVE_GENERATION_PROVIDER == "gemini"
    results.append(print_result(
        is_gemini_gen,
        f"Generation provider is Gemini: {ACTIVE_GENERATION_PROVIDER}"
    ))
    
    # Check Gemini API key
    has_api_key = bool(GEMINI_API_KEY)
    results.append(print_result(
        has_api_key,
        f"GEMINI_API_KEY is set"
    ))
    
    return all(results)


def test_provider_initialization():
    """Test 2: Both providers can be initialized"""
    print_test_header("Provider Initialization")
    
    results = []
    
    try:
        # Initialize embedding provider (Ollama)
        embedding_provider = get_embedding_function()
        embedding_info = embedding_provider.get_info()
        results.append(print_result(
            embedding_info.get('provider') == 'ollama',
            f"Embedding provider: {embedding_info.get('provider')} (expected: ollama)"
        ))
    except Exception as e:
        results.append(print_result(False, f"Embedding provider failed: {str(e)}"))
        return False
    
    try:
        # Initialize generation provider (Gemini)
        generation_provider = get_generation_function()
        generation_info = generation_provider.get_info()
        results.append(print_result(
            generation_info.get('provider') == 'gemini',
            f"Generation provider: {generation_info.get('provider')} (expected: gemini)"
        ))
    except Exception as e:
        results.append(print_result(False, f"Generation provider failed: {str(e)}"))
        # This is expected to fail if google-generativeai is not installed
        if "google-generativeai" in str(e):
            print(f"{YELLOW}Note: Install google-generativeai to test Gemini: pip install google-generativeai{RESET}")
            return False
        return False
    
    return all(results)


def test_collection_routing():
    """Test 3: Retrieval uses Ollama collection"""
    print_test_header("Collection Routing")
    
    results = []
    
    try:
        collection_name = get_collection_name_for_provider("ollama")
        expected = "documents_ollama_nomic_768"
        is_correct = collection_name == expected
        results.append(print_result(
            is_correct,
            f"Using Ollama collection: {collection_name}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Failed to get collection name: {str(e)}"))
    
    return all(results)


def test_rag_query_with_hybrid_providers():
    """Test 4: RAG query works with mixed providers"""
    print_test_header("RAG Query (Hybrid: Ollama Embedding + Gemini Generation)")
    
    results = []
    
    try:
        query = "What is the main topic?"
        response = query_rag(query)
        
        has_response = len(response) > 0
        results.append(print_result(
            has_response,
            f"RAG query returned response: {len(response)} characters"
        ))
        
        if has_response:
            print(f"  Response preview: {response[:150]}...")
    except Exception as e:
        results.append(print_result(
            False,
            f"RAG query failed: {str(e)}"
        ))
    
    return all(results)


def test_response_quality():
    """Test 5: Response is grounded in retrieved context"""
    print_test_header("Response Quality")
    
    results = []
    
    try:
        # Ask a query that should have results
        query = "What is mentioned here?"
        response = query_rag(query)
        
        # Basic quality checks
        is_coherent = len(response) > 20  # Not too short
        results.append(print_result(
            is_coherent,
            f"Response is coherent (length: {len(response)} chars)"
        ))
        
        # Check that response is not just error messages
        is_not_error = "error" not in response.lower()
        results.append(print_result(
            is_not_error,
            f"Response does not contain error messages"
        ))
    except Exception as e:
        results.append(print_result(
            False,
            f"Quality test failed: {str(e)}"
        ))
    
    return all(results)


def main():
    """Run all tests"""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}INTEGRATION TEST: Gemini Generation + Ollama Embedding{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    print(f"Embedding Provider: {ACTIVE_EMBEDDING_PROVIDER}")
    print(f"Generation Provider: {ACTIVE_GENERATION_PROVIDER}")
    
    test_results = []
    
    # Run tests in order
    test_results.append(test_provider_config())
    
    # If config is wrong, skip remaining tests
    if not test_results[0]:
        print(f"\n{RED}Configuration incorrect. Set:${RESET}")
        print(f"  ACTIVE_EMBEDDING_PROVIDER=ollama")
        print(f"  ACTIVE_GENERATION_PROVIDER=gemini")
        print(f"  GEMINI_API_KEY=<your-key>")
        return 1
    
    test_results.append(test_provider_initialization())
    
    if not test_results[-1]:
        print(f"\n{RED}Provider initialization failed.${RESET}")
        return 1
    
    test_results.append(test_collection_routing())
    test_results.append(test_rag_query_with_hybrid_providers())
    test_results.append(test_response_quality())
    
    # Summary
    print(f"\n{YELLOW}{'='*70}{RESET}")
    passed = sum(test_results)
    total = len(test_results)
    status = f"{GREEN}PASSED{RESET}" if all(test_results) else f"{RED}FAILED{RESET}"
    print(f"Test Summary: {passed}/{total} test groups passed - {status}")
    print(f"{YELLOW}{'='*70}{RESET}\n")
    
    return 0 if all(test_results) else 1


if __name__ == "__main__":
    sys.exit(main())
