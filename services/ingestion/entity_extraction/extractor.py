from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from configs.config import ai_config

if TYPE_CHECKING:
    from integrations.llms.vllm import VLLMClient

_task_cfg = ai_config.get("llm", {}).get("tasks", {}).get("entity_extraction", {})
_TEMPERATURE: float = _task_cfg.get("temperature", 0.0)
_MAX_TOKENS: int = _task_cfg.get("max_tokens", 1024)

_SYSTEM_PROMPT = """You are a clinical NLP assistant. Extract structured entities and signals from the user message.

Return ONLY a valid JSON object (no markdown, no explanation) with this exact schema:
{
  "entities": {
    "blood_pressure": [{"systolic": <int>, "diastolic": <int>}],
    "heart_rate": [<int>],
    "symptoms": [<string>],
    "medications": [<string>],
    "diagnoses": [<string>],
    "patient_info": {"age": <int|null>, "gender": <string|null>},
    "measurements": {}
  },
  "signals": {
    "uncertainty": <bool>,
    "negation": <bool>,
    "temporal": [<string>]
  }
}

Rules:
- Only include fields that are present in the message; omit empty arrays/nulls.
- uncertainty = true if the message contains words like "maybe", "possibly", "might", "suspect", "unclear".
- negation = true if the message contains explicit negation (no, not, denies, absent, none).
- temporal = list of time expressions found (e.g. "yesterday", "3 days ago", "last week").
- All keys must be present even if empty."""


@dataclass
class ExtractionResult:
    entities: dict = field(default_factory=dict)
    signals: dict = field(default_factory=dict)
    raw_message: str = ""
    # signals keys: uncertainty, negation, temporal


async def extract(message: str, llm: "VLLMClient") -> ExtractionResult:
    """Extract entities and signals (uncertainty, negation, temporal) from raw message using LLM."""
    response = await llm.chat(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=_TEMPERATURE,
        max_tokens=_MAX_TOKENS,
    )
    raw = response["choices"][0]["message"]["content"]
    parsed = _parse_json(raw)
    return ExtractionResult(
        entities=parsed.get("entities", {}),
        signals=parsed.get("signals", {"uncertainty": False, "negation": False, "temporal": []}),
        raw_message=message,
    )


def _parse_json(text: str) -> dict:
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Best-effort: extract first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {}
