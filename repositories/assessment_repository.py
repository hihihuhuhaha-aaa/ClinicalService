from __future__ import annotations

import json
import uuid
from typing import Any


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


class AssessmentRepository:
    def __init__(self, db) -> None:
        self._db = db

    async def _ensure_patient(self, patient_id: str) -> None:
        """Insert patient row if it doesn't exist (no-op if already present)."""
        await self._db.execute(
            """
            INSERT INTO patients (id) VALUES ($1::uuid)
            ON CONFLICT (id) DO NOTHING
            """,
            patient_id,
        )

    # ------------------------------------------------------------------
    # Stage 1
    # ------------------------------------------------------------------

    async def persist_stage1(
        self,
        patient_id: str,
        summary: dict[str, Any],
        rule_version: str = "1.0",
    ) -> str:
        """
        Upsert patient, then insert clinical_classifications + measurement_evaluation.
        Returns the classification UUID.
        Raises ValueError if patient_id is not a valid UUID.
        """
        if not _is_valid_uuid(patient_id):
            raise ValueError(f"patient_id must be a valid UUID, got: {patient_id!r}")

        await self._ensure_patient(patient_id)

        classification_id: str = await self._db.fetchval(
            """
            INSERT INTO clinical_classifications
                (patient_id, bp_category, bp_stage, phenotype,
                 source_used, source_value, confidence, flags, rule_version)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
            RETURNING id::text
            """,
            patient_id,
            summary.get("bp_category"),
            summary.get("bp_stage"),
            summary.get("phenotype"),
            summary.get("source_used_category"),
            summary.get("source_value_used"),
            summary.get("category_confidence"),
            json.dumps({
                "category_flags": summary.get("category_flags", []),
                "stage_flags": summary.get("stage_flags", []),
                "phenotype_flags": summary.get("phenotype_flags", []),
            }),
            rule_version,
        )

        for source in ("clinic", "home", "abpm_24h"):
            quality_score = summary.get(f"{source}_quality_score") if source != "abpm_24h" else summary.get("abpm_quality_score")
            quality_level = summary.get(f"{source}_quality_level") if source != "abpm_24h" else summary.get("abpm_quality_level")
            usable = summary.get(f"{source}_quality_usable") if source != "abpm_24h" else summary.get("abpm_quality_usable")
            flags = summary.get(f"{source}_quality_flags") if source != "abpm_24h" else summary.get("abpm_quality_flags")

            if quality_score is None and quality_level is None:
                continue

            await self._db.execute(
                """
                INSERT INTO measurement_evaluation
                    (patient_id, classification_id, source,
                     quality_score, quality_level, usable, flags, details)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7::jsonb, $8::jsonb)
                """,
                patient_id,
                classification_id,
                source,
                quality_score,
                quality_level,
                usable,
                json.dumps(flags or []),
                json.dumps({}),
            )

        return classification_id

    # ------------------------------------------------------------------
    # Stage 2
    # ------------------------------------------------------------------

    async def persist_stage2(
        self,
        patient_id: str,
        classification_id: str,
        result: dict[str, Any],
        rule_version: str = "1.0",
    ) -> str:
        """
        Insert risk_assessments + risk_reasonings.
        Returns the risk_assessment UUID.
        Raises ValueError if patient_id is not a valid UUID.
        """
        if not _is_valid_uuid(patient_id):
            raise ValueError(f"patient_id must be a valid UUID, got: {patient_id!r}")

        risk_id: str = await self._db.fetchval(
            """
            INSERT INTO risk_assessments
                (patient_id, classification_id, risk_level, rule_version)
            VALUES ($1::uuid, $2::uuid, $3, $4)
            RETURNING id::text
            """,
            patient_id,
            classification_id,
            result.get("risk_level"),
            rule_version,
        )

        await self._db.execute(
            """
            INSERT INTO risk_reasonings
                (patient_id, risk_assessment_id, explanation,
                 recommendation, confidence, rule_version)
            VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6)
            """,
            patient_id,
            risk_id,
            result.get("explanation"),
            result.get("recommendation"),
            result.get("confidence"),
            rule_version,
        )

        return risk_id
