from __future__ import annotations

from enum import Enum
from typing import Literal


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


QualityLevel = Literal["high", "medium", "low"]
Confidence = Literal["high", "medium", "low"]
BPStatus = Literal["hypertension", "elevated", "normal", "unknown"]
SourceUsed = Literal["clinic", "home", "abpm_24h", "unknown"]
