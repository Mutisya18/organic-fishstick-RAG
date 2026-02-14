"""
Command module - Slash-command parsing, validation, and dispatch.

Replaces intent-based eligibility routing with explicit commands.
Commands are recognized only when they start at the beginning of a line.
"""

from utils.commands.parser import parse_command
from utils.commands.registry import (
    get_registry,
    validate_command_args,
    get_validation_error_tooltip,
)
from utils.commands.dispatcher import dispatch_command

__all__ = [
    "parse_command",
    "get_registry",
    "validate_command_args",
    "get_validation_error_tooltip",
    "dispatch_command",
]
