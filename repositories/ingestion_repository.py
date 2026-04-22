from __future__ import annotations

from typing import Any


class IngestionRepository:
    def __init__(self, db) -> None:
        self._db = db

    async def insert_from_payload(
        self,
        patient_id: str,
        payload: dict[str, Any],
        severity: str,
        status: str,
    ) -> dict[str, list[str]]:
        """
        Insert curated payload into bp_records and/or clinical_facts.
        Returns dict of inserted record ids per table.
        """
        bp_ids = await self._insert_bp_records(patient_id, payload, severity, status)
        fact_ids = await self._insert_clinical_facts(patient_id, payload, severity, status)
        return {"bp_records": bp_ids, "clinical_facts": fact_ids}

    async def update_status(self, table: str, record_id: str, status: str) -> bool:
        """Update status of a record in bp_records or clinical_facts."""
        allowed = {"bp_records", "clinical_facts"}
        if table not in allowed:
            raise ValueError(f"table must be one of {allowed}")
        row = await self._db.fetchrow(
            f"UPDATE {table} SET status = $1 WHERE id = $2::uuid RETURNING id",
            status,
            record_id,
        )
        return row is not None

    # ------------------------------------------------------------------

    async def _insert_bp_records(
        self,
        patient_id: str,
        payload: dict[str, Any],
        severity: str,
        status: str,
    ) -> list[str]:
        readings = payload.get("blood_pressure_readings", [])
        ids: list[str] = []
        for reading in readings:
            systolic = reading.get("systolic")
            diastolic = reading.get("diastolic")
            if systolic is None or diastolic is None:
                continue
            row = await self._db.fetchrow(
                """
                INSERT INTO bp_records
                    (patient_id, systolic, diastolic, source, severity, status)
                VALUES ($1::uuid, $2, $3, $4, $5, $6)
                RETURNING id::text
                """,
                patient_id,
                int(systolic),
                int(diastolic),
                reading.get("source", "reported"),
                severity,
                status,
            )
            if row:
                ids.append(row["id"])
        return ids

    async def _insert_clinical_facts(
        self,
        patient_id: str,
        payload: dict[str, Any],
        severity: str,
        status: str,
    ) -> list[str]:
        ids: list[str] = []

        fact_groups: list[tuple[str, list[str]]] = [
            ("diagnosis",  payload.get("diagnoses", [])),
            ("symptom",    payload.get("symptoms", [])),
            ("medication", payload.get("medications", [])),
        ]

        for fact_group, items in fact_groups:
            for item in items:
                row = await self._db.fetchrow(
                    """
                    INSERT INTO clinical_facts
                        (patient_id, fact_group, fact_key, value, severity, status, source)
                    VALUES ($1::uuid, $2, $3, true, $4, $5, 'ingestion')
                    RETURNING id::text
                    """,
                    patient_id,
                    fact_group,
                    item,
                    severity,
                    status,
                )
                if row:
                    ids.append(row["id"])

        return ids
