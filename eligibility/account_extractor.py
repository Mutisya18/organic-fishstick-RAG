"""
Account Extractor - Extract 10-digit account numbers from user message.

Scans message for all 10-digit numeric sequences.
Deduplicates results.
Logs extraction count only (no account details, for PII compliance).
"""

import re
from typing import List
from datetime import datetime, timezone

from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager


class AccountExtractor:
    """Extract account numbers from user messages."""

    # Pattern for 10-digit account numbers
    ACCOUNT_PATTERN = re.compile(r"\b\d{10}\b")

    def __init__(self):
        """Initialize account extractor."""
        self.rag_logger = RAGLogger()
        self.session_manager = SessionManager()

    def extract(self, message: str) -> List[str]:
        """
        Extract 10-digit account numbers from message.

        Args:
            message: User message to scan.

        Returns:
            List of extracted account numbers (deduped, no order guaranteed).

        Raises:
            ValueError: If message is None or empty.
        """
        if not message or not message.strip():
            return []

        # Find all 10-digit sequences
        matches = self.ACCOUNT_PATTERN.findall(message)

        # Deduplicate while preserving first occurrence order
        seen = set()
        account_numbers = []
        for account in matches:
            if account not in seen:
                seen.add(account)
                account_numbers.append(account)

        # Log extraction result (count only, no account numbers)
        self.rag_logger.log(
            request_id=self.rag_logger.generate_request_id(),
            event="account_extraction",
            severity="DEBUG",
            message=f"Extracted {len(account_numbers)} account(s) from message",
            context={
                "account_count": len(account_numbers),
                "message_length": len(message),
            }
        )

        return account_numbers

    def extract_and_log(
        self,
        message: str,
        request_id: str
    ) -> List[str]:
        """
        Extract account numbers and log with specific request_id.

        Args:
            message: User message to scan.
            request_id: Request ID for logging.

        Returns:
            List of extracted account numbers.
        """
        account_numbers = self.extract(message)

        self.rag_logger.log(
            request_id=request_id,
            event="account_extraction",
            severity="DEBUG",
            message=f"Extracted {len(account_numbers)} account(s)",
            context={"account_count": len(account_numbers)}
        )

        return account_numbers
