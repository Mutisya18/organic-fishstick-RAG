"""
Conversation Model

Represents a conversation thread between a user and the assistant.
Supports multi-conversation management with auto-hiding based on relevance scores.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Enum, Integer, DateTime, Index, Boolean
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
    
    # Multi-conversation limit management columns
    is_hidden = Column(Boolean, default=False, nullable=False, index=True)
    hidden_at = Column(DateTime, nullable=True)
    auto_hidden = Column(Boolean, default=False, nullable=False, index=True)
    last_opened_at = Column(DateTime, nullable=True, index=True)
    
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
        Index('idx_conversations_visibility_priority', 'user_id', 'is_hidden', 'last_opened_at', 'last_message_at'),
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
    
    def hide(self) -> None:
        """Mark conversation as hidden (auto-hidden by system)."""
        self.is_hidden = True
        self.hidden_at = datetime.utcnow()
        self.auto_hidden = True
    
    def unhide(self) -> None:
        """Mark conversation as visible again."""
        self.is_hidden = False
        self.hidden_at = None
    
    def mark_opened(self) -> None:
        """Update last_opened_at to current time."""
        self.last_opened_at = datetime.utcnow()
    
    def get_relevance_score(self) -> float:
        """
        Calculate dual-factor relevance score for conversation prioritization.
        
        Score = (last_opened_at_unix * 0.6) + (last_message_at_unix * 0.4)
        
        Fallbacks:
        - If last_opened_at is None, use created_at
        - If last_message_at is None, use created_at
        
        Returns:
            Float relevance score for sorting (higher = more relevant)
        """
        assert self.created_at is not None, "Conversation must have created_at"
        
        # Fallback to created_at if timestamps are None
        opened_time = self.last_opened_at or self.created_at
        message_time = self.last_message_at or self.created_at
        
        # Convert to Unix timestamps
        opened_unix = opened_time.timestamp()
        message_unix = message_time.timestamp()
        
        # Weighted combination: 60% viewing activity, 40% message activity
        score = (opened_unix * 0.6) + (message_unix * 0.4)
        return score
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = super().to_dict()
        data['status'] = self.status.value if isinstance(self.status, ConversationStatus) else self.status
        data['is_active'] = self.is_active
        data['is_archived'] = self.is_archived
        data['is_hidden'] = self.is_hidden
        data['auto_hidden'] = self.auto_hidden
        return data
