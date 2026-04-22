"""Unit tests for the ingestion labeling module."""
from __future__ import annotations

import pytest

from services.ingestion.labeling.labeler import LabelResult, label
from services.ingestion.safety_check.checker import SafetyResult, Severity


def _make_safety(severity: Severity, reason: str = "test reason", flags: list | None = None) -> SafetyResult:
    return SafetyResult(severity=severity, reason=reason, flags=flags or [])


class TestLabel:
    def test_high_severity_is_pending(self):
        result = label(_make_safety(Severity.HIGH))
        assert result.status == "pending"
        assert result.requires_review is True

    def test_medium_severity_is_pending(self):
        result = label(_make_safety(Severity.MEDIUM))
        assert result.status == "pending"
        assert result.requires_review is True

    def test_low_severity_is_pass(self):
        result = label(_make_safety(Severity.LOW))
        assert result.status == "pass"
        assert result.requires_review is False

    def test_returns_label_result(self):
        result = label(_make_safety(Severity.LOW))
        assert isinstance(result, LabelResult)

    def test_severity_preserved_high(self):
        result = label(_make_safety(Severity.HIGH))
        assert result.severity == Severity.HIGH

    def test_severity_preserved_low(self):
        result = label(_make_safety(Severity.LOW))
        assert result.severity == Severity.LOW

    def test_severity_preserved_medium(self):
        result = label(_make_safety(Severity.MEDIUM))
        assert result.severity == Severity.MEDIUM

    def test_high_with_flags_still_pending(self):
        result = label(_make_safety(Severity.HIGH, flags=["acute_chest_pain", "bp_crisis"]))
        assert result.status == "pending"
        assert result.requires_review is True
