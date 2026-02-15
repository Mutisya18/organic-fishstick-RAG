"""
Regression Test: Ollama embeddings + Ollama generation (Original configuration).

This test ensures that the refactoring doesn't break the existing Ollama-only workflow.
Run this first to validate backwards compatibility.

Usage:
    python test_regression_ollama.py
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.get_embedding_function import get_embedding_function
from rag.get_generation_function import get_generation_function
from rag.config.provider_config import (
    ACTIVE_EMBEDDING_PROVIDER,
    ACTIVE_GENERATION_PROVIDER,
)
from rag.config.index_registry import (
    get_collection_name_for_provider,
    get_chroma_path_for_provider,
)
from rag.populate_database import load_documents, split_documents, add_to_chroma, calculate_chunk_ids
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
    """Test 1: Verify provider configuration"""
    print_test_header("Provider Configuration")
    
    results = []
    
    # Check embedding provider
    is_ollama_embed = ACTIVE_EMBEDDING_PROVIDER == "ollama"
    results.append(print_result(
        is_ollama_embed,
        f"Embedding provider is Ollama: {ACTIVE_EMBEDDING_PROVIDER}"
    ))
    
    # Check generation provider
    is_ollama_gen = ACTIVE_GENERATION_PROVIDER == "ollama"
    results.append(print_result(
        is_ollama_gen,
        f"Generation provider is Ollama: {ACTIVE_GENERATION_PROVIDER}"
    ))
    
    return all(results)


def test_provider_initialization():
    """Test 2: Providers can be initialized"""
    print_test_header("Provider Initialization")
    
    results = []
    
    try:
        embedding_provider = get_embedding_function()
        embedding_info = embedding_provider.get_info()
        results.append(print_result(
            True,
            f"Embedding provider initialized: {embedding_info.get('provider')}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Embedding provider failed: {str(e)}"))
    
    try:
        generation_provider = get_generation_function()
        generation_info = generation_provider.get_info()
        results.append(print_result(
            True,
            f"Generation provider initialized: {generation_info.get('provider')}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Generation provider failed: {str(e)}"))
    
    return all(results)


def test_collection_routing():
    """Test 3: Collection names and paths are correct"""
    print_test_header("Collection Routing")
    
    results = []
    
    try:
        collection_name = get_collection_name_for_provider("ollama")
        expected = "documents_ollama_nomic_768"
        is_correct = collection_name == expected
        results.append(print_result(
            is_correct,
            f"Ollama collection name: {collection_name} (expected: {expected})"
        ))
    except Exception as e:
        results.append(print_result(False, f"Failed to get collection name: {str(e)}"))
    
    try:
        chroma_path = get_chroma_path_for_provider("ollama")
        is_correct = "rag/chroma/ollama" in chroma_path
        results.append(print_result(
            is_correct,
            f"Ollama Chroma path: {chroma_path}"
        ))
    except Exception as e:
        results.append(print_result(False, f"Failed to get chroma path: {str(e)}"))
    
    return all(results)


def test_document_loading():
    """Test 4: Documents can be loaded"""
    print_test_header("Document Loading")
    
    results = []
    
    try:
        # Try to load documents (may be empty if rag/data/ is empty)
        docs = load_documents()
        results.append(print_result(
            True,
            f"Documents loaded: {len(docs)} documents"
        ))
        return all(results)
    except Exception as e:
        results.append(print_result(
            False,
            f"Failed to load documents: {str(e)}"
        ))
        return all(results)


def test_document_chunking():
    """Test 5: Documents can be chunked"""
    print_test_header("Document Chunking")
    
    results = []
    
    try:
        # Load and chunk test documents
        docs = load_documents()
        if not docs:
            print(f"{YELLOW}⚠ Skipping chunking test (no documents loaded){RESET}")
            return True
        
        chunks = split_documents(docs)
        results.append(print_result(
            len(chunks) > 0,
            f"Documents chunked: {len(chunks)} chunks from {len(docs)} documents"
        ))
    except Exception as e:
        results.append(print_result(
            False,
            f"Failed to chunk documents: {str(e)}"
        ))
    
    return all(results)


def test_embedding_space_metadata():
    """Test 6: Chunks have embedding_space_id metadata"""
    print_test_header("Embedding Space Metadata")
    
    results = []
    
    try:
        docs = load_documents()
        if not docs:
            print(f"{YELLOW}⚠ Skipping metadata test (no documents loaded){RESET}")
            return True
        
        chunks = split_documents(docs)
        if not chunks:
            print(f"{YELLOW}⚠ Skipping metadata test (no chunks created){RESET}")
            return True
        
        # Add metadata
        chunks_with_metadata = calculate_chunk_ids(chunks, "ollama:nomic-embed-text:dim=768")
        
        # Check first chunk
        first_chunk = chunks_with_metadata[0]
        has_id = "id" in first_chunk.metadata
        has_space_id = "embedding_space_id" in first_chunk.metadata
        
        results.append(print_result(
            has_id,
            f"Chunk has 'id' metadata: {first_chunk.metadata.get('id')}"
        ))
        results.append(print_result(
            has_space_id,
            f"Chunk has 'embedding_space_id' metadata: {first_chunk.metadata.get('embedding_space_id')}"
        ))
    except Exception as e:
        results.append(print_result(
            False,
            f"Failed to verify metadata: {str(e)}"
        ))
    
    return all(results)


def test_rag_query():
    """Test 7: RAG query can complete end-to-end"""
    print_test_header("RAG Query (End-to-End)")
    
    results = []
    
    try:
        query = "What is this about?"
        response = query_rag(query)
        
        results.append(print_result(
            len(response) > 0,
            f"RAG query returned response: {len(response)} characters"
        ))
        print(f"  Response preview: {response[:100]}...")
    except Exception as e:
        results.append(print_result(
            False,
            f"RAG query failed: {str(e)}"
        ))
    
    return all(results)


def main():
    """Run all tests"""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}REGRESSION TEST: Ollama Only (Original Configuration){RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    print(f"Embedding Provider: {ACTIVE_EMBEDDING_PROVIDER}")
    print(f"Generation Provider: {ACTIVE_GENERATION_PROVIDER}")
    
    test_results = []
    
    # Run tests in order
    test_results.append(test_provider_config())
    test_results.append(test_provider_initialization())
    test_results.append(test_collection_routing())
    test_results.append(test_document_loading())
    test_results.append(test_document_chunking())
    test_results.append(test_embedding_space_metadata())
    test_results.append(test_rag_query())
    
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
