"""Economic origin of capital used in a class or asset position."""

from __future__ import annotations

from enum import Enum


class CapitalFlowType(str, Enum):
    EXTERNAL_CAPITAL = "EXTERNAL_CAPITAL"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"
    EMPLOYER_CONTRIBUTION = "EMPLOYER_CONTRIBUTION"
    UNKNOWN = "UNKNOWN"
