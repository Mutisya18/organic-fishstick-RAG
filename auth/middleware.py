"""
FastAPI auth dependency: get_current_user.

Extracts session_id from cookie, validates session, returns user dict or raises 401.
"""

from typing import Dict, Any

from fastapi import Cookie, HTTPException

from auth.session import validate_session


def get_current_user(
    session_id: str = Cookie(None),
) -> Dict[str, Any]:
    """
    FastAPI dependency: validate session cookie and return current user.
    Raises HTTPException 401 if cookie missing or session invalid.
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = validate_session(session_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
