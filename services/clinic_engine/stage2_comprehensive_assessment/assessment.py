import json
from pathlib import Path
from typing import Any, Union

from .confidence_calculator import calculate_confidence
from .data_processing import process_payload
from .explanation_builder import build_explanation
from .recommendation_builder import build_recommendation
from .risk_classification import classify_risk_level


def load_patient_input(path: Union[Path, str]) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Stage 2 input JSON must produce a mapping at the top level.")
    return payload


def run_stage2_assessment(path: Union[Path, str, dict[str, Any]]) -> dict[str, Any]:
    if isinstance(path, dict):
        payload = path
    else:
        payload = load_patient_input(path)

    # Process and normalize the payload
    processed_data = process_payload(payload)

    # Classify risk level
    risk_level = classify_risk_level(processed_data)

    # Build explanation
    explanation = build_explanation(processed_data, risk_level)

    # Build recommendation
    recommendation = build_recommendation(risk_level, processed_data["bp_stage"])

    # Calculate confidence
    confidence = calculate_confidence(risk_level, processed_data)

    return {
        "risk_level": risk_level,
        "recommendation": recommendation,
        "explanation": explanation,
        "confidence": confidence,
    }
