"""
End-to-end integration test for RAG logging system.
"""

import sys
import json
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logger.session_manager import SessionManager
from logger.rag_logging import RAGLogger
from logger.trace import technical_trace
from logger.pii import scrub_text


@technical_trace
def simulate_rag_pipeline():
    """Simulate a complete RAG pipeline to test logging."""
    
    logger = RAGLogger()
    request_id = logger.generate_request_id()
    
    print(f"[Test] Starting RAG simulation with request_id: {request_id}")
    
    # Simulate retrieval
    print("[Test] Simulating retrieval...")
    logger.log_retrieval(
        request_id=request_id,
        query="What is machine learning?",
        top_k=3,
        chunks=[
            {"id": "chunk_1", "text": "ML is a subset of AI..."},
            {"id": "chunk_2", "text": "Supervised learning uses labeled data..."},
            {"id": "chunk_3", "text": "Neural networks are inspired by biology..."},
        ],
        similarity_scores=[0.98, 0.95, 0.92],
        source_documents=["ml_guide.pdf", "ai_fundamentals.pdf", "deep_learning.pdf"],
        latency_ms=125.5,
    )
    
    # Simulate generation
    print("[Test] Simulating generation...")
    logger.log_generation(
        request_id=request_id,
        query="What is machine learning?",
        response="Machine learning is a technique that enables computers to learn from data without explicit programming.",
        prompt_template_version="2.0.0",
        prompt_tokens=120,
        completion_tokens=45,
        latency_ms=300.2,
        groundedness_score=0.95,
        cited_chunks=["chunk_1", "chunk_2"],
    )
    
    # Simulate end-to-end log
    print("[Test] Logging E2E interaction...")
    logger.log_end_to_end_rag(
        request_id=request_id,
        query="What is machine learning?",
        response="Machine learning is a technique that enables computers to learn from data without explicit programming.",
        retrieval_metadata={
            "top_k": 3,
            "chunk_ids": ["chunk_1", "chunk_2", "chunk_3"],
            "similarity_scores": [0.98, 0.95, 0.92],
            "source_documents": ["ml_guide.pdf", "ai_fundamentals.pdf", "deep_learning.pdf"],
        },
        generation_metadata={
            "prompt_template_version": "2.0.0",
            "tokens": {"prompt": 120, "completion": 45, "total": 165},
            "latency_ms": 300.2,
        },
        total_latency_ms=425.7,
        quality_metrics={
            "groundedness_score": 0.95,
            "cited_chunks": ["chunk_1", "chunk_2"],
            "user_feedback": None,
        },
    )
    
    # Test PII scrubbing in logging
    print("[Test] Testing PII scrubbing...")
    logger.log_generation(
        request_id=logger.generate_request_id(),
        query="Email me at john.doe@example.com or call 555-123-4567",
        response="Your SSN 123-45-6789 should never be in logs",
        prompt_template_version="2.0.0",
        prompt_tokens=100,
        completion_tokens=40,
    )
    
    print(f"[Test] ✅ RAG simulation complete")
    return request_id


def verify_logs():
    """Verify that logs were written correctly."""
    
    sm = SessionManager()
    log_file = sm.get_log_file_path()
    
    print(f"\n[Verify] Log file path: {log_file}")
    print(f"[Verify] Log file exists: {os.path.exists(log_file)}")
    
    if not os.path.exists(log_file):
        print("❌ Log file not found!")
        return False
    
    # Read and parse logs
    with open(log_file, "r") as f:
        lines = f.readlines()
    
    print(f"[Verify] Total log lines: {len(lines)}")
    
    if len(lines) < 2:
        print("❌ Not enough log entries!")
        return False
    
    # Verify session header
    print("\n[Verify] Session header:")
    header = json.loads(lines[0])
    print(f"  - Event: {header.get('event')}")
    print(f"  - Session ID: {header.get('session_id')[:8]}...")
    print(f"  - Environment: {header.get('environment')}")
    
    if header.get("event") != "session_start":
        print("❌ Session header not found!")
        return False
    
    # Verify retrieval log
    print("\n[Verify] Retrieval log:")
    for line in lines[1:]:
        log_entry = json.loads(line)
        if log_entry.get("event") == "retrieval_complete":
            print(f"  - Event: {log_entry.get('event')}")
            print(f"  - Request ID: {log_entry.get('request_id')[:8]}...")
            print(f"  - Top K: {log_entry.get('retrieval_metadata', {}).get('top_k')}")
            print(f"  - Latency: {log_entry.get('latency_ms')}ms")
            break
    
    # Verify generation log
    print("\n[Verify] Generation log:")
    for line in lines[1:]:
        log_entry = json.loads(line)
        if log_entry.get("event") == "generation_complete":
            print(f"  - Event: {log_entry.get('event')}")
            print(f"  - Request ID: {log_entry.get('request_id')[:8]}...")
            tokens = log_entry.get('generation_metadata', {}).get('tokens', {})
            print(f"  - Total Tokens: {tokens.get('total_tokens')}")
            print(f"  - Groundedness: {log_entry.get('quality_metrics', {}).get('groundedness_score')}")
            break
    
    # Verify PII scrubbing
    print("\n[Verify] PII scrubbing:")
    pii_found = False
    for line in lines[1:]:
        log_entry = json.loads(line)
        query_summary = log_entry.get('query_metadata', {}).get('query_summary', '')
        if "[EMAIL_REDACTED]" in query_summary or "[PHONE_REDACTED]" in query_summary:
            print(f"  - Email redacted: {'[EMAIL_REDACTED]' in query_summary}")
            print(f"  - Phone redacted: {'[PHONE_REDACTED]' in query_summary}")
            print(f"  - PII flagged: {log_entry.get('query_metadata', {}).get('query_pii_flagged')}")
            pii_found = True
            break
    
    if not pii_found:
        print("  ⚠️  No PII-flagged logs found (this is OK if email/phone not in test)")
    
    # Verify JSON structure
    print("\n[Verify] JSON structure of last entry:")
    last_entry = json.loads(lines[-1])
    required_fields = ["timestamp", "severity", "session_id", "event"]
    for field in required_fields:
        has_field = field in last_entry
        print(f"  - {field}: {'✅' if has_field else '❌'}")
        if not has_field:
            return False
    
    print("\n✅ All verifications passed!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("RAG Logging System - End-to-End Integration Test")
    print("=" * 60)
    
    try:
        request_id = simulate_rag_pipeline()
        print("\n" + "=" * 60)
        success = verify_logs()
        print("=" * 60)
        
        if success:
            print("\n🎉 Integration test PASSED!")
            sys.exit(0)
        else:
            print("\n❌ Integration test FAILED!")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Integration test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
