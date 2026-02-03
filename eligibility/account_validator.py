"""
Account Validator - Validate account number format.

Checks that account numbers are:
- Exactly 10 digits
- Numeric characters only
- No whitespace or special characters

Logs validation results (counts only, no account details).
"""

from typing import Tuple, List
from datetime import datetime, timezone

from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager


class AccountValidator:
    """Validate account number formats."""

    def __init__(self):
        """Initialize account validator."""
        self.rag_logger = RAGLogger()
        self.session_manager = SessionManager()

    def validate(
        self,
        account_numbers: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Validate account numbers.

        Args:
            account_numbers: List of account numbers to validate.

        Returns:
            Tuple of (valid_accounts, invalid_accounts)
            Each is a list of account numbers.

        Raises:
            ValueError: If input is None.
        """
        if account_numbers is None:
            return [], []

        if not account_numbers:
            return [], []

        valid_accounts = []
        invalid_accounts = []

        for account in account_numbers:
            if self._is_valid_account(account):
                valid_accounts.append(account)
            else:
                invalid_accounts.append(account)

        # Log validation results (counts only)
        self.rag_logger.log(
            request_id=self.rag_logger.generate_request_id(),
            event="account_validation",
            severity="DEBUG",
            message=f"Account validation completed",
            context={
                "valid_count": len(valid_accounts),
                "invalid_count": len(invalid_accounts),
                "total_count": len(account_numbers),
            }
        )

        return valid_accounts, invalid_accounts

    def validate_and_log(
        self,
        account_numbers: List[str],
        request_id: str
    ) -> Tuple[List[str], List[str]]:
        """
        Validate account numbers and log with specific request_id.

        Args:
            account_numbers: List of account numbers to validate.
            request_id: Request ID for logging.

        Returns:
            Tuple of (valid_accounts, invalid_accounts)
        """
        valid, invalid = self.validate(account_numbers)

        self.rag_logger.log(
            request_id=request_id,
            event="account_validation",
            severity="DEBUG",
            message=f"Validation: {len(valid)} valid, {len(invalid)} invalid",
            context={
                "valid_count": len(valid),
                "invalid_count": len(invalid),
            }
        )

        return valid, invalid

    @staticmethod
    def _is_valid_account(account: str) -> bool:
        """
        Check if account number is valid format.

        Rules:
        - Exactly 10 characters
        - All digits (0-9)
        - No whitespace or special characters

        Args:
            account: Account number to validate.

        Returns:
            True if valid format, False otherwise.
        """
        if not account:
            return False

        if not isinstance(account, str):
            return False

        # Check length
        if len(account) != 10:
            return False

        # Check all digits
        if not account.isdigit():
            return False

        return True

    @staticmethod
    def is_valid(account: str) -> bool:
        """
        Static method to check if single account is valid.

        Args:
            account: Account number to validate.

        Returns:
            True if valid format, False otherwise.
        """
        return AccountValidator._is_valid_account(account)
