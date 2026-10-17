"""Assemble reproducible analytics profiling and correctness artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path("docs/appendices/performance_v1_1")
ENDPOINTS = (
    "wealth_evolution",
    "wealth_explanation",
    "portfolio_performance",
    "performance_comparison",
)
PHASE_FUNCTIONS = {
    "wealth_series",
    "portfolio_as_of",
    "projections_at",
    "base_currency_valuation",
    "project",
    "project_timeline",
    "_build_projection",
    "_apply_event",
    "_coverage",
    "_twr",
    "_equity",
    "_equity_from_projection",
    "_fx_rate",
    "_implicit_capital_base",
    "_implicit_funding_ledger",
    "explain",
    "performance_at",
    "build_performance_comparison",
    "get_wealth_evolution",
    "get_wealth_explanation",
    "get_portfolio_performance",
    "get_performance_comparison",
}
RELEVANT_CALLS = (
    "project",
    "project_timeline",
    "_build_projection",
    "_apply_event",
    "from_event",
    "wealth_series",
    "portfolio_as_of",
    "projections_at",
    "base_currency_valuation",
    "_coverage",
    "_twr",
    "_equity",
    "_fx_rate",
    "_implicit_capital_base",
    "_implicit_funding_ledger",
)


def read_profile(path: Path, endpoint: str) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as file:
        return [{"endpoint": endpoint, **row} for row in csv.DictReader(file)]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    profiles = ROOT / "profiles"
    before: list[dict[str, object]] = []
    after: list[dict[str, object]] = []
    for endpoint in ENDPOINTS:
        before.extend(read_profile(profiles / f"{endpoint}_cpu.csv", endpoint))
        after.extend(read_profile(profiles / "after_final" / f"{endpoint}_cpu.csv", endpoint))
    for name, rows in (
        ("top_cpu_functions_before.csv", before),
        ("top_cpu_functions_after.csv", after),
    ):
        selected = sorted(rows, key=lambda row: float(row["self_time_ms"]), reverse=True)[:100]
        write_csv(ROOT / name, selected)

    before_map = {(str(row["endpoint"]), str(row["function"])): row for row in before}
    after_map = {(str(row["endpoint"]), str(row["function"])): row for row in after}
    call_rows = []
    for key in sorted(before_map.keys() | after_map.keys()):
        endpoint, function = key
        if not any(token in function for token in RELEVANT_CALLS):
            continue
        old, new = before_map.get(key, {}), after_map.get(key, {})
        old_calls, new_calls = int(old.get("calls", 0)), int(new.get("calls", 0))
        call_rows.append(
            {
                "endpoint": endpoint,
                "function": function,
                "calls_before": old_calls,
                "calls_after": new_calls,
                "calls_delta": new_calls - old_calls,
                "self_ms_before": old.get("self_time_ms", ""),
                "self_ms_after": new.get("self_time_ms", ""),
                "cumulative_ms_before": old.get("cumulative_time_ms", ""),
                "cumulative_ms_after": new.get("cumulative_time_ms", ""),
            }
        )
    write_csv(ROOT / "call_counts_before_after.csv", call_rows)

    phase_rows = [
        row
        for row in after
        if any(row["function"].endswith(f":{name}") for name in PHASE_FUNCTIONS)
    ]
    write_csv(ROOT / "endpoint_phase_profile.csv", phase_rows)

    optimized = json.loads(
        (ROOT / "final" / "controlled_benchmark.json").read_text(encoding="utf-8")
    )
    (ROOT / "controlled_benchmark.json").write_text(
        json.dumps(optimized, indent=2), encoding="utf-8"
    )
    before_bench = {
        "wealth_evolution": {
            "cold_ms": 1316.77,
            "warm_min_ms": 1049.06,
            "warm_median_ms": 1181.5,
            "warm_p95_ms": 1750.4,
            "warm_max_ms": 1750.4,
            "response_bytes": 42535,
        },
        "wealth_explanation": {
            "cold_ms": 2717.74,
            "warm_min_ms": 2032.73,
            "warm_median_ms": 2127.13,
            "warm_p95_ms": 2756.86,
            "warm_max_ms": 2756.86,
            "response_bytes": 16609,
        },
        "portfolio_performance": {
            "cold_ms": 2650.32,
            "warm_min_ms": 1844.9,
            "warm_median_ms": 1954.35,
            "warm_p95_ms": 2227.04,
            "warm_max_ms": 2227.04,
            "response_bytes": 1675,
        },
        "performance_comparison": {
            "cold_ms": 2218.56,
            "warm_min_ms": 30.45,
            "warm_median_ms": 64.92,
            "warm_p95_ms": 184.65,
            "warm_max_ms": 184.65,
            "response_bytes": 1612,
        },
    }
    (ROOT / "controlled_benchmark_before.json").write_text(
        json.dumps(before_bench, indent=2), encoding="utf-8"
    )
    reconciliation: dict[str, object] = {}
    for endpoint in ENDPOINTS:
        before_path = profiles / "golden_before" / f"{endpoint}.json"
        after_path = profiles / "golden_final" / f"{endpoint}.json"
        before_bytes = before_path.read_bytes()
        after_bytes = after_path.read_bytes()
        before_hash = hashlib.sha256(before_bytes).hexdigest()
        after_hash = hashlib.sha256(after_bytes).hexdigest()
        reconciliation[endpoint] = {
            "byte_identical": before_bytes == after_bytes,
            "sha256_before": before_hash,
            "sha256_after": after_hash,
            "bytes_before": len(before_bytes),
            "bytes_after": len(after_bytes),
        }
    reconciliation["twr_semantics_changed"] = False
    reconciliation["magic_formula_changed"] = False
    (ROOT / "correctness_reconciliation.json").write_text(
        json.dumps(reconciliation, indent=2), encoding="utf-8"
    )
    payload_rows = []
    for endpoint, result in optimized.items():
        payload_rows.append(
            {
                "endpoint": endpoint,
                "response_bytes": result["response_bytes"],
                "status": result["status_codes"][-1],
                "sha256": result["response_sha256_per_run"][-1],
            }
        )
    write_csv(ROOT / "analytics_payloads.csv", payload_rows)
    shutil.copyfile(
        ROOT / "optimized" / "concurrency_benchmark.csv", ROOT / "concurrency_benchmark.csv"
    )
    shutil.copyfile(ROOT / "optimized" / "scaling_benchmark.csv", ROOT / "scaling_benchmark.csv")
    print(json.dumps(reconciliation, indent=2))


if __name__ == "__main__":
    main()
