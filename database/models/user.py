"""
User Model

Stores user credentials and profile for portal authentication.
Designed for SQLite and PostgreSQL compatibility (migratable).
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, func
from .base import Base


class User(Base):
    """
    User model for auth.

    user_id is the primary key (email used as ID for simplicity).
    metadata column is TEXT in SQLite (JSON string); can be JSONB in PostgreSQL later.
    """

    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
    )
    last_login = Column(DateTime, nullable=True)
    metadata_ = Column("metadata", Text, nullable=True)  # JSON string; reserved name

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id}, email={self.email})"

    def to_dict(self) -> dict:
        """Return dict for API (exclude password_hash)."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
