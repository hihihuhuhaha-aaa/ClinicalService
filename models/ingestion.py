from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from models.common import Severity


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    patient_id: str = Field(..., description="UUID of the patient this message belongs to")
    message: str = Field(..., min_length=1, description="Raw user message to ingest")


class ReviewDecision(BaseModel):
    table: Literal["bp_records", "clinical_facts"]
    record_id: str = Field(..., description="Record ID returned by POST /ingest")
    decision: Literal["accepted", "rejected"]


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class SafetyInfo(BaseModel):
    severity: str
    reason: str
    flags: list[str] = Field(default_factory=list)


class InsertedRecords(BaseModel):
    bp_records: list[str] = Field(default_factory=list)
    clinical_facts: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    status: Literal["pass", "pending"]
    severity: str
    requires_review: bool
    inserted: InsertedRecords
    extraction: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)
    safety: SafetyInfo
    curation: dict[str, Any] = Field(default_factory=dict)


class ReviewResponse(BaseModel):
    status: Literal["accepted", "rejected"]
    table: Literal["bp_records", "clinical_facts"]
    record_id: str
