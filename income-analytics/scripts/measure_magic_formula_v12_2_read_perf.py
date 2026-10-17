"""Measure persisted point-in-time ranking reads before publication."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from income_analytics.application.magic_formula_canonical_ranking import (
    MagicFormulaCanonicalRankingRepository,
    ranking_read_model,
)


def main() -> int:
    artifact = json.loads(
        Path("docs/appendices/magic_formula_v12_2/ranking_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    repository = MagicFormulaCanonicalRankingRepository()
    if repository.latest() is not None:
        raise ValueError("UNEXPECTED_PUBLISHED_RANKING_DURING_STAGED_PERFORMANCE_TEST")
    timings = []
    for _ in range(5):
        snapshot = repository.read(artifact["ranking_snapshot_id"])
        ranking_read_model(snapshot, page=1, page_size=25)
    for _ in range(100):
        started = time.perf_counter()
        snapshot = repository.read(artifact["ranking_snapshot_id"])
        ranking_read_model(snapshot, page=1, page_size=25)
        timings.append((time.perf_counter() - started) * 1000)
    ordered = sorted(timings)
    p95 = ordered[94]
    result = {
        "snapshot_id": artifact["ranking_snapshot_id"],
        "sample_count": len(timings),
        "p50_ms": round(statistics.median(timings), 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(max(timings), 3),
        "limit_ms": 250,
        "status": "PASS" if p95 <= 250 else "FAIL",
        "publication_state_during_test": "STAGED",
    }
    Path("docs/appendices/magic_formula_v12_2/performance.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
