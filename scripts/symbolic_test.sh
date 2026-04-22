#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

JSON_PATH=""
STAGE="stage1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      JSON_PATH="${2:-}"
      shift 2
      ;;
    --stage)
      STAGE="${2:-}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 --json <path/to/input.json> [--stage stage1|stage2]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 --json <path/to/input.json> [--stage stage1|stage2]"
      exit 1
      ;;
  esac
done

if [[ -z "$JSON_PATH" ]]; then
  echo "Missing --json argument"
  echo "Usage: $0 --json <path/to/input.json> [--stage stage1|stage2]"
  exit 1
fi

if [[ "$STAGE" != "stage1" && "$STAGE" != "stage2" ]]; then
  echo "Invalid --stage value: $STAGE (expected: stage1 or stage2)"
  exit 1
fi

if [[ ! -f "$JSON_PATH" ]]; then
  echo "JSON file not found: $JSON_PATH"
  exit 1
fi

cd "$ROOT_DIR"

python - "$JSON_PATH" "$STAGE" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from services.clinic_engine import run_stage2_assessment, run_symbolic_pipeline

REQUIRED_FIELDS = [
    "patient_id",
    "source",
    "day_period",
    "datetime",
    "systolic",
    "diastolic",
]

DEFAULT_SAMPLE = {
    "patient_id": "home_case_001",
    "source": "HBPM",
    "day_period": "morning",
    "datetime": datetime.now().isoformat(timespec="seconds"),
    "systolic": 138,
    "diastolic": 88,
}

FLAG_EXPLANATION = {
    "borderline": "Gia tri do gan nguong phan loai nen can theo doi sat hon.",
    "quality_low": "Chat luong du lieu thap, do tin cay ket luan bi giam.",
    "unknown_source": "Khong xac dinh duoc nguon du lieu phu hop.",
    "missing_clinic": "Thieu du lieu clinic nen khong the ket luan day du.",
    "missing_out_of_office": "Thieu du lieu ngoai phong kham (home/abpm).",
    "not_hypertension": "Khong thuoc nhom tang huyet ap nen khong xep stage.",
}


def parse_value(value: str, field: str) -> Any:
    value = value.strip()
    if value == "":
        return None
    if field in {"systolic", "diastolic"}:
        return float(value)
    if field == "datetime":
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("datetime must be ISO format, e.g. 2026-04-16T08:30:00") from exc
    return value


