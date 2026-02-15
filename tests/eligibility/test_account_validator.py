"""Unit tests for eligibility.account_validator module"""

import pytest
from eligibility.account_validator import AccountValidator


class TestAccountValidator:
    """Test suite for AccountValidator"""
    
    def setup_method(self):
        """Setup for each test"""
        self.validator = AccountValidator()
    
    # ===== VALID ACCOUNTS =====
    
    def test_valid_10_digit_account(self):
        """Test that 10-digit numeric account is valid"""
        result = self.validator.validate_accounts(["1234567890"])
        assert len(result["valid"]) == 1
        assert result["valid"][0] == "1234567890"
        assert len(result["invalid"]) == 0
    
    def test_multiple_valid_accounts(self):
        """Test multiple valid accounts"""
        accounts = ["1234567890", "9876543210", "1111111111"]
        result = self.validator.validate_accounts(accounts)
        assert len(result["valid"]) == 3
        assert len(result["invalid"]) == 0
    
    def test_account_with_leading_zeros(self):
        """Test account with leading zeros is valid"""
        result = self.validator.validate_accounts(["0000000001"])
        assert len(result["valid"]) == 1
        assert result["valid"][0] == "0000000001"
    
    def test_all_zeros_account(self):
        """Test all-zeros account is valid"""
        result = self.validator.validate_accounts(["0000000000"])
        assert len(result["valid"]) == 1
        assert result["valid"][0] == "0000000000"
    
    def test_all_nines_account(self):
        """Test all-nines account is valid"""
        result = self.validator.validate_accounts(["9999999999"])
        assert len(result["valid"]) == 1
        assert result["valid"][0] == "9999999999"
    
    # ===== INVALID ACCOUNTS =====
    
    def test_9_digit_account_invalid(self):
        """Test that 9-digit account is invalid"""
        result = self.validator.validate_accounts(["123456789"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
        assert result["invalid"][0] == "123456789"
    
    def test_11_digit_account_invalid(self):
        """Test that 11-digit account is invalid"""
        result = self.validator.validate_accounts(["12345678901"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
        assert result["invalid"][0] == "12345678901"
    
    def test_account_with_letters_invalid(self):
        """Test that account with letters is invalid"""
        result = self.validator.validate_accounts(["123456789A"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    def test_account_with_special_characters_invalid(self):
        """Test that account with special characters is invalid"""
        result = self.validator.validate_accounts(["12345678-90"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    def test_account_with_spaces_invalid(self):
        """Test that account with spaces is invalid"""
        result = self.validator.validate_accounts(["1234567 890"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    # ===== MIXED VALID AND INVALID =====
    
    def test_mixed_valid_and_invalid_accounts(self):
        """Test mix of valid and invalid accounts"""
        accounts = [
            "1234567890",    # Valid
            "123456789",     # Invalid (9 digits)
            "9876543210",    # Valid
            "12345678901",   # Invalid (11 digits)
        ]
        result = self.validator.validate_accounts(accounts)
        assert len(result["valid"]) == 2
        assert len(result["invalid"]) == 2
        assert "1234567890" in result["valid"]
        assert "9876543210" in result["valid"]
        assert "123456789" in result["invalid"]
        assert "12345678901" in result["invalid"]
    
    # ===== EDGE CASES =====
    
    def test_empty_list(self):
        """Test validation of empty list"""
        result = self.validator.validate_accounts([])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 0
    
    def test_none_input(self):
        """Test validation of None input"""
        result = self.validator.validate_accounts(None)
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 0
    
    def test_empty_string_account(self):
        """Test validation of empty string account"""
        result = self.validator.validate_accounts([""])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    def test_whitespace_only_account(self):
        """Test validation of whitespace-only account"""
        result = self.validator.validate_accounts(["   "])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    # ===== RETURN TYPE AND STRUCTURE =====
    
    def test_return_type_is_dict(self):
        """Test that return value is a dictionary"""
        result = self.validator.validate_accounts(["1234567890"])
        assert isinstance(result, dict)
    
    def test_return_has_valid_key(self):
        """Test that return dict has 'valid' key"""
        result = self.validator.validate_accounts(["1234567890"])
        assert "valid" in result
    
    def test_return_has_invalid_key(self):
        """Test that return dict has 'invalid' key"""
        result = self.validator.validate_accounts(["1234567890"])
        assert "invalid" in result
    
    def test_valid_is_list(self):
        """Test that 'valid' value is a list"""
        result = self.validator.validate_accounts(["1234567890"])
        assert isinstance(result["valid"], list)
    
    def test_invalid_is_list(self):
        """Test that 'invalid' value is a list"""
        result = self.validator.validate_accounts(["1234567890"])
        assert isinstance(result["invalid"], list)
    
    # ===== CASE SENSITIVITY =====
    
    def test_uppercase_letters_invalid(self):
        """Test that uppercase letters make account invalid"""
        result = self.validator.validate_accounts(["12345678A0"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    def test_lowercase_letters_invalid(self):
        """Test that lowercase letters make account invalid"""
        result = self.validator.validate_accounts(["12345678a0"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    # ===== FLOATING POINT NUMBERS =====
    
    def test_decimal_point_invalid(self):
        """Test that decimal point makes account invalid"""
        result = self.validator.validate_accounts(["123456789.0"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    def test_scientific_notation_invalid(self):
        """Test that scientific notation is invalid"""
        result = self.validator.validate_accounts(["1.23456789e9"])
        assert len(result["valid"]) == 0
        assert len(result["invalid"]) == 1
    
    # ===== ORDER PRESERVATION =====
    
    def test_order_preserved_in_valid(self):
        """Test that order is preserved in valid list"""
        accounts = ["1234567890", "9876543210", "1111111111"]
        result = self.validator.validate_accounts(accounts)
        assert result["valid"] == accounts
    
    def test_order_preserved_in_invalid(self):
        """Test that order is preserved in invalid list"""
        accounts = ["123456789", "123456789A", "12345678901"]
        result = self.validator.validate_accounts(accounts)
        assert result["invalid"] == accounts
    
    # ===== NO DUPLICATES =====
    
    def test_duplicate_accounts_both_valid(self):
        """Test handling of duplicate valid accounts"""
        accounts = ["1234567890", "1234567890"]
        result = self.validator.validate_accounts(accounts)
        # Both should be in valid (duplicates preserved)
        assert len(result["valid"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
