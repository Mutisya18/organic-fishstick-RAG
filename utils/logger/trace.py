"""
Technical Trace Decorator

Wraps functions to log entry, exit, exceptions with full context:
file path, function name, line number, args/kwargs, return value, duration, thread/process ID.
"""

import functools
import inspect
import threading
import time
import traceback
import os
from typing import Callable, Any
from datetime import datetime, timezone

from utils.logger.session_manager import SessionManager
from utils.logger.pii import scrub_text


def technical_trace(func: Callable) -> Callable:
    """
    Decorator to log function entry, exit, and exceptions with technical context.
    
    Logs automatically include:
    - File path, function name, line number (caller context)
    - Thread ID, process ID (execution state)
    - Arguments and return value (data flow)
    - Duration and timestamps (execution metrics)
    - Full traceback on exception (error handling)
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        sm = SessionManager()
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        
        # Extract caller context
        file_path = caller_frame.f_code.co_filename if caller_frame else "unknown"
        function_name = func.__name__
        line_number = caller_frame.f_lineno if caller_frame else 0
        thread_id = threading.get_ident()
        process_id = os.getpid()
        
        # Start timing
        start_time = time.time()
        
        # Log function entry
        entry_log = {
            "event": "function_call",
            "function_name": function_name,
            "file_path": file_path,
            "line_number": line_number,
            "thread_id": thread_id,
            "process_id": process_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "args": str(args)[:500],  # Limit length
            "kwargs": str(kwargs)[:500],  # Limit length
        }
        sm.log(entry_log, severity="DEBUG")
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Log function exit
            duration_ms = (time.time() - start_time) * 1000
            exit_log = {
                "event": "function_return",
                "function_name": function_name,
                "file_path": file_path,
                "line_number": line_number,
                "thread_id": thread_id,
                "process_id": process_id,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
                "duration_ms": duration_ms,
                "return_value_type": type(result).__name__,
            }
            sm.log(exit_log, severity="DEBUG")
            
            return result
        
        except Exception as e:
            # Log exception
            duration_ms = (time.time() - start_time) * 1000
            tb_str = traceback.format_exc()
            
            # Scrub any PII from traceback
            tb_scrubbed, _ = scrub_text(tb_str)
            
            error_log = {
                "event": "function_exception",
                "function_name": function_name,
                "file_path": file_path,
                "line_number": line_number,
                "thread_id": thread_id,
                "process_id": process_id,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
                "duration_ms": duration_ms,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": tb_scrubbed,
            }
            sm.log(error_log, severity="ERROR")
            
            raise
    
    return wrapper
