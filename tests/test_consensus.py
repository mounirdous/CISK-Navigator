"""
Consensus service tests
"""

from decimal import Decimal

import pytest

from app.models import Contribution, KPIValueTypeConfig
from app.services import ConsensusService


class MockContribution:
    """Mock contribution for testing"""

    def __init__(self, numeric_value=None, qualitative_level=None):
        self.numeric_value = numeric_value
        self.qualitative_level = qualitative_level


def test_no_data_consensus():
    """Test consensus with no contributions"""
    result = ConsensusService.calculate_consensus([])
    assert result["status"] == ConsensusService.STATUS_NO_DATA
    assert result["value"] is None
    assert result["is_rollup_eligible"] is False


def test_pending_confirmation_consensus():
    """Test consensus with only one contribution"""
    contributions = [MockContribution(numeric_value=100)]
    result = ConsensusService.calculate_consensus(contributions)

    assert result["status"] == ConsensusService.STATUS_PENDING
    assert result["value"] == 100
    assert result["count"] == 1
    assert result["is_rollup_eligible"] is False


def test_strong_consensus():
    """Test strong consensus (all values same)"""
    contributions = [
        MockContribution(numeric_value=100),
        MockContribution(numeric_value=100),
        MockContribution(numeric_value=100),
    ]
    result = ConsensusService.calculate_consensus(contributions)

    assert result["status"] == ConsensusService.STATUS_STRONG
    assert result["value"] == 100
    assert result["count"] == 3
    assert result["is_rollup_eligible"] is True  # Only strong consensus is eligible


def test_weak_consensus():
    """Test weak consensus (majority exists but not unanimous)"""
    contributions = [
        MockContribution(numeric_value=100),
        MockContribution(numeric_value=100),
        MockContribution(numeric_value=100),
        MockContribution(numeric_value=90),
    ]
    result = ConsensusService.calculate_consensus(contributions)

    assert result["status"] == ConsensusService.STATUS_WEAK
    assert result["value"] == 100  # Majority value
    assert result["is_rollup_eligible"] is False  # Weak consensus not eligible


def test_no_consensus():
    """Test no consensus (no clear majority)"""
    contributions = [
        MockContribution(numeric_value=100),
        MockContribution(numeric_value=90),
        MockContribution(numeric_value=80),
    ]
    result = ConsensusService.calculate_consensus(contributions)

    assert result["status"] == ConsensusService.STATUS_NO_CONSENSUS
    assert result["value"] is None
    assert result["is_rollup_eligible"] is False


def test_qualitative_strong_consensus():
    """Test strong consensus with qualitative values"""
    contributions = [
        MockContribution(qualitative_level=2),
        MockContribution(qualitative_level=2),
        MockContribution(qualitative_level=2),
    ]
    result = ConsensusService.calculate_consensus(contributions)

    assert result["status"] == ConsensusService.STATUS_STRONG
    assert result["value"] == 2
    assert result["is_rollup_eligible"] is True
