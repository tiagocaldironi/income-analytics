"""Explicitly build and persist one immutable canonical ranking snapshot."""

from income_analytics.application.magic_formula_canonical_ranking import (
    MagicFormulaCanonicalRankingRepository,
    build_canonical_snapshot,
)


def main() -> None:
    snapshot = build_canonical_snapshot()
    MagicFormulaCanonicalRankingRepository().save(snapshot)
    print(
        f"snapshot={snapshot['ranking_snapshot_id']} "
        f"ranked={snapshot['rankable_companies']} "
        f"blocked={snapshot['blocked_companies']} "
        f"hash={snapshot['ranking_hash']}"
    )


if __name__ == "__main__":
    main()
