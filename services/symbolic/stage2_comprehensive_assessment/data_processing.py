from __future__ import annotations

from typing import Any

from .constants import BP_STAGE_KEYS


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


def _normalize_age_over_65(payload: dict[str, Any], risk_factors: dict[str, Any]) -> dict[str, bool]:
    age = payload.get("patientInfo", {}).get("age")
    normalized = dict(risk_factors)

    if isinstance(age, (int, float)):
        normalized["ageOver65"] = age >= 65
    else:
        age_value = payload.get("patientInfo", {}).get("age")
        try:
            if age_value is not None:
                normalized["ageOver65"] = float(age_value) >= 65
        except (TypeError, ValueError):
            normalized["ageOver65"] = _normalize_bool(risk_factors.get("ageOver65", False))

    return normalized


def _bp_stage_from_payload(payload: dict[str, Any]) -> str | None:
    for key in BP_STAGE_KEYS:
        stage = payload.get(key)
        if stage is not None:
            return str(stage).lower()
    return None


def _pick_first_dict(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _pick_first_value(container: dict[str, Any], keys: list[str], default: Any = False) -> Any:
    for key in keys:
        if key in container:
            return container[key]
    return default


def process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Process and normalize the input payload for risk assessment.
    - Special
    - Risk factors
    - HMOD
    - Cardiovascular disease
    
    """
    special_block = _pick_first_dict(payload, ["special", "Special", "dacBiet", "riskSpecial"])
    risk_factor_block = _pick_first_dict(
        payload,
        ["ytnc", "YTNC", "riskFactors", "cardiovascularRiskFactors", "yeuToNguyCo"],
    )
    hmod_block = _pick_first_dict(payload, ["hmod", "HMOD", "targetOrganDamage", "tonThuongCoQuan"])
    cvd_block = _pick_first_dict(payload, ["cardiovascularDisease", "cvd", "benhTimMach"])

    special = {
        "diabetes": _normalize_bool(
            _pick_first_value(special_block, ["diabetes", "dtđ", "dtd", "daiThaoDuong"], False)
        ),
        "familialHypercholesterolemia": _normalize_bool(
            _pick_first_value(
                special_block,
                ["familialHypercholesterolemia", "fh", "familyHypercholesterolemia"],
                False,
            )
        ),
    }

    risk_factors = {
        "ageOver65": False,
        "male": _normalize_bool(_pick_first_value(risk_factor_block, ["male", "gioiTinhNam", "nam"], False)),
        "heartRateOver80": _normalize_bool(
            _pick_first_value(risk_factor_block, ["heartRateOver80", "nhipTimOver80", "tanSoTimOver80"], False)
        ),
        "overweight": _normalize_bool(_pick_first_value(risk_factor_block, ["overweight", "thuaCan"], False)),
        "diabetes": _normalize_bool(
            _pick_first_value(
                risk_factor_block,
                ["diabetes", "daiThaoDuong"],
                special["diabetes"],
            )
        ),
        "highLDLOrTriglyceride": _normalize_bool(
            _pick_first_value(
                risk_factor_block,
                ["highLDLOrTriglyceride", "tangLDLOrTriglyceride", "dyslipidemia"],
                False,
            )
        ),
        "familialHypercholesterolemia": _normalize_bool(
            _pick_first_value(
                risk_factor_block,
                ["familialHypercholesterolemia", "fh"],
                special["familialHypercholesterolemia"],
            )
        ),
        "familyHistoryOfHypertension": _normalize_bool(
            _pick_first_value(risk_factor_block, ["familyHistoryOfHypertension", "familyHypertension", "tienSuGiaDinhTHA"], False)
        ),
        "earlyMenopause": _normalize_bool(_pick_first_value(risk_factor_block, ["earlyMenopause", "manKinhSom"], False)),
        "smoking": _normalize_bool(_pick_first_value(risk_factor_block, ["smoking", "hutThuocLa"], False)),
        "environmentalSocioeconomicFactors": _normalize_bool(
            _pick_first_value(risk_factor_block, ["environmentalSocioeconomicFactors", "environmentSocioeconomicFactors", "yeuToMoiTruongXaHoi"], False)
        ),
        "menopause": _normalize_bool(_pick_first_value(risk_factor_block, ["menopause", "manKinh"], False)),
        "sedentaryLifestyle": _normalize_bool(
            _pick_first_value(risk_factor_block, ["sedentaryLifestyle", "itVanDong", "loiSongTinhTai"], False)
        ),
    }
    risk_factors = _normalize_age_over_65(payload, risk_factors)
    if "ageOver65" in risk_factor_block:
        risk_factors["ageOver65"] = _normalize_bool(risk_factor_block.get("ageOver65"))

    hmod = {
        "leftVentricularHypertrophy": _normalize_bool(
            _pick_first_value(hmod_block, ["leftVentricularHypertrophy", "dayThatTrai"], False)
        ),
        "brainDamage": _normalize_bool(_pick_first_value(hmod_block, ["brainDamage", "tonThuongNao"], False)),
        "heartDamage": _normalize_bool(_pick_first_value(hmod_block, ["heartDamage", "tonThuongTim"], False)),
        "kidneyDamage": _normalize_bool(_pick_first_value(hmod_block, ["kidneyDamage", "tonThuongThan"], False)),
        "vascularDamage": _normalize_bool(_pick_first_value(hmod_block, ["vascularDamage", "tonThuongMachMau"], False)),
        "ckdStage3": _normalize_bool(_pick_first_value(hmod_block, ["ckdStage3", "ckdIII"], False)),
        "pulsePressureOver60": _normalize_bool(_pick_first_value(hmod_block, ["pulsePressureOver60", "hieuApOver60"], False)),
    }

    cardiovascular_disease = {
        "coronaryArteryDisease": _normalize_bool(_pick_first_value(cvd_block, ["coronaryArteryDisease", "benhMachVanh"], False)),
        "heartFailure": _normalize_bool(_pick_first_value(cvd_block, ["heartFailure", "suyTim"], False)),
        "stroke": _normalize_bool(_pick_first_value(cvd_block, ["stroke", "dotQuy"], False)),
        "peripheralVascularDisease": _normalize_bool(
            _pick_first_value(cvd_block, ["peripheralVascularDisease", "benhMachMauNgoaiBien"], False)
        ),
        "atrialFibrillation": _normalize_bool(_pick_first_value(cvd_block, ["atrialFibrillation", "rungNhi"], False)),
        "ckdStage4": _normalize_bool(_pick_first_value(cvd_block, ["ckdStage4", "ckdStageIV"], False)),
        "ckdStage5": _normalize_bool(_pick_first_value(cvd_block, ["ckdStage5", "ckdStageV"], False)),
    }

    # Mirror CKD IV-V aliases into canonical stage4/5 fields
    cardiovascular_disease["ckdStage4"] = cardiovascular_disease["ckdStage4"] or _normalize_bool(
        _pick_first_value(cvd_block, ["ckdStageIV"], False)
    )
    cardiovascular_disease["ckdStage5"] = cardiovascular_disease["ckdStage5"] or _normalize_bool(
        _pick_first_value(cvd_block, ["ckdStageV"], False)
    )

    bp_stage = _bp_stage_from_payload(payload)

    return {
        "special": special,
        "riskFactors": risk_factors,
        "hmod": hmod,
        "cardiovascularDisease": cardiovascular_disease,
        "bp_stage": bp_stage,
        "has_any_data": any(special.values()) or any(risk_factors.values()) or any(hmod.values()) or any(cardiovascular_disease.values()),
    }
