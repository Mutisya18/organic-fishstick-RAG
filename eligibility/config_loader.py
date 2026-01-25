"""
Config Loader - Load and validate all eligibility configuration files.

Loads 3 JSON config files at startup:
- checks_catalog.json (column definitions & normalization rules)
- reason_detection_rules.json (extraction logic per reason code)
- reason_playbook.json (user-friendly meanings & remediation)

Caches all configs in memory for fast access.
Raises exceptions if any file is missing or malformed.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from logger.rag_logging import RAGLogger
from logger.session_manager import SessionManager


class ConfigLoader:
    """Singleton config loader with validation and caching."""

    _instance: Optional["ConfigLoader"] = None

    def __new__(cls) -> "ConfigLoader":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize config loader and load all configs."""
        if self._initialized:
            return

        self._initialized = True
        self.rag_logger = RAGLogger()
        self.session_manager = SessionManager()

        # Get config directory path
        self.config_dir = os.path.join(
            os.path.dirname(__file__), "config"
        )

        # Cache for all configs
        self.checks_catalog: Dict[str, Any] = {}
        self.reason_detection_rules: Dict[str, Any] = {}
        self.reason_playbook: Dict[str, Any] = {}
        self.explanation_playbook: Dict[str, Any] = {}
        self.evidence_display_rules: Dict[str, Any] = {}

        # Load all configs at startup
        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """Load and validate all 3 config files."""
        start_time = datetime.now(timezone.utc)
        request_id = self.rag_logger.generate_request_id()

        try:
            # Load checks_catalog.json
            self.checks_catalog = self._load_json_file(
                "checks_catalog.json",
                request_id
            )

            # Load reason_detection_rules.json
            self.reason_detection_rules = self._load_json_file(
                "reason_detection_rules.json",
                request_id
            )

            # Load reason_playbook.json
            self.reason_playbook = self._load_json_file(
                "reason_playbook.json",
                request_id
            )

            # Load explanation_playbook.json
            self.explanation_playbook = self._load_json_file(
                "explanation_playbook.json",
                request_id
            )

            # Load evidence_display_rules.json
            self.evidence_display_rules = self._load_json_file(
                "evidence_display_rules.json",
                request_id
            )

            # Calculate counts for logging
            checks_count = len(
                self.checks_catalog.get("columns", [])
            )
            reasons_count = len(
                self.reason_detection_rules.get("reasons", [])
            )
            playbook_count = len(
                self.reason_playbook.get("reason_playbook", {})
            )
            explanation_count = len(
                self.explanation_playbook.get("explanations", {})
            )
            display_count = len(
                self.evidence_display_rules.get("display_rules", {})
            )
            latency_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            # Log successful load
            self.rag_logger.log(
                request_id=request_id,
                event="eligibility_config_load_success",
                severity="INFO",
                message="Eligibility configs loaded successfully",
                context={
                    "checks_catalog_columns": checks_count,
                    "reason_detection_rules_count": reasons_count,
                    "reason_playbook_count": playbook_count,
                    "explanation_playbook_count": explanation_count,
                    "evidence_display_rules_count": display_count,
                    "latency_ms": latency_ms,
                    "config_dir": self.config_dir,
                }
            )

        except Exception as e:
            # Log critical failure
            self.rag_logger.log(
                request_id=request_id,
                event="eligibility_config_load_failure",
                severity="CRITICAL",
                message=f"Failed to load eligibility configs: {str(e)}",
                context={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "config_dir": self.config_dir,
                }
            )
            raise

    def _load_json_file(
        self,
        filename: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Load and validate a JSON config file.

        Args:
            filename: Name of the JSON file to load.
            request_id: Request ID for logging.

        Returns:
            Parsed JSON content as dictionary.

        Raises:
            FileNotFoundError: If file does not exist.
            json.JSONDecodeError: If file is not valid JSON.
        """
        filepath = os.path.join(self.config_dir, filename)

        if not os.path.exists(filepath):
            self.rag_logger.log(
                request_id=request_id,
                event="config_file_not_found",
                severity="ERROR",
                message=f"Config file not found: {filepath}",
                context={"filename": filename, "filepath": filepath}
            )
            raise FileNotFoundError(f"Config file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = json.load(f)

            self.rag_logger.log(
                request_id=request_id,
                event="config_file_loaded",
                severity="DEBUG",
                message=f"Config file loaded: {filename}",
                context={"filename": filename, "file_size_bytes": os.path.getsize(filepath)}
            )

            return content

        except json.JSONDecodeError as e:
            self.rag_logger.log(
                request_id=request_id,
                event="config_json_decode_error",
                severity="ERROR",
                message=f"Invalid JSON in config file {filename}: {str(e)}",
                context={
                    "filename": filename,
                    "error_message": str(e),
                    "line": e.lineno,
                    "column": e.colno,
                }
            )
            raise

    def get_checks_catalog(self) -> Dict[str, Any]:
        """Get cached checks catalog."""
        return self.checks_catalog

    def get_reason_detection_rules(self) -> Dict[str, Any]:
        """Get cached reason detection rules."""
        return self.reason_detection_rules

    def get_reason_playbook(self) -> Dict[str, Any]:
        """Get cached reason playbook."""
        return self.reason_playbook

    def get_explanation_playbook(self) -> Dict[str, Any]:
        """Get cached explanation playbook."""
        return self.explanation_playbook

    def get_evidence_display_rules(self) -> Dict[str, Any]:
        """Get cached evidence display rules."""
        return self.evidence_display_rules

    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all configs as a single dictionary."""
        return {
            "checks_catalog": self.checks_catalog,
            "reason_detection_rules": self.reason_detection_rules,
            "reason_playbook": self.reason_playbook,
            "explanation_playbook": self.explanation_playbook,
            "evidence_display_rules": self.evidence_display_rules,
        }
