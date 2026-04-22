"""Ingestion endpoints — message ingestion pipeline with safety review flow."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from models.ingestion import IngestRequest, IngestResponse, ReviewDecision, ReviewResponse
from repositories import IngestionRepository
from services.ingestion_service import IngestionService

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _get_llm(request: Request):
    return request.app.state.llm


def _get_ingestion_service(request: Request) -> IngestionService:
    repo = IngestionRepository(request.app.state.db_pool)
    return IngestionService(repo)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/ingest", summary="Ingest a user message through the full pipeline", response_model=IngestResponse)
async def ingest(
    body: IngestRequest,
    llm=Depends(_get_llm),
    svc: IngestionService = Depends(_get_ingestion_service),
) -> IngestResponse:
    """
    Run the ingestion pipeline:
      1. Entity extraction (LLM)
      2. Safety check → severity classification (LLM)
      3. Labeling → status pending / pass
      4. Data curation → normalised payload (LLM)
      5. Insert into bp_records / clinical_facts with severity + status

    - **LOW** severity: inserted with `status = pass`.
    - **MEDIUM / HIGH** severity: inserted with `status = pending`; call
      POST /ingest/review per record to accept or reject.
    """
    try:
        return await svc.ingest(body.patient_id, body.message, llm)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/ingest/review", summary="Update status (accepted/rejected) of a pending ingestion record", response_model=ReviewResponse)
async def review_ingestion(
    body: ReviewDecision,
    svc: IngestionService = Depends(_get_ingestion_service),
) -> ReviewResponse:
    """
    Update the status of a specific pending record:
    - **accepted**: sets status = 'accepted'.
    - **rejected**: sets status = 'rejected'.

    Call once per record ID returned by POST /ingest.
    """
    result = await svc.review(body.table, body.record_id, body.decision)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Record '{body.record_id}' not found in '{body.table}'.",
        )
    return result
