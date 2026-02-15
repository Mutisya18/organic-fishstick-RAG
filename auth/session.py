"""
Session CRUD: create, validate, extend, expire, cleanup.

Session expiry 30 minutes from last_activity; cleanup deletes sessions older than 7 days past expiry.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from database.core.session import get_session
from database.models import User, UserSession

from auth.logger import log_auth_event

_SESSION_EXPIRY_MINUTES = 30
_CLEANUP_DAYS_AFTER_EXPIRY = 7
_MAX_SESSION_ID_LEN = 36


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _expires_at_from_now() -> datetime:
    return _now_utc() + timedelta(minutes=_SESSION_EXPIRY_MINUTES)


def create_session(
    user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """
    Create a new session for user_id. Returns session_id (UUID string).
    """
    assert user_id is not None and len(user_id) > 0, "user_id required"
    session_id = str(uuid.uuid4())
    now = _now_utc()
    expires_at = _expires_at_from_now()
    ip_str = (ip_address or "")[:45] if ip_address else None
    ua_str = (user_agent or "")[:500] if user_agent else None

    with get_session() as session:
        row = UserSession(
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            last_activity=now,
            ip_address=ip_str,
            user_agent=ua_str,
            is_active=True,
        )
        session.add(row)

    log_auth_event(
        "session_created",
        level="INFO",
        message="Session created",
        context={"user_id": user_id},
    )
    return session_id


def validate_session(session_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Validate session: active, not expired, last_activity within 30 min.
    If valid: update last_activity and return user dict (user_id, email, full_name).
    If invalid: return None.
    """
    if not session_id or not isinstance(session_id, str):
        return None
    session_id = session_id.strip()
    if len(session_id) == 0 or len(session_id) > _MAX_SESSION_ID_LEN:
        return None

    now = _now_utc()
    cutoff = now - timedelta(minutes=_SESSION_EXPIRY_MINUTES)

    with get_session() as session:
        row = (
            session.query(UserSession)
            .filter(
                UserSession.session_id == session_id,
                UserSession.is_active == True,
                UserSession.expires_at > now,
                UserSession.last_activity > cutoff,
            )
            .first()
        )
        if not row:
            return None
        row.last_activity = now
        row.expires_at = _expires_at_from_now()

        user = session.query(User).filter(User.user_id == row.user_id).first()
        if not user or not user.is_active:
            return None
        return user.to_dict()


def extend_session(session_id: str) -> None:
    """Update last_activity and expires_at for session."""
    if not session_id or not isinstance(session_id, str):
        return
    now = _now_utc()
    expires_at = _expires_at_from_now()
    with get_session() as session:
        session.query(UserSession).filter(
            UserSession.session_id == session_id,
            UserSession.is_active == True,
        ).update(
            {"last_activity": now, "expires_at": expires_at},
            synchronize_session="fetch",
        )


def expire_session(session_id: str) -> None:
    """Soft-invalidate session (set is_active = False)."""
    if not session_id or not isinstance(session_id, str):
        return
    with get_session() as session:
        session.query(UserSession).filter(UserSession.session_id == session_id).update(
            {"is_active": False}, synchronize_session="fetch"
        )
    log_auth_event(
        "session_expired",
        level="INFO",
        message="Session invalidated",
        context={"session_id": session_id[:8] + "..."},
    )


def cleanup_expired_sessions() -> int:
    """
    Delete sessions where expires_at < now - 7 days. Returns count deleted.
    """
    now = _now_utc()
    cutoff = now - timedelta(days=_CLEANUP_DAYS_AFTER_EXPIRY)
    deleted = 0
    with get_session() as session:
        rows = (
            session.query(UserSession)
            .filter(UserSession.expires_at < cutoff)
            .limit(10000)
            .all()
        )
        for row in rows:
            session.delete(row)
            deleted += 1
    if deleted > 0:
        log_auth_event(
            "sessions_cleanup",
            level="INFO",
            message=f"Cleaned up {deleted} expired sessions",
            context={"deleted": deleted},
        )
    return deleted
