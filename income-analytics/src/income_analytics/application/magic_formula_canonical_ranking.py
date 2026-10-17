"""Build and read immutable MF_BR_2027_V1 ranking snapshots."""

from __future__ import annotations

import csv
import json
import sqlite3
import unicodedata
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID
from zipfile import ZipFile

from income_analytics.application.magic_formula_contract import digest
from income_analytics.application.magic_formula_investable_universe import normalized_sector
from income_analytics.application.magic_formula_preview import _ranking_input
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService

POLICY_ID = "MF_BR_2027_V1"
POLICY_HASH = "96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac"
BASELINE_PATH = Path("docs/appendices/magic_formula_v9_2/methodological_universe.csv")
UNIVERSE_DB = Path("data/magic_formula/universe_snapshots.db")
RANKING_DB = Path("data/magic_formula/canonical_rankings.db")
BASELINE_SNAPSHOT_ID = "ed8a9235-ee14-4a97-93fd-0dbcd87113fb"
RANKING_REFERENCE_DATE = "2025-12-30"
ACCOUNTING_CUTOFF = "2026-10-13"
DFP_ARCHIVE = Path("data/cvm/dfp_cia_aberta_2025.zip")


def build_canonical_snapshot(
    baseline_path: Path = BASELINE_PATH,
    universe_db: Path = UNIVERSE_DB,
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build from the frozen V9.2 eligible universe and audited source snapshot."""
    with baseline_path.open(encoding="utf-8-sig", newline="") as stream:
        baseline = list(csv.DictReader(stream))
    source = _read_universe(universe_db, BASELINE_SNAPSHOT_ID)
    filing_dates = _dfp_filing_dates(DFP_ARCHIVE)
    source_by_cvm = {
        str(int(row["cvm_code"])): row
        for row in source["issuers"]
        if str(row.get("cvm_code", "")).isdigit()
    }
    rankable_rows = []
    blocked = []
    reviews = []
    liquidity_fails = []
    for row in baseline:
        status = row["methodological_status"]
        if status == "ELIGIBLE_DATA_BLOCKED":
            blocked.append(row)
        elif status == "BUYABLE_SECURITY_REVIEW":
            reviews.append(row)
        elif status == "LIQUIDITY_FAIL":
            liquidity_fails.append(row)
        elif status == "ELIGIBLE_COMPLETE":
            issuer = source_by_cvm.get(str(int(row["cvm_code"])))
            if issuer is None or issuer.get("data_readiness_status") != "FULL_DATA_READY":
                raise ValueError(f"COMPLETE_UNIVERSE_SOURCE_MISMATCH:{row['cvm_code']}")
            rankable_rows.append((row, issuer))

    inputs = []
    input_by_issuer = {}
    row_by_issuer = {}
    security_by_issuer = {}
    non_rankable = []
    for baseline_row, issuer in rankable_rows:
        try:
            item = _ranking_input(issuer, source["reference_date"], source["universe_snapshot_id"])
        except (ValueError, KeyError) as exc:
            non_rankable.append(
                {
                    "cvm_code": baseline_row["cvm_code"],
                    "company_name": baseline_row["company"],
                    "ticker": baseline_row["selected_ticker"],
                    "reason": str(exc),
                    "status": "METRIC_DENOMINATOR_UNRESOLVED",
                }
            )
            continue
        selected = next(
            (
                security
                for security in issuer["securities"]
                if security.get("ticker") == baseline_row["selected_ticker"]
            ),
            None,
        )
        if selected is None or not selected.get("effective_market_date"):
            raise ValueError(f"PRICE_DATE_MISMATCH:{baseline_row['cvm_code']}")
        if date.fromisoformat(selected["effective_market_date"]) > date.fromisoformat(
            RANKING_REFERENCE_DATE
        ):
            raise ValueError(f"PRICE_LOOKAHEAD:{baseline_row['cvm_code']}")
        filing_date = filing_dates.get(str(int(baseline_row["cvm_code"])).zfill(6))
        if not filing_date or date.fromisoformat(filing_date) > date.fromisoformat(
            ACCOUNTING_CUTOFF
        ):
            raise ValueError(f"ACCOUNTING_CUTOFF_UNVERIFIED:{baseline_row['cvm_code']}")
        issuer_id = str(UUID(issuer["issuer_id"]))
        item["issuer_id"] = issuer_id
        inputs.append(item)
        input_by_issuer[issuer_id] = item
        row_by_issuer[issuer_id] = (baseline_row, issuer)
        security_by_issuer[issuer_id] = selected

    # Preserve the existing dense metric-rank engine; use stable issuer IDs for score ties.
    ranked = list(MagicFormulaStockRankingService()._rank_approved(inputs))
    ranked.sort(key=lambda row: (row["final_display_order"], row["issuer_id"]))
    results = []
    provenance = []
    for item in ranked:
        baseline_row, issuer = row_by_issuer[item["issuer_id"]]
        commerce_category = None
        if baseline_row["selected_ticker"] == "ASAI3":
            commerce_category = "CASH_AND_CARRY"
        elif (
            _fold(normalized_sector(issuer.get("economic_sector")) or "")
            == "comercio (atacado e varejo)"
        ):
            commerce_category = "TRADITIONAL_RETAIL"
        results.append(
            {
                "company_id": item["issuer_id"],
                "company_name": baseline_row["company"],
                "cvm_code": baseline_row["cvm_code"],
                "selected_security": baseline_row["selected_ticker"],
                "selected_isin": baseline_row["selected_isin"],
                "earnings_yield": str(item["earnings_yield"]),
                "return_on_capital": str(item["return_on_capital"]),
                "earnings_yield_rank": item["earnings_yield_rank"],
                "return_on_capital_rank": item["return_on_capital_rank"],
                "combined_score": item["magic_formula_score"],
                "global_rank": item["final_rank"],
                "commerce_category": commerce_category,
                "aviation_flag": str(issuer.get("cvm_code", "")).zfill(6) in {"024112", "019569"},
                "data_quality_status": "PASS",
                "provenance_status": "COMPLETE",
                "price": security_by_issuer[item["issuer_id"]]["price"],
                "price_reference_date": security_by_issuer[item["issuer_id"]][
                    "effective_market_date"
                ],
                "price_stale_calendar_days": (
                    date.fromisoformat(RANKING_REFERENCE_DATE)
                    - date.fromisoformat(
                        security_by_issuer[item["issuer_id"]]["effective_market_date"]
                    )
                ).days,
                "ebit": input_by_issuer[item["issuer_id"]]["ebit"],
                "enterprise_value": input_by_issuer[item["issuer_id"]]["enterprise_value"],
                "invested_capital": input_by_issuer[item["issuer_id"]]["invested_capital"],
                "financial_reference_date": source["reference_date"],
                "filing_date": filing_dates[str(int(baseline_row["cvm_code"])).zfill(6)],
                "ranking_reference_date": RANKING_REFERENCE_DATE,
            }
        )
        provenance.append(
            {
                "company_id": item["issuer_id"],
                "ticker": baseline_row["selected_ticker"],
                "source_snapshot_id": source["universe_snapshot_id"],
                "source_snapshot_digest": source["_document_digest"],
                "accounting": issuer["accounting_readiness"]["evidence"],
                "market": issuer["market_readiness"],
                "selected_security_source": security_by_issuer[item["issuer_id"]],
                "selected_isin": baseline_row["selected_isin"],
                "price_reference_date": RANKING_REFERENCE_DATE,
                "accounting_cutoff": ACCOUNTING_CUTOFF,
                "filing_date": filing_dates[str(int(baseline_row["cvm_code"])).zfill(6)],
            }
        )

    rank_hash = ranking_digest(
        POLICY_HASH,
        source["universe_snapshot_id"],
        source["_document_digest"],
        RANKING_REFERENCE_DATE,
        ACCOUNTING_CUTOFF,
        results,
    )
    snapshot_id = "mf-" + rank_hash[:24]
    created_at = created_at or datetime.now(UTC).isoformat()
    complete_count = sum(row["methodological_status"] == "ELIGIBLE_COMPLETE" for row in baseline)
    methodological_denominator = complete_count + len(blocked)
    conservative_denominator = complete_count + len(blocked) + len(reviews)
    return {
        "ranking_snapshot_id": snapshot_id,
        "policy_id": POLICY_ID,
        "policy_hash": POLICY_HASH,
        "data_snapshot_id": source["universe_snapshot_id"],
        "data_snapshot_digest": source["_document_digest"],
        "ranking_reference_date": RANKING_REFERENCE_DATE,
        "accounting_cutoff": ACCOUNTING_CUTOFF,
        "created_at": created_at,
        "rankable_companies": len(results),
        "blocked_companies": len(blocked),
        "review_companies": len(reviews),
        "liquidity_fail_companies": len(liquidity_fails),
        "eligible_complete_companies": complete_count,
        "methodological_denominator": methodological_denominator,
        "conservative_denominator": conservative_denominator,
        "methodological_coverage": (
            f"{Decimal(complete_count) / Decimal(methodological_denominator) * 100:.2f}%"
        ),
        "conservative_coverage": (
            f"{Decimal(complete_count) / Decimal(conservative_denominator) * 100:.2f}%"
        ),
        "ranking_hash": rank_hash,
        "ranking_style": "DENSE_METRIC_RANKS; COMPETITION_GLOBAL_RANK",
        "tie_policy": "SCORE_ASC; COMPANY_ID_ASC",
        "results": results,
        "provenance": provenance,
        "blocked": blocked,
        "reviews": reviews,
        "liquidity_fails": liquidity_fails,
        "metric_non_rankable": non_rankable,
    }


class MagicFormulaCanonicalRankingRepository:
    """SQLite append-only store for canonical ranking snapshots and provenance."""

    def __init__(self, database: Path = RANKING_DB):
        self.database = database.resolve()

    def initialize(self) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS magic_formula_ranking_snapshots (
                    ranking_snapshot_id TEXT PRIMARY KEY, policy_id TEXT NOT NULL,
                    policy_hash TEXT NOT NULL, ranking_reference_date TEXT NOT NULL,
                    accounting_cutoff TEXT NOT NULL, ranking_hash TEXT NOT NULL UNIQUE,
                    document_json TEXT NOT NULL CHECK(json_valid(document_json)),
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS magic_formula_ranking_results (
                    ranking_snapshot_id TEXT NOT NULL REFERENCES magic_formula_ranking_snapshots,
                    company_id TEXT NOT NULL, global_rank INTEGER NOT NULL,
                    result_json TEXT NOT NULL CHECK(json_valid(result_json)),
                    PRIMARY KEY(ranking_snapshot_id, company_id)
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS magic_formula_ranking_provenance (
                    ranking_snapshot_id TEXT NOT NULL REFERENCES magic_formula_ranking_snapshots,
                    company_id TEXT NOT NULL,
                    provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json)),
                    PRIMARY KEY(ranking_snapshot_id, company_id)
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS magic_formula_ranking_release_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ranking_snapshot_id TEXT NOT NULL REFERENCES magic_formula_ranking_snapshots,
                    release_status TEXT NOT NULL CHECK(
                        release_status IN ('STAGED','PUBLISHED','INVALIDATED')
                    ),
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS magic_formula_ranking_release_state_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ranking_snapshot_id TEXT NOT NULL REFERENCES magic_formula_ranking_snapshots,
                    release_status TEXT NOT NULL CHECK(
                        release_status IN ('STAGED','PUBLISHED','INVALIDATED')
                    ),
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE INDEX IF NOT EXISTS magic_formula_release_latest_idx
                ON magic_formula_ranking_release_events(ranking_snapshot_id,event_id DESC)"""
            )
            conn.execute(
                """CREATE INDEX IF NOT EXISTS magic_formula_release_state_latest_idx
                ON magic_formula_ranking_release_state_events(ranking_snapshot_id,event_id DESC)"""
            )
            conn.execute(
                """CREATE TRIGGER IF NOT EXISTS magic_formula_release_no_update
                BEFORE UPDATE ON magic_formula_ranking_release_events
                BEGIN SELECT RAISE(ABORT,'IMMUTABLE_RANKING_RELEASE_EVENT'); END"""
            )
            conn.execute(
                """CREATE TRIGGER IF NOT EXISTS magic_formula_release_no_delete
                BEFORE DELETE ON magic_formula_ranking_release_events
                BEGIN SELECT RAISE(ABORT,'IMMUTABLE_RANKING_RELEASE_EVENT'); END"""
            )
            for action in ("UPDATE", "DELETE"):
                conn.execute(
                    f"""CREATE TRIGGER IF NOT EXISTS magic_formula_release_state_no_{action.lower()}
                    BEFORE {action} ON magic_formula_ranking_release_state_events
                    BEGIN SELECT RAISE(ABORT,'IMMUTABLE_RANKING_RELEASE_EVENT'); END"""
                )
            for table in (
                "magic_formula_ranking_snapshots",
                "magic_formula_ranking_results",
                "magic_formula_ranking_provenance",
            ):
                for action in ("UPDATE", "DELETE"):
                    conn.execute(
                        f"""CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}
                        BEFORE {action} ON {table}
                        BEGIN SELECT RAISE(ABORT,'IMMUTABLE_RANKING_SNAPSHOT'); END"""
                    )
            conn.commit()

    def record_release_event(
        self, ranking_snapshot_id: str, release_status: str, reason: str, *, created_at: str
    ) -> None:
        """Append an auditable release decision without mutating snapshot history."""
        if release_status not in {"STAGED", "PUBLISHED", "INVALIDATED"}:
            raise ValueError("INVALID_RANKING_RELEASE_STATUS")
        if not reason.strip():
            raise ValueError("RANKING_RELEASE_REASON_REQUIRED")
        self.initialize()
        with sqlite3.connect(self.database) as conn:
            exists = conn.execute(
                "SELECT 1 FROM magic_formula_ranking_snapshots WHERE ranking_snapshot_id=?",
                (ranking_snapshot_id,),
            ).fetchone()
            if exists is None:
                raise ValueError("MISSING_RANKING_SNAPSHOT")
            latest_event = conn.execute(
                "SELECT release_status FROM magic_formula_ranking_release_state_events "
                "WHERE ranking_snapshot_id=? ORDER BY event_id DESC LIMIT 1",
                (ranking_snapshot_id,),
            ).fetchone()
            if latest_event is None:
                latest_event = conn.execute(
                    "SELECT release_status FROM magic_formula_ranking_release_events "
                    "WHERE ranking_snapshot_id=? ORDER BY event_id DESC LIMIT 1",
                    (ranking_snapshot_id,),
                ).fetchone()
            if (
                latest_event
                and latest_event[0] == "INVALIDATED"
                and release_status
                in {
                    "STAGED",
                    "PUBLISHED",
                }
            ):
                raise ValueError("INVALIDATED_SNAPSHOT_CANNOT_BE_REPUBLISHED")
            if latest_event and latest_event[0] == "PUBLISHED" and release_status == "STAGED":
                raise ValueError("PUBLISHED_SNAPSHOT_CANNOT_BE_RESTAGED")
            if (
                release_status == "STAGED"
                or conn.execute(
                    "SELECT 1 FROM magic_formula_ranking_release_state_events "
                    "WHERE ranking_snapshot_id=? LIMIT 1",
                    (ranking_snapshot_id,),
                ).fetchone()
            ):
                conn.execute(
                    "INSERT INTO magic_formula_ranking_release_state_events "
                    "(ranking_snapshot_id,release_status,reason,created_at) VALUES (?,?,?,?)",
                    (ranking_snapshot_id, release_status, reason, created_at),
                )
            else:
                conn.execute(
                    "INSERT INTO magic_formula_ranking_release_events "
                    "(ranking_snapshot_id,release_status,reason,created_at) VALUES (?,?,?,?)",
                    (ranking_snapshot_id, release_status, reason, created_at),
                )

    def save(self, document: dict[str, Any], *, initial_release_status: str = "PUBLISHED") -> None:
        if document["policy_id"] != POLICY_ID or document["policy_hash"] != POLICY_HASH:
            raise ValueError("ACTIVE_POLICY_MISMATCH")
        if initial_release_status not in {"STAGED", "PUBLISHED"}:
            raise ValueError("INVALID_INITIAL_RANKING_RELEASE_STATUS")
        if (
            ranking_digest(
                document["policy_hash"],
                document["data_snapshot_id"],
                document["data_snapshot_digest"],
                document["ranking_reference_date"],
                document["accounting_cutoff"],
                document["results"],
            )
            != document["ranking_hash"]
        ):
            raise ValueError("RANKING_HASH_MISMATCH")
        self.initialize()
        with sqlite3.connect(self.database) as conn:
            conn.execute("BEGIN IMMEDIATE")
            inserted = conn.execute(
                """INSERT OR IGNORE INTO magic_formula_ranking_snapshots
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    document["ranking_snapshot_id"],
                    document["policy_id"],
                    document["policy_hash"],
                    document["ranking_reference_date"],
                    document["accounting_cutoff"],
                    document["ranking_hash"],
                    json.dumps(document, ensure_ascii=False, sort_keys=True),
                    document["created_at"],
                ),
            )
            conn.executemany(
                """INSERT OR IGNORE INTO magic_formula_ranking_results VALUES (?,?,?,?)""",
                [
                    (
                        document["ranking_snapshot_id"],
                        row["company_id"],
                        row["global_rank"],
                        json.dumps(row, ensure_ascii=False, sort_keys=True),
                    )
                    for row in document["results"]
                ],
            )
            conn.executemany(
                """INSERT OR IGNORE INTO magic_formula_ranking_provenance VALUES (?,?,?)""",
                [
                    (
                        document["ranking_snapshot_id"],
                        row["company_id"],
                        json.dumps(row, ensure_ascii=False, sort_keys=True),
                    )
                    for row in document["provenance"]
                ],
            )
            if inserted.rowcount:
                event_table = (
                    "magic_formula_ranking_release_state_events"
                    if initial_release_status == "STAGED"
                    else "magic_formula_ranking_release_events"
                )
                conn.execute(
                    f"INSERT INTO {event_table} "
                    "(ranking_snapshot_id,release_status,reason,created_at) VALUES (?,?,?,?)",
                    (
                        document["ranking_snapshot_id"],
                        initial_release_status,
                        "INITIAL_SNAPSHOT_PERSISTENCE",
                        document["created_at"],
                    ),
                )
            conn.commit()

    def read(self, ranking_snapshot_id: str) -> dict[str, Any]:
        if not self.database.exists():
            raise ValueError("MISSING_RANKING_SNAPSHOT")
        with sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True) as conn:
            row = conn.execute(
                "SELECT document_json FROM magic_formula_ranking_snapshots "
                "WHERE ranking_snapshot_id=?",
                (ranking_snapshot_id,),
            ).fetchone()
        if row is None:
            raise ValueError("MISSING_RANKING_SNAPSHOT")
        document = json.loads(row[0])
        if (
            ranking_digest(
                document["policy_hash"],
                document["data_snapshot_id"],
                document["data_snapshot_digest"],
                document["ranking_reference_date"],
                document["accounting_cutoff"],
                document["results"],
            )
            != document["ranking_hash"]
        ):
            raise ValueError("RANKING_HASH_MISMATCH")
        return document

    def read_published(self, ranking_snapshot_id: str) -> dict[str, Any]:
        """Read a snapshot by id only when its latest release event is published."""
        document = self.read(ranking_snapshot_id)
        with sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True) as conn:
            legacy = conn.execute(
                "SELECT release_status FROM magic_formula_ranking_release_events "
                "WHERE ranking_snapshot_id=? ORDER BY event_id DESC LIMIT 1",
                (ranking_snapshot_id,),
            ).fetchone()
            state = conn.execute(
                "SELECT release_status FROM magic_formula_ranking_release_state_events "
                "WHERE ranking_snapshot_id=? ORDER BY event_id DESC LIMIT 1",
                (ranking_snapshot_id,),
            ).fetchone()
        release_status = (state or legacy or ("PUBLISHED",))[0]
        if release_status != "PUBLISHED":
            raise ValueError("RANKING_NOT_PUBLISHED")
        return document

    def latest(self) -> dict[str, Any] | None:
        if not self.database.exists():
            return None
        with sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True) as conn:
            rows = conn.execute(
                """SELECT s.document_json FROM magic_formula_ranking_snapshots AS s
                LEFT JOIN magic_formula_ranking_release_events AS e ON e.event_id=(
                    SELECT MAX(e2.event_id) FROM magic_formula_ranking_release_events AS e2
                    WHERE e2.ranking_snapshot_id=s.ranking_snapshot_id
                )
                LEFT JOIN magic_formula_ranking_release_state_events AS r ON r.event_id=(
                    SELECT MAX(r2.event_id) FROM magic_formula_ranking_release_state_events AS r2
                    WHERE r2.ranking_snapshot_id=s.ranking_snapshot_id
                )
                WHERE COALESCE(r.release_status,e.release_status,'PUBLISHED')='PUBLISHED'
                ORDER BY s.created_at DESC, s.ranking_snapshot_id DESC"""
            ).fetchall()
        for (serialized,) in rows:
            document = json.loads(serialized)
            if (
                ranking_digest(
                    document["policy_hash"],
                    document["data_snapshot_id"],
                    document["data_snapshot_digest"],
                    document["ranking_reference_date"],
                    document["accounting_cutoff"],
                    document["results"],
                )
                == document["ranking_hash"]
            ):
                return document
        return None


def ranking_read_model(
    snapshot: dict[str, Any] | None,
    *,
    company_metadata: dict[str, dict[str, Any]] | None = None,
    query: str = "",
    exclude_retail: bool = False,
    exclude_aviation: bool = False,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ValueError("INVALID_PAGINATION")
    if snapshot is None:
        return {"snapshot_available": False, "items": [], "total": 0, "page": page}
    needle = query.strip().casefold()
    filtered = []
    for source_row in snapshot["results"]:
        row = dict(source_row)
        if company_metadata is not None:
            row.update(company_metadata.get(row["company_id"], {}))
        if (
            needle
            and needle
            not in (
                row["company_name"] + " " + row["selected_security"] + " " + row["cvm_code"]
            ).casefold()
        ):
            continue
        if exclude_retail and row.get("commerce_category") == "TRADITIONAL_RETAIL":
            continue
        if exclude_aviation and row.get("aviation_flag"):
            continue
        filtered.append(row)
    start = (page - 1) * page_size
    return {
        "snapshot_available": True,
        "snapshot": {
            key: value
            for key, value in snapshot.items()
            if key
            not in {
                "results",
                "provenance",
                "blocked",
                "reviews",
                "liquidity_fails",
                "metric_non_rankable",
            }
        },
        "items": filtered[start : start + page_size],
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
        "pages": (len(filtered) + page_size - 1) // page_size,
        "summary": {
            "ranked": snapshot["rankable_companies"],
            "blocked": snapshot["blocked_companies"],
            "reviews": snapshot["review_companies"],
            "liquidity_fail": snapshot["liquidity_fail_companies"],
            "metric_non_rankable": len(snapshot["metric_non_rankable"]),
            "methodological_coverage": snapshot["methodological_coverage"],
            "conservative_coverage": snapshot["conservative_coverage"],
        },
        "filters": {"exclude_retail": exclude_retail, "exclude_aviation": exclude_aviation},
        "global_rank_preserved": True,
    }


@lru_cache(maxsize=8)
def _company_metadata_for_data_snapshot(
    data_snapshot_id: str, expected_digest: str
) -> dict[str, dict[str, Any]]:
    """Read descriptive issuer metadata from the exact immutable source snapshot."""
    source = _read_universe(UNIVERSE_DB, data_snapshot_id)
    if source["_document_digest"] != expected_digest:
        raise ValueError("RANKING_SOURCE_SNAPSHOT_MISMATCH")
    metadata = {}
    for issuer in source["issuers"]:
        metadata[issuer["issuer_id"]] = {
            "sector": issuer.get("economic_sector"),
            "sector_source_reference": issuer.get("sector_source_reference"),
        }
    return metadata


def company_metadata_for_snapshot(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return non-ranking descriptive metadata tied to a published snapshot's source."""
    return _company_metadata_for_data_snapshot(
        snapshot["data_snapshot_id"], snapshot["data_snapshot_digest"]
    )


def _read_universe(database: Path, snapshot_id: str) -> dict[str, Any]:
    uri = f"file:{database.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        row = conn.execute(
            """SELECT document_json,document_digest FROM magic_formula_universe_snapshots
            WHERE universe_snapshot_id=?""",
            (snapshot_id,),
        ).fetchone()
    if row is None:
        raise ValueError("MISSING_UNIVERSE_SNAPSHOT")
    document = json.loads(row[0])
    if digest(document) != row[1]:
        raise ValueError("UNIVERSE_SNAPSHOT_DIGEST_MISMATCH")
    document["_document_digest"] = row[1]
    return document


