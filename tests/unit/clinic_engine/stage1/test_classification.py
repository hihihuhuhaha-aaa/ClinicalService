"""Unit tests for Stage 1 BP classification functions."""
from __future__ import annotations

import pytest

from services.clinic_engine.stage1_measurement_classification.scoring.classification import (
    classify_abpm_pattern,
    classify_bp_category,
    classify_bp_stage,
    classify_hypertension_phenotype,
    classify_phenotype,
    classify_tha_stage,
    classify_tha_type,
)


# ---------------------------------------------------------------------------
# classify_tha_stage  (legacy – independent of RULEBOOK)
# ---------------------------------------------------------------------------

class TestClassifyThaStage:
    def test_unknown_when_none(self):
        assert classify_tha_stage(None, None) == "unknown"

    def test_unknown_when_nan(self):
        import math
        assert classify_tha_stage(float("nan"), 80) == "unknown"

    def test_hypertensive_crisis_sys(self):
        assert classify_tha_stage(180, 80) == "hypertensive_crisis"

    def test_hypertensive_crisis_dia(self):
        assert classify_tha_stage(170, 120) == "hypertensive_crisis"

    def test_stage2_sys(self):
        assert classify_tha_stage(160, 85) == "stage_2"

    def test_stage2_dia(self):
        assert classify_tha_stage(150, 100) == "stage_2"

    def test_stage1_boundary(self):
        assert classify_tha_stage(140, 90) == "stage_1"

    def test_stage1_sys_only(self):
        assert classify_tha_stage(145, 80) == "stage_1"

    def test_elevated(self):
        assert classify_tha_stage(125, 75) == "elevated"

    def test_normal(self):
        assert classify_tha_stage(110, 65) == "normal"

    def test_boundary_140_exactly(self):
        assert classify_tha_stage(140, 85) == "stage_1"

    def test_boundary_159_should_be_stage1(self):
        # 159/99 vẫn là stage_1, 160/100 mới là stage_2
        assert classify_tha_stage(159, 99) == "stage_1"

    def test_boundary_160_is_stage2(self):
        assert classify_tha_stage(160, 99) == "stage_2"


# ---------------------------------------------------------------------------
# classify_hypertension_phenotype  (legacy)
# ---------------------------------------------------------------------------

class TestClassifyHypertensionPhenotype:
    def test_unknown_when_any_missing(self):
        assert classify_hypertension_phenotype(None, 90, 120, 80) == "unknown"
        assert classify_hypertension_phenotype(145, 92, None, 80) == "unknown"

    def test_white_coat(self):
        # clinic cao (≥140/90), home thấp (<135/85)
        result = classify_hypertension_phenotype(145, 92, 128, 82)
        assert result == "white_coat_hypertension"

    def test_masked(self):
        # clinic thấp, home cao
        result = classify_hypertension_phenotype(130, 80, 138, 88)
        assert result == "masked_hypertension"

    def test_sustained(self):
        # cả 2 đều cao
        result = classify_hypertension_phenotype(150, 95, 140, 88)
        assert result == "sustained_hypertension"

    def test_normal(self):
        # clinic_dia=68 < 70 → không vào prehypertension branch → normal
        result = classify_hypertension_phenotype(115, 68, 112, 66)
        assert result == "normal"


# ---------------------------------------------------------------------------
# classify_abpm_pattern
# ---------------------------------------------------------------------------

class TestClassifyAbpmPattern:
    def test_unknown_when_missing(self):
        assert classify_abpm_pattern(None, 80) == "unknown"
        assert classify_abpm_pattern(120, None) == "unknown"

    def test_unknown_zero_day(self):
        assert classify_abpm_pattern(0, 80) == "unknown"

    def test_extreme_dipper(self):
        # dip > 20%: day=150, night=115 → dip% = (150-115)/150*100 ≈ 23.3%
        assert classify_abpm_pattern(150, 115) == "extreme_dipper"

    def test_dipper(self):
        # dip 10-20%: day=150, night=127 → dip% ≈ 15.3%
        assert classify_abpm_pattern(150, 127) == "dipper"

    def test_non_dipper(self):
        # dip 0-10%: day=150, night=145 → dip% ≈ 3.3%
        assert classify_abpm_pattern(150, 145) == "non_dipper"

    def test_reverse_dipper(self):
        # night > day → dip < 0
        assert classify_abpm_pattern(130, 135) == "reverse_dipper"


# ---------------------------------------------------------------------------
# classify_tha_type  (legacy)
# ---------------------------------------------------------------------------

class TestClassifyThaType:
    def test_unknown_when_clinic_missing(self):
        assert classify_tha_type(None, None, None, None) == "unknown"

    def test_tha_cap(self):
        assert classify_tha_type(185, 115, 130, 80) == "tha_cap"

    def test_tha_ao_choang_trang(self):
        # clinic cao, home+abpm đều thấp
        result = classify_tha_type(145, 92, 120, 78, 118, 76)
        assert result == "tha_ao_choang_trang"

    def test_tha_an_giau(self):
        # clinic thấp, home cao
        result = classify_tha_type(128, 82, 138, 88)
        assert result == "tha_an_giau"

    def test_tha_duy_tri(self):
        # clinic cao, home cao
        result = classify_tha_type(150, 95, 140, 88)
        assert result == "tha_duy_tri"


