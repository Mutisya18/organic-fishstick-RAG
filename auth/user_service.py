"""
User CRUD and authentication.

create_user, get_user_by_email, authenticate, update_last_login, deactivate_user.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from database.core.session import get_session
from database.models import User, UserSession

from auth.password import hash_password, verify_password
from auth.validation import validate_password, validate_email
from auth.session import create_session, expire_session
from auth.logger import log_auth_event


def create_user(
    email: str,
    password: str,
    full_name: str,
) -> Dict[str, Any]:
    """
    Create a new user. Validates email and password, hashes password, inserts user.
    Returns user dict (no password_hash). Raises ValueError if email exists or validation fails.
    """
    assert email is not None, "email required"
    assert password is not None, "password required"
    assert full_name is not None, "full_name required"
    ok, err = validate_email(email)
    if not ok:
        raise ValueError(err)
    ok, err = validate_password(password)
    if not ok:
        raise ValueError(err)
    full_name_stripped = (full_name or "").strip()
    if len(full_name_stripped) == 0:
        raise ValueError("Full name is required")

    user_id = email.strip().lower()
    with get_session() as session:
        existing = session.query(User).filter(User.email == user_id).first()
        if existing is not None:
            log_auth_event(
                "create_user_duplicate",
                level="WARN",
                message="Create user failed: email already exists",
                context={"email": user_id},
            )
            raise ValueError("Email already registered")
        pw_hash = hash_password(password)
        user = User(
            user_id=user_id,
            email=user_id,
            password_hash=pw_hash,
            full_name=full_name_stripped,
            is_active=True,
        )
        session.add(user)

    log_auth_event(
        "user_created",
        level="INFO",
        message="User created",
        context={"user_id": user_id},
    )
    return {
        "user_id": user_id,
        "email": user_id,
        "full_name": full_name_stripped,
        "is_active": True,
    }


def list_users() -> list:
    """Return list of all user dicts (no password_hash)."""
    with get_session() as session:
        users = session.query(User).order_by(User.created_at).all()
        return [u.to_dict() for u in users]


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Return user dict (no password_hash) or None."""
    if not email or not isinstance(email, str):
        return None
    user_id = email.strip().lower()
    with get_session() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return None
        return user.to_dict()


def authenticate(
    email: str,
    password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[str]:
    """
    Authenticate user. If valid: create session, update last_login, return session_id.
    If invalid: return None. Never log password.
    """
    if not email or not isinstance(email, str):
        return None
    if not password or not isinstance(password, str):
        return None
    user_id = email.strip().lower()
    with get_session() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            log_auth_event(
                "login_attempt",
                level="INFO",
                message="Login failed: user not found",
                context={"email": user_id, "success": False},
            )
            return None
        if not user.is_active:
            log_auth_event(
                "login_attempt",
                level="INFO",
                message="Login failed: user inactive",
                context={"user_id": user_id, "success": False},
            )
            return None
        ok = verify_password(password, user.password_hash)
        if not ok:
            log_auth_event(
                "login_attempt",
                level="INFO",
                message="Login failed: invalid password",
                context={"user_id": user_id, "success": False},
            )
            return None
        user.last_login = datetime.now(timezone.utc)
        session.merge(user)

    session_id = create_session(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    log_auth_event(
        "login_attempt",
        level="INFO",
        message="Login success",
        context={"user_id": user_id, "success": True},
    )
    return session_id


def update_last_login(user_id: str) -> None:
    """Update last_login timestamp for user."""
    if not user_id or not isinstance(user_id, str):
        return
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    with get_session() as session:
        session.query(User).filter(User.user_id == user_id).update(
            {"last_login": now}, synchronize_session="fetch"
        )


def deactivate_user(user_id: str) -> None:
    """Set user is_active = False and expire all their sessions."""
    if not user_id or not isinstance(user_id, str):
        return
    with get_session() as session:
        session.query(User).filter(User.user_id == user_id).update(
            {"is_active": False}, synchronize_session="fetch"
        )
        session.query(UserSession).filter(UserSession.user_id == user_id).update(
            {"is_active": False}, synchronize_session="fetch"
        )
    log_auth_event(
        "user_deactivated",
        level="INFO",
        message="User deactivated",
        context={"user_id": user_id},
    )
