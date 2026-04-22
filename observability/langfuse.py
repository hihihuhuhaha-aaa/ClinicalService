"""Minimal no-op Langfuse stub — replace with real langfuse client when ready."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class _LangfuseClient:
    def init(self) -> None:
        logger.info("Langfuse observability initialized (stub).")

    def flush(self) -> None:
        pass


langfuse_client = _LangfuseClient()
