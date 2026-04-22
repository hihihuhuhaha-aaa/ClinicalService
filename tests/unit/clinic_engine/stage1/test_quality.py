"""Unit tests for Stage 1 quality scoring (clinic, home, ABPM)."""
from __future__ import annotations

import pytest

from services.clinic_engine.stage1_measurement_classification.scoring.quality import (
    compute_abpm_quality,
    compute_clinic_quality,
    compute_home_quality,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _home_base(**overrides) -> dict:
    """Minimal context cho compute_home_quality — đủ để qua hard rules."""
    base = {
        # temporal_coverage group: num_days>=7, days_with_morning>=5, days_with_evening>=5
        "num_days": 7,
        "days_with_morning": 7,
        "days_with_evening": 7,
        # within_day_pattern group: has_morning, has_evening, days_with_both_sessions
        "has_morning": True,
        "has_evening": True,
        "days_with_both_sessions": 7,
        "pattern": "normal",
        # repeated_measurement_per_session group: pairs_per_session
        "pairs_per_session": 2,
        # device_quality group
        "device_validated": True,
        "device_type": "upper_arm",
        # measurement_condition group
        "position": "sitting",
        "rested_minutes": 5.0,
        # completeness group
        "all_readings_have_sys_dia_timestamp": True,
        "missing_timestamp_only": False,
        "missing_some_sys_or_dia": False,
        "many_unusable_readings": False,
    }
    base.update(overrides)
    return base


def _abpm_base(**overrides) -> dict:
    base = {
        "duration_hours": 24.0,
        "valid_readings": 48,
        "expected_readings": 48,
        "has_day_data": True,
        "has_night_data": True,
        "day_interval_minutes": 30.0,
        "night_interval_minutes": 60.0,
        "minor_deviation_from_target": False,
        "major_deviation_from_target": False,
        "interval_unknown": False,
        "all_readings_have_sys_dia_timestamp_period": True,
        "missing_period_tag_only": False,
        "missing_some_sys_or_dia_or_timestamp": False,
        "many_unusable_readings": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Clinic quality
# ---------------------------------------------------------------------------

class TestComputeClinicQuality:
    def test_high_quality_rested_multiple_readings(self):
        ctx = {
            "clinic_readings_count": 3,
            "clinic_rest_minutes": 5.0,
            "clinic_missing": False,
        }
        score, level, flags = compute_clinic_quality(ctx)
        assert level == "high"
        assert score > 0.5

    def test_low_quality_single_reading(self):
        ctx = {
            "clinic_readings_count": 1,
            "clinic_rest_minutes": 0.0,
            "clinic_missing": False,
        }
        score, level, flags = compute_clinic_quality(ctx)
        assert level in {"low", "medium"}

    def test_missing_clinic_data(self):
        ctx = {
            "clinic_readings_count": 0,
            "clinic_rest_minutes": None,
            "clinic_missing": True,
        }
        score, level, flags = compute_clinic_quality(ctx)
        assert level == "low"

    def test_returns_three_tuple(self):
        ctx = {"clinic_readings_count": 2, "clinic_rest_minutes": 5.0, "clinic_missing": False}
        result = compute_clinic_quality(ctx)
        assert len(result) == 3
        score, level, flags = result
        assert isinstance(score, float)
        assert level in {"low", "medium", "high"}
        assert isinstance(flags, list)


# ---------------------------------------------------------------------------
# Home quality
# ---------------------------------------------------------------------------

class TestComputeHomeQuality:
    def test_perfect_conditions_high_quality(self):
        ctx = _home_base()
        score, level, flags = compute_home_quality(ctx)
        assert level == "high"
        assert score >= 0.80

    def test_only_2_days_low_quality(self):
        # <3 ngày → temporal_coverage hard rule trả score thấp → level low
        ctx = _home_base(num_days=2)
        score, level, flags = compute_home_quality(ctx)
        assert level == "low"

    def test_no_day_period_random_only(self):
        ctx = _home_base(pattern="random_only", days_with_morning=0, days_with_evening=0)
        score, level, flags = compute_home_quality(ctx)
        # pattern random_only → within_day_pattern score thấp
        assert level in {"low", "medium"}

    def test_morning_only_no_evening_pattern(self):
        ctx = _home_base(pattern="no_time_pattern", days_with_evening=0)
        score, level, flags = compute_home_quality(ctx)
        assert level in {"low", "medium"}

    def test_unvalidated_device_penalizes(self):
        ctx = _home_base(device_validated=False, device_type="wrist")
        score, level, flags = compute_home_quality(ctx)
        # Unvalidated wrist → device_quality score thấp → ảnh hưởng tổng
        assert score < 1.0

    def test_many_unusable_readings_completeness_zero(self):
        # many_unusable_readings → completeness score=0, nhưng weight chỉ 10%
        # Tổng score vẫn có thể là medium nếu các nhóm khác cao
        ctx = _home_base(
            all_readings_have_sys_dia_timestamp=False,
            many_unusable_readings=True,
        )
        score, level, flags = compute_home_quality(ctx)
        # completeness_score=0 với weight=10%, không đủ kéo xuống low nếu 90% còn lại cao
        assert score < 1.0

    def test_missing_sys_or_dia_penalizes(self):
        ctx = _home_base(
            all_readings_have_sys_dia_timestamp=False,
            missing_some_sys_or_dia=True,
        )
        score, level, flags = compute_home_quality(ctx)
        assert score < 1.0

    def test_standing_position_penalizes(self):
        ctx = _home_base(position="standing")
        score, level, flags = compute_home_quality(ctx)
        assert score < 1.0

    def test_7_days_both_sessions_is_best(self):
        ctx = _home_base(num_days=7, pattern="normal")
        score_7, level_7, _ = compute_home_quality(ctx)
        ctx3 = _home_base(num_days=3, pattern="no_time_pattern", days_with_evening=0)
        score_3, level_3, _ = compute_home_quality(ctx3)
        assert score_7 >= score_3

    def test_output_types(self):
        ctx = _home_base()
        score, level, flags = compute_home_quality(ctx)
        assert isinstance(score, float)
        assert level in {"low", "medium", "high"}
        assert isinstance(flags, list)


# ---------------------------------------------------------------------------
# ABPM quality
# ---------------------------------------------------------------------------

class TestComputeAbpmQuality:
    def test_full_24h_coverage_high_quality(self):
        ctx = _abpm_base()
        score, level, flags = compute_abpm_quality(ctx)
        assert level == "high"
        assert score >= 0.80

    def test_no_night_data_penalizes(self):
        ctx = _abpm_base(has_night_data=False)
        score, level, flags = compute_abpm_quality(ctx)
        assert level in {"low", "medium"}

    def test_major_deviation_low_quality(self):
        ctx = _abpm_base(major_deviation_from_target=True)
        score, level, flags = compute_abpm_quality(ctx)
        assert level == "low"

    def test_interval_unknown_penalizes(self):
        ctx = _abpm_base(interval_unknown=True)
        score, level, flags = compute_abpm_quality(ctx)
        assert score < 1.0

    def test_many_unusable_readings_low(self):
        ctx = _abpm_base(many_unusable_readings=True)
        score, level, flags = compute_abpm_quality(ctx)
        assert level == "low"

    def test_missing_period_tag_penalizes(self):
        ctx = _abpm_base(
            all_readings_have_sys_dia_timestamp_period=False,
            missing_period_tag_only=True,
        )
        score, level, flags = compute_abpm_quality(ctx)
        assert score < 1.0

    def test_output_types(self):
        ctx = _abpm_base()
        score, level, flags = compute_abpm_quality(ctx)
        assert isinstance(score, float)
        assert level in {"low", "medium", "high"}
        assert isinstance(flags, list)

    def test_no_day_data_penalizes(self):
        ctx = _abpm_base(has_day_data=False)
        score, level, flags = compute_abpm_quality(ctx)
        assert level in {"low", "medium"}
