"""
Database Layer Custom Exceptions

All exceptions raised by the database layer for app-level handling.
"""


class DatabaseError(Exception):
    """Base exception for all database errors."""
    pass


class ConnectionError(DatabaseError):
    """Database connection failed."""
    pass


class DBConnectionTimeoutError(ConnectionError):
    """Database connection timeout (retriable)."""
    pass


class DBConnectionRefusedError(ConnectionError):
    """Database connection refused (retriable)."""
    pass


class OperationalError(DatabaseError):
    """Operational error during database operation."""
    pass


class DBLockTimeoutError(OperationalError):
    """Database lock timeout (retriable)."""
    pass


class DBDeadlockError(OperationalError):
    """Database deadlock detected (retriable)."""
    pass


class IntegrityError(DatabaseError):
    """Database integrity constraint violation (non-retriable)."""
    pass


class ForeignKeyError(IntegrityError):
    """Foreign key constraint violation."""
    pass


class UniqueConstraintError(IntegrityError):
    """Unique constraint violation."""
    pass


class NotNullError(IntegrityError):
    """NOT NULL constraint violation."""
    pass


class ValidationError(DatabaseError):
    """Data validation error (non-retriable)."""
    pass


class InvalidRoleError(ValidationError):
    """Message role is invalid (must be 'user', 'assistant', or 'system')."""
    pass


class InvalidStatusError(ValidationError):
    """Conversation status is invalid."""
    pass


class NotFoundError(DatabaseError):
    """Record not found in database (non-retriable)."""
    pass


class ConversationNotFoundError(NotFoundError):
    """Conversation with given ID not found."""
    pass


class MessageNotFoundError(NotFoundError):
    """Message with given ID not found."""
    pass


class DBInitializationError(DatabaseError):
    """Database initialization failed."""
    pass


class DBRetryExhaustedError(DatabaseError):
    """All retry attempts exhausted."""
    
    def __init__(self, message: str, last_error: Exception, attempts: int = 3):
        self.last_error = last_error
        self.attempts = attempts
        full_message = f"{message} (after {attempts} attempts). Last error: {str(last_error)}"
        super().__init__(full_message)