def normalize_record(sample: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for field in REQUIRED_FIELDS:
        record[field] = sample.get(field, DEFAULT_SAMPLE[field])
    for key, value in sample.items():
        if key not in record and value is not None:
            record[key] = value
    return record


def format_sample_value(value: Any, field: str) -> Any:
    if value is None:
        return None
    if field in {"systolic", "diastolic"}:
        return float(value)
    if field == "datetime":
        if isinstance(value, str):
            return parse_value(value, field)
        return value
    return value


def load_sample_from_json(path: Path) -> list[dict[str, Any]] | dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        sample = json.load(f)

    if isinstance(sample, list):
        normalized: list[dict[str, Any]] = []
        for item in sample:
            if not isinstance(item, dict):
                raise ValueError("Each record in the JSON array must be an object.")
            normalized.append({key: format_sample_value(value, key) for key, value in item.items()})
        return normalized

    if not isinstance(sample, dict):
        raise ValueError("JSON input must be an object or an array of objects.")

    return {key: format_sample_value(value, key) for key, value in sample.items()}


def is_stage2_payload(sample: Any) -> bool:
    return (
        isinstance(sample, dict)
        and any(key in sample for key in ("cardiovascularRiskFactors", "targetOrganDamage", "comorbidities", "patientInfo"))
    )


def build_dataframe(sample: list[dict[str, Any]] | dict[str, Any]) -> pd.DataFrame:
    if isinstance(sample, dict):
        return pd.DataFrame([normalize_record(sample)])
    return pd.DataFrame([normalize_record(item) for item in sample])


def _build_environment_view(record: dict[str, Any]) -> dict[str, Any]:
    valid_readings = record.get("valid_readings")
    expected_readings = record.get("expected_readings")
    valid_reading_ratio = None
    if isinstance(valid_readings, (int, float)) and isinstance(expected_readings, (int, float)) and expected_readings:
        valid_reading_ratio = float(valid_readings) / float(expected_readings)

    return {
        "environments": {
            "clinic": {
                "measurement": {
                    "bp_values": {
                        "sys": record.get("clinic_sys"),
                        "dia": record.get("clinic_dia"),
                        "available": record.get("clinic_available"),
                        "status": record.get("clinic_status"),
                    },
                    "quality_clinic_minimal_inputs": {
                        "clinic_readings_count": record.get("clinic_readings_count"),
                        "clinic_missing": record.get("clinic_missing"),
                        "clinic_rest_minutes": record.get("clinic_rest_minutes"),
                    },
                },
                "quality": {
                    "score": record.get("clinic_quality_score"),
                    "level": record.get("clinic_quality_level"),
                    "flags": record.get("clinic_quality_flags", []),
                    "usable": bool(record.get("clinic_available")) and record.get("clinic_quality_level") != "low",
                },
            },
            "home": {
                "measurement": {
                    "bp_values": {
                        "sys": record.get("home_sys"),
                        "dia": record.get("home_dia"),
                        "available": record.get("home_available"),
                        "status": record.get("home_status"),
                    },
                    "temporal_coverage": {
                        "num_days": record.get("num_days"),
                        "days_with_morning": record.get("days_with_morning"),
                        "days_with_evening": record.get("days_with_evening"),
                    },
                    "within_day_pattern": {
                        "has_morning": record.get("has_morning"),
                        "has_evening": record.get("has_evening"),
                        "days_with_both_sessions": record.get("days_with_both_sessions"),
                        "pattern": record.get("pattern"),
                    },
                    "repeated_measurement_per_session": {
                        "pairs_per_session": record.get("pairs_per_session"),
                        "avg_readings_per_session": record.get("avg_readings_per_session"),
                        "pct_sessions_with_pairs": record.get("pct_sessions_with_pairs"),
                    },
                    "device_quality": {
                        "device_validated": record.get("device_validated"),
                        "device_type": record.get("device_type"),
                    },
                    "measurement_condition": {
                        "position": record.get("position"),
                        "rested_minutes": record.get("rested_minutes"),
                    },
                    "completeness": {
                        "all_readings_have_sys_dia_timestamp": record.get("all_readings_have_sys_dia_timestamp"),
                        "missing_timestamp_only": record.get("missing_timestamp_only"),
                        "missing_some_sys_or_dia": record.get("missing_some_sys_or_dia"),
                        "many_unusable_readings": record.get("many_unusable_readings"),
                    },
                    "variability": {
                        "std_sys": record.get("std_sys"),
                        "std_dia": record.get("std_dia"),
                        "range": record.get("range"),
                        "outlier": record.get("outlier"),
                    },
                },
                "quality": {
                    "score": record.get("home_quality_score"),
                    "level": record.get("home_quality_level"),
                    "flags": record.get("home_quality_flags", []),
                    "usable": record.get("home_quality_usable"),
                },
            },
            "abpm_24h": {
                "measurement": {
                    "bp_values": {
                        "sys": record.get("abpm_24h_sys"),
                        "dia": record.get("abpm_24h_dia"),
                        "available": record.get("abpm_24h_available"),
                        "status": record.get("abpm_status"),
                    },
                    "duration": {
                        "duration_hours": record.get("duration_hours"),
                    },
                    "valid_reading_ratio": {
                        "valid_readings": valid_readings,
                        "expected_readings": expected_readings,
                        "ratio": valid_reading_ratio,
                    },
                    "day_night_coverage": {
                        "has_day_data": record.get("has_day_data"),
                        "has_night_data": record.get("has_night_data"),
                    },
                    "sampling_frequency": {
                        "day_interval_minutes": record.get("day_interval_minutes"),
                        "night_interval_minutes": record.get("night_interval_minutes"),
                        "minor_deviation_from_target": record.get("minor_deviation_from_target"),
                        "major_deviation_from_target": record.get("major_deviation_from_target"),
                        "interval_unknown": record.get("interval_unknown"),
                    },
                    "completeness": {
                        "all_readings_have_sys_dia_timestamp_period": record.get("all_readings_have_sys_dia_timestamp_period"),
                        "missing_period_tag_only": record.get("missing_period_tag_only"),
                        "missing_some_sys_or_dia_or_timestamp": record.get("missing_some_sys_or_dia_or_timestamp"),
                        "many_unusable_readings": record.get("many_unusable_readings"),
                    },
                    "activity_log": {
                        "activity_log": record.get("activity_log"),
                    },
                },
                "quality": {
                    "score": record.get("abpm_quality_score"),
                    "level": record.get("abpm_quality_level"),
                    "flags": record.get("abpm_quality_flags", []),
                    "usable": record.get("abpm_quality_usable"),
                },
            },
        }
    }


def _confidence_rank(value: Any) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(str(value), 0)


def _recommendation(record: dict[str, Any], top_confidence: str) -> str:
    bp_category = record.get("bp_category")
    bp_stage = record.get("bp_stage")
    if bp_stage == "stage2":
        return "Can kham chuyen khoa som de danh gia va dieu tri tang huyet ap stage2."
    if bp_stage == "stage1":
        return "Nen tai kham som, ket hop thay doi loi song va can nhac dieu tri theo danh gia bac si."
    if bp_category == "hypertension":
        return "Nen theo doi huyet ap sat hon trong 1-2 tuan va trao doi voi bac si."
    if bp_category == "elevated":
        return "Uu tien thay doi loi song (an manh, giam muoi, tang van dong) va theo doi dinh ky."
    if top_confidence == "low":
        return "Du lieu chua du tin cay, can do lai dung quy trinh de xac nhan."
    return "Tiep tuc theo doi huyet ap dinh ky va duy tri loi song lanh manh."


def _build_explaination(record: dict[str, Any]) -> str:
    flags: list[str] = []
    flags.extend(record.get("category_flags", []) or [])
    flags.extend(record.get("stage_flags", []) or [])
    flags.extend(record.get("phenotype_flags", []) or [])
    for source_flag_key in ("clinic_quality_flags", "home_quality_flags", "abpm_quality_flags"):
        flags.extend(record.get(source_flag_key, []) or [])

    ordered: list[str] = []
    seen = set()
    for flag in flags:
        if flag in seen:
            continue
        seen.add(flag)
        ordered.append(flag)

    messages = [FLAG_EXPLANATION.get(flag) for flag in ordered if FLAG_EXPLANATION.get(flag)]
    if not messages:
        return "Ket qua duoc tong hop tu nguon do co chat luong tot nhat hien co."
    return " ".join(messages)


def _format_stage1_output(result: dict[str, Any]) -> dict[str, Any]:
    raw_records = result["patient_summary"].to_dict(orient="records")
    if not raw_records:
        return {
            "patient_id": None,
            "patient_count": 0,
            "phenotypes": result.get("phenotypes", []),
            "tha_types": result.get("tha_types", []),
            "tha_stages": result.get("tha_stages", []),
            "classification": {},
            "explaination": "Khong co du lieu benh nhan hop le.",
            "recommendation": "Can bo sung du lieu do huyet ap.",
            "confidence": "low",
            "source_used": "unknown",
            "usable": {},
            "detail": [],
        }

    record = raw_records[0]
    confidence_candidates = [
        ("category", record.get("category_confidence"), record.get("source_used_category")),
        ("stage", record.get("stage_confidence"), record.get("stage_source")),
        ("phenotype", record.get("phenotype_confidence"), record.get("phenotype_source")),
    ]
    winner = max(confidence_candidates, key=lambda item: _confidence_rank(item[1]))
    top_confidence = winner[1] or "low"
    top_source = winner[2] or "unknown"

    output = {
        "patient_id": record.get("patient_id"),
        "patient_count": result["patient_count"],
        "phenotypes": result["phenotypes"],
        "tha_types": result["tha_types"],
        "tha_stages": result["tha_stages"],
        "classification": {
            "bp_category": record.get("bp_category"),
            "source_used_category": record.get("source_used_category"),
            "source_value_used": record.get("source_value_used"),
            "category_confidence": record.get("category_confidence"),
            "category_quality_level": record.get("category_quality_level"),
            "category_flags": record.get("category_flags", []),
            "bp_stage": record.get("bp_stage"),
            "stage_source": record.get("stage_source"),
            "stage_confidence": record.get("stage_confidence"),
            "stage_quality_level": record.get("stage_quality_level"),
            "stage_flags": record.get("stage_flags", []),
            "phenotype": record.get("phenotype"),
            "phenotype_source": record.get("phenotype_source"),
            "phenotype_confidence": record.get("phenotype_confidence"),
            "phenotype_quality_level": record.get("phenotype_quality_level"),
            "phenotype_flags": record.get("phenotype_flags", []),
        },
        "explaination": _build_explaination(record),
        "recommendation": _recommendation(record, top_confidence),
        "confidence": top_confidence,
        "source_used": top_source,
        "usable": {
            "clinic": bool(record.get("clinic_available")) and record.get("clinic_quality_level") != "low",
            "home": bool(record.get("home_available")) and record.get("home_quality_level") != "low",
            "abpm_24h": bool(record.get("abpm_24h_available")) and record.get("abpm_quality_level") != "low",
            "bp_category": record.get("bp_category") != "unknown",
            "bp_stage": record.get("bp_stage") not in {"unknown", "none"},
            "phenotype": record.get("phenotype") != "unknown",
        },
        "detail": [_build_environment_view(record)],
    }
    return output


def run_stage1(sample: list[dict[str, Any]] | dict[str, Any]) -> None:
    df = build_dataframe(sample)
    result = run_symbolic_pipeline(df)
    output = _format_stage1_output(result)
    print(json.dumps(output, default=str, indent=2, ensure_ascii=False))


def run_stage2(sample: dict[str, Any]) -> None:
    result = run_stage2_assessment(sample)
    print(json.dumps(result, default=str, indent=2, ensure_ascii=False))


def main() -> None:
    json_path = Path(sys.argv[1])
    stage = sys.argv[2]
    sample = load_sample_from_json(json_path)

    if stage == "stage2" or (stage == "stage1" and is_stage2_payload(sample)):
        if not isinstance(sample, dict):
            raise ValueError("Stage 2 input must be a JSON object.")
        run_stage2(sample)
        return

    run_stage1(sample)


if __name__ == "__main__":
    main()
PY
