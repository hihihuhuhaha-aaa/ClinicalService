from __future__ import annotations

from fastapi import APIRouter, Request

from models.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse, summary="Health check")
async def health(request: Request) -> HealthResponse:
    from configs.config import settings, ai_config

    db_status = "ok"
    try:
        async with request.app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_status = "unavailable"

    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        db=db_status,
        llm_url=ai_config.get("llm", {}).get("base_url", ""),
    )
