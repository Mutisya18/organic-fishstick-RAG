"""
Eligibility Processor - Core logic for eligibility checking and reason extraction.

For each account number:
1. Check if account in eligible_customers → ELIGIBLE
2. Check if account in reasons_file → NOT_ELIGIBLE (extract reasons)
3. Otherwise → CANNOT_CONFIRM

For NOT_ELIGIBLE accounts:
- Normalize row using checks_catalog rules
- Extract all "Exclude" checks + special Recency_Check="N" handling
- Build facts using reason_detection_rules
- Enrich with reason_playbook (meaning, next_steps, timing)

Logs processing steps, latency per account, reason extraction details.
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager
from eligibility.config_loader import ConfigLoader
from eligibility.data_loader import DataLoader


class EligibilityProcessor:
    """Process accounts and extract eligibility results."""

    def __init__(self):
        """Initialize processor with config and data loaders."""
        self.rag_logger = RAGLogger()
        self.session_manager = SessionManager()
        self.config_loader = ConfigLoader()
        self.data_loader = DataLoader()
        self.explanation_playbook = self.config_loader.get_explanation_playbook()
        self.evidence_display_rules = self.config_loader.get_evidence_display_rules()

    def process_accounts(
        self,
        account_numbers: List[str],
        request_id: str
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of account numbers and return eligibility results.

        Args:
            account_numbers: List of valid 10-digit account numbers.
            request_id: Request ID for logging.

        Returns:
            List of account results with status and reasons.

        Raises:
            ValueError: If account_numbers is empty.
        """
        if not account_numbers:
            self.rag_logger.log(
                request_id=request_id,
                event="eligibility_processing",
                severity="WARNING",
                message="No account numbers provided for processing",
                context={"account_count": 0}
            )
            return []

        start_time = time.time()
        results = []
        eligible_count = 0
        not_eligible_count = 0
        cannot_confirm_count = 0

        self.rag_logger.log(
            request_id=request_id,
            event="eligibility_processing_start",
            severity="INFO",
            message=f"Processing {len(account_numbers)} account(s)",
            context={"account_count": len(account_numbers)}
        )

        # Process each account
        for account_number in account_numbers:
            account_start = time.time()
            result = self._process_single_account(
                account_number,
                request_id
            )
            account_latency = (time.time() - account_start) * 1000

            results.append(result)

            # Track counts
            if result["status"] == "ELIGIBLE":
                eligible_count += 1
            elif result["status"] == "NOT_ELIGIBLE":
                not_eligible_count += 1
            else:
                cannot_confirm_count += 1

            # Log individual account processing
            self.rag_logger.log(
                request_id=request_id,
                event="account_processed",
                severity="DEBUG",
                message=f"Account processed: {result['status']}",
                context={
                    "status": result["status"],
                    "reason_count": len(result.get("reasons", [])),
                    "latency_ms": account_latency,
                }
            )

        total_latency = (time.time() - start_time) * 1000

        # Log completion
        self.rag_logger.log(
            request_id=request_id,
            event="eligibility_processing_complete",
            severity="INFO",
            message="Eligibility processing completed",
            context={
                "total_accounts": len(account_numbers),
                "eligible_count": eligible_count,
                "not_eligible_count": not_eligible_count,
                "cannot_confirm_count": cannot_confirm_count,
                "latency_ms": total_latency,
            }
        )

        return results

    def _process_single_account(
        self,
        account_number: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Process a single account.

        Args:
            account_number: 10-digit account number.
            request_id: Request ID for logging.

        Returns:
            Dict with account status and reasons (if applicable).
        """
        account_hash = self.rag_logger.hash_prompt(account_number)

        # Check if eligible
        if self.data_loader.is_eligible(account_number):
            return {
                "account_number": account_number,
                "account_number_hash": account_hash,
                "customer_name": "Unknown",
                "status": "ELIGIBLE",
                "reasons": [],
            }

        # Check if has ineligibility reasons
        if self.data_loader.has_ineligibility_reasons(account_number):
            reasons_record = self.data_loader.get_reasons_record(
                account_number
            )
            return self._extract_ineligibility_reasons(
                account_number,
                reasons_record,
                request_id,
                account_hash
            )

        # Cannot confirm
        return {
            "account_number": account_number,
            "account_number_hash": account_hash,
            "customer_name": "Unknown",
            "status": "CANNOT_CONFIRM",
            "reasons": [],
        }

    def _extract_ineligibility_reasons(
        self,
        account_number: str,
        reasons_record: Dict[str, Any],
        request_id: str,
        account_hash: str
    ) -> Dict[str, Any]:
        """
        Extract ineligibility reasons from a reasons record.

        Args:
            account_number: Account number (for logging).
            reasons_record: Row from reasons_file.
            request_id: Request ID for logging.
            account_hash: Hashed account number for logging.

        Returns:
            Dict with NOT_ELIGIBLE status and extracted reasons.
        """
        checks_catalog = self.config_loader.get_checks_catalog()
        reason_detection_rules = self.config_loader.get_reason_detection_rules()
        reason_playbook = self.config_loader.get_reason_playbook()

        extracted_reasons = []

        # Normalize the record
        normalized_record = self._normalize_record(
            reasons_record,
            checks_catalog
        )

        # Extract all "Exclude" checks
        for reason_config in reason_detection_rules.get("reasons", []):
            reason_code = reason_config.get("reason_code")
            trigger = reason_config.get("trigger", {})

            # Check if this reason is triggered
            if self._check_trigger(trigger, normalized_record):
                # Build facts and evidence
                facts_result = self._build_facts(
                    reason_config,
                    normalized_record
                )
                
                # facts_result can be a list (legacy) or dict with "facts" and "evidence"
                if isinstance(facts_result, dict):
                    facts = facts_result.get("facts", [])
                    evidence = facts_result.get("evidence", {})
                else:
                    facts = facts_result
                    evidence = {}

                # Get playbook entry
                playbook_entry = reason_playbook.get(
                    "reason_playbook", {}
                ).get(reason_code, {})

                # Build reason object
                reason_obj = {
                    "code": reason_code,
                    "meaning": playbook_entry.get("meaning", ""),
                    "facts": facts,
                    "evidence": evidence,
                    "next_steps": playbook_entry.get("next_steps", []),
                    "review_type": playbook_entry.get("review_type", ""),
                    "review_timing": playbook_entry.get("review_timing", ""),
                    "constraints": playbook_entry.get("constraints", []),
                }

                # Build evidence display
                evidence_display = self._build_evidence_display(
                    reason_code,
                    evidence
                )
                reason_obj["evidence_display"] = evidence_display

                extracted_reasons.append(reason_obj)

                self.rag_logger.log(
                    request_id=request_id,
                    event="reason_extracted",
                    severity="DEBUG",
                    message=f"Reason extracted: {reason_code}",
                    context={
                        "reason_code": reason_code,
                        "fact_count": len(facts),
                    }
                )

        # Get customer name from reasons record
        customer_name = reasons_record.get("CUSTOMERNAMES", "Unknown")
        if not customer_name or customer_name == "":
            customer_name = "Unknown"
        
        return {
            "account_number": account_number,
            "account_number_hash": account_hash,
            "customer_name": customer_name,
            "status": "NOT_ELIGIBLE",
            "reasons": self._validate_and_enrich_reasons(
                extracted_reasons,
                request_id
            ),
        }

    def _normalize_record(
        self,
        record: Dict[str, Any],
        checks_catalog: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalize a record using checks_catalog rules.

        Args:
            record: Raw record from data file.
            checks_catalog: Normalization rules from config.

        Returns:
            Normalized record.
        """
        normalized = dict(record)
        normalization_rules = checks_catalog.get(
            "normalization_rules", {}
        )

        # Handle blank values
        blank_values = normalization_rules.get(
            "blank_string_values", ["", " ", None]
        )

        for key, value in normalized.items():
            if value in blank_values:
                # Convert blanks to empty string for text fields
                normalized[key] = ""

        # Convert blanks to zero for numeric fields
        numeric_fields = normalization_rules.get(
            "convert_blanks_to_zero_for_numeric_fields", []
        )
        for field in numeric_fields:
            if field in normalized and normalized[field] == "":
                normalized[field] = 0

        return normalized

    def _check_trigger(
        self,
        trigger: Dict[str, Any],
        normalized_record: Dict[str, Any]
    ) -> bool:
        """
        Check if a reason trigger is satisfied.

        Args:
            trigger: Trigger configuration from reason_detection_rules.
            normalized_record: Normalized data record.

        Returns:
            True if trigger is satisfied, False otherwise.
        """
        trigger_type = trigger.get("type")

        if trigger_type == "check_equals":
            check_column = trigger.get("check_column")
            trigger_value = trigger.get("trigger_value")
            return normalized_record.get(check_column) == trigger_value

        elif trigger_type == "check_special_equals":
            # Special handling for Recency_Check
            check_column = trigger.get("check_column")
            trigger_value = trigger.get("trigger_value")
            return normalized_record.get(check_column) == trigger_value

        return False

    def _build_facts(
        self,
        reason_config: Dict[str, Any],
        normalized_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build facts and evidence for a reason.

        Args:
            reason_config: Reason configuration from reason_detection_rules.
            normalized_record: Normalized data record.

        Returns:
            Dict with "facts" (list) and "evidence" (dict), or list of fact strings for backward compatibility.
        """
        facts_builder = reason_config.get("facts_builder", {})
        builder_type = facts_builder.get("type", "simple")

        if builder_type == "simple":
            return facts_builder.get("facts", [])

        elif builder_type == "simple_with_evidence":
            # Build facts using template substitution and extract evidence fields
            templates = facts_builder.get("fact_templates", [])
            facts = []
            evidence = {}
            
            # Extract evidence fields directly from record
            evidence_columns = reason_config.get("evidence_columns", [])
            required_facts = reason_config.get("required_facts", [])
            
            for col in evidence_columns:
                # Map column names to evidence field names (lowercase)
                evidence_key = col.lower()
                if col in normalized_record:
                    evidence[evidence_key] = normalized_record[col]
            
            for template in templates:
                fact = template
                # Template variable substitution using both raw column names and evidence keys
                # Try evidence keys first (lowercase versions)
                for req_field in required_facts:
                    if req_field in evidence:
                        fact = fact.replace("{" + req_field + "}", str(evidence[req_field]))
                # Then try original columns
                for col, value in normalized_record.items():
                    fact = fact.replace("{" + col + "}", str(value))
                facts.append(fact)
            
            return {
                "facts": facts,
                "evidence": evidence
            }

        elif builder_type == "simple_with_parameters":
            # Build facts using template substitution
            templates = facts_builder.get("fact_templates", [])
            facts = []
            for template in templates:
                fact = template
                # Simple template variable substitution
                for col, value in normalized_record.items():
                    fact = fact.replace("{" + col + "}", str(value))
                facts.append(fact)
            return facts

        elif builder_type == "max_of_numeric_fields_with_evidence":
            # Find max value among numeric fields and extract all fields as evidence
            fields = facts_builder.get("fields", [])
            values = []
            field_mapping = {}  # Maps field to its column name
            
            for field in fields:
                val = normalized_record.get(field, 0)
                # Convert to numeric if possible
                try:
                    val = float(val) if val else 0
                except (ValueError, TypeError):
                    val = 0
                values.append(val)
                field_mapping[field] = val
            
            max_value = max(values) if values else 0
            max_field = fields[values.index(max_value)] if values and max_value > 0 else ""

            # Build evidence dict with all fields
            evidence = {
                "arrears_days": int(field_mapping.get("Arrears_Days", 0)),
                "credit_card_od_days": int(field_mapping.get("Credit_Card_OD_Days", 0)),
                "dpd_days": int(field_mapping.get("DPD_Days", 0)),
                "max_dpd_driver": int(max_value),
                "driver_source": max_field
            }

            templates = facts_builder.get("fact_templates", [])
            facts = []
            for template in templates:
                fact = template.replace("{arrears_days}", str(evidence["arrears_days"]))
                fact = fact.replace("{credit_card_od_days}", str(evidence["credit_card_od_days"]))
                fact = fact.replace("{dpd_days}", str(evidence["dpd_days"]))
                fact = fact.replace("{max_dpd_driver}", str(evidence["max_dpd_driver"]))
                fact = fact.replace("{driver_source}", evidence["driver_source"])
                facts.append(fact)
            
            return {
                "facts": facts,
                "evidence": evidence
            }

        elif builder_type == "max_of_numeric_fields":
            # Legacy behavior for backward compatibility
            fields = facts_builder.get("fields", [])
            values = [
                normalized_record.get(field, 0)
                for field in fields
            ]
            max_value = max(values) if values else 0
            max_field = fields[values.index(max_value)] if values and max_value > 0 else ""

            templates = facts_builder.get("fact_templates", [])
            facts = []
            for template in templates:
                fact = template.replace("{max_value}", str(max_value))
                fact = fact.replace("{max_field}", max_field)
                facts.append(fact)
            return facts

        return []

    def _validate_and_enrich_reasons(
        self,
        reasons: List[Dict[str, Any]],
        request_id: str
    ) -> List[Dict[str, Any]]:
        """
        Validate that all required facts are present for each reason.
        Add validation status and warnings if evidence is incomplete.
        Add explanation status and error messages for LLM payload builder.

        Args:
            reasons: List of extracted reason objects.
            request_id: Request ID for logging.

        Returns:
            List of enriched reason objects with validation and explanation status.
        """
        validated_reasons = []

        for reason in reasons:
            reason_code = reason.get("code")
            evidence = reason.get("evidence", {})

            # Get explanation requirements
            explanation_config = self.explanation_playbook.get(
                "explanations", {}
            ).get(reason_code, {})

            required_facts = explanation_config.get("required_facts", [])
            evidence_validation = explanation_config.get(
                "evidence_validation", ""
            )

            # Check if all required facts are present
            validation_passed = True
            missing_facts = []

            for required_fact in required_facts:
                if required_fact not in evidence or evidence[required_fact] is None:
                    validation_passed = False
                    missing_facts.append(required_fact)

            # Add validation status to reason
            reason["validation_status"] = "passed" if validation_passed else "failed"
            reason["required_facts"] = required_facts
            reason["missing_facts"] = missing_facts
            reason["evidence_validation_rule"] = evidence_validation

            # Add explanation status and error message
            explanation_error = self._get_explanation_validation_error(
                reason_code,
                evidence,
                validation_passed
            )
            
            reason["explanation_status"] = "ready" if validation_passed else "blocked"
            reason["explanation_error"] = explanation_error

            if not validation_passed:
                self.rag_logger.log(
                    request_id=request_id,
                    event="reason_validation_failed",
                    severity="WARNING",
                    message=f"Reason {reason_code} missing required evidence",
                    context={
                        "reason_code": reason_code,
                        "missing_facts": missing_facts,
                        "evidence_available": list(evidence.keys()),
                        "explanation_error": explanation_error,
                    }
                )

            validated_reasons.append(reason)

        return validated_reasons

    def _build_evidence_display(
        self,
        reason_code: str,
        evidence: Dict[str, Any]
    ) -> List[str]:
        """
        Build human-readable evidence display lines for a reason.

        Args:
            reason_code: The reason code (e.g., DPD_ARREARS_EXCLUSION).
            evidence: Dict of evidence fields extracted from data.

        Returns:
            List of formatted evidence strings for display.
        """
        display_rules = self.evidence_display_rules.get("display_rules", {})
        rule = display_rules.get(reason_code, {})

        # If reason has no evidence, return simple display lines
        if not rule.get("has_evidence", False):
            return rule.get("display_lines", [f"Evidence: {reason_code}"])

        # Reason has evidence - use template and substitute fields
        required_fields = rule.get("required_fields", [])
        format_template = rule.get("format_template", [])
        missing_error = rule.get("missing_error", "Evidence missing")

        # Check if all required fields are present
        missing_fields = [
            field for field in required_fields
            if field not in evidence or evidence[field] is None
        ]

        # If any required field is missing, return error message
        if missing_fields:
            self.rag_logger.log(
                request_id="N/A",
                event="evidence_display_missing_fields",
                severity="WARNING",
                message=f"Missing evidence fields for {reason_code}",
                context={
                    "reason_code": reason_code,
                    "missing_fields": missing_fields,
                }
            )
            return [f"⚠️ {missing_error}"]

        # All fields present - build display lines from template
        display_lines = []
        for template_line in format_template:
            line = template_line
            # Substitute field values
            for field, value in evidence.items():
                placeholder = "{" + field + "}"
                if placeholder in line:
                    line = line.replace(placeholder, str(value))
            display_lines.append(line)

        return display_lines

    def _get_explanation_validation_error(
        self,
        reason_code: str,
        evidence: Dict[str, Any],
        validation_passed: bool
    ) -> Optional[str]:
        """
        Generate explanation error message if validation failed.
        Extracted from evidence_validation_rule text.

        Args:
            reason_code: The reason code.
            evidence: The evidence dictionary.
            validation_passed: Whether validation passed.

        Returns:
            Error message string if validation failed, None otherwise.
        """
        if validation_passed:
            return None

        explanation_config = self.explanation_playbook.get(
            "explanations", {}
        ).get(reason_code, {})

        evidence_validation = explanation_config.get(
            "evidence_validation", ""
        )

        # Extract error message from validation rule
        # Rules format: "STRICT: ... output: 'Error message.'"
        # or "... output: 'Error message.'"
        if "output: " in evidence_validation:
            error_msg = evidence_validation.split("output: ")[-1].strip().strip("'\"")
            return error_msg
        
        # Fallback message if rule doesn't specify output format
        return f"Cannot confirm {reason_code.lower()} (missing required evidence)."
