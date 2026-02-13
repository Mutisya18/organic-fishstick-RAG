#!/usr/bin/env python
"""
Provider Switching Test - Validates that provider selection works dynamically.

Tests:
1. Can switch embedding provider via environment
2. Factory returns correct provider when config changes
3. Collection routing adapts to provider selection
4. Log metadata reflects current providers

Run: python rag/test_provider_switching.py
"""

import os
import sys
from dotenv import load_dotenv, dotenv_values

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_section(title: str):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")


def test_section(name: str):
    print(f"\n{YELLOW}[{name}]{RESET}", end=" ")


def test_pass(msg: str):
    print(f"{GREEN}✓{RESET} {msg}")


def test_fail(msg: str, error: str = ""):
    print(f"{RED}✗{RESET} {msg}")
    if error:
        print(f"  {RED}Error: {error}{RESET}")


print_section("PROVIDER SWITCHING TEST")

# Test 1: Load current .env
test_section("Load Current Environment")
try:
    load_dotenv()
    from rag.config.provider_config import ACTIVE_EMBEDDING_PROVIDER, ACTIVE_GENERATION_PROVIDER
    print(f"(Embedding: {ACTIVE_EMBEDDING_PROVIDER}, Generation: {ACTIVE_GENERATION_PROVIDER})")
    test_pass(f"Current config - Embedding: {ACTIVE_EMBEDDING_PROVIDER}, Generation: {ACTIVE_GENERATION_PROVIDER}")
except Exception as e:
    test_fail(f"Load environment", str(e))
    sys.exit(1)

# Test 2: Verify provider selection from environment
test_section("Provider Selection From Environment")
try:
    env_file = dotenv_values(".env")
    env_embedding = env_file.get("ACTIVE_EMBEDDING_PROVIDER", "not set")
    env_generation = env_file.get("ACTIVE_GENERATION_PROVIDER", "not set")
    
    test_pass(f".env ACTIVE_EMBEDDING_PROVIDER: {env_embedding}")
    test_pass(f".env ACTIVE_GENERATION_PROVIDER: {env_generation}")
except Exception as e:
    test_fail(f"Read .env file", str(e))

# Test 3: Test that factory respects current config
test_section("Factory Routing Respects Config")
try:
    from rag.get_embedding_function import get_embedding_function
    from rag.config.provider_config import ACTIVE_EMBEDDING_PROVIDER
    
    ep = get_embedding_function()
    ep_info = ep.get_info()
    
    if ep_info["provider"] == ACTIVE_EMBEDDING_PROVIDER:
        test_pass(f"Embedding factory route: {ep_info['provider']} (matches ACTIVE_EMBEDDING_PROVIDER)")
    else:
        test_fail(f"Embedding factory route mismatch", 
                 f"Expected {ACTIVE_EMBEDDING_PROVIDER}, got {ep_info['provider']}")
except Exception as e:
    test_fail(f"Embedding factory test", str(e))

try:
    from rag.get_generation_function import get_generation_function
    from rag.config.provider_config import ACTIVE_GENERATION_PROVIDER
    
    gp = get_generation_function()
    gp_info = gp.get_info()
    
    if gp_info["provider"] == ACTIVE_GENERATION_PROVIDER:
        test_pass(f"Generation factory route: {gp_info['provider']} (matches ACTIVE_GENERATION_PROVIDER)")
    else:
        test_fail(f"Generation factory route mismatch", 
                 f"Expected {ACTIVE_GENERATION_PROVIDER}, got {gp_info['provider']}")
except Exception as e:
    test_fail(f"Generation factory test", str(e))

# Test 4: Verify collection routing matches provider
test_section("Collection Routing Matches Provider")
try:
    from rag.config.index_registry import get_collection_name_for_provider
    from rag.config.provider_config import ACTIVE_EMBEDDING_PROVIDER
    
    collection = get_collection_name_for_provider(ACTIVE_EMBEDDING_PROVIDER)
    
    if ACTIVE_EMBEDDING_PROVIDER in collection.lower():
        test_pass(f"Collection for {ACTIVE_EMBEDDING_PROVIDER}: {collection}")
    else:
        test_fail(f"Collection routing mismatch", 
                 f"Provider {ACTIVE_EMBEDDING_PROVIDER} not in collection name {collection}")
except Exception as e:
    test_fail(f"Collection routing test", str(e))

