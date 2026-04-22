from __future__ import annotations

from dataclasses import dataclass

from services.ingestion.safety_check.checker import SafetyResult, Severity


@dataclass
class LabelResult:
    status: str          # "pending" | "pass"
    severity: Severity
    requires_review: bool


def label(safety: SafetyResult) -> LabelResult:
    """Mark high/medium severity data as pending (requires human review); low severity passes through."""
    requires_review = safety.severity in (Severity.HIGH, Severity.MEDIUM)
    status = "pending" if requires_review else "pass"
    return LabelResult(
        status=status,
        severity=safety.severity,
        requires_review=requires_review,
    )
