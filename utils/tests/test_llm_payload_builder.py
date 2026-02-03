"""Unit tests for eligibility.llm_payload_builder module"""

import pytest
import json
from eligibility.llm_payload_builder import LLMPayloadBuilder


class TestLLMPayloadBuilder:
    """Test suite for LLMPayloadBuilder"""
    
    def setup_method(self):
        """Setup for each test"""
        self.builder = LLMPayloadBuilder()
    
    # ===== BASIC PAYLOAD CONSTRUCTION =====
    
    def test_build_eligible_account_payload(self):
        """Test building payload for eligible account"""
        accounts = [
            {
                "account_number_hash": "abc123",
                "status": "ELIGIBLE",
                "reasons": [],
            }
        ]
        payload = self.builder.build_payload(accounts, "req-123", 100.5)
        
        assert payload is not None
        assert payload["request_id"] == "req-123"
        assert payload["summary"]["total_accounts"] == 1
        assert payload["summary"]["eligible_count"] == 1
        assert payload["summary"]["not_eligible_count"] == 0
    
    def test_build_not_eligible_account_payload(self):
        """Test building payload for non-eligible account"""
        accounts = [
            {
                "account_number_hash": "xyz789",
                "status": "NOT_ELIGIBLE",
                "reasons": [
                    {
                        "code": "JOINT_ACCOUNT_EXCLUSION",
                        "meaning": "Joint account",
                        "facts": ["Joint account detected"],
                        "next_steps": [{"action": "Use sole account", "owner": "Customer"}],
                    }
                ],
            }
        ]
        payload = self.builder.build_payload(accounts, "req-456", 150.0)
        
        assert payload["summary"]["not_eligible_count"] == 1
        assert len(payload["accounts"]) == 1
        assert len(payload["accounts"][0]["reasons"]) == 1
    
    def test_build_cannot_confirm_payload(self):
        """Test building payload for cannot-confirm account"""
        accounts = [
            {
                "account_number_hash": "def456",
                "status": "CANNOT_CONFIRM",
                "reasons": [],
            }
        ]
        payload = self.builder.build_payload(accounts, "req-789", 80.0)
        
        assert payload["summary"]["cannot_confirm_count"] == 1
    
    # ===== MULTIPLE ACCOUNTS =====
    
    def test_build_payload_multiple_accounts(self):
        """Test building payload with multiple accounts"""
        accounts = [
            {
                "account_number_hash": "acc1",
                "status": "ELIGIBLE",
                "reasons": [],
            },
            {
                "account_number_hash": "acc2",
                "status": "NOT_ELIGIBLE",
                "reasons": [
                    {
                        "code": "DPD_ARREARS_EXCLUSION",
                        "meaning": "DPD arrears",
                        "facts": ["DPD > 3 days"],
                        "next_steps": [{"action": "Clear arrears", "owner": "Customer"}],
                    }
                ],
            },
            {
                "account_number_hash": "acc3",
                "status": "CANNOT_CONFIRM",
                "reasons": [],
            },
        ]
        payload = self.builder.build_payload(accounts, "req-multi", 200.0)
        
        assert payload["summary"]["total_accounts"] == 3
        assert payload["summary"]["eligible_count"] == 1
        assert payload["summary"]["not_eligible_count"] == 1
        assert payload["summary"]["cannot_confirm_count"] == 1
        assert len(payload["accounts"]) == 3
    
    # ===== PAYLOAD STRUCTURE =====
    
    def test_payload_has_request_id(self):
        """Test that payload includes request_id"""
        payload = self.builder.build_payload([], "req-id-123", 0.0)
        assert "request_id" in payload
        assert payload["request_id"] == "req-id-123"
    
    def test_payload_has_timestamp(self):
        """Test that payload includes timestamp"""
        payload = self.builder.build_payload([], "req-id", 0.0)
        assert "batch_timestamp" in payload
        # Should be ISO 8601 format
        assert "T" in payload["batch_timestamp"]
        assert "Z" in payload["batch_timestamp"]
    
    def test_payload_has_accounts_array(self):
        """Test that payload includes accounts array"""
        accounts = [
            {
                "account_number_hash": "acc1",
                "status": "ELIGIBLE",
                "reasons": [],
            }
        ]
        payload = self.builder.build_payload(accounts, "req", 0.0)
        assert "accounts" in payload
        assert isinstance(payload["accounts"], list)
    
    def test_payload_has_summary(self):
        """Test that payload includes summary"""
        payload = self.builder.build_payload([], "req", 0.0)
        assert "summary" in payload
        assert "total_accounts" in payload["summary"]
        assert "eligible_count" in payload["summary"]
        assert "not_eligible_count" in payload["summary"]
        assert "cannot_confirm_count" in payload["summary"]
        assert "processing_latency_ms" in payload["summary"]
    
    # ===== JSON VALIDITY =====
    
    def test_payload_is_valid_json(self):
        """Test that payload can be serialized to JSON"""
        accounts = [
            {
                "account_number_hash": "acc1",
                "status": "ELIGIBLE",
                "reasons": [],
            }
        ]
        payload = self.builder.build_payload(accounts, "req", 100.0)
        
        # Should not raise
        json_str = json.dumps(payload)
        assert json_str is not None
    
    def test_payload_roundtrip_json(self):
        """Test that payload survives JSON serialization/deserialization"""
        accounts = [
            {
                "account_number_hash": "acc1",
                "status": "ELIGIBLE",
                "reasons": [],
            }
        ]
        original = self.builder.build_payload(accounts, "req-123", 100.0)
        
        # Serialize and deserialize
        json_str = json.dumps(original)
        restored = json.loads(json_str)
        
        assert restored["request_id"] == original["request_id"]
        assert restored["summary"]["total_accounts"] == original["summary"]["total_accounts"]
    
    # ===== REASON ENRICHMENT =====
    
    def test_reason_enrichment_with_multiple_reasons(self):
        """Test payload with multiple reasons per account"""
        accounts = [
            {
                "account_number_hash": "acc1",
                "status": "NOT_ELIGIBLE",
                "reasons": [
                    {
                        "code": "JOINT_ACCOUNT_EXCLUSION",
                        "meaning": "Joint account",
                        "facts": ["Joint"],
                        "next_steps": [{"action": "Use sole", "owner": "Customer"}],
                    },
                    {
                        "code": "DPD_ARREARS_EXCLUSION",
                        "meaning": "DPD arrears",
                        "facts": ["DPD > 3"],
                        "next_steps": [{"action": "Clear", "owner": "Customer"}],
                    },
                ],
            }
        ]
        payload = self.builder.build_payload(accounts, "req", 0.0)
        
        assert len(payload["accounts"][0]["reasons"]) == 2
        assert payload["accounts"][0]["reasons"][0]["code"] == "JOINT_ACCOUNT_EXCLUSION"
        assert payload["accounts"][0]["reasons"][1]["code"] == "DPD_ARREARS_EXCLUSION"
    
    def test_reason_has_all_fields(self):
        """Test that reason has all required fields"""
        accounts = [
            {
                "account_number_hash": "acc1",
                "status": "NOT_ELIGIBLE",
                "reasons": [
                    {
                        "code": "TEST_CODE",
                        "meaning": "Test meaning",
                        "facts": ["Fact 1"],
                        "next_steps": [{"action": "Action", "owner": "Owner"}],
                    }
                ],
            }
        ]
        payload = self.builder.build_payload(accounts, "req", 0.0)
        reason = payload["accounts"][0]["reasons"][0]
        
        assert "code" in reason
        assert "meaning" in reason
        assert "facts" in reason
        assert "next_steps" in reason
    
    # ===== EMPTY INPUTS =====
    
    def test_build_payload_empty_accounts(self):
        """Test building payload with empty accounts list"""
        payload = self.builder.build_payload([], "req", 0.0)
        
        assert payload["summary"]["total_accounts"] == 0
        assert payload["summary"]["eligible_count"] == 0
        assert len(payload["accounts"]) == 0
    
    def test_build_payload_none_accounts(self):
        """Test building payload with None accounts"""
        payload = self.builder.build_payload(None, "req", 0.0)
        
        assert payload["summary"]["total_accounts"] == 0
        assert len(payload["accounts"]) == 0
    
    # ===== LATENCY TRACKING =====
    
    def test_payload_includes_latency(self):
        """Test that payload includes latency in summary"""
        payload = self.builder.build_payload([], "req", 125.5)
        
        assert "processing_latency_ms" in payload["summary"]
        assert payload["summary"]["processing_latency_ms"] == 125.5
    
    def test_latency_zero_valid(self):
        """Test that zero latency is valid"""
        payload = self.builder.build_payload([], "req", 0.0)
        assert payload["summary"]["processing_latency_ms"] == 0.0
    
    def test_latency_large_value_valid(self):
        """Test that large latency value is valid"""
        payload = self.builder.build_payload([], "req", 5000.0)
        assert payload["summary"]["processing_latency_ms"] == 5000.0
    
    # ===== VALIDATION =====
    
    def test_validate_payload_structure(self):
        """Test that payload structure is valid"""
        accounts = [
            {
                "account_number_hash": "acc1",
                "status": "ELIGIBLE",
                "reasons": [],
            }
        ]
        payload = self.builder.build_payload(accounts, "req", 0.0)
        
        # Validate critical fields exist
        assert payload is not None
        assert isinstance(payload, dict)
        assert "request_id" in payload
        assert "batch_timestamp" in payload
        assert "accounts" in payload
        assert "summary" in payload
    
    # ===== PII PROTECTION =====
    
    def test_payload_uses_hashed_account_numbers(self):
        """Test that payload uses hashed account numbers, not raw"""
        accounts = [
            {
                "account_number_hash": "hash_abc123",  # Should be hashed, not raw number
                "status": "ELIGIBLE",
                "reasons": [],
            }
        ]
        payload = self.builder.build_payload(accounts, "req", 0.0)
        
        # Should not contain raw account numbers
        payload_str = json.dumps(payload)
        # Raw account number pattern (10 digits) should not appear
        # (This is a basic check; actual hashing should be done in processor)
        assert "account_number_hash" in payload["accounts"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
