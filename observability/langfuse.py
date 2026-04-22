"""Langfuse Cloud observability — span helpers using OTel context propagation."""
from __future__ import annotations

import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Any, Generator, AsyncGenerator

logger = logging.getLogger(__name__)

_client: "langfuse.Langfuse | None" = None


def get_client() -> "langfuse.Langfuse | None":
    return _client


class _LangfuseClient:
    def init(self) -> None:
        global _client
        try:
            import langfuse as lf
            from configs.config import settings

            if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
                logger.warning("Langfuse keys not set — tracing disabled.")
                return

            _client = lf.Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                base_url=settings.LANGFUSE_BASE_URL,
                debug=settings.DEBUG,
            )
            logger.info("Langfuse observability connected to %s.", settings.LANGFUSE_BASE_URL)
        except Exception:
            logger.exception("Langfuse init failed — tracing disabled.")

    def flush(self) -> None:
        if _client is not None:
            try:
                _client.flush()
            except Exception:
                logger.exception("Langfuse flush failed.")


# ---------------------------------------------------------------------------
# Span context managers — use start_as_current_observation so OTel propagates
# the active span into nested calls automatically, keeping all spans in one trace.
# ---------------------------------------------------------------------------

@contextmanager
def span(
    name: str,
    *,
    as_type: str = "span",
    input: Any = None,
    metadata: Any = None,
) -> Generator[Any, None, None]:
    """
    Sync span context manager. Nested calls automatically become child spans
    because start_as_current_observation sets the OTel active context.

    Usage::

        with span("stage1.pipeline", as_type="chain", input={"n": 5}) as s:
            result = run_symbolic_pipeline(df)
            s.update(output=result)
    """
    if _client is None:
        yield _NoopSpan()
        return

    with _client.start_as_current_observation(
        name=name, as_type=as_type, input=input, metadata=metadata
    ) as obs:
        try:
            yield obs
        except Exception as exc:
            obs.update(level="ERROR", status_message=str(exc))
            raise


@asynccontextmanager
async def aspan(
    name: str,
    *,
    as_type: str = "span",
    input: Any = None,
    metadata: Any = None,
) -> AsyncGenerator[Any, None]:
    """
    Async span context manager. Uses the same OTel context propagation as the
    sync version — nested aspan/span calls become child spans on the same trace.

    Usage::

        async with aspan("ingest.pipeline", as_type="chain", input={"patient_id": pid}) as s:
            result = await run_ingestion_pipeline(msg, llm)
            s.update(output={"status": result.label.status})
    """
    if _client is None:
        yield _NoopSpan()
        return

    # _AgnosticContextManager only has __enter__/__exit__, not __aenter__.
    # Enter synchronously inside the async body — safe because span creation
    # is non-blocking; only the application logic inside the block is async.
    cm = _client.start_as_current_observation(
        name=name, as_type=as_type, input=input, metadata=metadata
    )
    obs = cm.__enter__()
    try:
        yield obs
    except Exception as exc:
        obs.update(level="ERROR", status_message=str(exc))
        cm.__exit__(type(exc), exc, exc.__traceback__)
        raise
    else:
        cm.__exit__(None, None, None)


class _NoopSpan:
    """Returned when Langfuse is not initialised — all calls are silent no-ops."""

    def update(self, **_: Any) -> "_NoopSpan":
        return self

    def end(self, **_: Any) -> "_NoopSpan":
        return self

    def score(self, **_: Any) -> "_NoopSpan":
        return self


langfuse_client = _LangfuseClient()
