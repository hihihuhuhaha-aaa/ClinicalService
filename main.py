"""Entry point for Neural-Symbolic Clinical Decision Support API."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configs.config import settings, config
from api.routes.health import router as health_router
from api.routes.assessment import router as assessment_router
from api.routes.ingestion import router as ingestion_router
from integrations.llms.vllm import create_llm
from middleware.error_handler import register_error_handlers
from middleware.logging import RequestLoggingMiddleware
from utils.logger import setup_logging
from observability import langfuse_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    langfuse_client.init()

    app.state.db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
    app.state.pool = app.state.db_pool

    app.state.llm = create_llm(profile="primary")

    yield

    await app.state.db_pool.close()
    await app.state.llm.close()
    langfuse_client.flush()


def create_app() -> FastAPI:
    setup_logging(debug=settings.DEBUG)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    register_error_handlers(app)

    app.add_middleware(RequestLoggingMiddleware)

    _cors = config.get("cors", {})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors.get("allow_origins", ["*"]),
        allow_credentials=_cors.get("allow_credentials", True),
        allow_methods=_cors.get("allow_methods", ["*"]),
        allow_headers=_cors.get("allow_headers", ["*"]),
    )

    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(assessment_router, prefix="/api/v1", tags=["Assessment"])
    app.include_router(ingestion_router, prefix="/api/v1", tags=["Ingestion"])

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
