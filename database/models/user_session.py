"""
UserSession Model

Tracks active sessions for validation and cleanup.
Designed for SQLite and PostgreSQL compatibility (migratable).
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, func
from .base import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


class UserSession(Base):
    """
    Session model for auth.

    session_id is UUID string (primary key).
    expires_at and last_activity updated per request; is_active soft-invalidated on logout.
    """

    __tablename__ = "user_sessions"

    session_id = Column(String(36), primary_key=True, default=_uuid_str, nullable=False)
    user_id = Column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
    )
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        Index("idx_sessions_user", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"UserSession(session_id={self.session_id}, user_id={self.user_id})"


# Indexes for user_sessions (create via __table_args__ if needed)
# idx_sessions_user (user_id, is_active), idx_sessions_expires (expires_at)
# SQLAlchemy Index can be added on the table; partial index (WHERE is_active) is DB-specific.
