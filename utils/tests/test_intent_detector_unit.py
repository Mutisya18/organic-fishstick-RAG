"""Unit tests for eligibility.intent_detector module - SIMPLIFIED"""

import pytest
from eligibility.intent_detector import IntentDetector


class TestIntentDetector:
    """Test suite for IntentDetector - simplified for actual implementation"""
    
    def setup_method(self):
        """Setup for each test"""
        self.detector = IntentDetector()
    
    # ===== POSITIVE TESTS (Should detect eligibility) =====
    
    def test_detect_is_eligible_keyword(self):
        """Test detection of 'eligible' keyword"""
        message = "Is the customer eligible for a loan?"
        is_eligible, hash_val = self.detector.detect(message)
        assert is_eligible is True
        assert isinstance(hash_val, str)
    
    def test_detect_eligibility_check_keyword(self):
        """Test detection of 'check eligibility' phrase"""
        message = "Please check eligibility for account 1234567890"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is True
    
    def test_detect_why_no_limit_keyword(self):
        """Test detection of 'why no limit' phrase"""
        message = "Why is there no limit for this account?"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is True
    
    def test_detect_loan_limit_issue_keyword(self):
        """Test detection of 'loan limit issue' phrase"""
        message = "There's a loan limit issue with account 1234567890"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is True
    
    def test_detect_not_getting_limit_keyword(self):
        """Test detection of 'not getting limit' phrase"""
        message = "Customer is not getting limit approval"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is True
    
    def test_detect_limit_allocation_keyword(self):
        """Test detection of 'limit allocation' keyword"""
        message = "Limit allocation failed for this account"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is True
    
    def test_detect_why_excluded_keyword(self):
        """Test detection of 'why excluded' phrase"""
        message = "Why is the customer excluded?"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is True
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive"""
        messages = [
            "IS THE CUSTOMER ELIGIBLE?",
            "is the customer eligible?",
            "Is The Customer Eligible?",
        ]
        for message in messages:
            is_eligible, _ = self.detector.detect(message)
            assert is_eligible is True, f"Failed for: {message}"
    
    def test_detect_with_account_number(self):
        """Test detection with account number present"""
        message = "Is account 1234567890 eligible?"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is True
    
    # ===== NEGATIVE TESTS (Should NOT detect eligibility) =====
    
    def test_reject_normal_loan_question(self):
        """Test that normal loan questions are not detected"""
        message = "What are the loan requirements?"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is False
    
    def test_reject_general_banking_question(self):
        """Test rejection of general banking questions"""
        message = "How do I open a new account?"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is False
    
    def test_reject_unrelated_message(self):
        """Test rejection of completely unrelated messages"""
        message = "What's the weather today?"
        is_eligible, _ = self.detector.detect(message)
        assert is_eligible is False
    
    def test_reject_empty_message(self):
        """Test rejection of empty message"""
        is_eligible, _ = self.detector.detect("")
        assert is_eligible is False
    
    def test_reject_whitespace_only(self):
        """Test rejection of whitespace-only message"""
        is_eligible, _ = self.detector.detect("   \n\t   ")
        assert is_eligible is False
    
    # ===== MESSAGE HASHING =====
    
    def test_message_hash_returns_string(self):
        """Test that message hash is a string"""
        message = "Is account 1234567890 eligible?"
        _, hash_val = self.detector.detect(message)
        assert isinstance(hash_val, str)
    
    def test_message_hash_consistency(self):
        """Test that same message produces same hash"""
        message = "Is account 1234567890 eligible?"
        _, hash1 = self.detector.detect(message)
        _, hash2 = self.detector.detect(message)
        assert hash1 == hash2
    
    def test_message_hash_different_for_different_messages(self):
        """Test that different messages produce different hashes"""
        _, hash1 = self.detector.detect("Message 1")
        _, hash2 = self.detector.detect("Message 2")
        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
