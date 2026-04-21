from __future__ import annotations

"""Quality scoring utilities for symbolic rule evaluation.

This module converts YAML quality definitions into numeric scores and quality levels
for clinic, home, and ABPM sources.
"""

from typing import Any

from ..rules.rule_eval import evaluate_condition, evaluate_formula
from ..rules.rulebook import RULEBOOK


def _find_first_matching_rule(rules: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first rule in a rule list whose condition is true."""
    for rule in rules:
        if evaluate_condition(rule["if"], context):
            return rule
    return None


def evaluate_quality_definition(quality_definition: dict[str, Any], context: dict[str, Any]) -> tuple[float, str, list[str]]:
    """Compute a quality score and level from a YAML quality definition.

    The function matches each hard rule group, computes a group score, then
    evaluates either a formula or weighted average to produce an overall quality
    score. It finally maps the numeric score to a quality level.
    """
    hard_rules = quality_definition.get("hard_rules", {})
    chosen_scores: dict[str, float] = {}
    flags: list[str] = []

    for group_name, rules in hard_rules.items():
        matched = _find_first_matching_rule(rules, context)
        score = float(matched.get("score", 0.0)) if matched else 0.0
        chosen_scores[group_name] = score
        if matched is None:
            flags.append(f"{group_name}_unmatched")
        elif matched.get("level") != "high":
            flags.append(f"{group_name}_{matched.get('level')}")

    score_context = {f"{name}_score": value for name, value in chosen_scores.items()}
    formula = quality_definition.get("overall_score_formula", {}).get("formula")
    if formula:
        overall_score = evaluate_formula(formula, score_context)
    else:
        weights = quality_definition.get("overall_score_formula", {}).get("weights", {})
        total_weight = sum(weights.values()) or 1.0
        overall_score = sum(chosen_scores.get(name, 0.0) * weights.get(name, 0.0) for name in weights) / total_weight

    level = "low"
    mapping = quality_definition.get("score_to_level_mapping", {})
    for label, condition in mapping.items():
        if evaluate_condition(condition, {**context, "score": overall_score}):
            level = label
            break

    return overall_score, level, flags


def compute_clinic_quality(metrics: dict[str, Any]) -> tuple[float, str, list[str]]:
    """Compute minimal clinic quality based on clinic-specific YAML rules."""
    clinic_rules = RULEBOOK.common_rules.quality_clinic_minimal
    if not clinic_rules:
        return 0.0, "low", ["clinic_quality_missing"]

    for rule in clinic_rules.get("minimum_rules", []):
        if evaluate_condition(rule["if"], metrics):
            level = rule.get("level", "low")
            score_map = {"high": 1.0, "medium": 0.7, "low": 0.3}
            return score_map.get(level, 0.0), level, [f"clinic_quality_{level}"]

    return 0.0, "low", ["clinic_quality_unknown"]


def compute_home_quality(metrics: dict[str, Any]) -> tuple[float, str, list[str]]:
    """Compute home BP quality using the YAML home quality definition."""
    quality_definition = RULEBOOK.common_rules.quality_home
    return evaluate_quality_definition(quality_definition, metrics)


def compute_abpm_quality(metrics: dict[str, Any]) -> tuple[float, str, list[str]]:
    """Compute ABPM 24h quality using the YAML ABPM quality definition."""
    quality_definition = RULEBOOK.common_rules.quality_abpm_24h
    return evaluate_quality_definition(quality_definition, metrics)