def _fold(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


def _dfp_filing_dates(archive: Path) -> dict[str, str]:
    """Read official receipt dates for FY2025 DFPs from the CVM archive index."""
    with ZipFile(archive) as bundle:
        with bundle.open("dfp_cia_aberta_2025.csv") as raw:
            import io

            rows = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1"), delimiter=";")
            dates: dict[str, tuple[int, str]] = {}
            for row in rows:
                if row.get("DT_REFER") != "2025-12-31" or row.get("CATEG_DOC") != "DFP":
                    continue
                code = str(row.get("CD_CVM", "")).zfill(6)
                received = row.get("DT_RECEB") or ""
                version = int(row.get("VERSAO") or 0)
                if code.isdigit() and received and (code not in dates or version >= dates[code][0]):
                    dates[code] = (version, received)
    return {code: received for code, (_, received) in dates.items()}


def ranking_digest(
    policy_hash: str,
    data_snapshot_id: str,
    data_snapshot_digest: str,
    reference_date: str,
    accounting_cutoff: str,
    results: list[dict[str, Any]],
) -> str:
    """Hash the immutable ranking and its temporal/policy context."""
    return digest(
        {
            "policy_hash": policy_hash,
            "data_snapshot_id": data_snapshot_id,
            "data_snapshot_digest": data_snapshot_digest,
            "ranking_reference_date": reference_date,
            "accounting_cutoff": accounting_cutoff,
            "results": results,
        }
    )
