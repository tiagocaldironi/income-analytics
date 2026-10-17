"""Execute only the five-issuer validation sample; never publish the ranking."""

import argparse
import json
import random
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from income_analytics.application.magic_formula_activation_gate import MagicFormulaActivationGate
from income_analytics.application.magic_formula_contract import digest
from income_analytics.application.magic_formula_ranking_validation import (
    RankingGateBlocked,
    compare_independent_qa,
    freeze_sample,
    ranking_artifact,
)
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)
from income_analytics.infrastructure.magic_formula_ranking_repository import (
    MagicFormulaRankingRepository,
)

SAMPLE_CODES = ("009512", "005410", "013986", "017450", "017671")
TABLES = (
    "magic_formula_issuers",
    "magic_formula_golden_fixtures",
    "magic_formula_fundamentals_snapshots",
    "magic_formula_formal_qa",
)


def canonical_state(repo):
    with repo.connection() as conn:
        return {
            table: [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in TABLES
        }


def run(database: Path, ranking_database: Path, output: Path):
    if database.resolve() == ranking_database.resolve():
        raise ValueError("RANKING_ARTIFACT_REQUIRES_SEPARATE_DATABASE")
    repository = CanonicalMagicFormulaRepository(database)
    before = canonical_state(repository)
    reference = "2025-12-31"
    bindings, names, exclusions = [], {}, []
    for code in SAMPLE_CODES:
        issuers = [i for i in before["magic_formula_issuers"] if i["cvm_code"] == code]
        if len(issuers) != 1:
            exclusions.append(dict(cvm_code=code, reason_codes=["MISSING_CANONICAL_ISSUER"]))
            continue
        issuer = issuers[0]
        decision = repository.eligibility(issuer["issuer_id"], reference)
        if not decision.eligible or decision.issuer_status != "RESOLVED":
            exclusions.append(
                dict(issuer_id=issuer["issuer_id"], reason_codes=list(decision.reasons))
            )
            continue
        names[issuer["issuer_id"]] = issuer["display_name"]
        bindings.append(dict(issuer_id=issuer["issuer_id"], snapshot_id=decision.snapshot_id))
    if exclusions:
        raise RankingGateBlocked(exclusions)
    gate = MagicFormulaActivationGate().evaluate_canonical(
        repository,
        tuple(b["issuer_id"] for b in bindings),
        reference,
    )
    if gate.resolved_issuers != 5 or gate.critical_findings:
        raise RankingGateBlocked(
            [dict(reason_codes=list(gate.critical_findings) or ["MULTISECTOR_GOLDEN_GATE_BLOCKED"])]
        )
    sample = freeze_sample(repository, bindings, reference)
    artifacts = MagicFormulaRankingRepository(ranking_database)
    artifacts.initialize()
    artifacts.save_sample(sample, repository)
    # The database selection has ended. Everything below uses frozen concrete IDs.
    frozen = MagicFormulaRankingRepository(ranking_database).read(sample["sample_id"])
    engine = MagicFormulaStockRankingService()
    items = engine.rank_validation_sample(frozen, repository=repository)
    qa = compare_independent_qa(frozen["inputs"], items)
    determinism_digests = [digest(items)]
    for seed in range(12):
        reordered = deepcopy(frozen)
        if seed == 0:
            reordered["inputs"].reverse()
        else:
            random.Random(seed).shuffle(reordered["inputs"])
        actual = engine.rank_validation_sample(
            reordered,
            repository=CanonicalMagicFormulaRepository(database),
        )
        if actual != items:
            raise ValueError("RANKING_DETERMINISM_FAIL")
        determinism_digests.append(digest(actual))
    document = ranking_artifact(frozen, items, qa)
    artifacts.save_ranking(document, CanonicalMagicFormulaRepository(database))
    recovered = MagicFormulaRankingRepository(ranking_database).read(
        document["ranking_snapshot_id"]
    )
    if recovered != document:
        raise ValueError("RANKING_SNAPSHOT_READBACK_FAIL")
    after = canonical_state(CanonicalMagicFormulaRepository(database))
    if before != after:
        raise ValueError("CANONICAL_ARTIFACT_CHANGED")
    result = dict(
        ranking_engine_gate="PASS",
        validation_sample_status="PASS",
        ranking_engine_status="PASS",
        independent_qa_status="PASS",
        determinism_status="PASS",
        ranking_snapshot_readback="PASS",
        ranking_database=str(ranking_database.resolve()),
        pre_gate=asdict(gate),
        ranking_snapshot=document,
        issuer_names=names,
        determinism_digests=determinism_digests,
        canonical_before_digest=digest(before),
        canonical_after_digest=digest(after),
        excluded_issuers=[],
        open_defects=[],
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "ranking-validation-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf8",
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--ranking-database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.database, args.ranking_database, args.output)
    except RankingGateBlocked as error:
        print(json.dumps(dict(ranking_engine_gate="BLOCKED", exclusions=error.exclusions)))
        raise SystemExit(1) from error
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
