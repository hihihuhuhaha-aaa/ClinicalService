"""Shared pytest configuration and fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

# Đảm bảo project root nằm trong sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
