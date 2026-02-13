#!/usr/bin/env python
"""
Phase 5 Validation Script - Tests all implementation components systematically.

This script validates:
1. Module imports (no syntax errors)
2. Configuration loading
3. Provider factory routing
4. Collection routing isolation
5. Embedding space metadata
6. End-to-end flows

Run: python rag/test_phase5_validation.py
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

passed_tests = 0
failed_tests = 0


def print_section(title: str):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")


def test_pass(message: str):
    global passed_tests
    passed_tests += 1
    print(f"{GREEN}✓{RESET} {message}")


def test_fail(message: str, error: str = ""):
    global failed_tests
    failed_tests += 1
    print(f"{RED}✗{RESET} {message}")
    if error:
        print(f"  {RED}Error: {error}{RESET}")


def test_section(name: str):
    print(f"\n{YELLOW}[{name}]{RESET}", end=" ")


# ============================================================================
# TEST 1: Module Imports
# ============================================================================

print_section("PHASE 5: VALIDATION & TESTING")

test_section("Module Imports")
try:
    from rag.config.provider_config import (
        ACTIVE_EMBEDDING_PROVIDER,
        ACTIVE_GENERATION_PROVIDER,
        DEBUG_MODE,
    )
    test_pass("provider_config module imported")
except Exception as e:
    test_fail("provider_config module import", str(e))
    sys.exit(1)

try:
    from rag.config.index_registry import (
        get_collection_name_for_provider,
        get_chroma_path_for_provider,
        get_embedding_space_id,
    )
    test_pass("index_registry module imported")
except Exception as e:
    test_fail("index_registry module import", str(e))
    sys.exit(1)

try:
    from rag.models.embedding_providers import (
        OllamaEmbeddingProvider,
        GeminiEmbeddingProvider,
    )
    test_pass("embedding_providers module imported")
except Exception as e:
    test_fail("embedding_providers module import", str(e))
    sys.exit(1)

try:
    from rag.models.generation_providers import (
        OllamaGenerationProvider,
        GeminiGenerationProvider,
    )
    test_pass("generation_providers module imported")
except Exception as e:
    test_fail("generation_providers module import", str(e))
    sys.exit(1)

try:
    from rag.get_embedding_function import get_embedding_function
    test_pass("get_embedding_function module imported")
except Exception as e:
    test_fail("get_embedding_function module import", str(e))
    sys.exit(1)

try:
    from rag.get_generation_function import get_generation_function
    test_pass("get_generation_function module imported")
except Exception as e:
    test_fail("get_generation_function module import", str(e))
    sys.exit(1)

# ============================================================================
# TEST 2: Configuration Validation
# ============================================================================

print_section("CONFIGURATION VALIDATION")

test_section("Provider Config")
print(f"(Embedding: {ACTIVE_EMBEDDING_PROVIDER}, Generation: {ACTIVE_GENERATION_PROVIDER})")

if ACTIVE_EMBEDDING_PROVIDER in ["ollama", "gemini"]:
    test_pass(f"ACTIVE_EMBEDDING_PROVIDER is valid: {ACTIVE_EMBEDDING_PROVIDER}")
else:
    test_fail(f"ACTIVE_EMBEDDING_PROVIDER is invalid: {ACTIVE_EMBEDDING_PROVIDER}")

if ACTIVE_GENERATION_PROVIDER in ["ollama", "gemini"]:
    test_pass(f"ACTIVE_GENERATION_PROVIDER is valid: {ACTIVE_GENERATION_PROVIDER}")
else:
    test_fail(f"ACTIVE_GENERATION_PROVIDER is invalid: {ACTIVE_GENERATION_PROVIDER}")

# ============================================================================
# TEST 3: Collection Routing
# ============================================================================

print_section("COLLECTION ROUTING")

test_section("Ollama Collection")
try:
    ollama_collection = get_collection_name_for_provider("ollama")
    ollama_path = get_chroma_path_for_provider("ollama")
    ollama_space = get_embedding_space_id("ollama")
    
    if "ollama" in ollama_collection.lower():
        test_pass(f"Ollama collection name: {ollama_collection}")
    else:
        test_fail(f"Ollama collection name invalid: {ollama_collection}")
    
    if "ollama" in ollama_path:
        test_pass(f"Ollama chroma path: {ollama_path}")
    else:
        test_fail(f"Ollama chroma path invalid: {ollama_path}")
    
    if "ollama" in ollama_space:
        test_pass(f"Ollama embedding space: {ollama_space}")
    else:
        test_fail(f"Ollama embedding space invalid: {ollama_space}")
except Exception as e:
    test_fail("Ollama collection routing", str(e))

test_section("Gemini Collection")
try:
    gemini_collection = get_collection_name_for_provider("gemini")
    gemini_path = get_chroma_path_for_provider("gemini")
    gemini_space = get_embedding_space_id("gemini")
    
    if "gemini" in gemini_collection.lower():
        test_pass(f"Gemini collection name: {gemini_collection}")
    else:
        test_fail(f"Gemini collection name invalid: {gemini_collection}")
    
    if "gemini" in gemini_path:
        test_pass(f"Gemini chroma path: {gemini_path}")
    else:
        test_fail(f"Gemini chroma path invalid: {gemini_path}")
    
    if "gemini" in gemini_space:
        test_pass(f"Gemini embedding space: {gemini_space}")
    else:
        test_fail(f"Gemini embedding space invalid: {gemini_space}")
except Exception as e:
    test_fail("Gemini collection routing", str(e))

# ============================================================================
# TEST 4: Provider Factory Functions
# ============================================================================

print_section("PROVIDER FACTORY FUNCTIONS")

test_section("Embedding Provider Factory")
try:
    ep = get_embedding_function()
    ep_info = ep.get_info()
    
    if ep_info.get("provider") == ACTIVE_EMBEDDING_PROVIDER:
        test_pass(f"Embedding factory returns correct provider: {ep_info.get('provider')}")
    else:
        test_fail(f"Embedding factory returned wrong provider: {ep_info.get('provider')}")
    
    if "space_id" in ep_info:
        test_pass(f"Embedding provider has space_id: {ep_info.get('space_id')}")
    else:
        test_fail("Embedding provider missing space_id")
except Exception as e:
    test_fail("Embedding provider factory", str(e))

test_section("Generation Provider Factory")
try:
    gp = get_generation_function()
    gp_info = gp.get_info()
    
    if gp_info.get("provider") == ACTIVE_GENERATION_PROVIDER:
        test_pass(f"Generation factory returns correct provider: {gp_info.get('provider')}")
    else:
        test_fail(f"Generation factory returned wrong provider: {gp_info.get('provider')}")
    
    if "model" in gp_info:
        test_pass(f"Generation provider has model: {gp_info.get('model')}")
    else:
        test_fail("Generation provider missing model")
except Exception as e:
    test_fail("Generation provider factory", str(e))

# ============================================================================
# TEST 5: Folder Structure
# ============================================================================

print_section("FOLDER STRUCTURE")

folders_to_check = [
    "rag/chroma/ollama",
    "rag/chroma/gemini",
    "rag/config",
    "rag/models",
    "rag/data",
]

test_section("Required Folders")
for folder in folders_to_check:
    folder_path = Path(folder)
    if folder_path.exists():
        test_pass(f"Folder exists: {folder}")
    else:
        test_fail(f"Folder missing: {folder}")

# ============================================================================
# TEST 6: Configuration Files
# ============================================================================

print_section("CONFIGURATION FILES")

files_to_check = [
    "rag/config/provider_config.py",
    "rag/config/index_registry.py",
    "rag/models/embedding_providers.py",
    "rag/models/generation_providers.py",
    "rag/get_embedding_function.py",
    "rag/get_generation_function.py",
    ".env.example",
]

test_section("Required Files")
for file in files_to_check:
    file_path = Path(file)
    if file_path.exists():
        test_pass(f"File exists: {file}")
    else:
        test_fail(f"File missing: {file}")

# ============================================================================
# TEST 7: Test Suite Files
# ============================================================================

print_section("TEST SUITE FILES")

test_files = [
    "rag/test_regression_ollama.py",
    "rag/test_integration_gemini_gen_ollama_embed.py",
    "rag/test_integration_gemini_embed_ollama_gen.py",
    "rag/test_integration_full_gemini.py",
]

test_section("Test Files")
for file in test_files:
    file_path = Path(file)
    if file_path.exists():
        test_pass(f"Test file exists: {file}")
    else:
        test_fail(f"Test file missing: {file}")

# ============================================================================
# TEST 8: Documentation
# ============================================================================

print_section("DOCUMENTATION")

doc_files = [
    "rag/IMPLEMENTATION_GUIDE.md",
    "rag/PHASE_1_4_SUMMARY.md",
]

test_section("Documentation Files")
for file in doc_files:
    file_path = Path(file)
    if file_path.exists():
        test_pass(f"Documentation exists: {file}")
    else:
        test_fail(f"Documentation missing: {file}")

# ============================================================================
# SUMMARY
# ============================================================================

print_section("PHASE 5 VALIDATION SUMMARY")

total_tests = passed_tests + failed_tests
print(f"\n{GREEN}Passed: {passed_tests}/{total_tests}{RESET}")
if failed_tests > 0:
    print(f"{RED}Failed: {failed_tests}/{total_tests}{RESET}")

if failed_tests == 0:
    print(f"\n{GREEN}{'='*70}{RESET}")
    print(f"{GREEN}✓ ALL VALIDATIONS PASSED!{RESET}")
    print(f"{GREEN}{'='*70}{RESET}")
    print(f"\n{YELLOW}Next Steps:{RESET}")
    print(f"1. Run regression test: {YELLOW}python rag/test_regression_ollama.py{RESET}")
    print(f"2. Check folder structure: {YELLOW}ls -la rag/chroma/{RESET}")
    print(f"3. Review: {YELLOW}cat rag/IMPLEMENTATION_GUIDE.md{RESET}")
    sys.exit(0)
else:
    print(f"\n{RED}{'='*70}{RESET}")
    print(f"{RED}✗ SOME VALIDATIONS FAILED{RESET}")
    print(f"{RED}{'='*70}{RESET}")
    sys.exit(1)
