from __future__ import annotations

"""Rulebook loader for the symbolic engine.

This module loads the YAML rulebook from the configured default path and
exports a shared RULEBOOK object.
"""

from .rule_config import DEFAULT_RULEBOOK_PATH, load_rulebook

RULEBOOK = load_rulebook(DEFAULT_RULEBOOK_PATH)
