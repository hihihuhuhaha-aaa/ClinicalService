"""Assessment endpoints — Stage 1 (BP classification) and Stage 2 (risk assessment)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from models.stage1 import Stage1Request, Stage1Response
from models.stage2 import Stage2Request, Stage2Response
from repositories import AssessmentRepository
from services.assessment_service import AssessmentService

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def get_llm(request: Request):
    return request.app.state.llm


def _get_assessment_service(request: Request) -> AssessmentService:
    repo = AssessmentRepository(request.app.state.db_pool)
    return AssessmentService(repo)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/stage1", summary="Stage 1 — BP measurement classification", response_model=Stage1Response)
async def stage1_assessment(
    body: Stage1Request,
    llm=Depends(get_llm),
    svc: AssessmentService = Depends(_get_assessment_service),
) -> Stage1Response:
    try:
        records = [r.model_dump() for r in body.readings]
        result = await svc.run_stage1(records)
        return Stage1Response(**result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/stage2", summary="Stage 2 — Comprehensive cardiovascular risk assessment", response_model=Stage2Response)
async def stage2_assessment(
    body: Stage2Request,
    llm=Depends(get_llm),
    svc: AssessmentService = Depends(_get_assessment_service),
) -> Stage2Response:
    try:
        result = await svc.run_stage2(body.model_dump())
        return Stage2Response(**result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
