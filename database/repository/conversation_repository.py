"""
Conversation Repository

Domain-specific queries for Conversation model.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import desc

from ..models import Conversation, ConversationStatus
from ..exceptions import ConversationNotFoundError, DatabaseError
from ..core.session import get_session
from .base import BaseRepository

logger = logging.getLogger(__name__)


class ConversationRepository(BaseRepository[Conversation]):
    """
    Repository for Conversation model.
    
    Adds conversation-specific queries on top of base CRUD.
    """
    
    def __init__(self):
        """Initialize conversation repository."""
        super().__init__(Conversation)
    
    def create_for_user(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation for a user.
        
        Args:
            user_id: User ID who owns this conversation
            title: Optional conversation title
            
        Returns:
            Created Conversation instance
            
        Raises:
            DatabaseError: On creation failure
        """
        logger.info(f"Creating conversation for user_id={user_id}, title={title}")

        now = datetime.utcnow()
        data = {
            'user_id': user_id,
            'title': title,
            'status': ConversationStatus.ACTIVE,
            'message_count': 0,
            'last_opened_at': now,
        }

        return self.create(data)
    
    def get_by_user_id(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        include_archived: bool = False
    ) -> List[Conversation]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User ID to fetch conversations for
            limit: Max conversations to return
            offset: Pagination offset
            include_archived: If True, include archived conversations
            
        Returns:
            List of Conversation instances, sorted by last_message_at DESC
            
        Raises:
            DatabaseError: On query failure
        """
        logger.debug(f"Fetching conversations for user_id={user_id}, limit={limit}, offset={offset}")
        
        try:
            with get_session() as session:
                query = session.query(Conversation).filter(
                    Conversation.user_id == user_id
                )
                
                if not include_archived:
                    query = query.filter(
                        Conversation.status == ConversationStatus.ACTIVE
                    )
                
                return (query
                        .order_by(desc(Conversation.last_message_at))
                        .limit(limit)
                        .offset(offset)
                        .all())
        
        except Exception as e:
            logger.error(f"Failed to fetch conversations for user_id={user_id}: {str(e)}")
            raise DatabaseError(f"Failed to fetch conversations: {str(e)}") from e
    
    def archive(self, conversation_id: str) -> Conversation:
        """
        Archive (soft-delete) a conversation.
        
        Messages are retained for audit trail.
        Conversation becomes invisible in normal queries.
        
        Args:
            conversation_id: Conversation ID to archive
            
        Returns:
            Updated Conversation instance
            
        Raises:
            ConversationNotFoundError: If not found
        """
        logger.info(f"Archiving conversation_id={conversation_id}")
        
        try:
            with get_session() as session:
                conv = session.query(Conversation).filter_by(
                    id=conversation_id
                ).first()
                
                if conv is None:
                    raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
                
                conv.archive()
                session.add(conv)
                session.flush()  # Ensure changes are flushed to DB
                
                # Convert to dict while still attached to session
                conv_dict = conv.to_dict()
            
            return conv_dict
        
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to archive conversation {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to archive conversation: {str(e)}") from e
    
    def unarchive(self, conversation_id: str) -> Dict[str, Any]:
        """
        Unarchive a conversation (restore from soft-delete).
        
        Args:
            conversation_id: Conversation ID to unarchive
            
        Returns:
            Updated Conversation dict
            
        Raises:
            ConversationNotFoundError: If not found
        """
        logger.info(f"Unarchiving conversation_id={conversation_id}")
        
        try:
            with get_session() as session:
                conv = session.query(Conversation).filter_by(
                    id=conversation_id
                ).first()
                
                if conv is None:
                    raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
                
                conv.unarchive()
                session.add(conv)
                session.flush()
                
                # Convert to dict while still attached to session
                conv_dict = conv.to_dict()
            
            return conv_dict
        
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to unarchive conversation {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to unarchive conversation: {str(e)}") from e
    
    def update_last_message(self, conversation_id: str) -> Dict[str, Any]:
        """
        Update conversation's last_message_at to now.
        Called automatically when a message is added.
        
        Args:
            conversation_id: Conversation ID to update
            
        Returns:
            Updated Conversation dict
            
        Raises:
            ConversationNotFoundError: If not found
        """
        try:
            with get_session() as session:
                conv = session.query(Conversation).filter_by(
                    id=conversation_id
                ).first()
                
                if conv is None:
                    raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
                
                conv.last_message_at = datetime.utcnow()
                session.add(conv)
                session.flush()
                
                # Convert to dict while still attached to session
                conv_dict = conv.to_dict()
            
            return conv_dict
        
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update last_message_at for {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to update conversation: {str(e)}") from e
    
    def increment_message_count(self, conversation_id: str) -> Dict[str, Any]:
        """
        Increment conversation's message_count by 1.
        Called automatically when a message is added.
        
        Args:
            conversation_id: Conversation ID to update
            
        Returns:
            Updated Conversation dict
            
        Raises:
            ConversationNotFoundError: If not found
        """
        try:
            with get_session() as session:
                conv = session.query(Conversation).filter_by(
                    id=conversation_id
                ).first()
                
                if conv is None:
                    raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
                
                conv.message_count = (conv.message_count or 0) + 1
                session.add(conv)
                session.flush()
                
                # Convert to dict while still attached to session
                conv_dict = conv.to_dict()
            
            return conv_dict
        
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to increment message_count for {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to update conversation: {str(e)}") from e
    
    def count_for_user(self, user_id: str) -> int:
        """
        Count total conversations for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Total conversation count
        """
        try:
            with get_session() as session:
                return session.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    Conversation.status == ConversationStatus.ACTIVE
                ).count()
        
        except Exception as e:
            logger.error(f"Failed to count conversations for {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to count conversations: {str(e)}") from e

    def get_visible_by_relevance(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Conversation]:
        """
        Get non-hidden conversations for a user, ordered by relevance score.

        Relevance = 0.6 * last_opened_at + 0.4 * last_message_at (fallback created_at).
        Used for list API; only returns visible (is_hidden=False) conversations.

        Args:
            user_id: User ID
            limit: Max conversations to return (default 20)

        Returns:
            List of Conversation instances, highest relevance first
        """
        assert user_id, "user_id must not be empty"
        assert limit >= 1 and limit <= 1000, "limit must be between 1 and 1000"

        try:
            with get_session() as session:
                rows = (
                    session.query(Conversation)
                    .filter(
                        Conversation.user_id == user_id,
                        Conversation.is_hidden.is_(False),
                        Conversation.status == ConversationStatus.ACTIVE,
                    )
                    .all()
                )
            # Sort by relevance descending (higher = more relevant)
            sorted_list = sorted(
                rows,
                key=lambda c: c.get_relevance_score(),
                reverse=True,
            )
            return sorted_list[:limit]
        except Exception as e:
            logger.error(
                f"Failed to fetch visible conversations for user_id={user_id}: {str(e)}"
            )
            raise DatabaseError(
                f"Failed to fetch visible conversations: {str(e)}"
            ) from e

    def mark_opened(self, conversation_id: str) -> Dict[str, Any]:
        """
        Update conversation's last_opened_at to current time.
        
        Called when user switches to a conversation.
        Updates the "viewing activity" timestamp for relevance calculation.
        
        Args:
            conversation_id: Conversation ID to mark as opened
            
        Returns:
            Updated Conversation dict
            
        Raises:
            ConversationNotFoundError: If not found
        """
        logger.debug(f"Marking conversation {conversation_id} as opened")
        
        try:
            with get_session() as session:
                conv = session.query(Conversation).filter_by(
                    id=conversation_id
                ).first()
                
                assert conv is not None, f"Conversation {conversation_id} not found"
                
                conv.mark_opened()
                session.add(conv)
                session.flush()
                
                conv_dict = conv.to_dict()
            
            return conv_dict
        
        except AssertionError as e:
            raise ConversationNotFoundError(str(e))
        except Exception as e:
            logger.error(f"Failed to mark conversation opened {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to mark conversation opened: {str(e)}") from e
    
    def hide(self, conversation_id: str) -> Dict[str, Any]:
        """
        Mark conversation as hidden (system-imposed, for auto-limiting).
        
        Sets is_hidden=True, hidden_at=now(), auto_hidden=True.
        Conversation remains in database but becomes invisible.
        
        Args:
            conversation_id: Conversation ID to hide
            
        Returns:
            Updated Conversation dict
            
        Raises:
            ConversationNotFoundError: If not found
        """
        logger.info(f"Hiding conversation {conversation_id}")
        
        try:
            with get_session() as session:
                conv = session.query(Conversation).filter_by(
                    id=conversation_id
                ).first()
                
                assert conv is not None, f"Conversation {conversation_id} not found"
                
                conv.hide()
                session.add(conv)
                session.flush()
                
                conv_dict = conv.to_dict()
            
            return conv_dict
        
        except AssertionError as e:
            raise ConversationNotFoundError(str(e))
        except Exception as e:
            logger.error(f"Failed to hide conversation {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to hide conversation: {str(e)}") from e
    
    def unhide(self, conversation_id: str) -> Dict[str, Any]:
        """
        Mark conversation as unhidden (restore visibility).
        
        Sets is_hidden=False, hidden_at=None.
        (Future feature: admin panel to recover hidden conversations)
        
        Args:
            conversation_id: Conversation ID to unhide
            
        Returns:
            Updated Conversation dict
            
        Raises:
            ConversationNotFoundError: If not found
        """
        logger.info(f"Unhiding conversation {conversation_id}")
        
        try:
            with get_session() as session:
                conv = session.query(Conversation).filter_by(
                    id=conversation_id
                ).first()
                
                assert conv is not None, f"Conversation {conversation_id} not found"
                
                conv.unhide()
                session.add(conv)
                session.flush()
                
                conv_dict = conv.to_dict()
            
            return conv_dict
        
        except AssertionError as e:
            raise ConversationNotFoundError(str(e))
        except Exception as e:
            logger.error(f"Failed to unhide conversation {conversation_id}: {str(e)}")
            raise DatabaseError(f"Failed to unhide conversation: {str(e)}") from e
    
    def count_visible_for_user(self, user_id: str) -> int:
        """
        Count non-hidden conversations for a user.
        
        Only counts conversations where is_hidden=False.
        
        Args:
            user_id: User ID
            
        Returns:
            Count of visible conversations
            
        Raises:
            DatabaseError: On query failure
        """
        assert user_id, "user_id must not be empty"
        
        try:
            with get_session() as session:
                return session.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    Conversation.is_hidden == False,
                    Conversation.status == ConversationStatus.ACTIVE
                ).count()
        
        except Exception as e:
            logger.error(f"Failed to count visible conversations for {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to count visible conversations: {str(e)}") from e