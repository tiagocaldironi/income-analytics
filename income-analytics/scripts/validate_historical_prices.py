"""Audit the frozen universe against raw COTAHIST and the existing provider, offline."""

import hashlib
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from income_analytics.application.historical_price import POLICY_VERSION, gap_analysis, resolve
from income_analytics.application.market_data import MarketDataUnavailable
from income_analytics.infrastructure.b3_cotahist_market_data import B3CotahistMarketDataProvider
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)


def provider_evidence(ticker, requested):
    provider = B3CotahistMarketDataProvider(cache_directory=Path("data/cotahist"))
    try:
        quote = provider.price_evidence_on(ticker, date.fromisoformat(requested))
        return dict(
            found=True,
            price=str(quote.price),
            effective_date=quote.effective_date.isoformat(),
            source_reference=quote.record_reference,
        )
    except MarketDataUnavailable as error:
        return dict(found=False, error=str(error))


def run():
    output = Path("tmp/historical-price-phase3")
    before = json.loads((output / "before.json").read_text(encoding="utf8"))
    index = json.loads((output / "raw-index.json").read_text(encoding="utf8"))
    eligible = [i for i in before["issuers"] if i["methodology_eligibility"] == "ELIGIBLE"]
    gaps = [i for i in eligible if not i["market_readiness"]["price_ready"]]
    controls = [i for i in eligible if i["canonical_status"] == "RESOLVED"]
    requested = before["reference_date"]
    started = perf_counter()
    resolutions = {
        i["issuer_id"]: [resolve(s, index.get(s["ticker"], []), requested) for s in i["securities"]]
        for i in gaps + controls
    }
    features = {}
    for issuer in gaps:
        features[issuer["issuer_id"]] = {
            "sector:" + issuer["economic_sector"],
            "multiple:" + str(len(issuer["securities"]) > 1),
            *("class:" + s["share_class"] for s in issuer["securities"]),
            *("reason:" + str(r["reason_code"]) for r in resolutions[issuer["issuer_id"]]),
            "recent:"
            + str(any((s["valid_from"] or "")[:4] == requested[:4] for s in issuer["securities"])),
        }
    remaining, selected, covered = list(gaps), [], set()
    while remaining and len(selected) < 25:
        chosen = min(
            remaining, key=lambda i: (-len(features[i["issuer_id"]] - covered), i["issuer_id"])
        )
        selected.append(chosen)
        covered.update(features[chosen["issuer_id"]])
        remaining.remove(chosen)
    sample = dict(
        parent_id=before["universe_snapshot_id"],
        strata=sorted(covered),
        issuer_ids=[i["issuer_id"] for i in selected + controls],
    )
    (output / "sample.json").write_text(json.dumps(sample, indent=2), encoding="utf8")
    archive = Path("data/cotahist/COTAHIST_A" + requested[:4] + ".ZIP")
    source_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = json.loads((output / "source-manifest.json").read_text(encoding="utf8"))
    assert source_hash == manifest["sha256"]
    # Resume only evidence tied to this frozen archive and reference date.
    provider_results = json.loads((output / "provider-results.json").read_text(encoding="utf8"))
    # Public provider comparison uses only existing archives; no missing-file downloads.
    assert Path("data/cotahist/COTAHIST_A" + requested[:4] + ".ZIP").is_file()
    pending = sorted(
        {
            s["ticker"]
            for issuer in selected + controls + gaps
            for s in issuer["securities"]
            if s["ticker"] and s["ticker"] not in provider_results
        }
    )
    with ProcessPoolExecutor(max_workers=4) as workers:
        tasks = {workers.submit(provider_evidence, ticker, requested): ticker for ticker in pending}
        for task in as_completed(tasks):
            provider_results[tasks[task]] = task.result()
            temporary = output / "provider-results.pending.json"
            temporary.write_text(json.dumps(provider_results, indent=2), encoding="utf8")
            (output / "provider-results.json").write_text(
                temporary.read_text(encoding="utf8"), encoding="utf8"
            )
    sample_seconds = perf_counter() - started
    audit = []
    for issuer in gaps + controls:
        records = resolutions[issuer["issuer_id"]]
        for record in records:
            record["provider_output"] = provider_results.get(record["ticker"])
        blocking = [
            r
            for r in records
            if r["ticker"] in issuer["market_readiness"]["price_readiness_tickers"]
            and r["status"] != "RESOLVED"
        ]
        # Missing prices remain a source-window gap for the specified ticker;
        # an unproved alias is never classified as a resolved implementation defect.
        category = (
            "RESOLVED"
            if not blocking
            else "SECURITY_RESOLUTION_GAP"
            if any(
                r["reason_code"]
                in (
                    "SECURITY_MAPPING_GAP",
                    "TEMPORAL_CONFLICT",
                    "SECURITY_NOT_ACTIVE_AT_REFERENCE_DATE",
                )
                for r in blocking
            )
            else "SOURCE_DATA_GAP"
        )
        audit.append(
            dict(
                issuer_id=issuer["issuer_id"],
                display_name=issuer["display_name"],
                category=category,
                securities=records,
                control=issuer in controls,
                sampled=issuer in selected + controls,
                primary_gap_before=(issuer["data_reason_codes"] or [None])[0],
                primary_gap_after=(issuer["data_reason_codes"] or [None])[0],
            )
        )
    counts = Counter(i["category"] for i in audit if not i["control"])
    # There is no proved correction in this run: persist diagnostics, not invented readiness.
    assert counts["RESOLVED"] == 0, "RESOLVED_CASE_REQUIRES_EXPLICIT_APPLICATION_REVIEW"
    for issuer in controls:
        for security, resolution in zip(issuer["securities"], resolutions[issuer["issuer_id"]]):
            assert resolution["price"] == security["price"]
            assert resolution["effective_date"] == security["effective_market_date"]
    for issuer in gaps + controls:
        for security, resolution in zip(issuer["securities"], resolutions[issuer["issuer_id"]]):
            repeated = resolve(
                security, list(reversed(index.get(security["ticker"], []))), requested
            )
            assert repeated == {k: v for k, v in resolution.items() if k != "provider_output"}
    document = deepcopy(before)
    document.update(universe_snapshot_id=str(uuid4()), created_at=datetime.now(UTC).isoformat())
    document["price_resolution_run"] = dict(
        policy_version=POLICY_VERSION,
        parent_id=before["universe_snapshot_id"],
        sample=sample,
        diagnostics=audit,
        root_categories=dict(counts),
        gap_analysis=gap_analysis(eligible),
        resumed_audit_duration_seconds=sample_seconds,
        generalization_decision="NO_PROVEN_IMPLEMENTATION_CORRECTION",
        determinism_status="PASS",
        golden_price_regression="PASS",
        source_manifest=manifest,
        provider_comparison_scope="ALL_GAPS_AND_CONTROLS",
    )
    (output / "audited-universe.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf8"
    )
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    repository.save(document)
    assert (
        MagicFormulaUniverseRepository(repository.database).read(document["universe_snapshot_id"])
        == document
    )
    print(
        json.dumps(
            dict(
                snapshot_id=document["universe_snapshot_id"],
                categories=counts,
                gap_analysis=gap_analysis(eligible),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
