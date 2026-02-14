"""
Backend chat facade: build context + process query (RAG + eligibility/commands).

Used by app.py (Streamlit) and portal_api.py (FastAPI). No UI dependencies.
"""

import time
import traceback
from typing import Any, Dict, Optional, Tuple

from rag.query_data import query_rag, extract_sources_from_query
from utils.logger.rag_logging import RAGLogger
from utils.context.context_builder import build_rag_context
from rag.config.prompts import DEFAULT_PROMPT_VERSION
from utils.commands import (
    parse_command,
    dispatch_command,
    get_registry,
    get_validation_error_tooltip,
)

rag_logger = RAGLogger()


def validate_message(content: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the message can be sent (for command mode: block until required args provided).

    Returns:
        (valid, error_message). If valid is False, error_message is the text to show in the UI
        (e.g. placeholder). If valid is True, error_message is None.
    """
    if not (content or "").strip():
        return False, "Please enter a message."
    parsed = parse_command(content)
    if not parsed.is_command:
        return True, None
    if parsed.parse_errors:
        return False, (parsed.parse_errors[0] if parsed.parse_errors else "Invalid command.")
    registry = get_registry()
    if parsed.command_name not in registry.get("_by_command", {}):
        return False, "Unknown command."
    tooltip = get_validation_error_tooltip(parsed.command_name, parsed.args_raw, registry)
    if tooltip:
        return False, tooltip
    return True, None


def _get_reason_friendly_title(reason_code: str) -> str:
    """Map reason code to friendly display title."""
    title_map = {
        "JOINT_ACCOUNT_EXCLUSION": "Joint Account Status",
        "AVERAGE_BALANCE_EXCLUSION": "Average Balance",
        "DPD_ARREARS_EXCLUSION": "DPD Arrears",
        "ELMA_EXCLUSION": "ELMA Eligibility",
        "MANDATE_EXCLUSION": "Mandate/Signing Authority",
        "CLASSIFICATION_EXCLUSION": "Customer Classification",
        "LINKED_BASE_EXCLUSION": "Linked Base Account",
        "CUSTOMER_VINTAGE_EXCLUSION": "Customer Vintage",
        "DORMANCY_INACTIVE_EXCLUSION": "Account Activity Status",
        "TURNOVER_EXCLUSION": "Customer Turnover",
        "RECENCY_EXCLUSION": "Recent Banking Patterns",
    }
    return title_map.get(reason_code, reason_code)


def _substitute_evidence_placeholders(template: str, evidence: Dict[str, Any]) -> str:
    """Substitute placeholders in evidence template with actual values."""
    result = template
    for key, value in evidence.items():
        placeholder = "{" + key + "}"
        result = result.replace(placeholder, str(value))
    return result


def _build_inline_evidence(
    reason_code: str,
    evidence: Dict[str, Any],
    evidence_display_rules: Dict[str, Any],
) -> str:
    """Build inline evidence string using evidence display rules."""
    display_rules = evidence_display_rules.get("display_rules", {})
    rule = display_rules.get(reason_code, {})

    if rule.get("has_evidence") is False:
        return ""

    format_template = rule.get("format_template", [])
    if not format_template:
        return ""

    required_fields = rule.get("required_fields", [])
    for field in required_fields:
        if field not in evidence or evidence[field] is None or evidence[field] == "":
            return rule.get("missing_error", "Evidence unavailable")

    evidence_parts = []
    for template in format_template:
        formatted = _substitute_evidence_placeholders(template, evidence)
        if formatted and formatted.strip():
            evidence_parts.append(formatted)

    return " – ".join(evidence_parts)


def format_eligibility_response(payload: Dict[str, Any]) -> str:
    """Format eligibility payload into v1.1 compliant UI output."""
    try:
        from eligibility.config_loader import ConfigLoader

        config_loader = ConfigLoader()
        evidence_display_rules = config_loader.get_evidence_display_rules()
    except Exception:
        evidence_display_rules = {"display_rules": {}}

    response_lines = []
    accounts = payload.get("accounts", [])

    if not accounts:
        return "No accounts found in results."

    for account_idx, account in enumerate(accounts):
        customer_name = account.get("customer_name", "Unknown")
        account_number = account.get("account_number", "Unknown")
        status = account.get("status", "UNKNOWN")

        response_lines.append(f"Customer Name: {customer_name}")
        response_lines.append("")
        response_lines.append(f"Account Number: {account_number}")
        response_lines.append("")
        response_lines.append(f"Status: {status}")
        response_lines.append("")

        reasons = account.get("reasons", [])

        if not reasons:
            if status == "ELIGIBLE":
                response_lines.append("✅ Customer is eligible for loan limit.")
            elif status == "CANNOT_CONFIRM":
                response_lines.append("Account not found in eligibility database.")
            response_lines.append("")
        else:
            response_lines.append("Reasons")
            response_lines.append("---")

            for reason_idx, reason in enumerate(reasons):
                reason_number = reason_idx + 1
                reason_code = reason.get("code", "UNKNOWN")
                friendly_title = _get_reason_friendly_title(reason_code)
                evidence = reason.get("evidence", {})
                inline_evidence = _build_inline_evidence(
                    reason_code, evidence, evidence_display_rules
                )

                if inline_evidence:
                    response_lines.append(
                        f"{reason_number}. {friendly_title} ({inline_evidence})"
                    )
                else:
                    response_lines.append(f"{reason_number}. {friendly_title}")

                meaning = reason.get("meaning", "")
                if meaning:
                    response_lines.append(meaning)

                next_steps = reason.get("next_steps", [])
                if next_steps:
                    response_lines.append("")
                    response_lines.append("Next Steps")
                    for step in next_steps:
                        action = step.get("action", "")
                        owner = step.get("owner", "")
                        if owner:
                            response_lines.append(f"- {action} (Owner: {owner})")
                        else:
                            response_lines.append(f"- {action}")

                if reason_idx < len(reasons) - 1:
                    response_lines.append("---")

                response_lines.append("")

        if account_idx < len(accounts) - 1:
            response_lines.append(
                "==================== NEXT ACCOUNT ===================="
            )
            response_lines.append("")

    return "\n".join(response_lines)


def process_query(
    query_text: str,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    enriched_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process user query through RAG pipeline (commands + RAG).
    No Streamlit dependency.
    """
    request_id = rag_logger.generate_request_id()
    start_time = time.time()

    result = {
        "request_id": request_id,
        "success": False,
        "response": None,
        "error": None,
        "error_type": None,
        "latency_ms": 0,
        "sources": [],
        "prompt_version": prompt_version,
        "is_eligibility_flow": False,
        "eligibility_payload": None,
    }

    parsed = parse_command(query_text)
    if parsed.is_command and not parsed.parse_errors:
        try:
            cmd_result = dispatch_command(
                parsed.command_name,
                parsed.args_raw,
                get_registry(),
            )
            if cmd_result.get("payload") is not None:
                result["is_eligibility_flow"] = True
                result["eligibility_payload"] = cmd_result["payload"]
                if cmd_result.get("response"):
                    response_text = cmd_result["response"]
                else:
                    response_text = format_eligibility_response(cmd_result["payload"])
                result["success"] = cmd_result.get("success", True)
                result["response"] = response_text
                result["latency_ms"] = (time.time() - start_time) * 1000
                return result
            if not cmd_result.get("success") and cmd_result.get("response"):
                result["success"] = False
                result["error"] = cmd_result.get("error_message") or cmd_result["response"]
                result["response"] = cmd_result["response"]
                result["latency_ms"] = (time.time() - start_time) * 1000
                return result
        except Exception as e:
            rag_logger.log_error(
                request_id=request_id,
                error_type="CommandDispatchError",
                error_message=str(e),
                traceback_str=traceback.format_exc(),
            )
            result["success"] = False
            result["error"] = str(e)
            result["response"] = "I couldn't complete that command. Please try again."
            result["latency_ms"] = (time.time() - start_time) * 1000
            return result

    try:
        sources = extract_sources_from_query(query_text)
        result["sources"] = sources

        response = query_rag(
            query_text,
            prompt_version=prompt_version,
            enriched_context=enriched_context,
        )
        result["success"] = True
        result["response"] = response
        result["latency_ms"] = (time.time() - start_time) * 1000

        rag_logger.log_warning(
            request_id=request_id,
            message=f"UI query processed successfully in {result['latency_ms']:.2f}ms",
            event_type="ui_query_complete",
        )

    except ConnectionError as e:
        result["error_type"] = "ConnectionError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="ConnectionError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    except TimeoutError as e:
        result["error_type"] = "TimeoutError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="TimeoutError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    except ValueError as e:
        result["error_type"] = "ValueError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="ValueError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    except FileNotFoundError as e:
        result["error_type"] = "FileNotFoundError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="FileNotFoundError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    except KeyError as e:
        result["error_type"] = "KeyError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="KeyError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    except RuntimeError as e:
        result["error_type"] = "RuntimeError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="RuntimeError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    except Exception as e:
        result["error_type"] = type(e).__name__
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )

    return result


def run_chat(
    user_message: str,
    conversation_id: str,
    db_manager: Any,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> Dict[str, Any]:
    """
    Build RAG context and process one user message (single entry point for app and portal).

    Args:
        user_message: User's message text.
        conversation_id: Conversation ID for history/context.
        db_manager: Database manager instance (database.db).
        prompt_version: System prompt version.

    Returns:
        Same dict as process_query: request_id, success, response, error, sources,
        is_eligibility_flow, eligibility_payload, latency_ms, etc.
    """
    enriched_context = build_rag_context(
        conversation_id=conversation_id,
        user_message=user_message,
        db_manager=db_manager,
        prompt_version=prompt_version,
    )
    return process_query(
        user_message,
        prompt_version=prompt_version,
        enriched_context=enriched_context,
    )
