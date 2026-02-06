"""
Message Repository

Domain-specific queries for Message model.
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import desc

from ..models import Message, MessageRole
from ..exceptions import MessageNotFoundError, ConversationNotFoundError, DatabaseError
from ..core.session import get_session
from .base import BaseRepository

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository[Message]):
    """
    Repository for Message model.
    
    Adds message-specific queries on top of base CRUD.
    Messages are append-only (immutable after insert).
    """
    
    def __init__(self):
        """Initialize message repository."""
        super().__init__(Message)
    
    def create_for_conversation(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Create a message in a conversation.
        
        Args:
            conversation_id: Which conversation this message belongs to
            role: Message role ('user', 'assistant', or 'system')
            content: Message text content
            metadata: Optional metadata dict (request_id, source, tokens, model_name, etc.)
            
        Returns:
            Created Message instance
            
        Raises:
            DatabaseError: On creation failure
        """
        logger.debug(
            f"Creating message in conversation {conversation_id}: "
            f"role={role}, content_len={len(content)}"
        )
        
        # Validate role
        try:
            role_enum = MessageRole(role)
        except ValueError:
            raise ValueError(
                f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'"
            )
        
        data = {
            'conversation_id': conversation_id,
            'role': role_enum,
            'content': content,
            'msg_metadata': metadata or {}
        }
        
        return self.create(data)
    
    def get_by_conversation(
        self,
        conversation_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Message]:
        """
        Fetch messages from a conversation (paginated, chronological order).
        
        Args:
            conversation_id: Conversation ID to fetch messages from
            limit: Max messages to return
            offset: Pagination offset
            
        Returns:
            List of Message instances ordered by created_at ASC (oldest first)
            
        Raises:
            DatabaseError: On query failure
        """
        logger.debug(
            f"Fetching messages for conversation {conversation_id}: "
            f"limit={limit}, offset={offset}"
        )
        
        try:
            with get_session() as session:
                return (session.query(Message)
                        .filter(Message.conversation_id == conversation_id)
                        .order_by(Message.created_at)  # ASC: oldest first
                        .limit(limit)
                        .offset(offset)
                        .all())
        
        except Exception as e:
            logger.error(
                f"Failed to fetch messages for conversation {conversation_id}: {str(e)}"
            )
            raise DatabaseError(f"Failed to fetch messages: {str(e)}") from e
    
    def get_last_n_messages(
        self,
        conversation_id: str,
        n: int = 5
    ) -> List[Message]:
        """
        Get the last N messages from a conversation.
        
        Use case: For LLM context window, fetch last N messages to provide history.
        
        Args:
            conversation_id: Conversation ID
            n: Number of messages to fetch
            
        Returns:
            List of last N messages, oldest first (for chronological order in prompt)
            
        Raises:
            DatabaseError: On query failure
        """
        logger.debug(f"Fetching last {n} messages for conversation {conversation_id}")
        
        try:
            with get_session() as session:
                # Get last N by going DESC, then reverse to chronological
                messages = (session.query(Message)
                            .filter(Message.conversation_id == conversation_id)
                            .order_by(desc(Message.created_at))  # DESC: newest first
                            .limit(n)
                            .all())
                
                # Reverse to chronological order (oldest first)
                messages.reverse()
                return messages
        
        except Exception as e:
            logger.error(
                f"Failed to fetch last {n} messages for conversation {conversation_id}: {str(e)}"
            )
            raise DatabaseError(f"Failed to fetch last N messages: {str(e)}") from e
    
    def get_by_source(
        self,
        conversation_id: str,
        source: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """
        Get messages filtered by source (e.g., 'rag_retrieval', 'llm_generation').
        
        Args:
            conversation_id: Conversation ID
            source: Source type to filter by
            limit: Max results
            offset: Pagination offset
            
        Returns:
            Matching messages ordered by created_at
            
        Raises:
            DatabaseError: On query failure
        """
        logger.debug(
            f"Fetching messages for conversation {conversation_id} "
            f"with source={source}"
        )
        
        try:
            with get_session() as session:
                # Filter by JSON metadata: source field
                return (session.query(Message)
                        .filter(
                            Message.conversation_id == conversation_id,
                            Message.metadata['source'].astext == source
                        )
                        .order_by(Message.created_at)
                        .limit(limit)
                        .offset(offset)
                        .all())
        
        except Exception as e:
            logger.error(
                f"Failed to fetch messages by source for {conversation_id}: {str(e)}"
            )
            raise DatabaseError(f"Failed to fetch messages by source: {str(e)}") from e
    
    def count_by_conversation(self, conversation_id: str) -> int:
        """
        Count messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Total message count for this conversation
        """
        try:
            with get_session() as session:
                return session.query(Message).filter(
                    Message.conversation_id == conversation_id
                ).count()
        
        except Exception as e:
            logger.error(f"Failed to count messages for {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to count messages: {str(e)}") from e
    
    def count_by_role(self, conversation_id: str, role: str) -> int:
        """
        Count messages of a specific role in a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Role to count ('user', 'assistant', 'system')
            
        Returns:
            Count of messages with this role
        """
        try:
            role_enum = MessageRole(role)
        except ValueError:
            raise ValueError(f"Invalid role: {role}")
        
        try:
            with get_session() as session:
                return session.query(Message).filter(
                    Message.conversation_id == conversation_id,
                    Message.role == role_enum
                ).count()
        
        except Exception as e:
            logger.error(
                f"Failed to count {role} messages for {conversation_id}: {str(e)}"
            )
            raise DatabaseError(f"Failed to count messages: {str(e)}") from e
