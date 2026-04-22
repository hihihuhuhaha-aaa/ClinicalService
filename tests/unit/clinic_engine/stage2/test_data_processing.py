"""Unit tests for Stage 2 payload normalization (data_processing.py)."""
from __future__ import annotations

import pytest

from services.clinic_engine.stage2_comprehensive_assessment.data_processing import (
    _normalize_bool,
    process_payload,
)
from services.clinic_engine.stage2_comprehensive_assessment.risk_classification import (
    _normalize_bp_stage,
)


# ---------------------------------------------------------------------------
# _normalize_bool
# ---------------------------------------------------------------------------

class TestNormalizeBool:
    @pytest.mark.parametrize("val", [True, "true", "True", "TRUE", "1", "yes", "YES", "y", "Y", 1])
    def test_truthy_values(self, val):
        assert _normalize_bool(val) is True

    @pytest.mark.parametrize("val", [False, "false", "False", "FALSE", "0", "no", "n", 0, None])
    def test_falsy_values(self, val):
        assert _normalize_bool(val) is False

    def test_invalid_string_returns_false(self):
        assert _normalize_bool("maybe") is False

    def test_float_one_is_true(self):
        assert _normalize_bool(1.0) is True

    def test_float_zero_is_false(self):
        assert _normalize_bool(0.0) is False


# ---------------------------------------------------------------------------
# _normalize_bp_stage
# ---------------------------------------------------------------------------

class TestNormalizeBpStage:
    @pytest.mark.parametrize("raw", ["stage1", "stage_1", "tha do i", "tha do 1", "Stage I", "i", "I", "1"])
    def test_stage1_variants(self, raw):
        assert _normalize_bp_stage(raw) == "stage1"

    @pytest.mark.parametrize("raw", ["stage2", "stage_2", "tha do ii", "tha do 2", "Stage II", "ii", "II", "2"])
    def test_stage2_variants(self, raw):
        assert _normalize_bp_stage(raw) == "stage2"

    @pytest.mark.parametrize("raw", ["120-129/70-79", "prehypertension_120_129_70_79", "120-129_70-79", "120_129_70_79"])
    def test_prehypertension_120_variants(self, raw):
        assert _normalize_bp_stage(raw) == "prehypertension_120_129_70_79"

    @pytest.mark.parametrize("raw", [
        "130-139/80-89", "prehypertension_130_139_80_89", "prehypertension",
        "130-139_80-89", "130_139_80_89", "tien_tha", "tien-tha", "pre-tha",
    ])
    def test_prehypertension_130_variants(self, raw):
        assert _normalize_bp_stage(raw) == "prehypertension_130_139_80_89"

    def test_none_returns_unknown(self):
        assert _normalize_bp_stage(None) == "unknown"

    def test_empty_string_returns_unknown(self):
        assert _normalize_bp_stage("") == "unknown"

    def test_garbage_returns_unknown(self):
        assert _normalize_bp_stage("xyz_unknown") == "unknown"


# ---------------------------------------------------------------------------
# process_payload
# ---------------------------------------------------------------------------

