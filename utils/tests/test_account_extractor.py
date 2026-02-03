"""Unit tests for eligibility.account_extractor module"""

import pytest
from eligibility.account_extractor import AccountExtractor


class TestAccountExtractor:
    """Test suite for AccountExtractor"""
    
    def setup_method(self):
        """Setup for each test"""
        self.extractor = AccountExtractor()
    
    # ===== VALID EXTRACTION =====
    
    def test_extract_single_account(self):
        """Test extraction of single 10-digit account"""
        message = "Is account 1234567890 eligible?"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "1234567890"
    
    def test_extract_multiple_accounts(self):
        """Test extraction of multiple 10-digit accounts"""
        message = "Check accounts 1234567890 and 9876543210"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 2
        assert "1234567890" in accounts
        assert "9876543210" in accounts
    
    def test_extract_with_text_around_account(self):
        """Test extraction with surrounding text"""
        message = "The account 1234567890 needs eligibility check"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "1234567890"
    
    def test_extract_account_at_start(self):
        """Test extraction when account is at message start"""
        message = "1234567890 is not eligible"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "1234567890"
    
    def test_extract_account_at_end(self):
        """Test extraction when account is at message end"""
        message = "Check eligibility for 1234567890"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "1234567890"
    
    def test_extract_account_with_punctuation(self):
        """Test extraction with punctuation around account"""
        message = "Check account (1234567890)."
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "1234567890"
    
    # ===== DEDUPLICATION =====
    
    def test_deduplicate_same_account(self):
        """Test that duplicate accounts are removed"""
        message = "Accounts 1234567890 and 1234567890 need checking"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "1234567890"
    
    def test_deduplicate_multiple_occurrences(self):
        """Test deduplication with multiple occurrences"""
        message = "1234567890, 1234567890, 9876543210"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 2
        assert "1234567890" in accounts
        assert "9876543210" in accounts
    
    # ===== NO MATCHES =====
    
    def test_no_accounts_in_message(self):
        """Test extraction when no 10-digit numbers present"""
        message = "What is eligibility?"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 0
    
    def test_reject_9_digit_number(self):
        """Test that 9-digit numbers are not extracted"""
        message = "Check account 123456789"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 0
    
    def test_reject_11_digit_number(self):
        """Test that 11-digit numbers are not extracted"""
        message = "Check account 12345678901"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 0
    
    def test_partial_number_extraction(self):
        """Test extraction when multiple 10-digit sequences exist"""
        message = "9876543210 and 1234567890 both need checking"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 2
        assert "9876543210" in accounts
        assert "1234567890" in accounts
    
    # ===== EDGE CASES =====
    
    def test_empty_message(self):
        """Test extraction from empty message"""
        accounts = self.extractor.extract_accounts("")
        assert len(accounts) == 0
    
    def test_none_message(self):
        """Test extraction from None"""
        accounts = self.extractor.extract_accounts(None)
        assert len(accounts) == 0
    
    def test_whitespace_only_message(self):
        """Test extraction from whitespace-only message"""
        accounts = self.extractor.extract_accounts("   \n\t   ")
        assert len(accounts) == 0
    
    def test_account_with_leading_zeros(self):
        """Test extraction of account starting with zeros"""
        message = "Account 0000000001 is valid"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "0000000001"
    
    def test_all_digit_account(self):
        """Test extraction of all-digit account"""
        message = "1111111111 is a valid account"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 1
        assert accounts[0] == "1111111111"
    
    # ===== SPECIAL CHARACTERS =====
    
    def test_account_with_hyphen(self):
        """Test that accounts with hyphens are not extracted as single unit"""
        # E.g., "123456-7890" should not match as 10 consecutive digits
        message = "Account 123456-7890"
        accounts = self.extractor.extract_accounts(message)
        # Should not find as single account
        assert "123456-7890" not in accounts
    
    def test_multiple_accounts_with_commas(self):
        """Test extraction of accounts separated by commas"""
        message = "1234567890, 9876543210, 1111111111"
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 3
    
    def test_account_in_different_formats(self):
        """Test extraction from various formats"""
        message = "Accounts: 1234567890 (9876543210) and 1111111111."
        accounts = self.extractor.extract_accounts(message)
        assert len(accounts) == 3
    
    # ===== RETURN TYPE =====
    
    def test_return_type_is_list(self):
        """Test that return type is a list"""
        accounts = self.extractor.extract_accounts("1234567890")
        assert isinstance(accounts, list)
    
    def test_account_items_are_strings(self):
        """Test that extracted accounts are strings"""
        accounts = self.extractor.extract_accounts("1234567890")
        for account in accounts:
            assert isinstance(account, str)
    
    def test_order_preservation(self):
        """Test that account order is preserved"""
        message = "First 1234567890, second 9876543210"
        accounts = self.extractor.extract_accounts(message)
        assert accounts[0] == "1234567890"
        assert accounts[1] == "9876543210"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
