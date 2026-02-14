"""
Backend facade for chat processing.

Shared by Streamlit (app.py) and Portal (portal_api.py).
No Streamlit or FastAPI dependencies here.
"""

from .chat import run_chat

__all__ = ["run_chat"]
