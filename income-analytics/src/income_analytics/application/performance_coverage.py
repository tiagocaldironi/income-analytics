"""Configurable portfolio valuation coverage thresholds."""

from __future__ import annotations

import os
from decimal import Decimal

GOOD_COVERAGE = Decimal(os.getenv("INCOME_PERFORMANCE_COVERAGE_GOOD", "0.95"))
MINIMUM_COVERAGE = Decimal(os.getenv("INCOME_PERFORMANCE_COVERAGE_MINIMUM", "0.90"))
