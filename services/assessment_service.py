"""Assessment service — orchestrates clinic engine + persistence for Stage 1 & 2."""
from __future__ import annotations

from typing import Any

import pandas as pd

from observability import span
from repositories import AssessmentRepository
from services.clinic_engine import run_stage2_assessment, run_symbolic_pipeline


def _serialize_result(obj: Any) -> Any:
    """Recursively convert DataFrames/numpy scalars so they are JSON-safe."""
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: _serialize_result(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_result(v) for v in obj]
    try:
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
    except ImportError:
        pass
    return obj


class AssessmentService:
    def __init__(self, repo: AssessmentRepository) -> None:
        self._repo = repo

    async def run_stage1(self, readings: list[dict[str, Any]]) -> dict[str, Any]:
        with span(
            "assessment.stage1",
            as_type="chain",
            input={"readings": readings},
            metadata={"stage": 1},
        ) as root:
            with span("stage1.symbolic_pipeline", input={"readings": readings}) as s:
                df = pd.DataFrame(readings)
                result = run_symbolic_pipeline(df)
                serialized = _serialize_result(result)
                s.update(output=serialized)

            with span("stage1.persist", input={"patient_summary": serialized["patient_summary"]}) as s:
                persisted = 0
                for summary in serialized["patient_summary"]:
                    patient_id = summary.get("patient_id")
                    if patient_id:
                        await self._repo.persist_stage1(patient_id, summary)
                        persisted += 1
                s.update(output={"persisted_patients": persisted})

            root.update(output=serialized)

        return serialized

    async def run_stage2(self, payload: dict[str, Any]) -> dict[str, Any]:
        with span(
            "assessment.stage2",
            as_type="chain",
            input=payload,
            metadata={"stage": 2},
        ) as root:
            with span("stage2.risk_assessment", input=payload) as s:
                result = run_stage2_assessment(payload)
                s.update(output=result)

            with span("stage2.persist", input=payload) as s:
                patient_id = payload.get("patientInfo", {}).get("patient_id")
                if patient_id:
                    classification_id = await self._repo.persist_stage1(patient_id, payload)
                    await self._repo.persist_stage2(patient_id, classification_id, result)
                s.update(output={"persisted": patient_id is not None})

            root.update(output=result)

        return result
