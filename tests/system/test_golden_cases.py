"""System/regression tests: snapshot golden outputs cho toàn bộ 20 test cases.

Lần đầu chạy: tự động sinh golden files vào tests/system/golden/.
Các lần sau: so sánh output thực tế với golden → fail nếu khác.

Để cập nhật golden sau khi thay đổi logic có chủ đích:
    REGEN_GOLDEN=1 pytest tests/system/test_golden_cases.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from services.clinic_engine.stage1_measurement_classification.pipeline import run_symbolic_pipeline
from services.clinic_engine.stage2_comprehensive_assessment.assessment import run_stage2_assessment

STAGE1_DATA = Path(__file__).resolve().parent.parent.parent / "data" / "temp" / "stage1_test_cases"
STAGE2_DATA = Path(__file__).resolve().parent.parent.parent / "data" / "temp" / "stage2_test_cases"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
REGEN = os.environ.get("REGEN_GOLDEN", "0").strip() == "1"

STAGE1_CASES = [p.name for p in sorted(STAGE1_DATA.glob("case*.json"))]
STAGE2_CASES = [p.name for p in sorted(STAGE2_DATA.glob("case*.json"))]

# Cột cần so sánh trong Stage 1 patient_summary (bỏ qua cột số float có thể có epsilon diff)
STAGE1_COMPARE_COLS = [
    "bp_category",
    "source_used_category",
    "bp_stage",
    "stage_source",
    "phenotype",
    "phenotype_source",
    "tha_type",
    "category_confidence",
    "stage_confidence",
    "phenotype_confidence",
]


def _golden_path(prefix: str, case_name: str) -> Path:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    return GOLDEN_DIR / f"{prefix}_{case_name}.json"


def _save_golden(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _load_golden(path: Path) -> dict:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Stage 1 golden tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_name", STAGE1_CASES)
def test_stage1_golden(case_name: str):
    records = json.loads((STAGE1_DATA / case_name).read_text())
    df = pd.DataFrame(records)
    result = run_symbolic_pipeline(df)
    summary_df = result["patient_summary"]

    # Chỉ serialize các cột cần thiết
    available_cols = [c for c in STAGE1_COMPARE_COLS if c in summary_df.columns]
    actual = summary_df[available_cols].to_dict(orient="records")

    golden_path = _golden_path("stage1", case_name)

    if REGEN or not golden_path.exists():
        _save_golden(golden_path, {"cases": actual})
        pytest.skip(f"Golden generated: {golden_path.name}")

    expected = _load_golden(golden_path)["cases"]
    assert len(actual) == len(expected), (
        f"Patient count changed: expected {len(expected)}, got {len(actual)}"
    )
    for i, (act, exp) in enumerate(zip(actual, expected)):
        for col in available_cols:
            assert act.get(col) == exp.get(col), (
                f"[{case_name}] patient[{i}].{col}: expected {exp.get(col)!r}, got {act.get(col)!r}"
            )


# ---------------------------------------------------------------------------
# Stage 2 golden tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_name", STAGE2_CASES)
def test_stage2_golden(case_name: str):
    payload = json.loads((STAGE2_DATA / case_name).read_text())
    result = run_stage2_assessment(payload)

    # Chỉ so sánh các field ổn định (bỏ qua recommendation text dài có thể thay đổi)
    actual = {
        "risk_level": result["risk_level"],
        "confidence": result["confidence"],
    }

    golden_path = _golden_path("stage2", case_name)

    if REGEN or not golden_path.exists():
        _save_golden(golden_path, actual)
        pytest.skip(f"Golden generated: {golden_path.name}")

    expected = _load_golden(golden_path)
    assert actual["risk_level"] == expected["risk_level"], (
        f"[{case_name}] risk_level: expected {expected['risk_level']!r}, got {actual['risk_level']!r}"
    )
    assert actual["confidence"] == expected["confidence"], (
        f"[{case_name}] confidence: expected {expected['confidence']!r}, got {actual['confidence']!r}"
    )


# ---------------------------------------------------------------------------
# Determinism tests — cùng input → cùng output, chạy nhiều lần
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_stage1_deterministic_3_runs(self):
        records = json.loads((STAGE1_DATA / "case04_clinic_stage1.json").read_text())
        df = pd.DataFrame(records)
        results = [run_symbolic_pipeline(df)["patient_summary"].iloc[0]["bp_category"] for _ in range(3)]
        assert len(set(results)) == 1, f"Non-deterministic stage1 output: {results}"

    def test_stage2_deterministic_3_runs(self):
        payload = json.loads((STAGE2_DATA / "case08_rule3_medium_pre120_cvd.json").read_text())
        results = [run_stage2_assessment(payload)["risk_level"] for _ in range(3)]
        assert len(set(results)) == 1, f"Non-deterministic stage2 output: {results}"

    def test_stage1_all_cases_deterministic(self):
        for case_name in STAGE1_CASES:
            records = json.loads((STAGE1_DATA / case_name).read_text())
            df = pd.DataFrame(records)
            r1 = run_symbolic_pipeline(df)["patient_summary"]
            r2 = run_symbolic_pipeline(df)["patient_summary"]
            assert list(r1["bp_category"]) == list(r2["bp_category"]), (
                f"Non-deterministic for {case_name}"
            )

    def test_stage2_all_cases_deterministic(self):
        for case_name in STAGE2_CASES:
            payload = json.loads((STAGE2_DATA / case_name).read_text())
            r1 = run_stage2_assessment(payload)
            r2 = run_stage2_assessment(payload)
            assert r1["risk_level"] == r2["risk_level"], (
                f"Non-deterministic for {case_name}"
            )
