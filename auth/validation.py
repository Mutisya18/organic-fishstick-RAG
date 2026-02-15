"""
Validation for email and password strength.

Per user_management.md: min 12 chars, at least 1 number, at least 1 special character.
"""

import re
from typing import Tuple

_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
_SPECIAL_CHARS = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
_MIN_LENGTH = 12
_MAX_EMAIL_LEN = 255
_MAX_PASSWORD_LEN = 4096


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message). Error message empty when valid.
    """
    assert password is not None, "password required"
    if not isinstance(password, str):
        return False, "Password must be a string"
    if len(password) < _MIN_LENGTH:
        return False, f"Password must be at least {_MIN_LENGTH} characters"
    if len(password) > _MAX_PASSWORD_LEN:
        return False, "Password too long"
    has_digit = False
    has_special = False
    for i in range(len(password)):
        if password[i].isdigit():
            has_digit = True
        if password[i] in _SPECIAL_CHARS:
            has_special = True
        if has_digit and has_special:
            break
    if not has_digit:
        return False, "Password must contain at least one number"
    if not has_special:
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Basic email format validation.
    Returns (is_valid, error_message). Error message empty when valid.
    """
    assert email is not None, "email required"
    if not isinstance(email, str):
        return False, "Email must be a string"
    stripped = email.strip()
    if len(stripped) == 0:
        return False, "Email is required"
    if len(stripped) > _MAX_EMAIL_LEN:
        return False, "Email too long"
    if not _EMAIL_REGEX.match(stripped):
        return False, "Please enter a valid email address"
    return True, ""
