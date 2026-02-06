"""
Session Manager

Provides context manager for database session lifecycle management.
Handles automatic transaction commit/rollback and connection cleanup.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .engine import DatabaseEngine
from ..exceptions import DatabaseError, ConnectionError, IntegrityError, OperationalError

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Context manager for database sessions.
    
    Ensures:
    - Automatic session cleanup
    - Automatic transaction management (commit/rollback)
    - Proper error handling and logging
    - Thread-safe operation
    """
    
    def __init__(self, engine: Engine):
        """
        Initialize session manager.
        
        Args:
            engine: SQLAlchemy Engine instance
        """
        self.engine = engine
        self.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session as a context manager.
        
        Usage:
            with session_manager.get_session() as session:
                # Use session
                session.add(obj)
                # Auto-commit on exit
        
        Yields:
            SQLAlchemy Session instance
        """
        session = self.session_factory()
        
        try:
            yield session
            session.commit()
        
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Integrity error: {str(e)}")
            raise
        
        except OperationalError as e:
            session.rollback()
            logger.error(f"Operational error: {str(e)}")
            raise
        
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise DatabaseError(f"Database error: {str(e)}") from e
        
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in database transaction: {str(e)}")
            raise
        
        finally:
            session.close()
    
    def create_session(self) -> Session:
        """
        Create a new session without context manager.
        
        WARNING: Caller is responsible for cleanup!
        Prefer using get_session() context manager instead.
        
        Returns:
            SQLAlchemy Session instance
        """
        return self.session_factory()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Convenience function for getting a session with context manager.
    Uses the global engine instance.
    
    Usage:
        with get_session() as session:
            # Use session
    
    Yields:
        SQLAlchemy Session instance
        
    Raises:
        DatabaseError: If operation fails
    """
    engine = DatabaseEngine.get_engine()
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    
    try:
        yield session
        session.commit()
    
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error: {str(e)}")
        raise
    
    except OperationalError as e:
        session.rollback()
        logger.error(f"Operational error: {str(e)}")
        raise
    
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise DatabaseError(f"Database error: {str(e)}") from e
    
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error in database transaction: {str(e)}")
        raise
    
    finally:
        session.close()
