"""
Integration Test: Full Gemini (Gemini embeddings + Gemini generation).

Tests switching both embeddings and generation to Gemini.
This is the most comprehensive test of the multi-provider architecture.

Prerequisites:
    - Set ACTIVE_EMBEDDING_PROVIDER=gemini in .env
    - Set ACTIVE_GENERATION_PROVIDER=gemini in .env
    - Set GEMINI_API_KEY in .env
    - Run: python rag/populate_database.py to build Gemini collection

Usage:
    python test_integration_full_gemini.py
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
    GEMINI_THINKING_LEVEL,
)
from rag.config.index_registry import (
    get_collection_name_for_provider,
    get_embedding_space_id,
)
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
    """Test 1: Verify full Gemini configuration"""
    print_test_header("Provider Configuration (Full Gemini)")
    
    results = []
    
    # Check embedding provider (should be Gemini)
    is_gemini_embed = ACTIVE_EMBEDDING_PROVIDER == "gemini"
    results.append(print_result(
        is_gemini_embed,
        f"Embedding provider is Gemini: {ACTIVE_EMBEDDING_PROVIDER}"
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
    
    # Check thinking level
    thinking_ok = GEMINI_THINKING_LEVEL in ["off", "low", "medium", "high"]
    results.append(print_result(
        thinking_ok,
        f"GEMINI_THINKING_LEVEL is valid: {GEMINI_THINKING_LEVEL}"
    ))
    
    return all(results)


def test_provider_initialization():
    """Test 2: Both Gemini providers can be initialized"""
    print_test_header("Provider Initialization (Both Gemini)")
    
    results = []
    
    try:
        # Initialize embedding provider (Gemini)
        embedding_provider = get_embedding_function()
        embedding_info = embedding_provider.get_info()
        results.append(print_result(
            embedding_info.get('provider') == 'gemini',
            f"Embedding provider: {embedding_info.get('provider')} (expected: gemini)"
        ))
        print(f"  Model: {embedding_info.get('model')}")
    except Exception as e:
        results.append(print_result(False, f"Embedding provider failed: {str(e)}"))
        if "google-generativeai" in str(e):
            print(f"{YELLOW}Note: Install google-generativeai: pip install google-generativeai${RESET}")
        return False
    
    try:
        # Initialize generation provider (Gemini)
        generation_provider = get_generation_function()
        generation_info = generation_provider.get_info()
        results.append(print_result(
            generation_info.get('provider') == 'gemini',
            f"Generation provider: {generation_info.get('provider')} (expected: gemini)"
        ))
        print(f"  Model: {generation_info.get('model')}")
        print(f"  Thinking level: {generation_info.get('thinking_level')}")
    except Exception as e:
        results.append(print_result(False, f"Generation provider failed: {str(e)}"))
        return False
    
    return all(results)


def test_collection_routing():
    """Test 3: Retrieval uses Gemini collection"""
    print_test_header("Collection Routing")
    
    results = []
    
    try:
        collection_name = get_collection_name_for_provider("gemini")
        expected = "documents_gemini_embedding_768"
        is_correct = collection_name == expected
        results.append(print_result(
            is_correct,
            f"Using Gemini collection: {collection_name}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Failed to get collection name: {str(e)}"))
        return False
    
    try:
        embedding_space = get_embedding_space_id("gemini")
        is_correct = "gemini" in embedding_space.lower()
        results.append(print_result(
            is_correct,
            f"Embedding space ID: {embedding_space}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Failed to get embedding space ID: {str(e)}"))
        return False
    
    return all(results)


def test_rag_query_full_gemini():
    """Test 4: RAG query works with full Gemini"""
    print_test_header("RAG Query (Full Gemini)")
    
    results = []
    
    try:
        query = "What is the main topic discussed here?"
        print(f"  Query: {query}")
        response = query_rag(query)
        
        has_response = len(response) > 0
        results.append(print_result(
            has_response,
            f"RAG query returned response: {len(response)} characters"
        ))
        
        if has_response:
            print(f"  Response preview: {response[:200]}...")
    except Exception as e:
        error_msg = str(e)
        results.append(print_result(False, f"RAG query failed: {error_msg}"))
        
        # Check if it's because Gemini collection doesn't exist
        if "does not exist" in error_msg or "not found" in error_msg:
            print(f"{YELLOW}Note: Gemini collection doesn't exist. Run: python rag/populate_database.py${RESET}")
    
    return all(results)


def test_response_quality():
    """Test 5: Response quality and grounding"""
    print_test_header("Response Quality & Grounding")
    
    results = []
    
    try:
        # Run multiple queries to test consistency
        queries = [
            "What are the key points?",
            "Summarize the main ideas"
        ]
        
        all_good = True
        for query in queries:
            try:
                response = query_rag(query)
                
                # Check response length
                is_coherent = len(response) > 20
                is_not_error = "error" not in response.lower()
                
                if is_coherent and is_not_error:
                    print(f"  ✓ Query '{query}' returned good response ({len(response)} chars)")
                else:
                    print(f"  ✗ Query '{query}' returned poor response")
                    all_good = False
            except Exception as e:
                print(f"  ✗ Query '{query}' failed: {str(e)}")
                all_good = False
        
        results.append(print_result(all_good, "All response quality checks passed"))
    except Exception as e:
        results.append(print_result(False, f"Quality test failed: {str(e)}"))
    
    return all(results)


def test_thinking_mode():
    """Test 6: Gemini thinking mode is configured correctly"""
    print_test_header("Gemini Thinking Mode")
    
    results = []
    
    try:
        generation_provider = get_generation_function()
        gen_info = generation_provider.get_info()
        
        has_thinking_support = gen_info.get('supports_thinking', False)
        results.append(print_result(
            has_thinking_support,
            f"Generation provider supports thinking mode"
        ))
        
        thinking_level = gen_info.get('thinking_level')
        is_valid = thinking_level in ["off", "low", "medium", "high"]
        results.append(print_result(
            is_valid,
            f"Thinking level is valid: {thinking_level}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Thinking mode test failed: {str(e)}"))
    
    return all(results)


def main():
    """Run all tests"""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}INTEGRATION TEST: Full Gemini (Embeddings + Generation){RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    print(f"Embedding Provider: {ACTIVE_EMBEDDING_PROVIDER}")
    print(f"Generation Provider: {ACTIVE_GENERATION_PROVIDER}")
    print(f"Thinking Level: {GEMINI_THINKING_LEVEL}")
    
    test_results = []
    
    # Run tests in order
    test_results.append(test_provider_config())
    
    # If config is wrong, skip remaining tests
    if not test_results[0]:
        print(f"\n{RED}Configuration incorrect. Set:${RESET}")
        print(f"  ACTIVE_EMBEDDING_PROVIDER=gemini")
        print(f"  ACTIVE_GENERATION_PROVIDER=gemini")
        print(f"  GEMINI_API_KEY=<your-key>")
        print(f"  GEMINI_THINKING_LEVEL=low (or medium/high)")
        return 1
    
    test_results.append(test_provider_initialization())
    
    if not test_results[-1]:
        print(f"\n{RED}Provider initialization failed.${RESET}")
        return 1
    
    test_results.append(test_collection_routing())
    test_results.append(test_rag_query_full_gemini())
    test_results.append(test_response_quality())
    test_results.append(test_thinking_mode())
    
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