# ---------------------------------------------------------------------------
# classify_bp_category  (dùng RULEBOOK — integration qua rules thật)
# ---------------------------------------------------------------------------

class TestClassifyBpCategory:
    """
    Metrics dict dùng key chuẩn mà classify_bp_category đọc.
    Source selection policy: abpm_24h > home > clinic (từ YAML).
    """

    def _make_metrics(self, **kwargs):
        base = {
            "clinic_sys": None, "clinic_dia": None, "clinic_quality_level": None,
            "home_sys": None, "home_dia": None, "home_quality_level": None,
            "abpm_24h_sys": None, "abpm_24h_dia": None, "abpm_quality_level": None,
        }
        base.update(kwargs)
        return base

    def test_clinic_only_normal(self):
        # clinic normal: sys < 120 AND dia < 70
        m = self._make_metrics(clinic_sys=115.0, clinic_dia=65.0, clinic_quality_level="high")
        r = classify_bp_category(m)
        assert r["bp_category"] == "normal"
        assert r["source_used_category"] == "clinic"

    def test_clinic_only_hypertension(self):
        m = self._make_metrics(clinic_sys=150.0, clinic_dia=95.0, clinic_quality_level="high")
        r = classify_bp_category(m)
        assert r["bp_category"] == "hypertension"

    def test_home_preferred_over_clinic(self):
        # home có nhưng clinic cũng có → theo policy YAML, home được ưu tiên hơn clinic
        m = self._make_metrics(
            clinic_sys=150.0, clinic_dia=95.0, clinic_quality_level="high",
            home_sys=125.0, home_dia=80.0, home_quality_level="high",
        )
        r = classify_bp_category(m)
        # Home được pick khi có sẵn và quality đủ
        assert r["source_used_category"] == "home"
        assert r["bp_category"] == "elevated"

    def test_abpm_preferred_over_home(self):
        # abpm normal: sys < 115 AND dia < 65
        m = self._make_metrics(
            home_sys=140.0, home_dia=90.0, home_quality_level="high",
            abpm_24h_sys=112.0, abpm_24h_dia=62.0, abpm_quality_level="high",
        )
        r = classify_bp_category(m)
        assert r["source_used_category"] == "abpm_24h"
        assert r["bp_category"] == "normal"

    def test_no_source_returns_unknown(self):
        m = self._make_metrics()
        r = classify_bp_category(m)
        assert r["bp_category"] == "unknown"
        assert r["category_confidence"] == "low"

    def test_borderline_home_drops_confidence(self):
        # home_sys=134 gần ngưỡng hypertension=135 → borderline, confidence giảm
        m = self._make_metrics(
            home_sys=134.0, home_dia=83.0, home_quality_level="high",
        )
        r = classify_bp_category(m)
        assert "borderline" in r["category_flags"]
        assert r["category_confidence"] in {"medium", "low"}

    def test_home_hypertension_threshold(self):
        # home ≥135/85 → hypertension
        m = self._make_metrics(home_sys=138.0, home_dia=87.0, home_quality_level="high")
        r = classify_bp_category(m)
        assert r["bp_category"] == "hypertension"

    def test_source_value_format(self):
        m = self._make_metrics(clinic_sys=145.0, clinic_dia=92.0, clinic_quality_level="medium")
        r = classify_bp_category(m)
        assert "/" in str(r["source_value_used"])

    def test_quality_flag_appended_low_quality(self):
        m = self._make_metrics(clinic_sys=150.0, clinic_dia=95.0, clinic_quality_level="low")
        r = classify_bp_category(m)
        assert "quality_low" in r["category_flags"]


# ---------------------------------------------------------------------------
# classify_bp_stage
# ---------------------------------------------------------------------------

