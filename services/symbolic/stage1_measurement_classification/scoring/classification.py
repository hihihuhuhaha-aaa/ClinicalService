from __future__ import annotations

"""Blood pressure classification utilities.

This module implements the symbolic logic for blood pressure category, stage,
phenotype, and THA type classification using the rulebook thresholds and
condition evaluation engine.
"""

import math
from typing import Any

from ..rules.rulebook import RULEBOOK
from ..rules.rule_config import ThresholdRule
from ..rules.rule_eval import evaluate_condition


def _is_missing(value: float | None) -> bool:
    """Return True when a numeric blood pressure value is missing or NaN."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def classify_tha_stage(systolic: float | None, diastolic: float | None) -> str:
    """Classify clinic blood pressure stage according to THA staging rules.

    The returned stage is one of: hypertensive_crisis, stage_2, stage_1,
    elevated, normal, or unknown when clinic measurement is missing.
    """
    if _is_missing(systolic) or _is_missing(diastolic):
        return "unknown"
    if systolic >= 180 or diastolic >= 120:
        return "hypertensive_crisis"
    if systolic >= 160 or diastolic >= 100:
        return "stage_2"
    if systolic >= 140 or diastolic >= 90:
        return "stage_1"
    if systolic >= 120 or diastolic >= 70:
        return "elevated"
    return "normal"


def classify_hypertension_phenotype(clinic_sys: float | None, clinic_dia: float | None, home_sys: float | None, home_dia: float | None) -> str:
    """Classify hypertension phenotype using clinic and home measurements.

    Phenotypes include white_coat_hypertension, masked_hypertension,
    sustained_hypertension, prehypertension, normal, or unknown.
    """
    if _is_missing(clinic_sys) or _is_missing(clinic_dia) or _is_missing(home_sys) or _is_missing(home_dia):
        return "unknown"

    clinic_high = clinic_sys >= 140 or clinic_dia >= 90
    home_high = home_sys >= 135 or home_dia >= 85

    if clinic_high and not home_high:
        return "white_coat_hypertension"
    if not clinic_high and home_high:
        return "masked_hypertension"
    if clinic_high and home_high:
        return "sustained_hypertension"
    if 120 <= clinic_sys < 140 or 70 <= clinic_dia < 90:
        return "prehypertension"
    return "normal"


def classify_abpm_pattern(abpm_day_sys: float | None, abpm_night_sys: float | None) -> str:
    """Classify ABPM dipping pattern from daytime and nighttime systolic values.

    Returned values are: extreme_dipper, dipper, non_dipper, reverse_dipper,
    or unknown if the input is invalid.
    """
    if _is_missing(abpm_day_sys) or _is_missing(abpm_night_sys):
        return "unknown"
    if abpm_day_sys <= 0:
        return "unknown"

    dip_pct = (abpm_day_sys - abpm_night_sys) / abpm_day_sys * 100
    if dip_pct > 20:
        return "extreme_dipper"
    if 10 <= dip_pct <= 20:
        return "dipper"
    if dip_pct >= 0:
        return "non_dipper"
    return "reverse_dipper"


def classify_tha_type(
    clinic_sys: float | None,
    clinic_dia: float | None,
    home_sys: float | None,
    home_dia: float | None,
    abpm_sys: float | None = None,
    abpm_dia: float | None = None,
) -> str:
    """Classify the THA hypertension type across clinic, home, and ABPM.

    The THA type is derived from a hierarchy of conditions such as:
    - tha_cap
    - tha_ao_choang_trang
    - tha_an_giau
    - tha_duy_tri
    - tien_tha
    - tha_k_tang
    - unknown
    """
    if _is_missing(clinic_sys) or _is_missing(clinic_dia):
        return "unknown"

    home_missing = _is_missing(home_sys) or _is_missing(home_dia)
    abpm_missing = _is_missing(abpm_sys) or _is_missing(abpm_dia)

    clinic_high = clinic_sys >= 140 or clinic_dia >= 90
    home_high = False if home_missing else (home_sys >= 135 or home_dia >= 85)
    abpm_high = False if abpm_missing else (abpm_sys >= 130 or abpm_dia >= 80)

    if clinic_sys >= 180 or clinic_dia >= 120:
        return "tha_cap"
    if clinic_high and not home_missing and not abpm_missing and not home_high and not abpm_high:
        return "tha_ao_choang_trang"
    if not clinic_high and (home_high or abpm_high):
        return "tha_an_giau"
    if clinic_high and home_high:
        return "tha_duy_tri"
    if 120 <= clinic_sys < 140 or 80 <= clinic_dia < 90:
        return "tien_tha"
    if not clinic_high and not home_missing and not abpm_missing and not home_high and not abpm_high:
        return "tha_k_tang"
    return "unknown"


def _get_thresholds(source_key: str) -> ThresholdRule | None:
    return RULEBOOK.common_rules.thresholds.get(source_key)


def _match_threshold(sys_value: float | None, dia_value: float | None, threshold: ThresholdRule) -> bool:
    if _is_missing(sys_value) or _is_missing(dia_value):
        return False
    if threshold.sys_lt is not None and not (sys_value < threshold.sys_lt):
        return False
    if threshold.dia_lt is not None and not (dia_value < threshold.dia_lt):
        return False
    if threshold.sys_ge is not None and not (sys_value >= threshold.sys_ge):
        return False
    if threshold.dia_ge is not None and not (dia_value >= threshold.dia_ge):
        return False
    if threshold.sys_range is not None:
        lower, upper = threshold.sys_range
        if not (lower <= sys_value <= upper):
            return False
    if threshold.dia_range is not None:
        lower, upper = threshold.dia_range
        if not (lower <= dia_value <= upper):
            return False
    return True


def _classify_source(source_key: str, sys_value: float | None, dia_value: float | None) -> str:
    thresholds = _get_thresholds(source_key)
    if thresholds is None:
        return "unknown"
    if _match_threshold(sys_value, dia_value, thresholds.hypertension):
        return "hypertension"
    if _match_threshold(sys_value, dia_value, thresholds.elevated):
        return "elevated"
    if _match_threshold(sys_value, dia_value, thresholds.normal):
        return "normal"
    return "unknown"


def _classify_clinic_stage(clinic_sys: float | None, clinic_dia: float | None) -> str:
    thresholds = _get_thresholds("clinic")
    if thresholds is None or thresholds.stage is None:
        return "unknown"
    if _match_threshold(clinic_sys, clinic_dia, thresholds.stage.get("stage2", ThresholdRule())):
        return "stage2"
    if _match_threshold(clinic_sys, clinic_dia, thresholds.stage.get("stage1", ThresholdRule())):
        return "stage1"
    return "unknown"


def _detect_borderline(metric_value: float | None, thresholds: ThresholdRule) -> bool:
    """
    Phát hiện giá trị "borderline" = gần mốc ngưỡng trong vòng 5 mmHg
    
    Ví dụ:
    - Mốc hypertension = 140 systolic
    - Nếu giá trị = 137.5 → cách mốc 2.5 mmHg → BORDERLINE
    - Nếu giá trị = 125 → cách mốc 15 mmHg → KHÔNG borderline
    
    Công thức: abs(giá_trị - mốc) <= 5 mmHg
    """
    if _is_missing(metric_value):
        return False
    
    # Kiểm tra với mốc sys_ge (systolic >= ngưỡng)
    # VD: mốc hypertension = 140, nếu 137-142 → borderline
    if thresholds.sys_ge is not None and abs(metric_value - thresholds.sys_ge) <= 5:
        return True
    
    # Kiểm tra với mốc dia_ge (diastolic >= ngưỡng)
    if thresholds.dia_ge is not None and abs(metric_value - thresholds.dia_ge) <= 5:
        return True
    
    # Kiểm tra với mốc sys_lt (systolic < ngưỡng trên)
    if thresholds.sys_lt is not None and abs(metric_value - thresholds.sys_lt) <= 5:
        return True
    
    # Kiểm tra với mốc dia_lt (diastolic < ngưỡng trên)
    if thresholds.dia_lt is not None and abs(metric_value - thresholds.dia_lt) <= 5:
        return True
    
    # Kiểm tra với phạm vi systolic
    if thresholds.sys_range is not None:
        return abs(metric_value - thresholds.sys_range[0]) <= 5 or abs(metric_value - thresholds.sys_range[1]) <= 5
    
    # Kiểm tra với phạm vi diastolic
    if thresholds.dia_range is not None:
        return abs(metric_value - thresholds.dia_range[0]) <= 5 or abs(metric_value - thresholds.dia_range[1]) <= 5
    
    return False


def _get_category_threshold(source: str, category: str) -> ThresholdRule | None:
    thresholds = _get_thresholds(source)
    if thresholds is None:
        return None
    if category == "hypertension":
        return thresholds.hypertension
    if category == "elevated":
        return thresholds.elevated
    if category == "normal":
        return thresholds.normal
    return thresholds.normal


def _get_stage_threshold(source: str, stage: str) -> ThresholdRule | None:
    thresholds = _get_thresholds(source)
    if thresholds is None or thresholds.stage is None:
        return None
    return thresholds.stage.get(stage)


def _quality_level_for_source(source: str, metrics: dict[str, Any]) -> Any:
    if source == "abpm_24h":
        return metrics.get("abpm_quality_level")
    return metrics.get(f"{source}_quality_level")


def _confidence_for_source(source: str, metrics: dict[str, Any], category: str, threshold_kind: str | None = None) -> tuple[str, list[str]]:
    """
    Tính độ tin cậy (confidence) của phân loại dựa trên:
    1. Chất lượng dữ liệu (quality_level)
    2. Giá trị có gần mốc ngưỡng không (borderline)
    
    Ví dụ: Dữ liệu quality=high nhưng borderline → confidence giảm từ high → medium
    """
    # BƯỚC 1: Lấy chất lượng dữ liệu từ source (home, clinic, hoặc abpm)
    # quality_level = "low", "medium", hoặc "high"
    quality_level = _quality_level_for_source(source, metrics)
    
    # BƯỚC 2: Ban đầu, confidence = quality_level
    # Ý tưởng: Dữ liệu tốt → kết luận tin cậy hơn
    confidences = ["low", "medium", "high"]
    confidence = quality_level if quality_level in confidences else "medium"

    flags: list[str] = []
    
    # BƯỚC 3: Nếu phân loại không xác định → confidence PHẢI là "low"
    # Vì không thể tin vào kết luận "unknown"
    if category == "unknown":
        confidence = "low"
        flags.append("unknown_source")

    # BƯỚC 4: Lấy quy tắc ngưỡng để kiểm tra borderline
    # threshold_rules = các mốc systolic/diastolic (VD: 140/90 cho hypertension)
    threshold_rules: ThresholdRule | None = None
    if threshold_kind == "stage":
        threshold_rules = _get_stage_threshold(source, metrics.get("bp_stage", ""))
    elif threshold_kind is not None:
        threshold_rules = _get_stage_threshold(source, threshold_kind)
    else:
        threshold_rules = _get_category_threshold(source, category)

    # BƯỚC 5: KIỂM TRA BORDERLINE - Đây là phần quan trọng nhất!
    # "Borderline" = giá trị gần mốc ngưỡng (trong vòng 5 mmHg)
    # Nếu borderline → GIẢM confidence xuống 1 mức
    if threshold_rules is not None:
        if _detect_borderline(metrics.get(f"{source}_sys"), threshold_rules) or _detect_borderline(metrics.get(f"{source}_dia"), threshold_rules):
            # Giảm confidence: high → medium → low
            if confidence == "high":
                confidence = "medium"  # High confidence giảm xuống medium vì borderline
            elif confidence == "medium":
                confidence = "low"  # Medium confidence giảm xuống low vì borderline
            flags.append("borderline")

    # BƯỚC 6: Nếu chất lượng kém + kết luận khác "unknown" → thêm flag "quality_low"
    if quality_level == "low" and category != "unknown":
        flags.append("quality_low")

    return confidence, flags


def _pick_category_source(metrics: dict[str, Any]) -> dict[str, str]:
    policy = RULEBOOK.step1_bp_category["logic"]["step_1_select_source"]["selection_policy"]
    for entry in policy:
        if_clause = entry.get("if")
        elif_clause = entry.get("elif")
        selected_source = entry.get("selected_source")
        if if_clause and evaluate_condition(if_clause, metrics):
            return {"source_used": selected_source}
        if elif_clause and evaluate_condition(elif_clause, metrics):
            return {"source_used": selected_source}
    return {"source_used": "unknown"}


def _category_from_metric(metric_name: str, metrics: dict[str, Any]) -> str:
    if_selected = RULEBOOK.step1_bp_category["logic"]["step_2_apply_thresholds"][f"if_selected_source_{metric_name}"]
    for category in ["hypertension", "elevated", "normal"]:
        condition = if_selected[category]
        if evaluate_condition(condition, metrics):
            return category
    return "unknown"


def _choose_category_from_source(selected_source: str, metrics: dict[str, Any]) -> str:
    if selected_source == "abpm_24h":
        return _category_from_metric("abpm_24h", metrics)
    if selected_source == "home":
        return _category_from_metric("home", metrics)
    if selected_source == "clinic":
        return _category_from_metric("clinic", metrics)
    return "unknown"


def _build_source_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "clinic_status": _classify_source("clinic", metrics.get("clinic_sys"), metrics.get("clinic_dia")),
        "home_status": _classify_source("home", metrics.get("home_sys"), metrics.get("home_dia")),
        "abpm_status": _classify_source("abpm_24h", metrics.get("abpm_24h_sys"), metrics.get("abpm_24h_dia")),
    }


def _source_available(value: float | None) -> bool:
    return value is not None


def classify_bp_category(metrics: dict[str, Any]) -> dict[str, Any]:
    context = {
        "abpm_24h_available": _source_available(metrics.get("abpm_24h_sys")) and _source_available(metrics.get("abpm_24h_dia")),
        "home_available": _source_available(metrics.get("home_sys")) and _source_available(metrics.get("home_dia")),
        "clinic_available": _source_available(metrics.get("clinic_sys")) and _source_available(metrics.get("clinic_dia")),
        "abpm_quality_level": metrics.get("abpm_quality_level"),
        "home_quality_level": metrics.get("home_quality_level"),
        "clinic_quality_level": metrics.get("clinic_quality_level"),
        "clinic_sys": metrics.get("clinic_sys"),
        "clinic_dia": metrics.get("clinic_dia"),
        "home_sys": metrics.get("home_sys"),
        "home_dia": metrics.get("home_dia"),
        "abpm_sys": metrics.get("abpm_24h_sys"),
        "abpm_dia": metrics.get("abpm_24h_dia"),
    }
    context.update(metrics)
    selected = _pick_category_source(context)["source_used"]
    category = _choose_category_from_source(selected, context)
    quality_level = _quality_level_for_source(selected, context)
    confidence, flags = _confidence_for_source(selected, context, category)

    if selected == "clinic":
        source_value = f"{context.get('clinic_sys')} / {context.get('clinic_dia')}"
    elif selected == "home":
        source_value = f"{context.get('home_sys')} / {context.get('home_dia')}"
    elif selected == "abpm_24h":
        source_value = f"{context.get('abpm_sys')} / {context.get('abpm_dia')}"
    else:
        source_value = None

    return {
        "bp_category": category,
        "source_used_category": selected,
        "source_value_used": source_value,
        "category_confidence": confidence,
        "category_quality_level": quality_level,
        "category_flags": flags,
    }


def classify_bp_stage(metrics: dict[str, Any], bp_category: str) -> dict[str, Any]:
    if bp_category != "hypertension":
        return {
            "bp_stage": "none",
            "stage_source": "clinic",
            "stage_confidence": "low",
            "stage_quality_level": metrics.get("clinic_quality_level"),
            "stage_flags": ["not_hypertension"],
        }
    if not _source_available(metrics.get("clinic_sys")) or not _source_available(metrics.get("clinic_dia")):
        return {
            "bp_stage": "unknown",
            "stage_source": "clinic",
            "stage_confidence": "low",
            "stage_quality_level": metrics.get("clinic_quality_level"),
            "stage_flags": ["missing_clinic"],
        }
    stage = _classify_clinic_stage(metrics.get("clinic_sys"), metrics.get("clinic_dia"))
    confidence, flags = _confidence_for_source("clinic", metrics, stage, threshold_kind="stage")
    return {
        "bp_stage": stage,
        "stage_source": "clinic",
        "stage_confidence": confidence,
        "stage_quality_level": metrics.get("clinic_quality_level"),
        "stage_flags": flags,
    }


def classify_phenotype(metrics: dict[str, Any]) -> dict[str, Any]:
    context = metrics.copy()
    clinic_high = False
    if _source_available(context.get("clinic_sys")) and _source_available(context.get("clinic_dia")):
        clinic_high = context["clinic_sys"] >= 140 or context["clinic_dia"] >= 90
    context["clinic_high"] = clinic_high
    context["home_available"] = _source_available(context.get("home_sys")) and _source_available(context.get("home_dia"))
    context["abpm_24h_available"] = _source_available(context.get("abpm_24h_sys")) and _source_available(context.get("abpm_24h_dia"))
    context["home_high"] = context["home_available"] and (context["home_sys"] >= 135 or context["home_dia"] >= 85)
    context["abpm_high"] = context["abpm_24h_available"] and (context["abpm_24h_sys"] >= 130 or context["abpm_24h_dia"] >= 80)

    rules = RULEBOOK.step3_phenotype["logic"]["step_2_select_out_of_office_source"]["rules"]
    selected_out_source = "unknown"
    for entry in rules:
        if_clause = entry.get("if")
        elif_clause = entry.get("elif")
        if if_clause and evaluate_condition(if_clause, context):
            selected_out_source = entry.get("out_source", "unknown")
            break
        if elif_clause and evaluate_condition(elif_clause, context):
            selected_out_source = entry.get("out_source", "unknown")
            break

    out_high = False
    if selected_out_source == "abpm_24h":
        out_high = context.get("abpm_24h_sys", 0) >= 130 or context.get("abpm_24h_dia", 0) >= 80
    elif selected_out_source == "home":
        out_high = context.get("home_sys", 0) >= 135 or context.get("home_dia", 0) >= 85

    if not _source_available(context.get("clinic_sys")) or not _source_available(context.get("clinic_dia")):
        return {
            "phenotype": "unknown",
            "phenotype_source": selected_out_source,
            "phenotype_confidence": "low",
            "phenotype_quality_level": _quality_level_for_source(selected_out_source, context),
            "phenotype_flags": ["missing_clinic"],
        }
    if selected_out_source == "unknown":
        return {
            "phenotype": "unknown",
            "phenotype_source": "unknown",
            "phenotype_confidence": "low",
            "phenotype_quality_level": None,
            "phenotype_flags": ["missing_out_of_office"],
        }
    if clinic_high and not out_high:
        phenotype = "white_coat"
    elif not clinic_high and out_high:
        phenotype = "masked"
    else:
        phenotype = "none"
    confidence, flags = _confidence_for_source(selected_out_source, context, phenotype)
    return {
        "phenotype": phenotype,
        "phenotype_source": selected_out_source,
        "phenotype_confidence": confidence,
        "phenotype_quality_level": _quality_level_for_source(selected_out_source, context),
        "phenotype_flags": flags,
    }
