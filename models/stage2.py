from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from models.common import Confidence


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class Stage2Request(BaseModel):
    patientInfo: dict[str, Any] = Field(default_factory=dict)
    cardiovascularRiskFactors: dict[str, Any] = Field(default_factory=dict)
    targetOrganDamage: dict[str, Any] = Field(default_factory=dict)
    comorbidities: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class Stage2Response(BaseModel):
    risk_level: Confidence
    recommendation: str
    explanation: str
    confidence: Confidence
