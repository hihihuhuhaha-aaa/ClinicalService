from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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
    extraction: ExtractionResult = await extract(message, llm)
    safety: SafetyResult = await check(extraction, llm)
    label_result: LabelResult = label(safety)
    curation: CurationResult = await curate(extraction, label_result, llm)

    return IngestionResult(
        extraction=extraction,
        safety=safety,
        label=label_result,
        curation=curation,
    )
