"""Freeze a source-driven stratified sample before attempting unit resolution."""

import argparse
import json
from decimal import Decimal
from pathlib import Path
from time import perf_counter

from income_analytics.application.magic_formula_universe import decimal_or_none, digits
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)
from income_analytics.infrastructure.magic_formula_universe_sources import csv_records


def build_sample(universe, cvm_directory, count=25):
    year = int(universe["reference_date"][:4])
    archive = cvm_directory / f"dfp_cia_aberta_{year}.zip"
    capital = list(csv_records(archive, f"dfp_cia_aberta_composicao_capital_{year}.csv"))
    documents = list(csv_records(archive, f"dfp_cia_aberta_{year}.csv"))
    assets = {}
    for row in csv_records(archive, f"dfp_cia_aberta_BPA_con_{year}.csv"):
        if (
            row["CD_CONTA"] == "1"
            and row["ORDEM_EXERC"] == "ÚLTIMO"
            and row["DT_REFER"] == universe["reference_date"]
        ):
            value = decimal_or_none(row["VL_CONTA"])
            if value is not None and row["ESCALA_MOEDA"] in ("MIL", "UNIDADE"):
                assets[digits(row["CNPJ_CIA"])] = value * (
                    1000 if row["ESCALA_MOEDA"] == "MIL" else 1
                )
    candidates = [
        i
        for i in universe["issuers"]
        if i["methodology_eligibility"] == "ELIGIBLE"
        and "UNIT_UNRESOLVED" in i["data_reason_codes"]
    ]
    ranked = sorted((assets[i["cnpj"]], i["issuer_id"]) for i in candidates if i["cnpj"] in assets)
    size = {
        issuer: ("SMALL", "MEDIUM", "LARGE")[min(2, n * 3 // len(ranked))]
        for n, (_, issuer) in enumerate(ranked)
    }

    def describe(issuer):
        quantities = issuer["market_readiness"]["raw_capital_quantities"]
        issued = [Decimal(v["issued"]) for v in quantities.values() if v["issued"] is not None]
        classes = sorted(s["share_class"] for s in issuer["securities"])
        features = dict(
            sector=issuer["economic_sector"],
            size=size.get(issuer["issuer_id"], "UNKNOWN"),
            classes="+".join(sorted(set(classes))),
            multiple_securities=str(len(classes) > 1),
            treasury=str(any(Decimal(v["treasury"] or "0") > 0 for v in quantities.values())),
            raw_digits=str(max(len(str(abs(int(v)))) for v in issued)),
            raw_fractional=str(any(v != v.to_integral_value() for v in issued)),
        )
        return features

    features = {i["issuer_id"]: describe(i) for i in candidates}
    selected, covered, remaining = [], set(), list(candidates)
    while remaining and len(selected) < count:
        chosen = min(
            remaining,
            key=lambda i: (-len(set(features[i["issuer_id"]].items()) - covered), i["issuer_id"]),
        )
        selected.append(chosen)
        covered.update(features[chosen["issuer_id"]].items())
        remaining.remove(chosen)
    controls = [i for i in universe["issuers"] if i["canonical_status"] == "RESOLVED"]
    rows = []
    for issuer in sorted(selected + controls, key=lambda i: i["issuer_id"]):
        caps = [
            c
            for c in capital
            if digits(c["CNPJ_CIA"]) == issuer["cnpj"]
            and c["DT_REFER"] == universe["reference_date"]
        ]
        assert len(caps) == 1
        cap = caps[0]
        docs = [
            d
            for d in documents
            if digits(d["CNPJ_CIA"]) == issuer["cnpj"]
            and d["DT_REFER"] == cap["DT_REFER"]
            and d["VERSAO"] == cap["VERSAO"]
        ]
        assert len(docs) == 1
        rows.append(
            dict(
                issuer_id=issuer["issuer_id"],
                cvm_code=issuer["cvm_code"],
                cnpj=issuer["cnpj"],
                display_name=issuer["display_name"],
                control=issuer in controls,
                strata=features.get(issuer["issuer_id"], describe(issuer)),
                assets_for_stratification=str(assets.get(issuer["cnpj"]))
                if issuer["cnpj"] in assets
                else None,
                capital=cap,
                document=docs[0],
                securities=issuer["securities"],
            )
        )
    return dict(
        sample_policy="GREEDY_FEATURE_COVERAGE_V1_UUID_TIEBREAK",
        unresolved_count=len(selected),
        control_count=len(controls),
        magnitude_used_for_resolution=False,
        strata_covered=sorted([list(x) for x in covered]),
        issuers=rows,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-id", required=True)
    parser.add_argument(
        "--universe-database", type=Path, default=Path("data/magic_formula/universe_snapshots.db")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=25)
    args = parser.parse_args()
    start = perf_counter()
    universe = MagicFormulaUniverseRepository(args.universe_database).read(args.universe_id)
    sample = build_sample(universe, Path("data/cvm"), args.count)
    sample["universe_snapshot_id"] = args.universe_id
    sample["sample_selection_seconds"] = perf_counter() - start
    args.output.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf8")
    print(
        json.dumps(
            dict(sample_size=len(sample["issuers"]), strata=sample["strata_covered"]),
            ensure_ascii=False,
        )
    )
