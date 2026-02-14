"""
Command Parser - Detect slash commands at start of line only.

A line is a command line if it begins at a new line and the first
character is /. Command token is the first word (e.g. /check_eligibility).
Arguments are everything after the command token on that line, trimmed.
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    """Result of parsing a message for a command."""

    is_command: bool
    command_name: Optional[str] = None  # e.g. "/check_eligibility"
    args_raw: Optional[str] = None
    parse_errors: List[str] = None

    def __post_init__(self):
        if self.parse_errors is None:
            self.parse_errors = []


def parse_command(message: Optional[str]) -> ParsedCommand:
    """
    Parse message for a slash command at start of (first) line.

    Rules:
    - Command only if line starts at beginning of message or after newline.
    - First non-empty character of that line must be /.
    - Command token = first whitespace-delimited token (e.g. /check_eligibility).
    - Args = everything after the command token on that line, trimmed.
    - At most one command per message (first line only for Phase 1).

    Args:
        message: User message (can be multiline).

    Returns:
        ParsedCommand with is_command, command_name, args_raw, parse_errors.
    """
    if not message or not isinstance(message, str):
        return ParsedCommand(
            is_command=False,
            parse_errors=["Empty or invalid message."],
        )

    text = message.strip()
    if not text:
        return ParsedCommand(
            is_command=False,
            parse_errors=["Message is empty."],
        )

    # First line only
    first_line = text.split("\n")[0].strip()
    if not first_line.startswith("/"):
        return ParsedCommand(is_command=False)

    # Empty command: "/" or "/ " only
    parts = first_line.split(maxsplit=1)
    command_token = parts[0]
    if not command_token or command_token == "/":
        return ParsedCommand(
            is_command=True,
            command_name="/",
            args_raw=None,
            parse_errors=["Command cannot be empty. Use e.g. /check_eligibility."],
        )

    args_raw = parts[1].strip() if len(parts) > 1 else ""
    return ParsedCommand(
        is_command=True,
        command_name=command_token,
        args_raw=args_raw if args_raw else None,
        parse_errors=[],
    )
