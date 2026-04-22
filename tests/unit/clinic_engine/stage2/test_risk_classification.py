"""Unit tests for Stage 2 risk classification rules."""
from __future__ import annotations

import pytest

from services.clinic_engine.stage2_comprehensive_assessment.risk_classification import classify_risk_level


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data(
    bp_stage: str = "unknown",
    rf: dict | None = None,
    special: dict | None = None,
    hmod: dict | None = None,
    cvd: dict | None = None,
) -> dict:
    """Build a processed_data dict compatible with classify_risk_level."""
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
    if rf is not None:
        merged_rf = dict(_empty_rf)
        merged_rf.update(rf)
    else:
        merged_rf = _empty_rf

    merged_hmod = dict(_empty_hmod)
    if hmod:
        merged_hmod.update(hmod)

    merged_cvd = dict(_empty_cvd)
    if cvd:
        merged_cvd.update(cvd)

    return {
        "bp_stage": bp_stage,
        "riskFactors": merged_rf,
        "special": special or {},
        "hmod": merged_hmod,
        "cardiovascularDisease": merged_cvd,
        "has_any_data": True,
    }


# ---------------------------------------------------------------------------
# Rule 3 — Cardiovascular Disease present
# ---------------------------------------------------------------------------

class TestRule3:
    def test_cvd_with_prehtn_120_is_medium(self):
        data = _make_data(bp_stage="prehypertension_120_129_70_79", cvd={"coronaryArteryDisease": True})
        assert classify_risk_level(data) == "medium"

    def test_cvd_with_prehtn_130_is_high(self):
        data = _make_data(bp_stage="prehypertension_130_139_80_89", cvd={"heartFailure": True})
        assert classify_risk_level(data) == "high"

    def test_cvd_with_stage1_is_high(self):
        data = _make_data(bp_stage="stage1", cvd={"stroke": True})
        assert classify_risk_level(data) == "high"

    def test_cvd_with_stage2_is_high(self):
        data = _make_data(bp_stage="stage2", cvd={"atrialFibrillation": True})
        assert classify_risk_level(data) == "high"

    def test_cvd_ckd4_triggers_rule3(self):
        data = _make_data(bp_stage="stage1", cvd={"ckdStage4": True})
        assert classify_risk_level(data) == "high"

    def test_cvd_ckd5_triggers_rule3(self):
        data = _make_data(bp_stage="stage2", cvd={"ckdStage5": True})
        assert classify_risk_level(data) == "high"

    def test_cvd_unknown_bp_stage_is_high(self):
        data = _make_data(bp_stage="unknown", cvd={"stroke": True})
        assert classify_risk_level(data) == "high"

    def test_cvd_peripheral_vascular_is_high_stage2(self):
        data = _make_data(bp_stage="stage2", cvd={"peripheralVascularDisease": True})
        assert classify_risk_level(data) == "high"

    def test_no_cvd_does_not_trigger_rule3(self):
        # 0 CVD → rule 3 không apply → default
        data = _make_data(bp_stage="stage1")
        assert classify_risk_level(data) == "high"  # default cho stage1


# ---------------------------------------------------------------------------
# Rule 2 — ≥3 non-special risk factors OR special conditions
# ---------------------------------------------------------------------------

