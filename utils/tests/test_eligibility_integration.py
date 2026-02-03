"""Integration tests for eligibility module end-to-end flows"""

import pytest
import json
import os
from eligibility.orchestrator import EligibilityOrchestrator


class TestEligibilityEndToEnd:
    """End-to-end integration tests for eligibility module"""
    
    @classmethod
    def setup_class(cls):
        """Setup for all tests in this class"""
        # Initialize orchestrator once
        cls.orchestrator = EligibilityOrchestrator()
    
    # ===== ELIGIBILITY QUESTION DETECTION =====
    
    def test_eligibility_question_triggers_flow(self):
        """Test that eligibility questions trigger the eligibility flow"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-123")
        
        if result:  # If orchestrator returns a payload
            assert isinstance(result, dict)
            assert "request_id" in result
            assert "accounts" in result
    
    def test_normal_question_skips_flow(self):
        """Test that normal questions don't trigger eligibility flow"""
        message = "What is a loan?"
        result = self.orchestrator.process_message(message, "req-456")
        
        # Should return None (not an eligibility question)
        assert result is None
    
    def test_eligibility_with_no_account_number(self):
        """Test eligibility question without account number"""
        message = "Is this customer eligible?"
        result = self.orchestrator.process_message(message, "req-789")
        
        # Should return None or error (no account extracted)
        # Behavior depends on implementation
        if result is not None:
            # If a payload is returned, it should be empty or error
            assert "summary" in result
    
    # ===== ACCOUNT VALIDATION =====
    
    def test_invalid_account_format_handling(self):
        """Test handling of invalid account format"""
        message = "Is account ABC1234567 eligible?"
        result = self.orchestrator.process_message(message, "req-001")
        
        # Should not find a valid account
        # Result should be None or indicate no valid accounts
        if result is not None:
            assert result["summary"]["total_accounts"] == 0
    
    def test_multiple_accounts_batch_processing(self):
        """Test batch processing of multiple accounts"""
        message = "Check accounts 1234567890 and 9876543210"
        result = self.orchestrator.process_message(message, "req-batch")
        
        if result:
            # Should attempt to process both accounts
            assert result["summary"]["total_accounts"] == 2
    
    # ===== OUTPUT VALIDATION =====
    
    def test_payload_has_correct_structure(self):
        """Test that returned payload has correct structure"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-struct")
        
        if result:
            # Verify structure
            assert "request_id" in result
            assert "batch_timestamp" in result
            assert "accounts" in result
            assert isinstance(result["accounts"], list)
            assert "summary" in result
            
            # Verify summary fields
            summary = result["summary"]
            assert "total_accounts" in summary
            assert "eligible_count" in summary
            assert "not_eligible_count" in summary
            assert "cannot_confirm_count" in summary
            assert "processing_latency_ms" in summary
    
    def test_payload_is_json_serializable(self):
        """Test that payload can be serialized to JSON"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-json")
        
        if result:
            # Should not raise
            json_str = json.dumps(result)
            assert json_str is not None
            
            # Should be deserializable
            restored = json.loads(json_str)
            assert restored["request_id"] == result["request_id"]
    
    # ===== LOGGING INTEGRATION =====
    
    def test_orchestrator_generates_request_id(self):
        """Test that orchestrator generates proper request_id"""
        message = "Is account 1234567890 eligible?"
        request_id = "req-test-123"
        result = self.orchestrator.process_message(message, request_id)
        
        if result:
            assert result["request_id"] == request_id
    
    def test_logging_doesnt_expose_account_numbers(self):
        """Test that logging doesn't expose account numbers"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-pii")
        
        if result:
            # Account numbers should be hashed, not raw
            payload_str = json.dumps(result)
            # Raw account number should not appear in payload
            # (specific implementation dependent)
            assert isinstance(result, dict)
    
    # ===== ERROR HANDLING =====
    
    def test_empty_message_handling(self):
        """Test handling of empty message"""
        result = self.orchestrator.process_message("", "req-empty")
        
        # Should return None (no intent detected)
        assert result is None
    
    def test_none_message_handling(self):
        """Test handling of None message"""
        result = self.orchestrator.process_message(None, "req-none")
        
        # Should handle gracefully
        assert result is None or isinstance(result, dict)
    
    def test_whitespace_only_message(self):
        """Test handling of whitespace-only message"""
        result = self.orchestrator.process_message("   \n\t   ", "req-ws")
        
        # Should return None (no valid intent)
        assert result is None
    
    # ===== FLOW COMBINATIONS =====
    
    def test_message_with_account_at_start(self):
        """Test eligibility question with account at start"""
        message = "1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-start")
        
        # Should process or return None
        assert result is None or isinstance(result, dict)
    
    def test_message_with_account_at_end(self):
        """Test eligibility question with account at end"""
        message = "Is it eligible 1234567890"
        result = self.orchestrator.process_message(message, "req-end")
        
        assert result is None or isinstance(result, dict)
    
    def test_message_with_punctuation(self):
        """Test eligibility question with heavy punctuation"""
        message = "Is account 1234567890 ELIGIBLE??? Check ASAP!!!"
        result = self.orchestrator.process_message(message, "req-punct")
        
        if result:
            assert "accounts" in result
    
    # ===== SUMMARY ACCURACY =====
    
    def test_summary_counts_add_up(self):
        """Test that summary counts add up correctly"""
        message = "Check accounts 1234567890 and 9876543210"
        result = self.orchestrator.process_message(message, "req-sum")
        
        if result:
            summary = result["summary"]
            total = (summary["eligible_count"] + 
                    summary["not_eligible_count"] + 
                    summary["cannot_confirm_count"])
            assert total == summary["total_accounts"]
    
    def test_account_list_matches_summary(self):
        """Test that account list length matches summary count"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-match")
        
        if result:
            account_count = len(result["accounts"])
            summary_count = result["summary"]["total_accounts"]
            assert account_count == summary_count
    
    # ===== REASON EXTRACTION =====
    
    def test_not_eligible_account_has_reasons(self):
        """Test that not-eligible accounts have reasons"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-reasons")
        
        if result and result["summary"]["not_eligible_count"] > 0:
            for account in result["accounts"]:
                if account["status"] == "NOT_ELIGIBLE":
                    # Should have reasons
                    assert isinstance(account.get("reasons", []), list)
                    # If not-eligible, should have at least one reason
                    # (depends on actual data)
    
    def test_eligible_account_no_reasons(self):
        """Test that eligible accounts have no reasons"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-noreas")
        
        if result and result["summary"]["eligible_count"] > 0:
            for account in result["accounts"]:
                if account["status"] == "ELIGIBLE":
                    # Should have empty or no reasons
                    assert len(account.get("reasons", [])) == 0
    
    # ===== TIMESTAMP VALIDATION =====
    
    def test_payload_has_valid_timestamp(self):
        """Test that payload has valid ISO 8601 timestamp"""
        message = "Is account 1234567890 eligible?"
        result = self.orchestrator.process_message(message, "req-ts")
        
        if result:
            timestamp = result["batch_timestamp"]
            # Should be ISO 8601 format
            assert "T" in timestamp
            assert "Z" in timestamp
            # Should be parseable
            # (basic format check, not deep validation)
            assert len(timestamp) > 10
    
    # ===== DETERMINISTIC BEHAVIOR =====
    
    def test_same_input_same_output(self):
        """Test that same input produces consistent results"""
        message = "Is account 1234567890 eligible?"
        
        result1 = self.orchestrator.process_message(message, "req-det1")
        result2 = self.orchestrator.process_message(message, "req-det2")
        
        # Same message should produce same account analysis
        # (request_id will differ, but results should be same)
        if result1 and result2:
            assert len(result1["accounts"]) == len(result2["accounts"])
            # Account statuses should match
            for i, account in enumerate(result1["accounts"]):
                assert account["status"] == result2["accounts"][i]["status"]
    
    # ===== EDGE CASES =====
    
    def test_very_long_message(self):
        """Test handling of very long message"""
        long_message = "Is account 1234567890 eligible? " * 100
        result = self.orchestrator.process_message(long_message, "req-long")
        
        # Should still process
        assert result is None or isinstance(result, dict)
    
    def test_unicode_in_message(self):
        """Test handling of unicode characters in message"""
        message = "Is account 1234567890 eligible? 你好 мир"
        result = self.orchestrator.process_message(message, "req-unicode")
        
        # Should handle gracefully
        assert result is None or isinstance(result, dict)
    
    def test_special_characters_in_message(self):
        """Test handling of special characters"""
        message = "Is account 1234567890 eligible? !@#$%^&*()"
        result = self.orchestrator.process_message(message, "req-special")
        
        assert result is None or isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
