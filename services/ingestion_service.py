"""Ingestion service — orchestrates the ingestion pipeline + persistence."""
from __future__ import annotations

from models.ingestion import IngestResponse, InsertedRecords, ReviewResponse, SafetyInfo
from repositories import IngestionRepository
from services.ingestion import run_ingestion_pipeline


class IngestionService:
    def __init__(self, repo: IngestionRepository) -> None:
        self._repo = repo

    async def ingest(self, patient_id: str, message: str, llm) -> IngestResponse:
        result = await run_ingestion_pipeline(message, llm)

        severity = result.safety.severity
        status = result.label.status
        payload = result.curation.payload

        inserted = await self._repo.insert_from_payload(
            patient_id=patient_id,
            payload=payload,
            severity=severity.value,
            status=status,
        )

        return IngestResponse(
            status=status,
            severity=severity.value,
            requires_review=result.label.requires_review,
            inserted=InsertedRecords(**inserted),
            extraction=result.extraction.entities,
            signals=result.extraction.signals,
            safety=SafetyInfo(
                severity=severity.value,
                reason=result.safety.reason,
                flags=result.safety.flags,
            ),
            curation=payload,
        )

    async def review(self, table: str, record_id: str, decision: str) -> ReviewResponse | None:
        updated = await self._repo.update_status(table, record_id, decision)
        if not updated:
            return None
        return ReviewResponse(status=decision, table=table, record_id=record_id)
