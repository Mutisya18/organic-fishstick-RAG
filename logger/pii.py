"""
PII Scrubbing Module

Detects and redacts Personally Identifiable Information (emails, phone numbers,
names heuristics) from log text.
"""

import re
from typing import Tuple


# Regex patterns for common PII
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b")
# Simple name heuristic: Capitalized words that look like names (basic approach)
NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
# SSN pattern
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# Credit card pattern (basic)
CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")


def scrub_text(text: str) -> Tuple[str, bool]:
    """
    Scrub PII from text.
    
    Args:
        text: Raw text that may contain PII.
    
    Returns:
        Tuple of (scrubbed_text, is_flagged) where is_flagged=True if any PII was found/redacted.
    """
    if not text or not isinstance(text, str):
        return text, False
    
    original_text = text
    is_flagged = False
    
    # Redact emails
    if EMAIL_PATTERN.search(text):
        is_flagged = True
        text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    
    # Redact phone numbers
    if PHONE_PATTERN.search(text):
        is_flagged = True
        text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
    
    # Redact SSNs
    if SSN_PATTERN.search(text):
        is_flagged = True
        text = SSN_PATTERN.sub("[SSN_REDACTED]", text)
    
    # Redact credit cards
    if CREDIT_CARD_PATTERN.search(text):
        is_flagged = True
        text = CREDIT_CARD_PATTERN.sub("[CC_REDACTED]", text)
    
    # Simple name heuristic (optional, can be aggressive)
    # Uncomment if you want to redact names:
    # if NAME_PATTERN.search(text):
    #     is_flagged = True
    #     text = NAME_PATTERN.sub("[NAME_REDACTED]", text)
    
    return text, is_flagged


def scrub_dict(data: dict, keys_to_scrub=None) -> Tuple[dict, bool]:
    """
    Scrub PII from dictionary values.
    
    Args:
        data: Dictionary that may contain PII.
        keys_to_scrub: List of specific keys to scrub (if None, scrub all string values).
    
    Returns:
        Tuple of (scrubbed_dict, is_flagged).
    """
    if not data:
        return data, False
    
    scrubbed = data.copy()
    is_flagged = False
    
    if keys_to_scrub is None:
        keys_to_scrub = list(data.keys())
    
    for key in keys_to_scrub:
        if key in scrubbed and isinstance(scrubbed[key], str):
            scrubbed[key], pii_found = scrub_text(scrubbed[key])
            if pii_found:
                is_flagged = True
    
    return scrubbed, is_flagged
