from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from observability import aspan
from services.ingestion.data_curation.curator import CurationResult, curate
from services.ingestion.entity_extraction.extractor import ExtractionResult, extract
from services.ingestion.labeling.labeler import LabelResult, label
from services.ingestion.safety_check.checker import SafetyResult, check

if TYPE_CHECKING:
    from integrations.llms.vllm import VLLMClient


@dataclass
class IngestionResult:
    extraction: ExtractionResult
    safety: SafetyResult
    label: LabelResult
    curation: CurationResult


async def run_ingestion_pipeline(message: str, llm: "VLLMClient") -> IngestionResult:
    """
    Orchestrate the full ingestion flow for a raw user message:

      1. entity_extraction  — LLM extracts entities + signals (uncertainty, negation, temporal)
      2. safety_check       — LLM classifies severity: high | medium | low
      3. labeling           — tag high/medium as "pending"; low as "pass"
      4. data_curation      — LLM normalises and prepares payload for DB (all severities)
    """
    async with aspan(
        "ingest.pipeline",
        as_type="chain",
        input={"message": message},
    ) as root:
        async with aspan(
            "ingest.entity_extraction",
            as_type="span",
            input={"message": message},
        ) as s:
            extraction: ExtractionResult = await extract(message, llm)
            s.update(output={"entities": extraction.entities, "signals": extraction.signals})

        async with aspan(
            "ingest.safety_check",
            as_type="span",
            input={"entities": extraction.entities, "signals": extraction.signals},
        ) as s:
            safety: SafetyResult = await check(extraction, llm)
            s.update(output={"severity": safety.severity.value, "reason": safety.reason, "flags": safety.flags})

        async with aspan(
            "ingest.labeling",
            as_type="span",
            input={"severity": safety.severity.value, "reason": safety.reason, "flags": safety.flags},
        ) as s:
            label_result: LabelResult = label(safety)
            s.update(output={"status": label_result.status, "requires_review": label_result.requires_review})

        async with aspan(
            "ingest.data_curation",
            as_type="span",
            input={"entities": extraction.entities, "signals": extraction.signals, "label": label_result.status},
        ) as s:
            curation: CurationResult = await curate(extraction, label_result, llm)
            s.update(output=curation.payload)

        root.update(output=curation.payload)

    return IngestionResult(
        extraction=extraction,
        safety=safety,
        label=label_result,
        curation=curation,
    )
