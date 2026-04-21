from __future__ import annotations

def _normalize_bp_stage(bp_stage: str | None) -> str:
    if not bp_stage:
        return "unknown"
    normalized = bp_stage.strip().lower()
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
    if normalized in {"stage1", "stage_1", "tha do i", "tha do 1", "stage i", "i", "1"}:
        return "stage1"
    if normalized in {"stage2", "stage_2", "tha do ii", "tha do 2", "stage ii", "ii", "2"}:
        return "stage2"
    return "unknown"


def build_recommendation(risk_level: str, bp_stage: str | None) -> str:
    """Build recommendation from risk level and blood-pressure stage."""
    normalized_stage = _normalize_bp_stage(bp_stage)
    prehypertension_group = normalized_stage in {"prehypertension_120_129_70_79", "prehypertension_130_139_80_89"}

    if risk_level == "high":
        recommendation = (
            "Nguy co cao (>10%): can thay doi loi song (TDLS) ket hop dieu tri thuoc ha ap ngay, "
            "theo doi sat va tai kham som."
        )
    elif risk_level == "medium":
        recommendation = (
            "Nguy co trung binh (5-10%): uu tien TDLS, theo doi trong 6 thang; "
            "neu chua dat muc tieu huyet ap thi can nhac bat dau dieu tri thuoc."
        )
    else:
        recommendation = (
            "Nguy co thap (<5%): uu tien TDLS va theo doi dinh ky; chua can dieu tri thuoc ngay."
        )

    if prehypertension_group:
        recommendation += " O nhom tien THA, neu TDLS khong dat dich thi chi dinh dieu tri thuoc."

    return recommendation
