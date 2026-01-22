"""
Test suite for RAG logging system.
"""

import pytest
import json
import os
import time
import tempfile
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logger.session_manager import SessionManager
from logger.pii import scrub_text, scrub_dict
from logger.trace import technical_trace
from logger.rag_logging import RAGLogger


class TestPIIScrubbing:
    """Test PII detection and redaction."""
    
    def test_email_redaction(self):
        text = "Contact me at john.doe@example.com for more info"
        scrubbed, flagged = scrub_text(text)
        assert "[EMAIL_REDACTED]" in scrubbed
        assert flagged is True
    
    def test_phone_redaction(self):
        text = "Call me at 555-123-4567 or (555) 987-6543"
        scrubbed, flagged = scrub_text(text)
        assert "[PHONE_REDACTED]" in scrubbed
        assert flagged is True
    
    def test_ssn_redaction(self):
        text = "My SSN is 123-45-6789"
        scrubbed, flagged = scrub_text(text)
        assert "[SSN_REDACTED]" in scrubbed
        assert flagged is True
    
    def test_credit_card_redaction(self):
        text = "Payment: 4532-1234-5678-9101"
        scrubbed, flagged = scrub_text(text)
        assert "[CC_REDACTED]" in scrubbed
        assert flagged is True
    
    def test_no_pii(self):
        text = "This is a normal sentence without sensitive data"
        scrubbed, flagged = scrub_text(text)
        assert scrubbed == text
        assert flagged is False
    
    def test_dict_scrubbing(self):
        data = {
            "query": "Email john@example.com",
            "response": "Safe response"
        }
        scrubbed, flagged = scrub_dict(data, keys_to_scrub=["query"])
        assert "[EMAIL_REDACTED]" in scrubbed["query"]
        assert flagged is True


class TestSessionManager:
    """Test session-based log file management."""
    
    def test_singleton(self):
        sm1 = SessionManager()
        sm2 = SessionManager()
        assert sm1 is sm2
    
    def test_log_file_creation(self):
        sm = SessionManager()
        log_path = sm.get_log_file_path()
        assert os.path.exists(log_path)
        assert log_path.endswith(".log")
    
    def test_session_header(self):
        # Create a new session manager with temp dir
        with tempfile.TemporaryDirectory() as tmpdir:
            old_log_dir = SessionManager.LOG_DIR
            SessionManager.LOG_DIR = tmpdir
            
            # Create fresh instance
            SessionManager._instance = None
            sm = SessionManager()
            
            log_path = sm.get_log_file_path()
            with open(log_path, "r") as f:
                first_line = f.readline()
                header = json.loads(first_line)
                assert header["event"] == "session_start"
                assert "session_id" in header
                assert "system_version" in header
            
            # Restore
            SessionManager._instance = None
            SessionManager.LOG_DIR = old_log_dir
    
    def test_json_logging(self):
        sm = SessionManager()
        test_entry = {"event": "test", "message": "Hello"}
        sm.log(test_entry)
        
        # Read log and verify
        log_path = sm.get_log_file_path()
        with open(log_path, "r") as f:
            lines = f.readlines()
            # Should have header + test entry
            assert len(lines) >= 2
            last_line = json.loads(lines[-1])
            assert last_line["event"] == "test"
            assert last_line["message"] == "Hello"


class TestTechnicalTrace:
    """Test function tracing decorator."""
    
    def test_successful_trace(self):
        @technical_trace
        def sample_function(x, y):
            return x + y
        
        result = sample_function(2, 3)
        assert result == 5
    
    def test_exception_trace(self):
        @technical_trace
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()


class TestRAGLogger:
    """Test RAG-specific logging."""
    
    def test_generate_request_id(self):
        logger = RAGLogger()
        req_id = logger.generate_request_id()
        assert len(req_id) > 0
        assert "-" in req_id  # UUID format
    
    def test_hash_prompt(self):
        logger = RAGLogger()
        prompt = "This is a system prompt"
        hash_val = logger.hash_prompt(prompt)
        assert len(hash_val) == 16
        assert hash_val.isalnum()
    
    def test_log_retrieval(self):
        logger = RAGLogger()
        request_id = logger.generate_request_id()
        
        chunks = [
            {"id": "chunk_1", "text": "Content 1"},
            {"id": "chunk_2", "text": "Content 2"},
        ]
        
        logger.log_retrieval(
            request_id=request_id,
            query="What is AI?",
            top_k=2,
            chunks=chunks,
            similarity_scores=[0.95, 0.87],
            source_documents=["doc1.pdf", "doc2.pdf"],
            latency_ms=150.5,
        )
        
        # Verify log was written
        sm = SessionManager()
        log_path = sm.get_log_file_path()
        with open(log_path, "r") as f:
            lines = f.readlines()
            last_line = json.loads(lines[-1])
            assert last_line["event"] == "retrieval_complete"
            assert last_line["request_id"] == request_id
            assert last_line["retrieval_metadata"]["top_k"] == 2
    
    def test_log_generation(self):
        logger = RAGLogger()
        request_id = logger.generate_request_id()
        
        logger.log_generation(
            request_id=request_id,
            query="What is AI?",
            response="AI is artificial intelligence.",
            prompt_template_version="1.0.0",
            prompt_tokens=50,
            completion_tokens=25,
            latency_ms=200.3,
            groundedness_score=0.92,
            cited_chunks=["chunk_1", "chunk_2"],
        )
        
        sm = SessionManager()
        log_path = sm.get_log_file_path()
        with open(log_path, "r") as f:
            lines = f.readlines()
            last_line = json.loads(lines[-1])
            assert last_line["event"] == "generation_complete"
            assert last_line["request_id"] == request_id
            assert last_line["generation_metadata"]["tokens"]["total_tokens"] == 75
    
    def test_pii_scrubbing_in_logging(self):
        logger = RAGLogger()
        request_id = logger.generate_request_id()
        
        # Query with email
        query = "Contact support@company.com for help"
        response = "Your SSN 123-45-6789 is safe"
        
        logger.log_generation(
            request_id=request_id,
            query=query,
            response=response,
            prompt_template_version="1.0.0",
            prompt_tokens=50,
            completion_tokens=25,
        )
        
        sm = SessionManager()
        log_path = sm.get_log_file_path()
        with open(log_path, "r") as f:
            lines = f.readlines()
            last_line = json.loads(lines[-1])
            # Verify PII was redacted
            assert "[EMAIL_REDACTED]" in last_line["query_metadata"]["query_summary"]
            assert last_line["query_metadata"]["query_pii_flagged"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
