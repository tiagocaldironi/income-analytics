"""Bounded synthetic/adapter transport contract; no financial fallback or telemetry."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from income_analytics.infrastructure.operational import signals


class ProviderUnavailable(ValueError):
    """Stable operational exception; never carries source payload or credentials."""


def fetch_json(
    transport: Callable[[float], tuple[int, bytes]], *, attempts: int = 2,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not 1 <= attempts <= 3:
        raise ValueError("INVALID_RETRY_LIMIT")
    for attempt in range(attempts):
        started = time.monotonic()
        try:
            status, body = transport(5)
            if status != 200 or len(body) > 1024 * 1024:
                raise ProviderUnavailable("PROVIDER_UNAVAILABLE")
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict):
                raise ProviderUnavailable("PROVIDER_SCHEMA_INVALID")
            return data
        except (OSError, ValueError):
            signals.event("provider_unavailable", duration=time.monotonic() - started)
            if attempt + 1 < attempts:
                sleep(min(0.1 * (2 ** attempt), 0.4))
        finally:
            signals.dependency(time.monotonic() - started)
    raise ProviderUnavailable("PROVIDER_UNAVAILABLE")
