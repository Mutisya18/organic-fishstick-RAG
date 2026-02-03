"""
LLM Payload Builder - Format eligibility results into LLM-ready JSON.

Takes output from EligibilityProcessor and wraps it in a structured payload
with metadata, summary statistics, and proper JSON formatting.

Validates payload structure before returning.
Logs validation results.
"""

import json
import time
from typing import List, Dict, Any
from datetime import datetime, timezone

from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager


class LLMPayloadBuilder:
    """Build LLM-ready eligibility payload."""

    def __init__(self):
        """Initialize payload builder."""
        self.rag_logger = RAGLogger()
        self.session_manager = SessionManager()

    def build(
        self,
        eligibility_results: List[Dict[str, Any]],
        request_id: str,
        processing_latency_ms: float = 0.0
    ) -> Dict[str, Any]:
        """
        Build LLM payload from eligibility results.

        Args:
            eligibility_results: List of account results from EligibilityProcessor.
            request_id: Request ID for logging.
            processing_latency_ms: Latency of processor in milliseconds.

        Returns:
            Formatted payload ready for LLM.

        Raises:
            ValueError: If results list is empty.
        """
        if not eligibility_results:
            self.rag_logger.log(
                request_id=request_id,
                event="llm_payload_build",
                severity="WARNING",
                message="No eligibility results provided for payload",
                context={"result_count": 0}
            )
            # Return minimal valid payload
            return self._build_empty_payload(request_id)

        start_time = time.time()

        # Count status types
        eligible_count = sum(
            1 for r in eligibility_results
            if r.get("status") == "ELIGIBLE"
        )
        not_eligible_count = sum(
            1 for r in eligibility_results
            if r.get("status") == "NOT_ELIGIBLE"
        )
        cannot_confirm_count = sum(
            1 for r in eligibility_results
            if r.get("status") == "CANNOT_CONFIRM"
        )

        # Count total reasons and explanation-ready reasons
        total_reasons_count = 0
        ready_for_llm_count = 0
        
        for r in eligibility_results:
            reasons = r.get("reasons", [])
            total_reasons_count += len(reasons)
            ready_for_llm_count += sum(
                1 for reason in reasons
                if reason.get("explanation_status") == "ready"
            )

        # Build payload
        payload = {
            "request_id": request_id,
            "batch_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "accounts": eligibility_results,
            "summary": {
                "total_accounts": len(eligibility_results),
                "eligible_count": eligible_count,
                "not_eligible_count": not_eligible_count,
                "cannot_confirm_count": cannot_confirm_count,
                "total_reasons_extracted": total_reasons_count,
                "reasons_ready_for_llm": ready_for_llm_count,
                "processing_latency_ms": processing_latency_ms,
            }
        }

        # Validate payload structure
        is_valid = self._validate_payload(payload, request_id)

        if is_valid:
            build_latency = (time.time() - start_time) * 1000
            self.rag_logger.log(
                request_id=request_id,
                event="llm_payload_complete",
                severity="INFO",
                message="LLM payload built and validated",
                context={
                    "total_accounts": len(eligibility_results),
                    "total_reasons": total_reasons_count,
                    "build_latency_ms": build_latency,
                }
            )

        return payload

    def build_to_json_string(
        self,
        eligibility_results: List[Dict[str, Any]],
        request_id: str,
        processing_latency_ms: float = 0.0
    ) -> str:
        """
        Build and serialize LLM payload to JSON string.

        Args:
            eligibility_results: List of account results from EligibilityProcessor.
            request_id: Request ID for logging.
            processing_latency_ms: Latency of processor in milliseconds.

        Returns:
            JSON string ready to send to LLM.
        """
        payload = self.build(
            eligibility_results,
            request_id,
            processing_latency_ms
        )

        try:
            return json.dumps(payload, indent=2, default=str)
        except Exception as e:
            self.rag_logger.log(
                request_id=request_id,
                event="llm_payload_json_serialization_error",
                severity="ERROR",
                message=f"Failed to serialize payload to JSON: {str(e)}",
                context={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            raise

    def _build_empty_payload(self, request_id: str) -> Dict[str, Any]:
        """
        Build minimal valid payload for empty results.

        Args:
            request_id: Request ID for logging.

        Returns:
            Minimal valid payload.
        """
        return {
            "request_id": request_id,
            "batch_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "accounts": [],
            "summary": {
                "total_accounts": 0,
                "eligible_count": 0,
                "not_eligible_count": 0,
                "cannot_confirm_count": 0,
                "total_reasons_extracted": 0,
                "processing_latency_ms": 0.0,
            }
        }

    def _validate_payload(
        self,
        payload: Dict[str, Any],
        request_id: str
    ) -> bool:
        """
        Validate payload structure.

        Args:
            payload: Payload to validate.
            request_id: Request ID for logging.

        Returns:
            True if valid, False otherwise.
        """
        required_fields = ["request_id", "batch_timestamp", "accounts", "summary"]

        for field in required_fields:
            if field not in payload:
                self.rag_logger.log(
                    request_id=request_id,
                    event="llm_payload_validation_error",
                    severity="ERROR",
                    message=f"Missing required field in payload: {field}",
                    context={"field": field}
                )
                return False

        # Validate summary structure
        summary = payload.get("summary", {})
        summary_fields = [
            "total_accounts",
            "eligible_count",
            "not_eligible_count",
            "cannot_confirm_count",
            "total_reasons_extracted",
            "processing_latency_ms",
        ]

        for field in summary_fields:
            if field not in summary:
                self.rag_logger.log(
                    request_id=request_id,
                    event="llm_payload_validation_error",
                    severity="ERROR",
                    message=f"Missing required summary field: {field}",
                    context={"field": field}
                )
                return False

        # Validate accounts list
        if not isinstance(payload.get("accounts"), list):
            self.rag_logger.log(
                request_id=request_id,
                event="llm_payload_validation_error",
                severity="ERROR",
                message="Accounts field is not a list",
                context={"accounts_type": type(payload.get("accounts"))}
            )
            return False

        # Validate each account result
        for idx, account in enumerate(payload.get("accounts", [])):
            if not isinstance(account, dict):
                self.rag_logger.log(
                    request_id=request_id,
                    event="llm_payload_validation_error",
                    severity="ERROR",
                    message=f"Account at index {idx} is not a dict",
                    context={"index": idx, "type": type(account)}
                )
                return False

            if "account_number_hash" not in account:
                self.rag_logger.log(
                    request_id=request_id,
                    event="llm_payload_validation_error",
                    severity="ERROR",
                    message=f"Account at index {idx} missing account_number_hash",
                    context={"index": idx}
                )
                return False

            if "status" not in account:
                self.rag_logger.log(
                    request_id=request_id,
                    event="llm_payload_validation_error",
                    severity="ERROR",
                    message=f"Account at index {idx} missing status",
                    context={"index": idx}
                )
                return False

            # Validate status value
            if account.get("status") not in ["ELIGIBLE", "NOT_ELIGIBLE", "CANNOT_CONFIRM"]:
                self.rag_logger.log(
                    request_id=request_id,
                    event="llm_payload_validation_error",
                    severity="ERROR",
                    message=f"Account at index {idx} has invalid status",
                    context={"index": idx, "status": account.get("status")}
                )
                return False

        self.rag_logger.log(
            request_id=request_id,
            event="llm_payload_validation_success",
            severity="DEBUG",
            message="Payload validation successful",
            context={"account_count": len(payload.get("accounts", []))}
        )

        return True
    def get_explanation_ready_reasons(
        self,
        account_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter reasons to only those ready for LLM explanation generation.
        Excludes reasons with validation failures that have error messages.

        Args:
            account_result: Single account result from EligibilityProcessor.

        Returns:
            List of reasons with explanation_status == "ready".
        """
        reasons = account_result.get("reasons", [])
        return [
            reason for reason in reasons
            if reason.get("explanation_status") == "ready"
        ]

    def get_blocked_reasons(
        self,
        account_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get reasons that are blocked from LLM generation due to missing evidence.

        Args:
            account_result: Single account result from EligibilityProcessor.

        Returns:
            List of reasons with explanation_status == "blocked".
        """
        reasons = account_result.get("reasons", [])
        return [
            reason for reason in reasons
            if reason.get("explanation_status") == "blocked"
        ]