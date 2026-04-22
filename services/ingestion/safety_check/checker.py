from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from configs.config import ai_config
from services.ingestion.entity_extraction.extractor import ExtractionResult

if TYPE_CHECKING:
    from integrations.llms.vllm import VLLMClient

_task_cfg = ai_config.get("llm", {}).get("tasks", {}).get("safety_check", {})
_TEMPERATURE: float = _task_cfg.get("temperature", 0.0)
_MAX_TOKENS: int = _task_cfg.get("max_tokens", 512)


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SafetyResult:
    severity: Severity
    reason: str = ""
    flags: list[str] = None  # specific triggers that raised the severity

    def __post_init__(self):
        if self.flags is None:
            self.flags = []


_SYSTEM_PROMPT = """You are a clinical safety classifier. Given extracted clinical entities and signals, determine the safety severity of the patient message.

Severity levels:
- HIGH: Any of the following → acute chest pain, syncope/loss of consciousness, severe dyspnea at rest, BP ≥ 180/120 (hypertensive crisis), suicidal/self-harm ideation, stroke symptoms (sudden facial droop, arm weakness, speech difficulty), severe arrhythmia.
- MEDIUM: Any of the following → BP 160–179 / 100–119, new or worsening symptoms (dizziness, palpitations, edema), medication side effects reported, uncertainty about current treatment, new diagnosis mentioned without management plan.
- LOW: Routine monitoring data, stable chronic disease, no acute symptoms, administrative queries, follow-up messages with no new concerns.

Return ONLY a valid JSON object (no markdown, no explanation):
{
  "severity": "high" | "medium" | "low",
  "reason": "<one sentence explanation>",
  "flags": ["<specific trigger 1>", ...]
}"""


async def check(extraction: ExtractionResult, llm: "VLLMClient") -> SafetyResult:
    """Classify severity (high/medium/low) based on extracted entities and signals using LLM."""
    context = json.dumps(
        {"entities": extraction.entities, "signals": extraction.signals},
        ensure_ascii=False,
    )
    response = await llm.chat(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Extracted data:\n{context}\n\nOriginal message:\n{extraction.raw_message}"},
        ],
        temperature=_TEMPERATURE,
        max_tokens=_MAX_TOKENS,
    )
    raw = response["choices"][0]["message"]["content"]
    parsed = _parse_json(raw)
    severity_str = parsed.get("severity", "low").lower()
    try:
        severity = Severity(severity_str)
    except ValueError:
        severity = Severity.LOW
    return SafetyResult(
        severity=severity,
        reason=parsed.get("reason", ""),
        flags=parsed.get("flags", []),
    )


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
