"""
Database Initialization Utility

Handles database startup with proper error messages and retry logic.
Called by app.py and start.sh to ensure database is ready.
"""

import logging
import os
import sys
import time
from typing import Optional

logger = logging.getLogger(__name__)


def check_database_availability(
    timeout_seconds: int = 30,
    retry_count: int = 3,
    retry_delay_ms: int = 100
) -> bool:
    """
    Check if database is available and ready.
    
    For SQLite: Checks if database path is writable
    For PostgreSQL: Attempts connection with retries
    
    Args:
        timeout_seconds: Max time to wait for DB to be ready
        retry_count: Max retry attempts
        retry_delay_ms: Initial delay between retries (exponential backoff)
        
    Returns:
        True if database is available, False otherwise
    """
    from database.core.config import is_sqlite, get_database_url
    
    logger.info("Checking database availability...")
    
    if is_sqlite():
        return _check_sqlite_available()
    else:
        return _check_postgresql_available(
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            retry_delay_ms=retry_delay_ms
        )


def _check_sqlite_available() -> bool:
    """Check if SQLite is available and database path is writable."""
    from database.core.config import get_database_url
    
    try:
        db_url = get_database_url()
        # SQLite: extract path from URL
        db_path = db_url.replace("sqlite:///", "")
        
        # Check if directory is writable
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Test write access
        test_file = os.path.join(db_dir, ".write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        logger.info(f"✅ SQLite database ready: {db_path}")
        return True
    
    except Exception as e:
        logger.error(f"❌ SQLite database check failed: {str(e)}")
        return False


def _check_postgresql_available(
    timeout_seconds: int = 30,
    retry_count: int = 3,
    retry_delay_ms: int = 100
) -> bool:
    """Check if PostgreSQL is available with retries."""
    from database.core.config import get_database_url, get_masked_database_url
    
    start_time = time.time()
    
    for attempt in range(1, retry_count + 1):
        try:
            # Attempt connection
            from sqlalchemy import create_engine, text
            
            url = get_masked_database_url()
            logger.debug(f"PostgreSQL connection attempt {attempt}/{retry_count} to {url}")
            
            engine = create_engine(get_database_url(), connect_args={"timeout": 5})
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("✅ PostgreSQL database ready")
            return True
        
        except Exception as e:
            elapsed = time.time() - start_time
            
            if elapsed > timeout_seconds:
                logger.error(
                    f"❌ Database not available after {timeout_seconds} seconds: {str(e)}"
                )
                return False
            
            if attempt < retry_count:
                wait_ms = retry_delay_ms * (2 ** (attempt - 1))
                logger.warning(
                    f"Database connection failed. Retrying in {wait_ms}ms... "
                    f"({attempt}/{retry_count})"
                )
                time.sleep(wait_ms / 1000.0)
            else:
                logger.error(f"❌ Database connection failed after {retry_count} attempts")
                return False
    
    return False


def initialize_database(
    debug: bool = False
) -> bool:
    """
    Initialize the database connection and create tables.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from database import db
        
        logger.info("Initializing database...")
        db.initialize(debug=debug)
        logger.info("✅ Database initialized successfully")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        return False


def print_database_error_guide() -> None:
    """Print helpful error message if database initialization fails."""
    print("\n" + "="*70)
    print(" ❌ DATABASE INITIALIZATION FAILED")
    print("="*70)
    print("\nThe application could not connect to the database.")
    print("\n📋 TROUBLESHOOTING STEPS:")
    print("\n1. Check your .env file configuration:")
    print("   - DATABASE_TYPE (sqlite or postgresql)")
    print("   - DATABASE_URL (connection string)")
    print("   - DATABASE_TIMEOUT (wait time for DB)")
    print("\n2. For SQLite:")
    print("   - Ensure the directory is writable")
    print("   - Check disk space")
    print("   - Verify no permission errors")
    print("\n3. For PostgreSQL:")
    print("   - Verify PostgreSQL server is running")
    print("   - Check connection credentials")
    print("   - Ensure database exists")
    print("   - Verify firewall allows connections")
    print("\n4. Check logs for detailed error:")
    print("   - tail -f logs/rag_*.log")
    print("\n5. Reset SQLite and try again:")
    print("   - rm chat_history.db (if using SQLite)")
    print("   - bash start.sh")
    print("\n" + "="*70 + "\n")
