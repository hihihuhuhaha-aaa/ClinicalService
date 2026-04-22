from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from configs.config import ai_config
from services.ingestion.entity_extraction.extractor import ExtractionResult
from services.ingestion.labeling.labeler import LabelResult

if TYPE_CHECKING:
    from integrations.llms.vllm import VLLMClient

_task_cfg = ai_config.get("llm", {}).get("tasks", {}).get("data_curation", {})
_TEMPERATURE: float = _task_cfg.get("temperature", 0.0)
_MAX_TOKENS: int = _task_cfg.get("max_tokens", 1024)


@dataclass
class CurationResult:
    payload: dict = field(default_factory=dict)
    ready_for_db: bool = False


_SYSTEM_PROMPT = """You are a clinical data normaliser. Given extracted entities, signals, and label metadata, produce a clean, structured JSON payload ready for database insertion.

Return ONLY a valid JSON object (no markdown, no explanation) following this schema:
{
  "patient_info": {
    "age": <int|null>,
    "gender": <string|null>
  },
  "blood_pressure_readings": [
    {"systolic": <int>, "diastolic": <int>, "source": "reported"}
  ],
  "heart_rate": <int|null>,
  "symptoms": [<string>],
  "medications": [<string>],
  "diagnoses": [<string>],
  "measurements": {},
  "temporal_context": [<string>],
  "flags": {
    "has_negation": <bool>,
    "has_uncertainty": <bool>
  }
}

Rules:
- Normalise symptom names to lowercase snake_case (e.g. "chest pain" → "chest_pain").
- Normalise medication names to lowercase generic names.
- Omit any field that is null or an empty list/dict.
- Do not invent data that is not in the provided entities."""


async def curate(
    extraction: ExtractionResult,
    label: LabelResult,
    llm: "VLLMClient",
) -> CurationResult:
    """Prepare structured payload for database insertion using LLM normalisation."""
    context = json.dumps(
        {
            "entities": extraction.entities,
            "signals": extraction.signals,
        },
        ensure_ascii=False,
    )
    response = await llm.chat(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Extracted data:\n{context}"},
        ],
        temperature=_TEMPERATURE,
        max_tokens=_MAX_TOKENS,
    )
    raw = response["choices"][0]["message"]["content"]
    normalised = _parse_json(raw)

    payload = {
        **normalised,
        "label": {
            "status": label.status,
            "severity": label.severity.value,
            "requires_review": label.requires_review,
        },
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "raw_message": extraction.raw_message,
    }

    return CurationResult(payload=payload, ready_for_db=True)


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {}
