"""Integration tests for Stage 1 pipeline — chạy trên các test case JSON thực."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from services.clinic_engine.stage1_measurement_classification.pipeline import run_symbolic_pipeline

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "temp" / "stage1_test_cases"


def _load_case(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    records = json.loads(path.read_text())
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class TestOutputSchema:
    def test_required_keys_present(self):
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        for key in ["patient_summary", "patient_count", "phenotypes", "tha_types", "tha_stages"]:
            assert key in result

    def test_patient_summary_is_dataframe(self):
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        assert isinstance(result["patient_summary"], pd.DataFrame)

    def test_patient_count_matches_summary(self):
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        assert result["patient_count"] == len(result["patient_summary"])

    def test_patient_summary_has_classification_columns(self):
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        summary = result["patient_summary"]
        for col in ["bp_category", "bp_stage", "phenotype"]:
            assert col in summary.columns

    def test_phenotypes_is_list(self):
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        assert isinstance(result["phenotypes"], list)

    def test_tha_stages_is_list(self):
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        assert isinstance(result["tha_stages"], list)


# ---------------------------------------------------------------------------
# Case-specific expected outcomes
# ---------------------------------------------------------------------------

class TestCase01NormalHome:
    def test_bp_category_normal_or_elevated(self):
        # case01: HBPM 116-119/72-75 → normal
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["bp_category"] in {"normal", "elevated"}

    def test_source_is_home(self):
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["source_used_category"] == "home"

    def test_bp_stage_none(self):
        # không phải hypertension → stage=none
        df = _load_case("case01_normal_home.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["bp_stage"] == "none"


class TestCase02ElevatedHome:
    def test_bp_category_elevated(self):
        # case02: HBPM 126-129/78-79
        df = _load_case("case02_elevated_home.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["bp_category"] in {"elevated", "normal"}


class TestCase03HomeHypertension:
    def test_bp_category_hypertension(self):
        # case03: HBPM 137-140/87-90 → hypertension (≥135/85)
        df = _load_case("case03_home_hypertension.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["bp_category"] == "hypertension"


class TestCase04ClinicStage1:
    def test_bp_stage_stage1(self):
        # case04: OBPM 143-145/91-92 → hypertension stage1
        df = _load_case("case04_clinic_stage1.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["bp_category"] == "hypertension"
        assert row["bp_stage"] == "stage1"

    def test_stage_source_clinic(self):
        df = _load_case("case04_clinic_stage1.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["stage_source"] == "clinic"


class TestCase05ClinicStage2:
    def test_bp_stage_stage2(self):
        # case05: OBPM 166-168/102-104 → stage2
        df = _load_case("case05_clinic_stage2.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["bp_stage"] == "stage2"


class TestCase06WhiteCoat:
    def test_phenotype_white_coat(self):
        # case06: clinic cao (146-148/92-94), home thấp (123-124/77-78)
        df = _load_case("case06_white_coat.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["phenotype"] == "white_coat"


class TestCase07Masked:
    def test_phenotype_masked(self):
        # case07: clinic bình thường, home cao → masked
        df = _load_case("case07_masked.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["phenotype"] == "masked"


class TestCase08AbpmHypertension:
    def test_abpm_source_used(self):
        df = _load_case("case08_abpm_hypertension.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["source_used_category"] == "abpm_24h"
        assert row["bp_category"] == "hypertension"


class TestCase09AbpmNormal:
    def test_abpm_normal_classification(self):
        df = _load_case("case09_abpm_normal.json")
        result = run_symbolic_pipeline(df)
        row = result["patient_summary"].iloc[0]
        assert row["source_used_category"] == "abpm_24h"
        assert row["bp_category"] in {"normal", "elevated"}


class TestCase10BorderlineMixed:
    def test_no_crash(self):
        df = _load_case("case10_borderline_mixed.json")
        result = run_symbolic_pipeline(df)
        assert result["patient_count"] >= 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_missing_source_column_raises(self):
        df = pd.DataFrame([{"patient_id": "p1", "systolic": 120, "diastolic": 80}])
        with pytest.raises(ValueError, match="source"):
            run_symbolic_pipeline(df)

    def test_single_reading_does_not_crash(self):
        df = pd.DataFrame([{
            "patient_id": "single_p",
            "source": "OBPM",
            "datetime": "2026-04-01T09:00:00",
            "systolic": 145.0,
            "diastolic": 92.0,
        }])
        result = run_symbolic_pipeline(df)
        assert result["patient_count"] == 1

    def test_multi_patient_count(self):
        df1 = _load_case("case01_normal_home.json")
        df2 = _load_case("case02_elevated_home.json")
        combined = pd.concat([df1, df2], ignore_index=True)
        result = run_symbolic_pipeline(combined)
        assert result["patient_count"] == 2

    def test_deterministic_output(self):
        df = _load_case("case04_clinic_stage1.json")
        r1 = run_symbolic_pipeline(df)
        r2 = run_symbolic_pipeline(df)
        row1 = r1["patient_summary"].iloc[0]
        row2 = r2["patient_summary"].iloc[0]
        assert row1["bp_category"] == row2["bp_category"]
        assert row1["bp_stage"] == row2["bp_stage"]
