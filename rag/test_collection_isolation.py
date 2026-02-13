#!/usr/bin/env python
"""
Collection Isolation & Metadata Validation Test.

Verifies:
1. Both Ollama and Gemini collection directories can coexist
2. Chunks have correct embedding_space_id metadata
3. Collection routing prevents cross-provider queries
4. Metadata integrity across operations

Run: python rag/test_collection_isolation.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.config.provider_config import (
    DEBUG_MODE,
)
from rag.config.index_registry import (
    get_collection_name_for_provider,
    get_chroma_path_for_provider,
    get_embedding_space_id,
    validate_embedding_space_match,
)
from rag.populate_database import (
    load_documents,
    split_documents,
    calculate_chunk_ids,
)

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def test_section(name: str):
    print(f"\n{YELLOW}═══ {name} ═══{RESET}")


def test_pass(msg: str):
    print(f"{GREEN}✓{RESET} {msg}")


def test_fail(msg: str, error: str = ""):
    print(f"{RED}✗{RESET} {msg}")
    if error:
        print(f"  {RED}Error: {error}{RESET}")


print(f"\n{YELLOW}{'='*70}{RESET}")
print(f"{YELLOW}Collection Isolation & Metadata Validation{RESET}")
print(f"{YELLOW}{'='*70}{RESET}")

# Test 1: Collection Directory Structure
test_section("Collection Directory Structure")

ollama_path = get_chroma_path_for_provider("ollama")
gemini_path = get_chroma_path_for_provider("gemini")

try:
    assert "ollama" in ollama_path, "Ollama path doesn't contain 'ollama'"
    test_pass(f"Ollama path correct: {ollama_path}")
except AssertionError as e:
    test_fail(f"Ollama path validation", str(e))

try:
    assert "gemini" in gemini_path, "Gemini path doesn't contain 'gemini'"
    test_pass(f"Gemini path correct: {gemini_path}")
except AssertionError as e:
    test_fail(f"Gemini path validation", str(e))

try:
    assert ollama_path != gemini_path, "Paths should be different"
    test_pass(f"Paths are isolated")
except AssertionError as e:
    test_fail(f"Path isolation", str(e))

# Test 2: Collection Names
test_section("Collection Names")

ollama_collection = get_collection_name_for_provider("ollama")
gemini_collection = get_collection_name_for_provider("gemini")

try:
    assert "ollama" in ollama_collection.lower(), "Ollama collection name invalid"
    test_pass(f"Ollama collection: {ollama_collection}")
except AssertionError as e:
    test_fail(f"Ollama collection name", str(e))

try:
    assert "gemini" in gemini_collection.lower(), "Gemini collection name invalid"
    test_pass(f"Gemini collection: {gemini_collection}")
except AssertionError as e:
    test_fail(f"Gemini collection name", str(e))

try:
    assert ollama_collection != gemini_collection, "Collection names should differ"
    test_pass(f"Collection names are isolated")
except AssertionError as e:
    test_fail(f"Collection name isolation", str(e))

# Test 3: Embedding Space IDs
test_section("Embedding Space IDs")

ollama_space = get_embedding_space_id("ollama")
gemini_space = get_embedding_space_id("gemini")

try:
    assert "ollama" in ollama_space.lower(), "Ollama space_id invalid"
    assert "nomic" in ollama_space.lower(), "Space ID should include model name"
    assert "768" in ollama_space, "Space ID should include dimension"
    test_pass(f"Ollama space_id: {ollama_space}")
except AssertionError as e:
    test_fail(f"Ollama space_id format", str(e))

try:
    assert "gemini" in gemini_space.lower(), "Gemini space_id invalid"
    assert "embedding" in gemini_space.lower(), "Space ID should include model name"
    assert "768" in gemini_space, "Space ID should include dimension"
    test_pass(f"Gemini space_id: {gemini_space}")
except AssertionError as e:
    test_fail(f"Gemini space_id format", str(e))

try:
    assert ollama_space != gemini_space, "Space IDs should be different"
    test_pass(f"Space IDs are isolated")
except AssertionError as e:
    test_fail(f"Space ID isolation", str(e))

# Test 4: Metadata in Chunks
test_section("Chunk Metadata")

try:
    # Load and process documents
    docs = load_documents()
    if not docs:
        print(f"{YELLOW}⚠ No documents loaded, skipping chunk metadata test{RESET}")
    else:
        chunks = split_documents(docs)
        
        # Test Ollama metadata
        ollama_chunks = calculate_chunk_ids(chunks.copy(), ollama_space)
        
        # Verify first chunk has metadata
        first_chunk = ollama_chunks[0]
        assert "id" in first_chunk.metadata, "Chunk missing 'id' in metadata"
        assert "embedding_space_id" in first_chunk.metadata, "Chunk missing 'embedding_space_id'"
        
        chunk_space = first_chunk.metadata["embedding_space_id"]
        assert chunk_space == ollama_space, f"Space mismatch: {chunk_space} != {ollama_space}"
        
        test_pass(f"Chunk has correct id: {first_chunk.metadata['id'][:50]}...")
        test_pass(f"Chunk has correct embedding_space_id: {chunk_space}")
        
        # Verify multiple chunks
        for i in range(min(5, len(ollama_chunks))):
            chunk = ollama_chunks[i]
            assert chunk.metadata["embedding_space_id"] == ollama_space, \
                f"Chunk {i} has mismatched space_id"
        
        test_pass(f"All {min(5, len(ollama_chunks))} sampled chunks have correct metadata")
        
except Exception as e:
    test_fail(f"Chunk metadata validation", str(e))

# Test 5: Embedding Space Validation Function
test_section("Embedding Space Validation")

try:
    # Valid match
    validate_embedding_space_match(ollama_space, ollama_space, strict=True)
    test_pass(f"Valid match detection works")
except Exception as e:
    test_fail(f"Valid match detection", str(e))

try:
    # Invalid match (should raise)
    try:
        validate_embedding_space_match(ollama_space, gemini_space, strict=True)
        test_fail(f"Should have detected space mismatch")
    except ValueError:
        test_pass(f"Mismatch detection works (strict=True)")
except Exception as e:
    test_fail(f"Mismatch detection", str(e))

try:
    # Invalid match (non-strict)
    result = validate_embedding_space_match(ollama_space, gemini_space, strict=False)
    assert result is False, "Should return False for mismatch"
    test_pass(f"Mismatch detection works (strict=False)")
except Exception as e:
    test_fail(f"Non-strict mismatch detection", str(e))

# Test 6: Multiple Providers Configuration
test_section("Multiple Providers Coexistence")

try:
    # Verify both provider paths can exist simultaneously
    ollama_path_obj = Path(get_chroma_path_for_provider("ollama"))
    gemini_path_obj = Path(get_chroma_path_for_provider("gemini"))
    
    # Check if they're in same parent but different subdirs
    assert ollama_path_obj.parent == gemini_path_obj.parent, \
        "Both collections should be in same parent (rag/chroma/)"
    test_pass(f"Both collections can coexist in: {ollama_path_obj.parent}")
    
    # Verify they're different
    assert ollama_path_obj != gemini_path_obj, "Paths must be different"
    test_pass(f"Collections are isolated from each other")
    
except Exception as e:
    test_fail(f"Coexistence validation", str(e))

print(f"\n{YELLOW}{'='*70}{RESET}")
print(f"{YELLOW}Collection Isolation Test Complete!{RESET}")
print(f"{YELLOW}{'='*70}{RESET}\n")