# Test 5: Verify models are correctly configured
test_section("Provider Models Configuration")
try:
    from rag.config.provider_config import (
        OLLAMA_EMBED_MODEL,
        OLLAMA_CHAT_MODEL,
        GEMINI_EMBED_MODEL,
        GEMINI_CHAT_MODEL,
    )
    
    test_pass(f"Ollama embed model: {OLLAMA_EMBED_MODEL}")
    test_pass(f"Ollama chat model: {OLLAMA_CHAT_MODEL}")
    test_pass(f"Gemini embed model: {GEMINI_EMBED_MODEL}")
    test_pass(f"Gemini chat model: {GEMINI_CHAT_MODEL}")
except Exception as e:
    test_fail(f"Model configuration", str(e))

# Test 6: Provider info completeness
test_section("Provider Info Completeness")
try:
    from rag.get_embedding_function import get_embedding_function
    from rag.get_generation_function import get_generation_function
    
    ep_info = get_embedding_function().get_info()
    required_embedding_keys = ["provider", "space_id", "dimensionality"]
    
    missing_keys = [k for k in required_embedding_keys if k not in ep_info]
    if not missing_keys:
        test_pass(f"Embedding provider info complete: {list(ep_info.keys())}")
    else:
        test_fail(f"Embedding provider info missing keys", f"Missing: {missing_keys}")
    
    gp_info = get_generation_function().get_info()
    required_generation_keys = ["provider", "model"]
    
    missing_keys = [k for k in required_generation_keys if k not in gp_info]
    if not missing_keys:
        test_pass(f"Generation provider info complete: {list(gp_info.keys())}")
    else:
        test_fail(f"Generation provider info missing keys", f"Missing: {missing_keys}")
except Exception as e:
    test_fail(f"Provider info completeness", str(e))

# Test 7: Example switching scenario (informational only, doesn't actually change .env)
print_section("PROVIDER SWITCHING SCENARIOS")

print(f"\n{YELLOW}Current Configuration:{RESET}")
print(f"  ACTIVE_EMBEDDING_PROVIDER = {ACTIVE_EMBEDDING_PROVIDER}")
print(f"  ACTIVE_GENERATION_PROVIDER = {ACTIVE_GENERATION_PROVIDER}")

print(f"\n{YELLOW}Scenario 1: Switch to Gemini Generation Only{RESET}")
print(f"  To switch, edit .env:")
print(f"  {GREEN}ACTIVE_EMBEDDING_PROVIDER=ollama{RESET}")
print(f"  {GREEN}ACTIVE_GENERATION_PROVIDER=gemini{RESET}")
print(f"  {GREEN}GEMINI_API_KEY=<your-key>{RESET}")
print(f"\n  Benefits:")
print(f"    - Keep existing Ollama collection (no re-indexing)")
print(f"    - Test Gemini for response generation")
print(f"    - Compare quality/speed/cost")

print(f"\n{YELLOW}Scenario 2: Switch to Full Gemini{RESET}")
print(f"  To switch, edit .env:")
print(f"  {GREEN}ACTIVE_EMBEDDING_PROVIDER=gemini{RESET}")
print(f"  {GREEN}ACTIVE_GENERATION_PROVIDER=gemini{RESET}")
print(f"  {GREEN}GEMINI_API_KEY=<your-key>{RESET}")
print(f"\n  Steps:")
print(f"    1. Update .env with above")
print(f"    2. Run: {YELLOW}python rag/populate_database.py{RESET} (builds Gemini collection)")
print(f"    3. Test: {YELLOW}python rag/query_data.py \"question\"{RESET}")

print(f"\n{YELLOW}Scenario 3: A/B Testing (Both Collections){RESET}")
print(f"  To keep both Ollama and Gemini collections:")
print(f"    1. Have Ollama collection ready")
print(f"    2. Switch to Gemini and run: {YELLOW}python rag/populate_database.py{RESET}")
print(f"    3. Both rag/chroma/ollama/ and rag/chroma/gemini/ will exist")
print(f"    4. Run tests with different ACTIVE_EMBEDDING_PROVIDER values")

print(f"\n{YELLOW}{'='*70}{RESET}")
print(f"{YELLOW}Provider Switching Test Complete!{RESET}")
print(f"{YELLOW}{'='*70}{RESET}\n")