class TestClassifyBpStage:
    def _base_metrics(self, sys_val, dia_val, quality="high"):
        return {"clinic_sys": sys_val, "clinic_dia": dia_val, "clinic_quality_level": quality}

    def test_not_hypertension_returns_none(self):
        r = classify_bp_stage(self._base_metrics(120, 78), "normal")
        assert r["bp_stage"] == "none"
        assert "not_hypertension" in r["stage_flags"]

    def test_elevated_returns_none(self):
        r = classify_bp_stage(self._base_metrics(128, 82), "elevated")
        assert r["bp_stage"] == "none"

    def test_hypertension_missing_clinic_returns_unknown(self):
        r = classify_bp_stage({"clinic_sys": None, "clinic_dia": None, "clinic_quality_level": None}, "hypertension")
        assert r["bp_stage"] == "unknown"
        assert "missing_clinic" in r["stage_flags"]

    def test_stage1_boundary_140_90(self):
        r = classify_bp_stage(self._base_metrics(140.0, 90.0), "hypertension")
        assert r["bp_stage"] == "stage1"

    def test_stage1_high_sys(self):
        r = classify_bp_stage(self._base_metrics(155.0, 95.0), "hypertension")
        assert r["bp_stage"] == "stage1"

    def test_stage2_sys_and_dia(self):
        # stage2 YAML: sys_ge=160 AND dia_ge=100 — cả hai phải thoả
        r = classify_bp_stage(self._base_metrics(165.0, 105.0), "hypertension")
        assert r["bp_stage"] == "stage2"

    def test_stage2_sys_high_dia_below_100_is_unknown(self):
        # sys=160 nhưng dia=95 < 100 → không khớp stage2 AND stage1 → unknown
        r = classify_bp_stage(self._base_metrics(160.0, 95.0), "hypertension")
        assert r["bp_stage"] == "unknown"

    def test_stage2_both_criteria(self):
        r = classify_bp_stage(self._base_metrics(162.0, 102.0), "hypertension")
        assert r["bp_stage"] == "stage2"

    def test_borderline_stage1_upper_boundary(self):
        # 157/97 trong stage1 range [140-159/90-99], gần mốc 159 → borderline
        r = classify_bp_stage(self._base_metrics(157.0, 97.0), "hypertension")
        assert r["bp_stage"] == "stage1"
        assert "borderline" in r["stage_flags"]

    def test_confidence_reflects_quality(self):
        r = classify_bp_stage(self._base_metrics(145.0, 92.0, quality="low"), "hypertension")
        assert "quality_low" in r["stage_flags"]


# ---------------------------------------------------------------------------
# classify_phenotype
# ---------------------------------------------------------------------------

class TestClassifyPhenotype:
    def _make_metrics(self, **kw):
        base = {
            "clinic_sys": None, "clinic_dia": None, "clinic_quality_level": None,
            "home_sys": None, "home_dia": None, "home_quality_level": None,
            "abpm_24h_sys": None, "abpm_24h_dia": None, "abpm_quality_level": None,
        }
        base.update(kw)
        return base

    def test_missing_clinic_returns_unknown(self):
        m = self._make_metrics(home_sys=130.0, home_dia=82.0, home_quality_level="high")
        r = classify_phenotype(m)
        assert r["phenotype"] == "unknown"
        assert "missing_clinic" in r["phenotype_flags"]

    def test_no_out_of_office_source_returns_unknown(self):
        m = self._make_metrics(clinic_sys=148.0, clinic_dia=94.0, clinic_quality_level="high")
        r = classify_phenotype(m)
        assert r["phenotype"] == "unknown"
        assert "missing_out_of_office" in r["phenotype_flags"]

    def test_white_coat_clinic_high_home_normal(self):
        # clinic ≥140/90, home <135/85
        m = self._make_metrics(
            clinic_sys=148.0, clinic_dia=94.0, clinic_quality_level="high",
            home_sys=124.0, home_dia=78.0, home_quality_level="high",
        )
        r = classify_phenotype(m)
        assert r["phenotype"] == "white_coat"

    def test_masked_clinic_normal_home_high(self):
        # clinic <140/90, home ≥135/85
        m = self._make_metrics(
            clinic_sys=132.0, clinic_dia=82.0, clinic_quality_level="high",
            home_sys=138.0, home_dia=88.0, home_quality_level="high",
        )
        r = classify_phenotype(m)
        assert r["phenotype"] == "masked"

    def test_none_phenotype_both_high(self):
        m = self._make_metrics(
            clinic_sys=150.0, clinic_dia=95.0, clinic_quality_level="high",
            home_sys=140.0, home_dia=88.0, home_quality_level="high",
        )
        r = classify_phenotype(m)
        assert r["phenotype"] == "none"

    def test_none_phenotype_both_normal(self):
        m = self._make_metrics(
            clinic_sys=118.0, clinic_dia=75.0, clinic_quality_level="high",
            home_sys=115.0, home_dia=72.0, home_quality_level="high",
        )
        r = classify_phenotype(m)
        assert r["phenotype"] == "none"

    def test_abpm_used_when_available(self):
        # ABPM ưu tiên hơn home
        m = self._make_metrics(
            clinic_sys=148.0, clinic_dia=94.0, clinic_quality_level="high",
            home_sys=138.0, home_dia=88.0, home_quality_level="high",
            abpm_24h_sys=122.0, abpm_24h_dia=76.0, abpm_quality_level="high",
        )
        r = classify_phenotype(m)
        # abpm_24h_sys=122 < 130 → out_high=False, clinic_high=True → white_coat
        assert r["phenotype"] == "white_coat"
        assert r["phenotype_source"] == "abpm_24h"

    def test_output_has_required_keys(self):
        m = self._make_metrics(
            clinic_sys=118.0, clinic_dia=75.0, clinic_quality_level="high",
            home_sys=115.0, home_dia=72.0, home_quality_level="high",
        )
        r = classify_phenotype(m)
        for key in ["phenotype", "phenotype_source", "phenotype_confidence", "phenotype_quality_level", "phenotype_flags"]:
            assert key in r
