"""
Command Registry - Load command definitions and validate arguments.

Validates args against args_schema. For check_eligibility, account is required
(10-digit account number). Returns validation result and optional extracted account(s).
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# 10-digit account pattern (same as eligibility.account_extractor)
ACCOUNT_PATTERN = re.compile(r"\b\d{10}\b")


def _registry_path() -> Path:
    return Path(__file__).resolve().parent / "commands_registry.json"


def get_registry() -> Dict[str, Any]:
    """Load and return the command registry (commands list keyed by command string)."""
    path = _registry_path()
    if not path.exists():
        return {"commands": [], "_by_command": {}}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    commands = data.get("commands", [])
    by_command = {c["command"]: c for c in commands if c.get("enabled", True)}
    data["_by_command"] = by_command
    return data


def _extract_accounts_from_args(args_raw: Optional[str]) -> List[str]:
    """Extract 10-digit account numbers from args string. Dedupe, preserve order."""
    if not args_raw or not args_raw.strip():
        return []
    seen = set()
    result = []
    for m in ACCOUNT_PATTERN.findall(args_raw):
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def validate_command_args(
    command_name: str,
    args_raw: Optional[str],
    registry: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[str], Optional[List[str]]]:
    """
    Validate command arguments against the command's args_schema.

    For check_eligibility, account is required: at least one 10-digit account
    must be present in args_raw.

    Returns:
        (valid, parse_errors, extracted_accounts)
        - valid: True if args satisfy schema.
        - parse_errors: List of user-facing error messages.
        - extracted_accounts: List of account numbers if type is account and valid.
    """
    reg = registry or get_registry()
    by_command = reg.get("_by_command", {})
    spec = by_command.get(command_name)
    if not spec:
        return False, [f"Unknown command: {command_name}."], None

    schema = spec.get("args_schema") or {}
    errors: List[str] = []
    extracted_accounts: Optional[List[str]] = None

    for arg_key, arg_spec in schema.items():
        if not isinstance(arg_spec, dict):
            continue
        required = arg_spec.get("required", False)
        arg_type = arg_spec.get("type", "string")

        if arg_type == "account":
            accounts = _extract_accounts_from_args(args_raw)
            extracted_accounts = accounts
            if required and not accounts:
                errors.append("Please provide a 10-digit account number.")
            elif not required and not accounts:
                pass
            # else: we have at least one account

    valid = len(errors) == 0
    return valid, errors, extracted_accounts


def get_validation_error_tooltip(
    command_name: str,
    args_raw: Optional[str],
    registry: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Return a single tooltip string when command args are invalid, else None.

    Used by the UI to block send and show an error tooltip when e.g.
    /check_eligibility is used without an account number.
    """
    valid, errors, _ = validate_command_args(command_name, args_raw, registry)
    if valid or not errors:
        return None
    return " ".join(errors)
