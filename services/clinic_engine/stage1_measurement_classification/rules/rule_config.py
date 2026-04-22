from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class ThresholdRule(BaseModel):
    sys_lt: float | None = None
    dia_lt: float | None = None
    sys_range: list[float] | None = None
    dia_range: list[float] | None = None
    sys_ge: float | None = None
    dia_ge: float | None = None

    @field_validator("sys_range", "dia_range", mode="before")
    @classmethod
    def normalize_range(cls, value: Any) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return [float(value[0]), float(value[1])]
        raise ValueError("range must be a list of two numbers")


class SourceThresholds(BaseModel):
    description: str
    normal: ThresholdRule
    elevated: ThresholdRule
    hypertension: ThresholdRule
    stage: dict[str, ThresholdRule] | None = None


class CommonRules(BaseModel):
    source_priority: list[str]
    thresholds: dict[str, SourceThresholds]
    quality_home: dict[str, Any]
    quality_abpm_24h: dict[str, Any]
    quality_clinic_minimal: dict[str, Any]


class RuleBook(BaseModel):
    version: str
    name: str
    language: str
    description: str
    common_rules: CommonRules
    step1_bp_category: dict[str, Any]
    step2_bp_stage: dict[str, Any]
    step3_phenotype: dict[str, Any]
    shared_output_contract: dict[str, Any]


_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_RULES_CONFIG_PATH = _PROJECT_ROOT / "configs" / "rules_config.yaml"


def _resolve_active_rulebook_path() -> Path:
    with _RULES_CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    active_version = cfg["rulebooks"]["stage1"]["active"]
    relative_file = cfg["rulebooks"]["stage1"]["versions"][active_version]["file"]
    return _PROJECT_ROOT / relative_file


DEFAULT_RULEBOOK_PATH = _resolve_active_rulebook_path()


def load_rulebook(path: Path | str | None = None) -> RuleBook:
    target = Path(path) if path else DEFAULT_RULEBOOK_PATH
    with target.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"Rulebook YAML must produce a mapping, got {type(raw).__name__}")

    return RuleBook.model_validate(raw)
