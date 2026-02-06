"""
Database Engine Setup

Initializes SQLAlchemy engine with connection pooling.
Supports lazy initialization: engine created on first use, not at import.
"""

import threading
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.pool import QueuePool, StaticPool
from typing import Optional

from .config import (
    get_database_url,
    get_masked_database_url,
    is_sqlite,
    ENGINE_CONFIG,
)
from ..exceptions import DBInitializationError
from ..models import Base


class DatabaseEngine:
    """
    Singleton database engine with lazy initialization.
    Handles SQLAlchemy engine creation and connection pooling.
    """
    
    _engine: Optional[Engine] = None
    _initialized = False
    _lock = threading.Lock()
    
    @staticmethod
    def initialize(debug: bool = False) -> Engine:
        """
        Initialize the database engine (lazy initialization).
        
        Called on first database operation or explicit app startup.
        Thread-safe: only one thread initializes the engine.
        
        Args:
            debug: If True, log all SQL queries
            
        Returns:
            SQLAlchemy Engine instance
            
        Raises:
            DBInitializationError: If initialization fails
        """
        
        if DatabaseEngine._initialized:
            return DatabaseEngine._engine
        
        with DatabaseEngine._lock:
            # Double-check pattern: another thread might have initialized
            if DatabaseEngine._initialized:
                return DatabaseEngine._engine
            
            try:
                database_url = get_database_url()
                masked_url = get_masked_database_url()
                
                # Configure pooling based on database type
                if is_sqlite():
                    # SQLite: use StaticPool (no actual pooling, one connection)
                    engine = create_engine(
                        database_url,
                        poolclass=StaticPool,
                        echo=debug,
                        connect_args={"check_same_thread": False}
                    )
                else:
                    # PostgreSQL: use QueuePool for connection pooling
                    engine = create_engine(
                        database_url,
                        poolclass=QueuePool,
                        pool_size=ENGINE_CONFIG["pool_size"],
                        max_overflow=ENGINE_CONFIG["max_overflow"],
                        pool_timeout=ENGINE_CONFIG["pool_timeout"],
                        pool_recycle=ENGINE_CONFIG["pool_recycle"],
                        pool_pre_ping=ENGINE_CONFIG["pool_pre_ping"],
                        echo=debug,
                    )
                
                # Create all tables
                Base.metadata.create_all(engine)
                
                # Configure SQLite pragmas if using SQLite
                if is_sqlite():
                    configure_sqlite_pragmas(engine)
                
                DatabaseEngine._engine = engine
                DatabaseEngine._initialized = True
                
                return engine
            
            except Exception as e:
                raise DBInitializationError(
                    f"Failed to initialize database: {str(e)}"
                ) from e
    
    @staticmethod
    def get_engine() -> Engine:
        """
        Get the initialized engine.
        
        Returns:
            SQLAlchemy Engine instance
            
        Raises:
            DBInitializationError: If engine not initialized
        """
        if DatabaseEngine._engine is None:
            raise DBInitializationError(
                "Database engine not initialized. Call DatabaseEngine.initialize() first."
            )
        return DatabaseEngine._engine
    
    @staticmethod
    def close() -> None:
        """
        Gracefully close all connections and dispose of the engine.
        Called at app shutdown.
        """
        if DatabaseEngine._engine:
            DatabaseEngine._engine.dispose()
            DatabaseEngine._engine = None
            DatabaseEngine._initialized = False
    
    @staticmethod
    def is_initialized() -> bool:
        """Check if engine is initialized."""
        return DatabaseEngine._initialized


def configure_sqlite_pragmas(engine: Engine) -> None:
    """
    Configure SQLite pragmas for better performance and safety.
    Called automatically after SQLite engine creation.
    """
    
    if not is_sqlite():
        return
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite pragmas for safety and performance."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
        cursor.close()
