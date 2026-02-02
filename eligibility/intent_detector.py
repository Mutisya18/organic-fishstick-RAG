"""
Intent Detector - Detect if user message is asking about eligibility.

Matches user message against eligibility keyword patterns.
Returns boolean indicating if message is an eligibility question.
Logs intent detection with message hash (not raw text, for PII compliance).
"""

import re
from typing import Tuple, Optional
from datetime import datetime, timezone

from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager


class IntentDetector:
    """Detect eligibility questions from user messages."""

    # Eligibility question keywords (case-insensitive)
    # Uses word boundaries and specific phrases to avoid false positives
    ELIGIBILITY_KEYWORDS = [
        r"\beligible(?:ity)?\b",  # "is customer eligible?" or "eligibility"
        r"\bwhy\s+(?:is|am|are|should)\s+(?:i|we|customer|they|he|she)?\s*no\s+limit\b",  # "why no limit?"
        r"\bloan\s+limit\b",  # "loan limit" (not "limited")
        r"\bnot\s+getting\s+(?:a\s+)?limit\b",  # "not getting limit"
        r"\bcheck\s+eligibility\b",  # "check eligibility"
        r"\blimit\s+allocation\s+failed\b",  # "limit allocation failed"
        r"\bwhy\s+(?:is|am|are|was)\s+.*?excluded\b",  # "why is/am/are excluded"
        r"\b(?:customer|account)?\s*excluded\b",  # "excluded" or "customer excluded"
        r"\blimit\s+issue\b",  # "limit issue" (not "limited issue")
    ]

    def __init__(self):
        """Initialize intent detector."""
        self.rag_logger = RAGLogger()
        self.session_manager = SessionManager()
        # Compile regex patterns for performance
        self.patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.ELIGIBILITY_KEYWORDS
        ]

    def detect(self, message: Optional[str]) -> Tuple[bool, str]:
        """
        Detect if message is asking about eligibility.

        Args:
            message: User message to analyze.

        Returns:
            Tuple of (is_eligibility_check: bool, message_hash: str)

        Raises:
            ValueError: If message is None or empty.
        """
        if not message or not message.strip():
            return False, ""

        # Hash message for logging (PII compliance)
        message_hash = self.rag_logger.hash_prompt(message)

        # Check if any eligibility keyword matches
        is_eligibility_check = any(
            pattern.search(message)
            for pattern in self.patterns
        )
        
        # If no keywords found, check for account number (9+ digits)
        if not is_eligibility_check:
            account_number_pattern = re.compile(r'\b\d{9,}\b')
            is_eligibility_check = bool(account_number_pattern.search(message))

        # Log detection result
        self.rag_logger.log_warning(
            request_id=self.rag_logger.generate_request_id(),
            message=f"Intent detection: {is_eligibility_check}",
            event_type="intent_detection",
        )

        return is_eligibility_check, message_hash

    def get_keywords(self) -> list:
        """Get list of eligibility keywords."""
        return self.ELIGIBILITY_KEYWORDS
