"""
Database Configuration

Loads database settings from environment variables.
Supports both SQLite (development) and PostgreSQL (production).
"""

import os
from typing import Optional
from urllib.parse import quote_plus

# Get environment variables with defaults
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_TIMEOUT = int(os.getenv("DATABASE_TIMEOUT", "30"))
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "5"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "5"))
DATABASE_POOL_TIMEOUT = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
DATABASE_POOL_RECYCLE = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
DATABASE_INIT_RETRY_COUNT = int(os.getenv("DATABASE_INIT_RETRY_COUNT", "3"))
DATABASE_INIT_RETRY_DELAY_MS = int(os.getenv("DATABASE_INIT_RETRY_DELAY_MS", "100"))


def get_database_url() -> str:
    """
    Get the database URL from environment.
    
    Supports:
    - SQLite: sqlite:///path/to/organic-fishstick.db
    - PostgreSQL: postgresql://user:password@localhost/dbname
    
    Returns:
        str: Database connection URL
        
    Raises:
        ValueError: If database configuration is invalid
    """
    
    if DATABASE_TYPE == "postgresql":
        if not DATABASE_URL or not DATABASE_URL.startswith("postgresql"):
            raise ValueError(
                "DATABASE_TYPE=postgresql but DATABASE_URL not set or invalid. "
                "Expected format: postgresql://user:password@localhost/dbname"
            )
        return DATABASE_URL
    
    elif DATABASE_TYPE == "sqlite":
        #If DATABASE_URL not set, use default in project root
        if not DATABASE_URL:
            # Go up 3 levels: config.py -> core -> database -> project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, "organic-fishstick.db")
        else:
            db_path = DATABASE_URL.replace("sqlite:///", "")
        
        # Create absolute path
        if not db_path.startswith("/"):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, db_path)
        
        return f"sqlite:///{db_path}"
    
    else:
        raise ValueError(
            f"Invalid DATABASE_TYPE: {DATABASE_TYPE}. "
            f"Supported: sqlite, postgresql"
        )


def is_sqlite() -> bool:
    """Check if using SQLite (development mode)."""
    return DATABASE_TYPE == "sqlite"


def is_postgresql() -> bool:
    """Check if using PostgreSQL (production mode)."""
    return DATABASE_TYPE == "postgresql"


# Database engine configuration
ENGINE_CONFIG = {
    "poolclass": "QueuePool" if is_postgresql() else "StaticPool",
    "pool_size": DATABASE_POOL_SIZE if is_postgresql() else 0,
    "max_overflow": DATABASE_MAX_OVERFLOW if is_postgresql() else 0,
    "pool_timeout": DATABASE_POOL_TIMEOUT,
    "pool_recycle": DATABASE_POOL_RECYCLE,
    "pool_pre_ping": is_postgresql(),  # Only useful for PostgreSQL
    "echo": os.getenv("DATABASE_ECHO", "false").lower() == "true",
}


# Connection string for logging (masked password)
def get_masked_database_url() -> str:
    """Get database URL with password masked for logging."""
    url = get_database_url()
    if "postgresql://" in url:
        # Mask password
        parts = url.split("@")
        if len(parts) == 2:
            user_part = parts[0].split("://")[1]
            if ":" in user_part:
                user = user_part.split(":")[0]
                return f"postgresql://{user}:***@{parts[1]}"
    return url
