"""
Tests for evidence display feature.
Verifies that evidence_display is generated correctly for each reason type.
"""

import pytest
from eligibility.eligibility_processor import EligibilityProcessor


class TestEvidenceDisplay:
    """Test evidence display generation."""

    def setup_method(self):
        """Initialize processor for each test."""
        self.processor = EligibilityProcessor()

    def test_dpd_evidence_display(self):
        """Test DPD evidence display with all fields present."""
        evidence = {
            "arrears_days": 109,
            "credit_card_od_days": 1,
            "dpd_days": 0,
            "max_dpd_driver": 109,
            "driver_source": "Arrears_Days"
        }
        
        display = self.processor._build_evidence_display(
            "DPD_ARREARS_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 4  # 4 template lines
        assert "109" in str(display)
        assert "Arrears_Days" in str(display)
        assert "Loan arrears days: 109" in display[0]

    def test_classification_evidence_display(self):
        """Test CLASSIFICATION evidence display."""
        evidence = {"classification": "B10"}
        
        display = self.processor._build_evidence_display(
            "CLASSIFICATION_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 2
        assert "B10" in display[0]
        assert "A5" in display[1]

    def test_linked_base_evidence_display(self):
        """Test LINKED_BASE evidence display."""
        evidence = {
            "linked_base": "575198",
            "linked_base_classification": "B11"
        }
        
        display = self.processor._build_evidence_display(
            "LINKED_BASE_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 3
        assert "575198" in display[0]
        assert "B11" in display[1]
        assert "A5" in display[2]

    def test_customer_vintage_evidence_display(self):
        """Test CUSTOMER_VINTAGE evidence display."""
        evidence = {"customer_vintage_months": 4}
        
        display = self.processor._build_evidence_display(
            "CUSTOMER_VINTAGE_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 2
        assert "4 months" in display[0]
        assert "7 months" in display[1]

    def test_missing_evidence_dpd(self):
        """Test DPD evidence display with missing fields."""
        evidence = {
            "arrears_days": 109,
            "credit_card_od_days": 1,
            # Missing: dpd_days, max_dpd_driver, driver_source
        }
        
        display = self.processor._build_evidence_display(
            "DPD_ARREARS_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 1
        assert "⚠️" in display[0] or "missing" in display[0].lower()
        assert "Cannot confirm arrears days" in display[0]

    def test_missing_evidence_classification(self):
        """Test CLASSIFICATION evidence display with missing field."""
        evidence = {}  # Empty evidence
        
        display = self.processor._build_evidence_display(
            "CLASSIFICATION_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 1
        assert "⚠️" in display[0] or "missing" in display[0].lower()

    def test_no_evidence_reason_joint_account(self):
        """Test reason that doesn't require evidence."""
        evidence = {}
        
        display = self.processor._build_evidence_display(
            "JOINT_ACCOUNT_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 1
        assert "Joint account status" in display[0]

    def test_no_evidence_reason_dormancy(self):
        """Test DORMANCY which has no evidence."""
        evidence = {}
        
        display = self.processor._build_evidence_display(
            "DORMANCY_INACTIVE_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 1
        assert "dormant" in display[0].lower() or "inactive" in display[0].lower()

    def test_average_balance_no_evidence(self):
        """Test AVERAGE_BALANCE which explicitly has no evidence."""
        evidence = {}
        
        display = self.processor._build_evidence_display(
            "AVERAGE_BALANCE_EXCLUSION",
            evidence
        )
        
        assert isinstance(display, list)
        assert len(display) == 1
        assert "⚠️" in display[0]
        assert "not provided" in display[0].lower()


class TestEvidenceDisplayIntegration:
    """Integration tests: extract reasons and verify evidence_display field."""

    def setup_method(self):
        """Initialize processor."""
        self.processor = EligibilityProcessor()

    def test_extracted_reason_has_evidence_display(self):
        """Test that extracted reasons include evidence_display field."""
        results = self.processor.process_accounts(['5140020791'], 'test-evidence-display')
        
        assert len(results) > 0
        account = results[0]
        assert "reasons" in account
        assert len(account["reasons"]) > 0
        
        for reason in account["reasons"]:
            assert "evidence_display" in reason
            assert isinstance(reason["evidence_display"], list)
            assert len(reason["evidence_display"]) > 0
            assert all(isinstance(line, str) for line in reason["evidence_display"])

    def test_dpd_reason_evidence_display_shows_days(self):
        """Test DPD reason displays actual days in evidence_display."""
        results = self.processor.process_accounts(['5140020791'], 'test-dpd-display')
        
        dpd_reason = None
        for reason in results[0]["reasons"]:
            if reason["code"] == "DPD_ARREARS_EXCLUSION":
                dpd_reason = reason
                break
        
        assert dpd_reason is not None
        assert "evidence_display" in dpd_reason
        display_text = " ".join(dpd_reason["evidence_display"])
        
        # Verify evidence values are shown
        assert "39" in display_text  # The actual days from test data
        assert "Credit_Card_OD_Days" in display_text or "credit card" in display_text.lower()

    def test_all_reason_types_have_valid_display(self):
        """Test that all reason types produce valid evidence_display."""
        # Find an account with multiple reason types
        results = self.processor.process_accounts(['5140020791'], 'test-all-types')
        
        reasons = results[0]["reasons"]
        for reason in reasons:
            display = reason.get("evidence_display", [])
            
            # Each reason must have display
            assert isinstance(display, list), f"{reason['code']} display should be list"
            assert len(display) > 0, f"{reason['code']} display should not be empty"
            
            # Each line in display should be a string
            for line in display:
                assert isinstance(line, str), f"{reason['code']} display line should be string"
                assert len(line) > 0, f"{reason['code']} display line should not be empty"
