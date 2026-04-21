from __future__ import annotations

from typing import Any

def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "y"}
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return False


def _normalize_bp_stage(bp_stage: str | None) -> str:
    if not bp_stage:
        return "unknown"
    normalized = bp_stage.strip().lower()
    if normalized in {"stage1", "stage_1", "tha do i", "tha do 1", "stage i", "i", "1"}:
        return "stage1"
    if normalized in {"stage2", "stage_2", "tha do ii", "tha do 2", "stage ii", "ii", "2"}:
        return "stage2"
    if normalized in {"prehypertension_120_129_70_79", "120-129/70-79", "120-129_70-79", "120_129_70_79"}:
        return "prehypertension_120_129_70_79"
    if normalized in {
        "prehypertension_130_139_80_89",
        "prehypertension",
        "130-139/80-89",
        "130-139_80-89",
        "130_139_80_89",
        "tien_tha",
        "tien-tha",
        "pre-tha",
    }:
        return "prehypertension_130_139_80_89"
    return "unknown"


def _count_non_special_risk_factors(risk_factors: dict[str, Any]) -> int:
    fields = [
        "ageOver65",
        "male",
        "heartRateOver80",
        "overweight",
        "highLDLOrTriglyceride",
        "familyHistoryOfHypertension",
        "earlyMenopause",
        "smoking",
        "environmentalSocioeconomicFactors",
        "menopause",
        "sedentaryLifestyle",
    ]
    return sum(_normalize_bool(risk_factors.get(field, False)) for field in fields)


def _bp_stage_label(bp_stage: str) -> str:
    labels = {
        "prehypertension_120_129_70_79": "prehypertension 120-129/70-79",
        "prehypertension_130_139_80_89": "prehypertension 130-139/80-89",
        "stage1": "hypertension stage 1",
        "stage2": "hypertension stage 2",
        "unknown": "unknown blood pressure stage",
    }
    return labels.get(bp_stage, bp_stage)


def build_explanation(processed_data: dict[str, Any], risk_level: str) -> str:
    """Build rule-based explanation aligned with classify_risk_level."""
    risk_factors = processed_data.get("riskFactors", {}) or {}
    special = processed_data.get("special", {}) or {}
    hmod = processed_data.get("hmod", {}) or {}
    cardiovascular_disease = processed_data.get("cardiovascularDisease", {}) or {}
    bp_stage = _normalize_bp_stage(processed_data.get("bp_stage"))

    non_special_count = _count_non_special_risk_factors(risk_factors)
    has_diabetes = _normalize_bool(risk_factors.get("diabetes", False)) or _normalize_bool(special.get("diabetes", False))
    has_fh = _normalize_bool(risk_factors.get("familialHypercholesterolemia", False)) or _normalize_bool(
        special.get("familialHypercholesterolemia", False)
    )
    has_ckd_stage3 = _normalize_bool(hmod.get("ckdStage3", False))
    has_any_hmod = any(_normalize_bool(value) for value in hmod.values())
    cvd_count = sum(_normalize_bool(value) for value in cardiovascular_disease.values())

    if cvd_count >= 1:
        return (
            f"Rule 3 applied: at least one cardiovascular disease condition is present (count={cvd_count}). "
            f"Blood pressure stage is {_bp_stage_label(bp_stage)}; therefore risk level is {risk_level}."
        )

    if non_special_count >= 3 or has_diabetes or has_fh or has_ckd_stage3 or has_any_hmod:
        reasons: list[str] = []
        if non_special_count >= 3:
            reasons.append(f"{non_special_count} non-special risk factors (>=3)")
        if has_diabetes:
            reasons.append("diabetes")
        if has_fh:
            reasons.append("familial hypercholesterolemia")
        if has_ckd_stage3:
            reasons.append("CKD stage 3")
        if has_any_hmod:
            reasons.append("at least one HMOD")
        return (
            f"Rule 2 applied: {', '.join(reasons)} detected. "
            f"Blood pressure stage is {_bp_stage_label(bp_stage)}; therefore risk level is {risk_level}."
        )

    if 1 <= non_special_count <= 2:
        return (
            "Rule 1 applied: "
            f"{non_special_count} non-special risk factor(s) detected (excluding diabetes and familial hypercholesterolemia). "
            f"Blood pressure stage is {_bp_stage_label(bp_stage)}; therefore risk level is {risk_level}."
        )

    return (
        "No explicit rule trigger found from provided fields; "
        f"blood pressure stage is {_bp_stage_label(bp_stage)} and risk level is {risk_level}."
    )
