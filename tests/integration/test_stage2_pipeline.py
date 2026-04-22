"""Integration tests for Stage 2 pipeline — chạy trên 10 test case JSON thực."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.clinic_engine.stage2_comprehensive_assessment.assessment import run_stage2_assessment

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "temp" / "stage2_test_cases"


def _load(filename: str) -> dict:
    return json.loads((DATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class TestOutputSchema:
    def test_required_keys_present(self):
        result = run_stage2_assessment(_load("case01_rule1_low_pre120.json"))
        for key in ["risk_level", "recommendation", "explanation", "confidence"]:
            assert key in result

    def test_risk_level_valid_values(self):
        result = run_stage2_assessment(_load("case01_rule1_low_pre120.json"))
        assert result["risk_level"] in {"low", "medium", "high"}

    def test_confidence_valid_values(self):
        result = run_stage2_assessment(_load("case01_rule1_low_pre120.json"))
        assert result["confidence"] in {"low", "medium", "high"}

    def test_recommendation_is_string(self):
        result = run_stage2_assessment(_load("case01_rule1_low_pre120.json"))
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 0

    def test_explanation_is_string(self):
        result = run_stage2_assessment(_load("case01_rule1_low_pre120.json"))
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 0


# ---------------------------------------------------------------------------
# Case-specific expected risk levels
# ---------------------------------------------------------------------------

class TestCase01Rule1LowPre120:
    def test_risk_level_low(self):
        # 1 RF (male), prehtn_120 → Rule 1 → low
        result = run_stage2_assessment(_load("case01_rule1_low_pre120.json"))
        assert result["risk_level"] == "low"

    def test_explanation_mentions_rule1(self):
        result = run_stage2_assessment(_load("case01_rule1_low_pre120.json"))
        assert "Rule 1" in result["explanation"]


class TestCase02Rule1HighStage1:
    def test_risk_level_high(self):
        # 2 RF (overweight, familyHistory), stage1 → Rule 1 → high
        result = run_stage2_assessment(_load("case02_rule1_high_stage1.json"))
        assert result["risk_level"] == "high"

    def test_explanation_mentions_rule1(self):
        result = run_stage2_assessment(_load("case02_rule1_high_stage1.json"))
        assert "Rule 1" in result["explanation"]


class TestCase03Rule2LowPre120:
    def test_risk_level_low(self):
        # 3 RF (ageOver65, male, heartRateOver80), prehtn_120 → Rule 2 → low
        result = run_stage2_assessment(_load("case03_rule2_low_pre120_ge3rf.json"))
        assert result["risk_level"] == "low"

    def test_explanation_mentions_rule2(self):
        result = run_stage2_assessment(_load("case03_rule2_low_pre120_ge3rf.json"))
        assert "Rule 2" in result["explanation"]


class TestCase04Rule2MediumPre130Diabetes:
    def test_risk_level_medium(self):
        # diabetes, prehtn_130 → Rule 2 → medium
        result = run_stage2_assessment(_load("case04_rule2_medium_pre130_diabetes.json"))
        assert result["risk_level"] == "medium"


class TestCase05Rule2HighStage2Fh:
    def test_risk_level_high(self):
        # familial hypercholesterolemia, stage2 → Rule 2 → high
        result = run_stage2_assessment(_load("case05_rule2_high_stage2_fh.json"))
        assert result["risk_level"] == "high"


class TestCase06Rule2MediumPre130Ckd3:
    def test_risk_level_medium(self):
        # ckdStage3 (HMOD), prehtn_130 → Rule 2 → medium
        result = run_stage2_assessment(_load("case06_rule2_medium_pre130_ckd3.json"))
        assert result["risk_level"] == "medium"


class TestCase07Rule2LowPre120Hmod:
    def test_risk_level_low(self):
        # LVH (HMOD), prehtn_120 → Rule 2 → low
        result = run_stage2_assessment(_load("case07_rule2_low_pre120_hmod.json"))
        assert result["risk_level"] == "low"


class TestCase08Rule3MediumPre120Cvd:
    def test_risk_level_medium(self):
        # stroke (CVD), prehtn_120 → Rule 3 → medium
        result = run_stage2_assessment(_load("case08_rule3_medium_pre120_cvd.json"))
        assert result["risk_level"] == "medium"

    def test_explanation_mentions_rule3(self):
        result = run_stage2_assessment(_load("case08_rule3_medium_pre120_cvd.json"))
        assert "Rule 3" in result["explanation"]


class TestCase09Rule3HighPre130Cvd:
    def test_risk_level_high(self):
        # CAD (CVD), prehtn_130 → Rule 3 → high
        result = run_stage2_assessment(_load("case09_rule3_high_pre130_cvd.json"))
        assert result["risk_level"] == "high"


class TestCase10Rule3HighStage1Ckd5:
    def test_risk_level_high(self):
        # ckdStage5 (CVD), stage1 → Rule 3 → high
        result = run_stage2_assessment(_load("case10_rule3_high_stage1_ckd5.json"))
        assert result["risk_level"] == "high"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_dict_does_not_crash(self):
        result = run_stage2_assessment({})
        assert result["risk_level"] in {"low", "medium", "high"}

    def test_file_path_input(self):
        path = DATA_DIR / "case01_rule1_low_pre120.json"
        result = run_stage2_assessment(path)
        assert result["risk_level"] == "low"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            run_stage2_assessment("/tmp/nonexistent_stage2_input.json")

    def test_invalid_json_top_level_raises(self):
        import tempfile, json, os
        # JSON hợp lệ nhưng top-level là list, không phải dict
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([1, 2, 3], f)
            tmp_path = f.name
        try:
            with pytest.raises(ValueError):
                run_stage2_assessment(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_deterministic_output(self):
        payload = _load("case04_rule2_medium_pre130_diabetes.json")
        r1 = run_stage2_assessment(payload)
        r2 = run_stage2_assessment(payload)
        assert r1["risk_level"] == r2["risk_level"]
        assert r1["confidence"] == r2["confidence"]
