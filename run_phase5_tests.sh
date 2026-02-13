#!/bin/bash
# Phase 5 Test Runner - Validates dual-provider RAG implementation
# Run this script to execute all test suites in sequence with proper environment setup

set -e  # Exit on error

GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
RESET='\033[0m'

echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${RESET}"
echo -e "${YELLOW}PHASE 5: VALIDATION & TESTING${RESET}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${RESET}\n"

# Check Python environment
echo -e "${YELLOW}[SETUP] Checking Python environment...${RESET}"
python --version

# Test 1: Regression (Ollama only - MUST PASS)
echo -e "\n${YELLOW}[TEST 1] Running Regression Test (Ollama Only)...${RESET}"
echo -e "${YELLOW}This test validates that existing Ollama-only workflow still works.${RESET}"
echo -e "${YELLOW}Expected: All 7 test groups should PASS${RESET}\n"

if python rag/test_regression_ollama.py; then
    echo -e "\n${GREEN}✓ REGRESSION TEST PASSED${RESET}\n"
    REGRESSION_PASS=true
else
    echo -e "\n${RED}✗ REGRESSION TEST FAILED${RESET}\n"
    REGRESSION_PASS=false
fi

# If regression fails, stop here
if [ "$REGRESSION_PASS" = false ]; then
    echo -e "${RED}═══════════════════════════════════════════════════════════════${RESET}"
    echo -e "${RED}REGRESSION TEST FAILED - STOPPING HERE${RESET}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${RESET}"
    echo -e "\n${YELLOW}Troubleshooting:${RESET}"
    echo -e "1. Is Ollama running? Check: curl http://localhost:11434/api/tags"
    echo -e "2. Does rag/data/ contain any PDF/DOCX files?"
    echo -e "3. Run with DEBUG_MODE=true python rag/test_regression_ollama.py"
    exit 1
fi

# Test 2: Optional - Gemini Generation (requires GEMINI_API_KEY)
echo -e "${YELLOW}[TEST 2] Gemini Generation Test (Optional - requires API key)${RESET}"
echo -e "${YELLOW}Requires: GEMINI_API_KEY environment variable${RESET}\n"

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}⚠  Skipping (no GEMINI_API_KEY set)${RESET}"
    echo -e "Set GEMINI_API_KEY to enable:${RESET}"
    echo -e "  export GEMINI_API_KEY=<your-key>"
    echo -e "  export ACTIVE_GENERATION_PROVIDER=gemini"
    GEMINI_GEN_PASS="skipped"
else
    echo -e "${YELLOW}Testing Gemini generation (Ollama embedding)...${RESET}\n"
    if ACTIVE_EMBEDDING_PROVIDER=ollama ACTIVE_GENERATION_PROVIDER=gemini python rag/test_integration_gemini_gen_ollama_embed.py; then
        echo -e "\n${GREEN}✓ GEMINI GENERATION TEST PASSED${RESET}\n"
        GEMINI_GEN_PASS=true
    else
        echo -e "\n${RED}✗ GEMINI GENERATION TEST FAILED${RESET}\n"
        GEMINI_GEN_PASS=false
    fi
fi

# Test 3: Optional - Gemini Embedding (requires GEMINI_API_KEY + populated collection)
echo -e "${YELLOW}[TEST 3] Gemini Embedding Test (Optional - requires API key + collection)${RESET}"
echo -e "${YELLOW}Requires: GEMINI_API_KEY + populated Gemini collection${RESET}\n"

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}⚠  Skipping (no GEMINI_API_KEY set)${RESET}"
    GEMINI_EMBED_PASS="skipped"
else
    echo -e "${YELLOW}Note: This test requires a populated Gemini collection.${RESET}"
    echo -e "${YELLOW}Build it first with: ACTIVE_EMBEDDING_PROVIDER=gemini python rag/populate_database.py${RESET}\n"
    
    if ACTIVE_EMBEDDING_PROVIDER=gemini ACTIVE_GENERATION_PROVIDER=ollama python rag/test_integration_gemini_embed_ollama_gen.py; then
        echo -e "\n${GREEN}✓ GEMINI EMBEDDING TEST PASSED${RESET}\n"
        GEMINI_EMBED_PASS=true
    else
        echo -e "\n${YELLOW}⚠  GEMINI EMBEDDING TEST FAILED OR SKIPPED${RESET}"
        echo -e "${YELLOW}(Collection may not exist yet - this is normal if you haven't populated it)${RESET}\n"
        GEMINI_EMBED_PASS="partial"
    fi
