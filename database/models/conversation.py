"""
Conversation Model

Represents a conversation thread between a user and the assistant.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Enum, Integer, DateTime, Index
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class ConversationStatus(str, enum.Enum):
    """Conversation status enumeration."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    CLOSED = "CLOSED"
    DELETED = "DELETED"


class Conversation(BaseModel):
    """
    Conversation model.
    
    Represents a conversation thread owned by a user.
    Multiple conversations per user are supported (one per topic).
    """
    
    __tablename__ = "conversations"
    
    # Columns
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    status = Column(
        Enum(ConversationStatus),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True
    )
    message_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime, nullable=True, index=True)
    archived_at = Column(DateTime, nullable=True)
    
    # Relationships
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_user_last_message', 'user_id', 'last_message_at'),
        Index('idx_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"Conversation(id={self.id}, user_id={self.user_id}, status={self.status})"
    
    @property
    def is_active(self) -> bool:
        """Check if conversation is active."""
        return self.status == ConversationStatus.ACTIVE
    
    @property
    def is_archived(self) -> bool:
        """Check if conversation is archived."""
        return self.status == ConversationStatus.ARCHIVED
    
    def archive(self) -> None:
        """Archive this conversation (soft-delete)."""
        self.status = ConversationStatus.ARCHIVED
        self.archived_at = datetime.utcnow()
    
    def unarchive(self) -> None:
        """Unarchive this conversation."""
        self.status = ConversationStatus.ACTIVE
        self.archived_at = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = super().to_dict()
        data['status'] = self.status.value if isinstance(self.status, ConversationStatus) else self.status
        data['is_active'] = self.is_active
        data['is_archived'] = self.is_archived
        return data
