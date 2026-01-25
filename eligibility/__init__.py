"""
Eligibility Module - Loan limit eligibility checking and reason extraction.

Provides intent detection, account extraction/validation, and eligibility
determination with detailed reason extraction and playbook enrichment.
"""

from eligibility.config_loader import ConfigLoader
from eligibility.data_loader import DataLoader
from eligibility.orchestrator import EligibilityOrchestrator

__version__ = "1.0.0"
__all__ = ["ConfigLoader", "DataLoader", "EligibilityOrchestrator"]
