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
    if normalized in {
        "prehypertension_120_129_70_79",
        "120-129/70-79",
        "120-129_70-79",
        "120_129_70_79",
    }:
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

    if "120-129" in normalized and "70-79" in normalized:
        return "prehypertension_120_129_70_79"
    if "130-139" in normalized and "80-89" in normalized:
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


def classify_risk_level(processed_data: dict[str, Any]) -> str:
    """Classify risk level according to custom clinical rules."""
    risk_factors = processed_data.get("riskFactors", {}) or {}
    special = processed_data.get("special", {}) or {}
    hmod = processed_data.get("hmod", {}) or {}
    cardiovascular_disease = processed_data.get("cardiovascularDisease", {}) or {}
    bp_stage = _normalize_bp_stage(processed_data.get("bp_stage"))

    non_special_risk_count = _count_non_special_risk_factors(risk_factors)
    has_diabetes = _normalize_bool(risk_factors.get("diabetes", False)) or _normalize_bool(special.get("diabetes", False))
    has_fh = _normalize_bool(risk_factors.get("familialHypercholesterolemia", False)) or _normalize_bool(
        special.get("familialHypercholesterolemia", False)
    )
    has_ckd_stage3 = _normalize_bool(hmod.get("ckdStage3", False))
    has_any_hmod = any(_normalize_bool(value) for value in hmod.values())
    cardiovascular_disease_count = sum(_normalize_bool(value) for value in cardiovascular_disease.values())

    # Rule 3
    if cardiovascular_disease_count >= 1:
        if bp_stage == "prehypertension_120_129_70_79":
            return "medium"
        return "high"

    # Rule 2
    if non_special_risk_count >= 3 or has_diabetes or has_fh or has_ckd_stage3 or has_any_hmod:
        if bp_stage == "prehypertension_120_129_70_79":
            return "low"
        if bp_stage == "prehypertension_130_139_80_89":
            return "medium"
        if bp_stage in {"stage1", "stage2"}:
            return "high"
        return "medium"

    # Rule 1
    if 1 <= non_special_risk_count <= 2:
        if bp_stage in {"prehypertension_120_129_70_79", "prehypertension_130_139_80_89"}:
            return "low"
        if bp_stage in {"stage1", "stage2"}:
            return "high"
        return "low"

    if bp_stage in {"stage1", "stage2"}:
        return "high"
    return "low"
