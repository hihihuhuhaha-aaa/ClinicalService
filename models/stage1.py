from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from models.common import BPStatus, Confidence, QualityLevel, SourceUsed


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class BPReading(BaseModel):
    patient_id: str
    source: str
    day_period: str | None = None
    datetime: str
    systolic: float
    diastolic: float

    model_config = {"extra": "allow"}


class Stage1Request(BaseModel):
    readings: list[BPReading] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class RangeInfo(BaseModel):
    sys_min: float | None = None
    sys_max: float | None = None
    sys_range: float | None = None
    dia_min: float | None = None
    dia_max: float | None = None
    dia_range: float | None = None


class OutlierInfo(BaseModel):
    method: str | None = None
    sys_outlier_count: int | None = None
    dia_outlier_count: int | None = None
    outlier_count: int | None = None
    has_outlier: bool | None = None


class PatientSummary(BaseModel):
    patient_id: str

    # Raw BP averages per source
    clinic_sys: float | None = None
    clinic_dia: float | None = None
    home_sys: float | None = None
    home_dia: float | None = None
    abpm_24h_sys: float | None = None
    abpm_24h_dia: float | None = None

    # Source availability
    clinic_available: bool = False
    home_available: bool = False
    abpm_24h_available: bool = False

    # Clinic quality
    clinic_quality_score: float | None = None
    clinic_quality_level: QualityLevel | None = None
    clinic_quality_flags: list[str] = Field(default_factory=list)
    clinic_readings_count: int | None = None
    clinic_missing: bool | None = None
    clinic_rest_minutes: float | None = None

    # Home BP quality
    home_quality_score: float | None = None
    home_quality_level: QualityLevel | None = None
    home_quality_flags: list[str] = Field(default_factory=list)
    home_quality_usable: bool | None = None
    num_days: int | None = None
    days_with_morning: int | None = None
    days_with_evening: int | None = None
    days_with_both_sessions: int | None = None
    has_morning: bool | None = None
    has_evening: bool | None = None
    pairs_per_session: float | None = None
    avg_readings_per_session: float | None = None
    pct_sessions_with_pairs: float | None = None
    pattern: Literal["random_only", "no_time_pattern", "normal"] | None = None
    std_sys: float | None = None
    std_dia: float | None = None
    range: RangeInfo | None = None
    outlier: OutlierInfo | None = None
    device_validated: bool | None = None
    device_type: str | None = None
    position: str | None = None
    rested_minutes: float | None = None
    all_readings_have_sys_dia_timestamp: bool | None = None
    missing_timestamp_only: bool | None = None
    missing_some_sys_or_dia: bool | None = None
    many_unusable_readings: bool | None = None

    # ABPM quality
    abpm_quality_score: float | None = None
    abpm_quality_level: QualityLevel | None = None
    abpm_quality_flags: list[str] = Field(default_factory=list)
    abpm_quality_usable: bool | None = None
    duration_hours: float | None = None
    valid_readings: int | None = None
    expected_readings: int | None = None
    has_day_data: bool | None = None
    has_night_data: bool | None = None
    day_interval_minutes: float | None = None
    night_interval_minutes: float | None = None
    minor_deviation_from_target: bool | None = None
    major_deviation_from_target: bool | None = None
    interval_unknown: bool | None = None
    all_readings_have_sys_dia_timestamp_period: bool | None = None
    missing_period_tag_only: bool | None = None
    missing_some_sys_or_dia_or_timestamp: bool | None = None
    activity_log: bool | None = None

    # Per-source status
    clinic_status: BPStatus | None = None
    home_status: BPStatus | None = None
    abpm_status: BPStatus | None = None

    # Step 1 — BP category
    bp_category: BPStatus | None = None
    source_used_category: SourceUsed | None = None
    source_value_used: str | None = None
    category_confidence: Confidence | None = None
    category_quality_level: QualityLevel | None = None
    category_flags: list[str] = Field(default_factory=list)

    # Step 2 — BP stage (clinic-only)
    bp_stage: Literal["stage1", "stage2", "none", "unknown"] | None = None
    stage_source: str | None = None
    stage_confidence: Confidence | None = None
    stage_quality_level: QualityLevel | None = None
    stage_flags: list[str] = Field(default_factory=list)

    # Step 3 — Phenotype
    phenotype: Literal["white_coat", "masked", "none", "unknown"] | None = None
    phenotype_source: SourceUsed | None = None
    phenotype_confidence: Confidence | None = None
    phenotype_quality_level: QualityLevel | None = None
    phenotype_flags: list[str] = Field(default_factory=list)

    # Aggregated THA classification
    tha_type: Literal["stage_2", "stage_1", "elevated", "hypertension", "normal", "unknown"] | None = None

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class Stage1Response(BaseModel):
    patient_summary: list[PatientSummary]
    patient_count: int
    phenotypes: list[str]
    tha_types: list[str]
    tha_stages: list[str]
