"""
Command Dispatcher - Invoke the handler for a parsed command.

When a command is detected and args are valid, dispatches to the
appropriate handler (e.g. check_eligibility -> Eligibility Orchestrator).
"""

from typing import Dict, Any, Optional

from utils.commands.registry import get_registry, validate_command_args


def dispatch_command(
    command_name: str,
    args_raw: Optional[str],
    registry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate args and run the handler for the given command.

    Returns a result dict with:
    - success: bool
    - response: str or None (formatted response for UI)
    - payload: dict or None (e.g. eligibility payload)
    - error_type: str or None (missing_args, invalid_args, handler_error, unknown_command)
    - error_message: str or None
    """
    reg = registry or get_registry()
    by_command = reg.get("_by_command", {})

    if command_name not in by_command:
        return {
            "success": False,
            "response": None,
            "payload": None,
            "error_type": "unknown_command",
            "error_message": "I don't recognize that command.",
        }

    valid, errors, extracted_accounts = validate_command_args(
        command_name, args_raw, reg
    )
    if not valid:
        return {
            "success": False,
            "response": " ".join(errors),
            "payload": None,
            "error_type": "missing_args",
            "error_message": " ".join(errors),
        }

    spec = by_command[command_name]
    handler_id = spec.get("handler")
    if handler_id == "check_eligibility":
        return _handle_check_eligibility(
            args_raw or "",
            extracted_accounts or [],
        )

    return {
        "success": False,
        "response": None,
        "payload": None,
        "error_type": "unknown_command",
        "error_message": "No handler for this command.",
    }


def _handle_check_eligibility(
    args_raw: str,
    extracted_accounts: list,
) -> Dict[str, Any]:
    """
    Run eligibility flow with the provided account number(s).

    Uses Eligibility Orchestrator with skip_intent_detection and
    the pre-extracted account list so intent detection is bypassed.
    """
    try:
        from eligibility.orchestrator import EligibilityOrchestrator
    except ImportError:
        return {
            "success": False,
            "response": "Eligibility service is not available.",
            "payload": None,
            "error_type": "handler_error",
            "error_message": "Eligibility module not available.",
        }

    try:
        orchestrator = EligibilityOrchestrator()
        # Pass a message that contains the account(s) so extractor finds them;
        # orchestrator will skip intent and run extraction -> validation -> process
        message_with_account = args_raw if args_raw.strip() else " ".join(extracted_accounts)
        payload = orchestrator.process_message(
            message_with_account,
            skip_intent_detection=True,
        )
        if payload is None:
            return {
                "success": False,
                "response": "Unable to process eligibility check. Please try again.",
                "payload": None,
                "error_type": "handler_error",
                "error_message": "Orchestrator returned no result.",
            }
        if payload.get("status") == "ERROR":
            return {
                "success": True,
                "response": payload.get("error_message", "An error occurred."),
                "payload": payload,
                "error_type": None,
                "error_message": None,
            }
        return {
            "success": True,
            "response": None,
            "payload": payload,
            "error_type": None,
            "error_message": None,
        }
    except Exception as e:
        return {
            "success": False,
            "response": "I couldn't complete that command. Please try again.",
            "payload": None,
            "error_type": "handler_error",
            "error_message": str(e),
        }
