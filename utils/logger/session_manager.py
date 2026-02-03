"""
Session Manager - Singleton logger with session-based file rotation.

Manages log file creation, rotation (idle 15min / age 60min),
immediate flushing, session headers, and trace IDs.
"""

import os
import json
import time
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class SessionManager:
    """Singleton session-based logger with file rotation."""
    
    _instance: Optional["SessionManager"] = None
    _lock = threading.Lock()
    
    # Configuration
    LOG_DIR = os.getenv("LOG_DIR", "/workspaces/rag-tutorial-v2/logs")
    IDLE_TIMEOUT_SECONDS = int(os.getenv("IDLE_TIMEOUT_SECONDS", "900"))  # 15 min
    MAX_AGE_SECONDS = int(os.getenv("MAX_AGE_SECONDS", "3600"))  # 60 min
    ENV = os.getenv("ENV", "dev")
    SYSTEM_VERSION = "1.0.0"
    
    def __new__(cls) -> "SessionManager":
        """Ensure singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize session manager (called once)."""
        if self._initialized:
            return
        
        self._initialized = True
        os.makedirs(self.LOG_DIR, exist_ok=True)
        
        self.file_handle: Optional[object] = None
        self.file_creation_time: float = 0.0
        self.last_entry_time: float = 0.0
        self.file_path: str = ""
        self._session_id = str(uuid.uuid4())
        
        self._open_new_log_file()
    
    def _get_log_filename(self) -> str:
        """Generate timestamp-based log filename."""
        now = datetime.now(timezone.utc)
        return f"session_{now.strftime('%Y%m%d_%H%M%S')}.log"
    
    def _open_new_log_file(self):
        """Open a new log file and write session header."""
        with self._lock:
            # Close previous file if open
            if self.file_handle:
                try:
                    self.file_handle.close()
                except Exception:
                    pass
            
            # Create new file
            self.file_path = os.path.join(self.LOG_DIR, self._get_log_filename())
            self.file_handle = open(self.file_path, "a", buffering=1)  # Line-buffered
            self.file_creation_time = time.time()
            self.last_entry_time = time.time()
            
            # Write session header
            header = {
                "event": "session_start",
                "session_id": self._session_id,
                "system_version": self.SYSTEM_VERSION,
                "environment": self.ENV,
                "start_time": datetime.now(timezone.utc).isoformat() + "Z",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            }
            self.file_handle.write(json.dumps(header) + "\n")
            self.file_handle.flush()
    
    def _should_rotate(self) -> bool:
        """Check if log rotation is needed (idle or age)."""
        now = time.time()
        idle_time = now - self.last_entry_time
        age_time = now - self.file_creation_time
        
        # Trigger A: Idle > 15 minutes
        if idle_time > self.IDLE_TIMEOUT_SECONDS:
            return True
        
        # Trigger B: Age > 60 minutes
        if age_time > self.MAX_AGE_SECONDS:
            return True
        
        return False
    
    def log(self, entry: Dict[str, Any], severity: str = "INFO") -> None:
        """
        Log a JSON entry with automatic rotation and flushing.
        
        Args:
            entry: Dictionary to log as JSON.
            severity: Log severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        with self._lock:
            # Rotate if needed
            if self._should_rotate():
                self._open_new_log_file()
            
            # Update last entry time
            self.last_entry_time = time.time()
            
            # Ensure required fields
            if "timestamp" not in entry:
                entry["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z"
            
            if "severity" not in entry:
                entry["severity"] = severity
            
            if "session_id" not in entry:
                entry["session_id"] = self._session_id
            
            # Write to file and flush immediately
            try:
                self.file_handle.write(json.dumps(entry) + "\n")
                self.file_handle.flush()
            except Exception as e:
                # Fallback: print to stderr if file write fails
                import sys
                print(f"Failed to write log: {e}", file=sys.stderr)
    
    def get_session_id(self) -> str:
        """Return the current session ID."""
        return self._session_id
    
    def get_log_file_path(self) -> str:
        """Return the current log file path."""
        return self.file_path
    
    def close(self):
        """Close the log file (cleanup)."""
        with self._lock:
            if self.file_handle:
                try:
                    self.file_handle.close()
                except Exception:
                    pass
                self.file_handle = None


# Global singleton instance
_session_manager = SessionManager()