class TestProcessPayload:
    def _full_payload(self) -> dict:
        return {
            "patientInfo": {"age": 45, "gender": "male"},
            "bp_stage": "120-129/70-79",
            "special": {"diabetes": False, "familialHypercholesterolemia": False},
            "riskFactors": {
                "male": True, "ageOver65": False, "heartRateOver80": False,
                "overweight": False, "diabetes": False, "highLDLOrTriglyceride": False,
                "familialHypercholesterolemia": False, "familyHistoryOfHypertension": False,
                "earlyMenopause": False, "smoking": False,
                "environmentalSocioeconomicFactors": False, "menopause": False,
                "sedentaryLifestyle": False,
            },
            "hmod": {
                "leftVentricularHypertrophy": False, "brainDamage": False,
                "heartDamage": False, "kidneyDamage": False, "vascularDamage": False,
                "ckdStage3": False, "pulsePressureOver60": False,
            },
            "cardiovascularDisease": {
                "coronaryArteryDisease": False, "heartFailure": False, "stroke": False,
                "peripheralVascularDisease": False, "atrialFibrillation": False,
                "ckdStage4": False, "ckdStage5": False,
            },
        }

    def test_output_keys_present(self):
        result = process_payload(self._full_payload())
        for key in ["special", "riskFactors", "hmod", "cardiovascularDisease", "bp_stage", "has_any_data"]:
            assert key in result

    def test_bp_stage_raw_preserved(self):
        # process_payload trả raw bp_stage string, normalize xảy ra trong classify_risk_level
        result = process_payload(self._full_payload())
        assert result["bp_stage"] == "120-129/70-79"

    def test_age_over_65_auto_computed_true_when_no_explicit_field(self):
        # Nếu riskFactors không có ageOver65 key, tính từ patientInfo.age
        payload = {"patientInfo": {"age": 70}, "riskFactors": {"smoking": False}}
        result = process_payload(payload)
        assert result["riskFactors"]["ageOver65"] is True

    def test_age_over_65_false_when_explicit_false_in_rf(self):
        # Nếu riskFactors có ageOver65=False explicit → override tính từ age
        payload = self._full_payload()
        payload["patientInfo"]["age"] = 70
        payload["riskFactors"]["ageOver65"] = False  # explicit False ghi đè
        result = process_payload(payload)
        assert result["riskFactors"]["ageOver65"] is False

    def test_age_over_65_true_when_no_explicit_field_65(self):
        # age=65 ≥ 65 → ageOver65=True khi không có explicit field
        payload = {"patientInfo": {"age": 65}, "riskFactors": {}}
        result = process_payload(payload)
        assert result["riskFactors"]["ageOver65"] is True

    def test_age_string_converts_when_no_explicit_field(self):
        payload = {"patientInfo": {"age": "68"}, "riskFactors": {}}
        result = process_payload(payload)
        assert result["riskFactors"]["ageOver65"] is True

    def test_empty_payload_no_crash(self):
        result = process_payload({})
        assert result["has_any_data"] is False
        assert result["bp_stage"] is None

    def test_has_any_data_true_when_risk_factor(self):
        payload = self._full_payload()
        payload["riskFactors"]["smoking"] = True
        result = process_payload(payload)
        assert result["has_any_data"] is True

    def test_has_any_data_false_all_false(self):
        # patientInfo.age=45 → ageOver65=False, all others False → has_any_data=False
        payload = {
            "patientInfo": {"age": 45},
            "riskFactors": {"male": False, "smoking": False},
        }
        result = process_payload(payload)
        assert result["has_any_data"] is False

    def test_cardiovascular_risk_factors_alias(self):
        # "cardiovascularRiskFactors" cũng được nhận
        payload = {
            "bp_stage": "stage1",
            "cardiovascularRiskFactors": {"smoking": True},
        }
        result = process_payload(payload)
        assert result["riskFactors"]["smoking"] is True

    def test_target_organ_damage_alias(self):
        payload = {
            "targetOrganDamage": {"leftVentricularHypertrophy": True},
        }
        result = process_payload(payload)
        assert result["hmod"]["leftVentricularHypertrophy"] is True

    def test_cvd_block_alias(self):
        # "cvd" key cũng được nhận
        payload = {
            "cvd": {"coronaryArteryDisease": True},
        }
        result = process_payload(payload)
        assert result["cardiovascularDisease"]["coronaryArteryDisease"] is True

    def test_boolean_string_coercion_in_risk_factors(self):
        payload = self._full_payload()
        payload["riskFactors"]["smoking"] = "true"
        payload["riskFactors"]["overweight"] = "1"
        result = process_payload(payload)
        assert result["riskFactors"]["smoking"] is True
        assert result["riskFactors"]["overweight"] is True

    def test_ckd_alias_stage4(self):
        payload = {"cvd": {"ckdStageIV": True}}
        result = process_payload(payload)
        assert result["cardiovascularDisease"]["ckdStage4"] is True

    def test_ckd_alias_stage5(self):
        payload = {"cvd": {"ckdStageV": True}}
        result = process_payload(payload)
        assert result["cardiovascularDisease"]["ckdStage5"] is True

    def test_special_block_extracted(self):
        payload = {"special": {"diabetes": True, "familialHypercholesterolemia": True}}
        result = process_payload(payload)
        assert result["special"]["diabetes"] is True
        assert result["special"]["familialHypercholesterolemia"] is True
