"""
Message Model

Represents a single message in a conversation.
Messages are append-only (immutable) - never updated after insert.
"""

from sqlalchemy import Column, String, Text, Enum, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class MessageRole(str, enum.Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """
    Message model.
    
    Represents a single message in a conversation.
    Designed as append-only event log (immutable after insert).
    """
    
    __tablename__ = "messages"
    
    # Columns
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    role = Column(
        Enum(MessageRole),
        nullable=False,
        index=True
    )
    
    content = Column(Text, nullable=False)
    
    msg_metadata = Column(
        JSON,
        nullable=True,
        comment="JSON metadata: request_id, source, tokens, model_name, latency_ms, etc."
    )
    
    # Relationships
    conversation = relationship(
        "Conversation",
        back_populates="messages",
        lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_role_created', 'role', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})"
    
    @property
    def request_id(self) -> str | None:
        """Extract request_id from metadata for tracing."""
        if self.msg_metadata:
            return self.msg_metadata.get('request_id')
        return None
    
    @property
    def source(self) -> str | None:
        """Extract source from metadata (e.g., 'user_input', 'llm_generation', 'rag_retrieval')."""
        if self.msg_metadata:
            return self.msg_metadata.get('source')
        return None
    
    @property
    def tokens(self) -> int | None:
        """Extract token count from metadata."""
        if self.msg_metadata:
            return self.msg_metadata.get('tokens')
        return None
    
    @property
    def model_name(self) -> str | None:
        """Extract model name from metadata."""
        if self.msg_metadata:
            return self.msg_metadata.get('model_name')
        return None
    
    @property
    def latency_ms(self) -> int | None:
        """Extract latency in milliseconds from metadata."""
        if self.msg_metadata:
            return self.msg_metadata.get('latency_ms')
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = super().to_dict()
        data['role'] = self.role.value if isinstance(self.role, MessageRole) else self.role
        # Include metadata with column name and extracted fields
        data['msg_metadata'] = self.msg_metadata or {}
        data['request_id'] = self.request_id
        data['source'] = self.source
        data['tokens'] = self.tokens
        data['model_name'] = self.model_name
        data['latency_ms'] = self.latency_ms
        return data
