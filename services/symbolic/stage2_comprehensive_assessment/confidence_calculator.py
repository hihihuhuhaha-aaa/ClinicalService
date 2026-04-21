from __future__ import annotations

from typing import Any

from .constants import (
    HIGH_RISK_CONDITIONS,
    HMOD_FIELDS,
    MAIN_RISK_FACTOR_FIELDS,
)


def calculate_confidence(risk_level: str, processed_data: dict[str, Any]) -> str:
    """Calculate confidence level for the risk assessment."""
    has_any_data = processed_data["has_any_data"]

    if not has_any_data:
        return "low"

    if risk_level == "high":
        return "high"

    if risk_level == "medium":
        return "medium"

    return "low"
