"""
Eligibility Orchestrator - Orchestrate entire eligibility flow.

Startup:
- Initialize ConfigLoader (may raise on bad config)
- Initialize DataLoader (may raise on bad data)

User message processing:
1. Intent detection - is this an eligibility question?
2. Account extraction - find 10-digit account numbers
3. Account validation - format check
4. Eligibility processing - check eligible/ineligible + extract reasons
5. LLM payload building - format for LLM

Returns structured response at each step.
Logs entire flow with request_id.
Handles all exceptions with proper error responses.
"""

import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager
from eligibility.config_loader import ConfigLoader
from eligibility.data_loader import DataLoader
from eligibility.intent_detector import IntentDetector
from eligibility.account_extractor import AccountExtractor
from eligibility.account_validator import AccountValidator
from eligibility.eligibility_processor import EligibilityProcessor
from eligibility.llm_payload_builder import LLMPayloadBuilder


class EligibilityOrchestrator:
    """Orchestrate entire eligibility flow."""

    _instance: Optional["EligibilityOrchestrator"] = None

    def __new__(cls) -> "EligibilityOrchestrator":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize orchestrator and all components."""
        if self._initialized:
            return

        self._initialized = True
        self.rag_logger = RAGLogger()
        self.session_manager = SessionManager()

        # Initialize all components
        try:
            self.config_loader = ConfigLoader()
            self.data_loader = DataLoader()
            self.intent_detector = IntentDetector()
            self.account_extractor = AccountExtractor()
            self.account_validator = AccountValidator()
            self.eligibility_processor = EligibilityProcessor()
            self.payload_builder = LLMPayloadBuilder()

            self.rag_logger.log(
                request_id=self.rag_logger.generate_request_id(),
                event="orchestrator_initialized",
                severity="INFO",
                message="Eligibility orchestrator initialized successfully"
            )
        except Exception as e:
            self.rag_logger.log(
                request_id=self.rag_logger.generate_request_id(),
                event="orchestrator_init_failed",
                severity="CRITICAL",
                message=f"Failed to initialize orchestrator: {str(e)}",
                context={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            raise

    def process_message(
        self,
        user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process user message through entire eligibility flow.

        Args:
            user_message: User's message to analyze.

        Returns:
            LLM payload (dict) if eligibility question, None otherwise.

        Raises:
            Never - always returns structured response or None.
        """
        request_id = self.rag_logger.generate_request_id()
        start_time = time.time()

        try:
            self.rag_logger.log(
                request_id=request_id,
                event="eligibility_flow_start",
                severity="INFO",
                message="Starting eligibility flow"
            )

            # STEP 1: Intent Detection
            is_eligibility_check, message_hash = (
                self.intent_detector.detect(user_message)
            )

            if not is_eligibility_check:
                self.rag_logger.log(
                    request_id=request_id,
                    event="intent_not_eligibility",
                    severity="DEBUG",
                    message="Message is not an eligibility question",
                    context={"message_hash": message_hash}
                )
                return None

            self.rag_logger.log(
                request_id=request_id,
                event="intent_eligibility_detected",
                severity="DEBUG",
                message="Eligibility question detected"
            )

            # STEP 2: Account Extraction
            account_numbers = self.account_extractor.extract(
                user_message
            )

            if not account_numbers:
                error_response = self._build_error_response(
                    request_id,
                    "No account numbers found",
                    "Please share the 10-digit account number(s) so I can confirm eligibility."
                )
                self.rag_logger.log(
                    request_id=request_id,
                    event="no_accounts_extracted",
                    severity="INFO",
                    message="No accounts extracted from message"
                )
                return error_response

            self.rag_logger.log(
                request_id=request_id,
                event="accounts_extracted",
                severity="DEBUG",
                message=f"Extracted {len(account_numbers)} account(s)",
                context={"account_count": len(account_numbers)}
            )

            # STEP 3: Account Validation
            valid_accounts, invalid_accounts = (
                self.account_validator.validate(account_numbers)
            )

            if not valid_accounts:
                error_response = self._build_error_response(
                    request_id,
                    "Invalid account numbers",
                    f"The following account numbers are invalid: {', '.join(invalid_accounts)}. "
                    "Account numbers must be exactly 10 digits."
                )
                self.rag_logger.log(
                    request_id=request_id,
                    event="no_valid_accounts",
                    severity="WARNING",
                    message="No valid account numbers after validation",
                    context={"invalid_count": len(invalid_accounts)}
                )
                return error_response

            if invalid_accounts:
                self.rag_logger.log(
                    request_id=request_id,
                    event="some_accounts_invalid",
                    severity="WARNING",
                    message="Some accounts invalid",
                    context={
                        "valid_count": len(valid_accounts),
                        "invalid_count": len(invalid_accounts),
                    }
                )

            self.rag_logger.log(
                request_id=request_id,
                event="accounts_validated",
                severity="DEBUG",
                message=f"Validation: {len(valid_accounts)} valid, {len(invalid_accounts)} invalid",
                context={
                    "valid_count": len(valid_accounts),
                    "invalid_count": len(invalid_accounts),
                }
            )

            # STEP 4: Eligibility Processing
            processor_start = time.time()
            eligibility_results = self.eligibility_processor.process_accounts(
                valid_accounts,
                request_id
            )
            processor_latency = (time.time() - processor_start) * 1000

            if not eligibility_results:
                error_response = self._build_error_response(
                    request_id,
                    "Processing failed",
                    "Unable to process eligibility check. Please try again."
                )
                self.rag_logger.log(
                    request_id=request_id,
                    event="processor_no_results",
                    severity="ERROR",
                    message="Processor returned no results"
                )
                return error_response

            self.rag_logger.log(
                request_id=request_id,
                event="eligibility_results_ready",
                severity="DEBUG",
                message=f"Generated {len(eligibility_results)} account results",
                context={"result_count": len(eligibility_results)}
            )

            # STEP 5: LLM Payload Building
            payload = self.payload_builder.build(
                eligibility_results,
                request_id,
                processor_latency
            )

            total_latency = (time.time() - start_time) * 1000

            self.rag_logger.log(
                request_id=request_id,
                event="eligibility_flow_complete",
                severity="INFO",
                message="Eligibility flow completed successfully",
                context={
                    "total_latency_ms": total_latency,
                    "result_count": len(eligibility_results),
                }
            )

            return payload

        except Exception as e:
            self.rag_logger.log(
                request_id=request_id,
                event="eligibility_flow_error",
                severity="ERROR",
                message=f"Eligibility flow failed: {str(e)}",
                context={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )

            # Return error response instead of raising
            return self._build_error_response(
                request_id,
                "Processing error",
                "An error occurred while processing your eligibility check. Please try again."
            )

    def _build_error_response(
        self,
        request_id: str,
        error_type: str,
        error_message: str
    ) -> Dict[str, Any]:
        """
        Build structured error response.

        Args:
            request_id: Request ID for logging.
            error_type: Type of error.
            error_message: User-friendly error message.

        Returns:
            Structured error response.
        """
        return {
            "request_id": request_id,
            "status": "ERROR",
            "error_type": error_type,
            "error_message": error_message,
            "accounts": [],
            "summary": {
                "total_accounts": 0,
                "eligible_count": 0,
                "not_eligible_count": 0,
                "cannot_confirm_count": 0,
                "total_reasons_extracted": 0,
            }
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of orchestrator components.

        Returns:
            Status dict with counts of loaded data.
        """
        return {
            "initialized": self._initialized,
            "config_loader": "ready" if self.config_loader else "not_initialized",
            "data_loader": "ready" if self.data_loader else "not_initialized",
            "data_summary": self.data_loader.get_data_summary() if self.data_loader else {},
        }
