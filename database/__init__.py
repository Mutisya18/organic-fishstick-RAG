"""
Database Manager

Main facade for database operations.
This is the primary API that app.py uses to interact with the database.
"""

import logging
import time
from typing import Optional, List, Dict, Any

from .core import DatabaseEngine, SessionManager, get_session
from .repository import ConversationRepository, MessageRepository
from .exceptions import (
    DatabaseError,
    DBInitializationError,
    ConversationNotFoundError,
    InvalidRoleError,
    DBRetryExhaustedError,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Facade class providing clean API for app.py.
    Hides complexity of repositories, sessions, and pooling.
    
    This is what app.py imports and uses.
    Lazy initialization: DB not initialized until first call.
    
    Usage:
        # At app startup:
        db = DatabaseManager()
        db.initialize()
        
        # In request handlers:
        conversation = db.create_conversation(user_id='user_001', title='My Chat')
        message = db.save_user_message(conversation.id, 'Hello!', request_id='req_123')
        last_messages = db.get_last_n_messages(conversation.id, n=5)
        
        # At app shutdown:
        db.shutdown()
    """
    
    _instance = None
    _initialized = False
    _conversation_repo: Optional[ConversationRepository] = None
    _message_repo: Optional[MessageRepository] = None
    
    def __new__(cls):
        """Singleton pattern: one DatabaseManager instance per process."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def initialize(
        self,
        database_url: Optional[str] = None,
        debug: bool = False,
        retry_count: int = 3,
        retry_delay_ms: int = 100
    ) -> None:
        """
        Initialize the database.
        
        Called at app startup. Lazy initialization: doesn't connect until first DB operation.
        
        Args:
            database_url: Optional override for database URL (normally from env)
            debug: If True, log all SQL queries
            retry_count: Max retries on initialization failure
            retry_delay_ms: Initial retry delay in milliseconds
            
        Raises:
            DBInitializationError: If initialization fails
        """
        if self._initialized:
            logger.debug("Database already initialized, skipping")
            return
        
        logger.info("Initializing database...")
        
        if database_url:
            import os
            os.environ["DATABASE_URL"] = database_url
        
        # Retry logic for initialization
        last_error = None
        for attempt in range(1, retry_count + 1):
            try:
                # Initialize engine (this creates tables if needed)
                engine = DatabaseEngine.initialize(debug=debug)
                
                # Initialize repositories
                self._conversation_repo = ConversationRepository()
                self._message_repo = MessageRepository()
                
                self._initialized = True
                logger.info("✅ Database initialized successfully")
                return
            
            except Exception as e:
                last_error = e
                if attempt < retry_count:
                    wait_ms = retry_delay_ms * (2 ** (attempt - 1))
                    logger.warning(
                        f"Database initialization failed (attempt {attempt}/{retry_count}): "
                        f"{str(e)}. Retrying in {wait_ms}ms..."
                    )
                    time.sleep(wait_ms / 1000.0)
                else:
                    logger.error(
                        f"Database initialization failed after {retry_count} attempts"
                    )
        
        # All retries exhausted
        raise DBInitializationError(
            f"Failed to initialize database after {retry_count} attempts. "
            f"Last error: {str(last_error)}"
        ) from last_error
    
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized and DatabaseEngine.is_initialized()
    
    # ==================== CONVERSATION OPERATIONS ====================
    
    def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation.
        
        Args:
            user_id: User ID who owns this conversation
            title: Optional conversation title
            
        Returns:
            Conversation dict with id, user_id, title, etc.
            
        Raises:
            DatabaseError: On failure
        """
        self._check_initialized()
        
        try:
            conv = self._conversation_repo.create_for_user(user_id, title)
            logger.info(f"Created conversation {conv.id} for user {user_id}")
            return conv.to_dict()
        
        except Exception as e:
            logger.error(f"Failed to create conversation: {str(e)}")
            raise
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation dict or None if not found
        """
        self._check_initialized()
        
        try:
            conv = self._conversation_repo.get_by_id(conversation_id)
            return conv.to_dict() if conv else None
        
        except Exception as e:
            logger.error(f"Failed to fetch conversation {conversation_id}: {str(e)}")
            raise
    
    def list_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List conversations for a user.
        
        Args:
            user_id: User ID
            limit: Max results
            offset: Pagination offset
            include_archived: Include archived conversations
            
        Returns:
            List of conversation dicts, sorted newest first
        """
        self._check_initialized()
        
        try:
            convs = self._conversation_repo.get_by_user_id(
                user_id,
                limit=limit,
                offset=offset,
                include_archived=include_archived
            )
            return [conv.to_dict() for conv in convs]
        
        except Exception as e:
            logger.error(f"Failed to list conversations for {user_id}: {str(e)}")
            raise
    
    def archive_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Archive (soft-delete) a conversation.
        
        Args:
            conversation_id: Conversation ID to archive
            
        Returns:
            Updated conversation dict
            
        Raises:
            ConversationNotFoundError: If not found
        """
        self._check_initialized()
        
        try:
            return self._conversation_repo.archive(conversation_id)
        
        except Exception as e:
            logger.error(f"Failed to archive conversation {conversation_id}: {str(e)}")
            raise
    
    # ==================== MESSAGE OPERATIONS ====================
    
    def save_user_message(
        self,
        conversation_id: str,
        content: str,
        request_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a message from the user.
        
        Automatically updates conversation's last_message_at and message_count.
        
        Args:
            conversation_id: Conversation ID
            content: Message text
            request_id: UUID for tracing (from orchestrator)
            metadata: Optional metadata dict
            
        Returns:
            Message dict with id, created_at, etc.
            
        Raises:
            ConversationNotFoundError: If conversation doesn't exist
            DatabaseError: On failure
        """
        self._check_initialized()
        
        # Check conversation exists first
        if not self._conversation_repo.get_by_id(conversation_id):
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found"
            )
        
        try:
            # Prepare metadata
            msg_metadata = metadata or {}
            msg_metadata['request_id'] = request_id
            msg_metadata['source'] = msg_metadata.get('source', 'user_input')
            
            # Create message
            message = self._message_repo.create_for_conversation(
                conversation_id=conversation_id,
                role='user',
                content=content,
                metadata=msg_metadata
            )
            
            # Update conversation metadata
            self._conversation_repo.update_last_message(conversation_id)
            self._conversation_repo.increment_message_count(conversation_id)
            
            logger.debug(
                f"Saved user message {message.id} to conversation {conversation_id}"
            )
            return message.to_dict()
        
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to save user message: {str(e)}")
            raise
    
    def save_assistant_message(
        self,
        conversation_id: str,
        content: str,
        request_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a message from the assistant (LLM).
        
        Automatically updates conversation's last_message_at and message_count.
        
        Args:
            conversation_id: Conversation ID
            content: Assistant response text
            request_id: UUID for tracing
            metadata: Dict with tokens, model_name, latency_ms, source, etc.
            
        Returns:
            Message dict
            
        Raises:
            ConversationNotFoundError: If conversation doesn't exist
            DatabaseError: On failure
        """
        self._check_initialized()
        
        # Check conversation exists first
        if not self._conversation_repo.get_by_id(conversation_id):
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found"
            )
        
        try:
            # Prepare metadata
            msg_metadata = metadata or {}
            msg_metadata['request_id'] = request_id
            msg_metadata['source'] = msg_metadata.get('source', 'llm_generation')
            
            # Create message
            message = self._message_repo.create_for_conversation(
                conversation_id=conversation_id,
                role='assistant',
                content=content,
                metadata=msg_metadata
            )
            
            # Update conversation metadata
            self._conversation_repo.update_last_message(conversation_id)
            self._conversation_repo.increment_message_count(conversation_id)
            
            logger.debug(
                f"Saved assistant message {message.id} to conversation {conversation_id}"
            )
            return message.to_dict()
        
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to save assistant message: {str(e)}")
            raise
    
    def save_system_message(
        self,
        conversation_id: str,
        content: str,
        request_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a system message (e.g., 'Eligibility check completed').
        
        Args:
            conversation_id: Conversation ID
            content: System message text
            request_id: UUID for tracing
            metadata: Optional metadata
            
        Returns:
            Message dict
        """
        self._check_initialized()
        
        # Check conversation exists first
        if not self._conversation_repo.get_by_id(conversation_id):
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found"
            )
        
        try:
            # Prepare metadata
            msg_metadata = metadata or {}
            msg_metadata['request_id'] = request_id
            msg_metadata['source'] = msg_metadata.get('source', 'system')
            
            # Create message
            message = self._message_repo.create_for_conversation(
                conversation_id=conversation_id,
                role='system',
                content=content,
                metadata=msg_metadata
            )
            
            # Update conversation metadata
            self._conversation_repo.update_last_message(conversation_id)
            self._conversation_repo.increment_message_count(conversation_id)
            
            return message.to_dict()
        
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to save system message: {str(e)}")
            raise
    
    def get_messages(
        self,
        conversation_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a conversation (paginated, chronological).
        
        Args:
            conversation_id: Conversation ID
            limit: Max messages
            offset: Pagination offset
            
        Returns:
            List of message dicts, oldest first
        """
        self._check_initialized()
        
        try:
            messages = self._message_repo.get_by_conversation(
                conversation_id,
                limit=limit,
                offset=offset
            )
            return [msg.to_dict() for msg in messages]
        
        except Exception as e:
            logger.error(f"Failed to fetch messages for {conversation_id}: {str(e)}")
            raise
    
    def get_last_n_messages(
        self,
        conversation_id: str,
        n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get the last N messages (for LLM context window).
        
        Args:
            conversation_id: Conversation ID
            n: Number of messages (default 5)
            
        Returns:
            List of message dicts, oldest first (but last N)
        """
        self._check_initialized()
        
        try:
            messages = self._message_repo.get_last_n_messages(conversation_id, n=n)
            return [msg.to_dict() for msg in messages]
        
        except Exception as e:
            logger.error(f"Failed to fetch last {n} messages: {str(e)}")
            raise
    
    def get_message_count(self, conversation_id: str) -> int:
        """
        Count total messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Message count
        """
        self._check_initialized()
        
        try:
            return self._message_repo.count_by_conversation(conversation_id)
        
        except Exception as e:
            logger.error(f"Failed to count messages for {conversation_id}: {str(e)}")
            raise
    
    # ==================== LIFECYCLE OPERATIONS ====================
    
    def shutdown(self) -> None:
        """
        Gracefully close all database connections.
        Called at app shutdown (e.g., Streamlit closing).
        """
        logger.info("Shutting down database...")
        try:
            DatabaseEngine.close()
            self._initialized = False
            logger.info("✅ Database shutdown complete")
        except Exception as e:
            logger.error(f"Error during database shutdown: {str(e)}")
    
    # ==================== INTERNAL HELPERS ====================
    
    def _check_initialized(self) -> None:
        """
        Check if database is initialized.
        
        Raises:
            DBInitializationError: If not initialized
        """
        if not self._initialized or not DatabaseEngine.is_initialized():
            raise DBInitializationError(
                "Database not initialized. Call db.initialize() first."
            )


# Create singleton instance
db = DatabaseManager()