class TestRule2:
    def test_3_rf_prehtn_120_is_low(self):
        data = _make_data(
            bp_stage="prehypertension_120_129_70_79",
            rf={"ageOver65": True, "male": True, "heartRateOver80": True},
        )
        assert classify_risk_level(data) == "low"

    def test_3_rf_prehtn_130_is_medium(self):
        data = _make_data(
            bp_stage="prehypertension_130_139_80_89",
            rf={"ageOver65": True, "male": True, "heartRateOver80": True},
        )
        assert classify_risk_level(data) == "medium"

    def test_3_rf_stage1_is_high(self):
        data = _make_data(
            bp_stage="stage1",
            rf={"ageOver65": True, "male": True, "heartRateOver80": True},
        )
        assert classify_risk_level(data) == "high"

    def test_3_rf_stage2_is_high(self):
        data = _make_data(
            bp_stage="stage2",
            rf={"ageOver65": True, "male": True, "smoking": True},
        )
        assert classify_risk_level(data) == "high"

    def test_3_rf_unknown_bp_is_medium(self):
        data = _make_data(
            bp_stage="unknown",
            rf={"ageOver65": True, "male": True, "heartRateOver80": True},
        )
        assert classify_risk_level(data) == "medium"

    def test_diabetes_alone_triggers_rule2(self):
        data = _make_data(bp_stage="prehypertension_120_129_70_79", rf={"diabetes": True})
        assert classify_risk_level(data) == "low"

    def test_diabetes_in_special_triggers_rule2(self):
        data = _make_data(bp_stage="prehypertension_130_139_80_89", special={"diabetes": True})
        assert classify_risk_level(data) == "medium"

    def test_fh_in_special_triggers_rule2(self):
        data = _make_data(bp_stage="stage2", special={"familialHypercholesterolemia": True})
        assert classify_risk_level(data) == "high"

    def test_ckd3_triggers_rule2(self):
        data = _make_data(bp_stage="prehypertension_130_139_80_89", hmod={"ckdStage3": True})
        assert classify_risk_level(data) == "medium"

    def test_hmod_lvh_triggers_rule2(self):
        data = _make_data(bp_stage="stage1", hmod={"leftVentricularHypertrophy": True})
        assert classify_risk_level(data) == "high"

    def test_any_hmod_triggers_rule2(self):
        data = _make_data(bp_stage="prehypertension_120_129_70_79", hmod={"brainDamage": True})
        assert classify_risk_level(data) == "low"

    def test_exactly_3_rf_triggers_rule2_not_rule1(self):
        # 3 non-special RF → rule2, bất kể bp_stage
        data = _make_data(
            bp_stage="prehypertension_120_129_70_79",
            rf={"overweight": True, "smoking": True, "menopause": True},
        )
        assert classify_risk_level(data) == "low"  # rule2: prehtn_120 → low


# ---------------------------------------------------------------------------
# Rule 1 — 1-2 non-special risk factors
# ---------------------------------------------------------------------------

class TestRule1:
    def test_1_rf_prehtn_120_is_low(self):
        data = _make_data(bp_stage="prehypertension_120_129_70_79", rf={"male": True})
        assert classify_risk_level(data) == "low"

    def test_1_rf_prehtn_130_is_low(self):
        data = _make_data(bp_stage="prehypertension_130_139_80_89", rf={"smoking": True})
        assert classify_risk_level(data) == "low"

    def test_2_rf_prehtn_is_low(self):
        data = _make_data(bp_stage="prehypertension_120_129_70_79", rf={"male": True, "overweight": True})
        assert classify_risk_level(data) == "low"

    def test_1_rf_stage1_is_high(self):
        data = _make_data(bp_stage="stage1", rf={"male": True})
        assert classify_risk_level(data) == "high"

    def test_2_rf_stage2_is_high(self):
        data = _make_data(bp_stage="stage2", rf={"male": True, "smoking": True})
        assert classify_risk_level(data) == "high"

    def test_1_rf_unknown_bp_is_low(self):
        data = _make_data(bp_stage="unknown", rf={"male": True})
        assert classify_risk_level(data) == "low"


# ---------------------------------------------------------------------------
# Default path — 0 risk factors, no CVD, no HMOD
# ---------------------------------------------------------------------------

class TestDefault:
    def test_stage1_no_factors_is_high(self):
        data = _make_data(bp_stage="stage1")
        assert classify_risk_level(data) == "high"

    def test_stage2_no_factors_is_high(self):
        data = _make_data(bp_stage="stage2")
        assert classify_risk_level(data) == "high"

    def test_normal_bp_no_factors_is_low(self):
        data = _make_data(bp_stage="unknown")
        assert classify_risk_level(data) == "low"

    def test_prehtn_no_factors_no_rule_is_low(self):
        data = _make_data(bp_stage="prehypertension_120_129_70_79")
        assert classify_risk_level(data) == "low"

    def test_empty_processed_data_does_not_crash(self):
        data = {"bp_stage": None, "riskFactors": {}, "special": {}, "hmod": {}, "cardiovascularDisease": {}}
        result = classify_risk_level(data)
        assert result in {"low", "medium", "high"}