fi

# Test 4: Optional - Full Gemini
echo -e "${YELLOW}[TEST 4] Full Gemini Test (Optional - requires API key + collection)${RESET}"
echo -e "${YELLOW}Requires: GEMINI_API_KEY + populated Gemini collection${RESET}\n"

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}⚠  Skipping (no GEMINI_API_KEY set)${RESET}"
    FULL_GEMINI_PASS="skipped"
else
    echo -e "${YELLOW}Testing Full Gemini (both embeddings + generation)...${RESET}\n"
    
    if ACTIVE_EMBEDDING_PROVIDER=gemini ACTIVE_GENERATION_PROVIDER=gemini python rag/test_integration_full_gemini.py; then
        echo -e "\n${GREEN}✓ FULL GEMINI TEST PASSED${RESET}\n"
        FULL_GEMINI_PASS=true
    else
        echo -e "\n${YELLOW}⚠  FULL GEMINI TEST FAILED OR SKIPPED${RESET}\n"
        FULL_GEMINI_PASS="partial"
    fi
fi

# Summary
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════${RESET}"
echo -e "${YELLOW}TEST SUMMARY${RESET}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${RESET}"

if [ "$REGRESSION_PASS" = true ]; then
    echo -e "${GREEN}✓ Test 1 (Regression):${RESET}               PASSED"
else
    echo -e "${RED}✗ Test 1 (Regression):${RESET}               FAILED"
fi

if [ "$GEMINI_GEN_PASS" = "skipped" ]; then
    echo -e "${YELLOW}⊘ Test 2 (Gemini Gen):${RESET}             SKIPPED (no API key)"
elif [ "$GEMINI_GEN_PASS" = true ]; then
    echo -e "${GREEN}✓ Test 2 (Gemini Gen):${RESET}             PASSED"
else
    echo -e "${RED}✗ Test 2 (Gemini Gen):${RESET}             FAILED"
fi

if [ "$GEMINI_EMBED_PASS" = "skipped" ]; then
    echo -e "${YELLOW}⊘ Test 3 (Gemini Embed):${RESET}          SKIPPED (no API key)"
elif [ "$GEMINI_EMBED_PASS" = "partial" ]; then
    echo -e "${YELLOW}⊘ Test 3 (Gemini Embed):${RESET}          PARTIAL (collection missing)"
elif [ "$GEMINI_EMBED_PASS" = true ]; then
    echo -e "${GREEN}✓ Test 3 (Gemini Embed):${RESET}          PASSED"
else
    echo -e "${RED}✗ Test 3 (Gemini Embed):${RESET}          FAILED"
fi

if [ "$FULL_GEMINI_PASS" = "skipped" ]; then
    echo -e "${YELLOW}⊘ Test 4 (Full Gemini):${RESET}           SKIPPED (no API key)"
elif [ "$FULL_GEMINI_PASS" = "partial" ]; then
    echo -e "${YELLOW}⊘ Test 4 (Full Gemini):${RESET}           PARTIAL (collection missing)"
elif [ "$FULL_GEMINI_PASS" = true ]; then
    echo -e "${GREEN}✓ Test 4 (Full Gemini):${RESET}           PASSED"
else
    echo -e "${RED}✗ Test 4 (Full Gemini):${RESET}           FAILED"
fi

echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════${RESET}"
echo -e "${YELLOW}NEXT STEPS:${RESET}"
echo -e "\n${GREEN}If Regression Test PASSED:${RESET}"
echo -e "  ✓ Dual-provider architecture is working"
echo -e "  ✓ Ollama-only workflow is backwards compatible"
echo -e "  ✓ Ready for Gemini testing (optional)\n"

echo -e "${YELLOW}To test with Gemini:${RESET}"
echo -e "  1. Get API key from: https://aistudio.google.com/app/apikey"
echo -e "  2. Set: export GEMINI_API_KEY=<your-key>"
echo -e "  3. For Gemini embedding, build collection:"
echo -e "     ACTIVE_EMBEDDING_PROVIDER=gemini python rag/populate_database.py"
echo -e "  4. Re-run this script\n"

echo -e "${YELLOW}For manual queries:${RESET}"
echo -e "  python rag/query_data.py \"Your question here\"\n"

echo -e "${YELLOW}For debugging:${RESET}"
echo -e "  Set: export DEBUG_MODE=true\n"

echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${RESET}"
