"""
Integration Test: Gemini embeddings with Ollama generation.

Tests switching to Gemini for embeddings while keeping Ollama for generation.
This validates that switching embedding providers works correctly with collection routing.

Prerequisites:
    - Set ACTIVE_EMBEDDING_PROVIDER=gemini in .env
    - Keep ACTIVE_GENERATION_PROVIDER=ollama in .env
    - Set GEMINI_API_KEY in .env
    - Run: python rag/populate_database.py to build Gemini collection

Usage:
    python test_integration_gemini_embed_ollama_gen.py
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
    """Test 1: Verify hybrid provider configuration"""
    print_test_header("Provider Configuration (Hybrid)")
    
    results = []
    
    # Check embedding provider (should be Gemini)
    is_gemini_embed = ACTIVE_EMBEDDING_PROVIDER == "gemini"
    results.append(print_result(
        is_gemini_embed,
        f"Embedding provider is Gemini: {ACTIVE_EMBEDDING_PROVIDER}"
    ))
    
    # Check generation provider (should be Ollama)
    is_ollama_gen = ACTIVE_GENERATION_PROVIDER == "ollama"
    results.append(print_result(
        is_ollama_gen,
        f"Generation provider is Ollama: {ACTIVE_GENERATION_PROVIDER}"
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
        # Initialize embedding provider (Gemini)
        embedding_provider = get_embedding_function()
        embedding_info = embedding_provider.get_info()
        results.append(print_result(
            embedding_info.get('provider') == 'gemini',
            f"Embedding provider: {embedding_info.get('provider')} (expected: gemini)"
        ))
    except Exception as e:
        results.append(print_result(False, f"Embedding provider failed: {str(e)}"))
        if "google-generativeai" in str(e):
            print(f"{YELLOW}Note: Install google-generativeai to test Gemini: pip install google-generativeai{RESET}")
        return False
    
    try:
        # Initialize generation provider (Ollama)
        generation_provider = get_generation_function()
        generation_info = generation_provider.get_info()
        results.append(print_result(
            generation_info.get('provider') == 'ollama',
            f"Generation provider: {generation_info.get('provider')} (expected: ollama)"
        ))
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
    
    try:
        embedding_space = get_embedding_space_id("gemini")
        is_correct = "gemini" in embedding_space.lower()
        results.append(print_result(
            is_correct,
            f"Embedding space ID: {embedding_space}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Failed to get embedding space ID: {str(e)}"))
    
    return all(results)


def test_rag_query_with_hybrid_providers():
    """Test 4: RAG query works with mixed providers"""
    print_test_header("RAG Query (Hybrid: Gemini Embedding + Ollama Generation)")
    
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
        error_msg = str(e)
        results.append(print_result(False, f"RAG query failed: {error_msg}"))
        
        # Check if it's because Gemini collection doesn't exist
        if "does not exist" in error_msg or "not found" in error_msg:
            print(f"{YELLOW}Note: Gemini collection doesn't exist. Run: python rag/populate_database.py${RESET}")
    
    return all(results)


def test_embedding_space_validation():
    """Test 5: Retrieved chunks have correct embedding space metadata"""
    print_test_header("Embedding Space Validation")
    
    results = []
    
    try:
        from langchain_chroma import Chroma
        from rag.config.index_registry import get_chroma_path_for_provider
        
        embedding_provider = get_embedding_function()
        collection_name = get_collection_name_for_provider("gemini")
        chroma_path = get_chroma_path_for_provider("gemini")
        embedding_space_id = get_embedding_space_id("gemini")
        
        db = Chroma(
            persist_directory=chroma_path,
            collection_name=collection_name,
            embedding_function=embedding_provider
        )
        
        # Try to search
        query = "test"
        results_docs = db.similarity_search(query, k=1)
        
        if results_docs:
            first_doc = results_docs[0]
            doc_space = first_doc.metadata.get("embedding_space_id")
            matches = doc_space == embedding_space_id
            
            results.append(print_result(
                matches,
                f"Retrieved doc embedding_space_id matches: {doc_space} == {embedding_space_id}"
            ))
        else:
            print(f"{YELLOW}⚠ No documents in Gemini collection (populate first)${RESET}")
            return True
    
    except Exception as e:
        results.append(print_result(
            False,
            f"Embedding space validation failed: {str(e)}"
        ))
    
    return all(results)


def main():
    """Run all tests"""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}INTEGRATION TEST: Gemini Embedding + Ollama Generation{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    print(f"Embedding Provider: {ACTIVE_EMBEDDING_PROVIDER}")
    print(f"Generation Provider: {ACTIVE_GENERATION_PROVIDER}")
    
    test_results = []
    
    # Run tests in order
    test_results.append(test_provider_config())
    
    # If config is wrong, skip remaining tests
    if not test_results[0]:
        print(f"\n{RED}Configuration incorrect. Set:${RESET}")
        print(f"  ACTIVE_EMBEDDING_PROVIDER=gemini")
        print(f"  ACTIVE_GENERATION_PROVIDER=ollama")
        print(f"  GEMINI_API_KEY=<your-key>")
        return 1
    
    test_results.append(test_provider_initialization())
    
    if not test_results[-1]:
        print(f"\n{RED}Provider initialization failed.${RESET}")
        return 1
    
    test_results.append(test_collection_routing())
    test_results.append(test_rag_query_with_hybrid_providers())
    test_results.append(test_embedding_space_validation())
    
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
