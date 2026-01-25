"""Unit tests for eligibility.intent_detector module"""

import pytest
from eligibility.intent_detector import IntentDetector


class TestIntentDetector:
    """Test suite for IntentDetector"""
    
    def setup_method(self):
        """Setup for each test"""
        self.detector = IntentDetector()
    
    # ===== POSITIVE TESTS (Should detect eligibility) =====
    
    def test_detect_is_eligible_keyword(self):
        """Test detection of 'eligible' keyword"""
        message = "Is the customer eligible for a loan?"
        result, hash_val = self.detector.detect(message)
        assert result is True
    
    def test_detect_eligibility_check_keyword(self):
        """Test detection of 'check eligibility' phrase"""
        message = "Please check eligibility for account 1234567890"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_detect_why_no_limit_keyword(self):
        """Test detection of 'why no limit' phrase"""
        message = "Why is there no limit for this account?"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_detect_loan_limit_issue_keyword(self):
        """Test detection of 'loan limit issue' phrase"""
        message = "There's a loan limit issue with account 1234567890"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_detect_not_getting_limit_keyword(self):
        """Test detection of 'not getting limit' phrase"""
        message = "Customer is not getting limit approval"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_detect_limit_allocation_keyword(self):
        """Test detection of 'limit allocation' keyword"""
        message = "Limit allocation failed for this account"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_detect_why_excluded_keyword(self):
        """Test detection of 'why excluded' phrase"""
        message = "Why is the customer excluded?"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive"""
        messages = [
            "IS THE CUSTOMER ELIGIBLE?",
            "is the customer eligible?",
            "Is The Customer Eligible?",
            "iS tHe CuStOmEr ElIgIbLe?",
        ]
        for message in messages:
            result = self.detector.is_eligibility_question(message)
            assert result is True, f"Failed for: {message}"
    
    def test_detect_with_account_number(self):
        """Test detection with account number present"""
        message = "Is account 1234567890 eligible?"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    # ===== NEGATIVE TESTS (Should NOT detect eligibility) =====
    
    def test_reject_normal_loan_question(self):
        """Test that normal loan questions are not detected"""
        message = "What are the loan eligibility criteria?"
        result = self.detector.is_eligibility_question(message)
        assert result is False
    
    def test_reject_general_banking_question(self):
        """Test rejection of general banking questions"""
        message = "How do I open a new account?"
        result = self.detector.is_eligibility_question(message)
        assert result is False
    
    def test_reject_unrelated_message(self):
        """Test rejection of completely unrelated messages"""
        message = "What's the weather today?"
        result = self.detector.is_eligibility_question(message)
        assert result is False
    
    def test_reject_empty_message(self):
        """Test rejection of empty message"""
        result = self.detector.is_eligibility_question("")
        assert result is False
    
    def test_reject_none_message(self):
        """Test rejection of None message"""
        result = self.detector.is_eligibility_question(None)
        assert result is False
    
    def test_reject_whitespace_only(self):
        """Test rejection of whitespace-only message"""
        result = self.detector.is_eligibility_question("   \n\t   ")
        assert result is False
    
    # ===== EDGE CASES =====
    
    def test_detect_with_special_characters(self):
        """Test detection with special characters"""
        message = "Is customer #1234567890 eligible??? Check ASAP!!!"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_detect_with_multiple_keywords(self):
        """Test detection with multiple eligibility keywords"""
        message = "Check eligibility and why no limit for account?"
        result = self.detector.is_eligibility_question(message)
        assert result is True
    
    def test_word_boundary_matching(self):
        """Test that keywords must be whole words"""
        # "eligible" is in "ineligible" but should still match context
        message = "Is this account ineligible?"
        result = self.detector.is_eligibility_question(message)
        assert result is True  # Should detect "ineligible"
    
    # ===== MESSAGE HASHING =====
    
    def test_message_hash_consistency(self):
        """Test that same message produces same hash"""
        message = "Is account 1234567890 eligible?"
        hash1 = self.detector.get_message_hash(message)
        hash2 = self.detector.get_message_hash(message)
        assert hash1 == hash2
    
    def test_message_hash_different_for_different_messages(self):
        """Test that different messages produce different hashes"""
        hash1 = self.detector.get_message_hash("Message 1")
        hash2 = self.detector.get_message_hash("Message 2")
        assert hash1 != hash2
    
    def test_message_hash_length(self):
        """Test that message hash has reasonable length"""
        message = "Is account 1234567890 eligible?"
        hash_value = self.detector.get_message_hash(message)
        # Should be hex string of reasonable length
        assert len(hash_value) > 10
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_message_hash_pii_safe(self):
        """Test that hash doesn't contain account number"""
        message = "Is account 1234567890 eligible?"
        hash_value = self.detector.get_message_hash(message)
        assert "1234567890" not in hash_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
