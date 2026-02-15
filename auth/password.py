"""
Password hashing and verification using bcrypt.

Cost factor 12 per user_management.md. Timing-safe comparison.
"""

import bcrypt

_BCRYPT_COST = 12
_MAX_PASSWORD_BYTES = 4096


def hash_password(plain_text: str) -> str:
    """
    Hash a plain-text password. Use cost factor 12.
    Returns base64-encoded hash string. Never log plain_text.
    """
    assert plain_text is not None, "plain_text required"
    if not isinstance(plain_text, str):
        raise TypeError("plain_text must be str")
    encoded = plain_text.encode("utf-8")
    if len(encoded) > _MAX_PASSWORD_BYTES:
        raise ValueError("password too long")
    salt = bcrypt.gensalt(rounds=_BCRYPT_COST)
    result = bcrypt.hashpw(encoded, salt)
    if result is None or len(result) == 0:
        raise RuntimeError("bcrypt hashpw returned empty")
    return result.decode("utf-8")


def verify_password(plain_text: str, hash_string: str) -> bool:
    """
    Verify plain text against a bcrypt hash. Uses timing-safe comparison.
    Returns True if match, False otherwise. Never log plain_text or hash.
    """
    assert plain_text is not None, "plain_text required"
    assert hash_string is not None, "hash_string required"
    if not isinstance(plain_text, str) or not isinstance(hash_string, str):
        return False
    encoded = plain_text.encode("utf-8")
    if len(encoded) > _MAX_PASSWORD_BYTES:
        return False
    try:
        hash_bytes = hash_string.encode("utf-8")
    except Exception:
        return False
    result = bcrypt.checkpw(encoded, hash_bytes)
    return result is True
