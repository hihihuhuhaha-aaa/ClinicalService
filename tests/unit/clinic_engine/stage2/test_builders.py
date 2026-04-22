"""Unit tests for Stage 2 explanation, recommendation, and confidence builders."""
from __future__ import annotations

import pytest

from services.clinic_engine.stage2_comprehensive_assessment.confidence_calculator import calculate_confidence
from services.clinic_engine.stage2_comprehensive_assessment.explanation_builder import build_explanation
from services.clinic_engine.stage2_comprehensive_assessment.recommendation_builder import build_recommendation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pd(bp_stage="unknown", rf=None, special=None, hmod=None, cvd=None, has_any_data=True) -> dict:
    _empty_rf = {
        "ageOver65": False, "male": False, "heartRateOver80": False,
        "overweight": False, "highLDLOrTriglyceride": False,
        "familyHistoryOfHypertension": False, "earlyMenopause": False,
        "smoking": False, "environmentalSocioeconomicFactors": False,
        "menopause": False, "sedentaryLifestyle": False, "diabetes": False,
        "familialHypercholesterolemia": False,
    }
    _empty_hmod = {
        "leftVentricularHypertrophy": False, "brainDamage": False,
        "heartDamage": False, "kidneyDamage": False, "vascularDamage": False,
        "ckdStage3": False, "pulsePressureOver60": False,
    }
    _empty_cvd = {
        "coronaryArteryDisease": False, "heartFailure": False, "stroke": False,
        "peripheralVascularDisease": False, "atrialFibrillation": False,
        "ckdStage4": False, "ckdStage5": False,
    }
    merged_rf = {**_empty_rf, **(rf or {})}
    merged_hmod = {**_empty_hmod, **(hmod or {})}
    merged_cvd = {**_empty_cvd, **(cvd or {})}
    return {
        "bp_stage": bp_stage,
        "riskFactors": merged_rf,
        "special": special or {},
        "hmod": merged_hmod,
        "cardiovascularDisease": merged_cvd,
        "has_any_data": has_any_data,
    }


# ---------------------------------------------------------------------------
# build_explanation
# ---------------------------------------------------------------------------

class TestBuildExplanation:
    def test_rule3_mentioned_when_cvd(self):
        data = _pd(bp_stage="stage1", cvd={"coronaryArteryDisease": True})
        exp = build_explanation(data, "high")
        assert "Rule 3" in exp
        assert "cardiovascular" in exp.lower()

    def test_rule3_shows_cvd_count(self):
        data = _pd(bp_stage="stage1", cvd={"coronaryArteryDisease": True, "heartFailure": True})
        exp = build_explanation(data, "high")
        assert "count=2" in exp

    def test_rule2_mentioned_when_3_rf(self):
        data = _pd(bp_stage="stage1", rf={"ageOver65": True, "male": True, "smoking": True})
        exp = build_explanation(data, "high")
        assert "Rule 2" in exp
        assert "3" in exp

    def test_rule2_mentions_diabetes(self):
        data = _pd(bp_stage="stage1", rf={"diabetes": True})
        exp = build_explanation(data, "high")
        assert "Rule 2" in exp
        assert "diabetes" in exp

    def test_rule2_mentions_hmod(self):
        data = _pd(bp_stage="stage1", hmod={"leftVentricularHypertrophy": True})
        exp = build_explanation(data, "high")
        assert "Rule 2" in exp
        assert "HMOD" in exp

    def test_rule1_mentioned_when_1_rf(self):
        data = _pd(bp_stage="prehypertension_120_129_70_79", rf={"male": True})
        exp = build_explanation(data, "low")
        assert "Rule 1" in exp
        assert "1 non-special risk factor" in exp

    def test_rule1_mentions_2_factors(self):
        data = _pd(bp_stage="stage1", rf={"male": True, "smoking": True})
        exp = build_explanation(data, "high")
        assert "Rule 1" in exp
        assert "2 non-special risk factor" in exp

    def test_no_rule_default_explanation(self):
        data = _pd(bp_stage="unknown")
        exp = build_explanation(data, "low")
        assert "No explicit rule" in exp

    def test_explanation_includes_risk_level(self):
        data = _pd(bp_stage="stage1", cvd={"stroke": True})
        exp = build_explanation(data, "high")
        assert "high" in exp.lower()

    def test_explanation_is_string(self):
        data = _pd(bp_stage="stage1")
        result = build_explanation(data, "high")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# build_recommendation
# ---------------------------------------------------------------------------

class TestBuildRecommendation:
    def test_high_risk_contains_thuoc(self):
        rec = build_recommendation("high", "stage1")
        # Tiếng Việt: "thuoc" = thuốc (medication)
        assert "thuoc" in rec.lower() or "dieu tri" in rec.lower()

    def test_medium_risk_contains_6_thang(self):
        rec = build_recommendation("medium", "stage1")
        assert "6" in rec or "trung binh" in rec.lower()

    def test_low_risk_contains_tdls(self):
        rec = build_recommendation("low", "stage1")
        assert "TDLS" in rec or "thap" in rec.lower()

    def test_prehypertension_appends_extra_note(self):
        rec = build_recommendation("low", "120-129/70-79")
        assert "tien THA" in rec or "O nhom" in rec

    def test_prehypertension_130_appends_extra_note(self):
        rec = build_recommendation("medium", "prehypertension")
        assert "tien THA" in rec or "TDLS" in rec

    def test_stage1_no_extra_note(self):
        rec = build_recommendation("high", "stage1")
        # "O nhom tien THA" chỉ xuất hiện khi là prehypertension
        assert "O nhom tien THA" not in rec

    def test_recommendation_is_string(self):
        result = build_recommendation("low", None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_all_risk_levels_return_non_empty(self):
        for level in ["low", "medium", "high"]:
            assert len(build_recommendation(level, "stage1")) > 0


# ---------------------------------------------------------------------------
# calculate_confidence
# ---------------------------------------------------------------------------

class TestCalculateConfidence:
    def test_high_risk_with_data_is_high(self):
        data = _pd(has_any_data=True)
        assert calculate_confidence("high", data) == "high"

    def test_medium_risk_with_data_is_medium(self):
        data = _pd(has_any_data=True)
        assert calculate_confidence("medium", data) == "medium"

    def test_low_risk_with_data_is_low(self):
        data = _pd(has_any_data=True)
        assert calculate_confidence("low", data) == "low"

    def test_no_data_always_low(self):
        data = _pd(has_any_data=False)
        for level in ["low", "medium", "high"]:
            assert calculate_confidence(level, data) == "low"

    def test_returns_string(self):
        data = _pd(has_any_data=True)
        result = calculate_confidence("high", data)
        assert isinstance(result, str)
        assert result in {"low", "medium", "high"}
