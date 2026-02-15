"""
Auth module for portal user management.

Public API: password hashing, validation, session CRUD, user service, middleware.
"""

from auth.password import hash_password, verify_password
from auth.validation import validate_password, validate_email
from auth.session import (
    create_session,
    validate_session,
    extend_session,
    expire_session,
    cleanup_expired_sessions,
)
from auth.user_service import (
    create_user,
    get_user_by_email,
    list_users,
    authenticate,
    update_last_login,
    deactivate_user,
)
from auth.middleware import get_current_user

__all__ = [
    "hash_password",
    "verify_password",
    "validate_password",
    "validate_email",
    "create_session",
    "validate_session",
    "extend_session",
    "expire_session",
    "cleanup_expired_sessions",
    "create_user",
    "get_user_by_email",
    "list_users",
    "authenticate",
    "update_last_login",
    "deactivate_user",
    "get_current_user",
]
