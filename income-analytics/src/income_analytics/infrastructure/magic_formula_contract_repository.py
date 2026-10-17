"""Canonical evidence repository with explicit database paths and no startup writes."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from income_analytics.application.magic_formula_contract import (
    ADAPTER_VERSION,
    DIMENSIONS,
    EligibilityDecision,
    canonical_identity,
    digest,
    final_qa_status,
    golden_contract_errors,
    is_ranking_eligible,
    snapshot_digest,
)
from income_analytics.application.magic_formula_formal_qa import evaluate_formal_qa


class CanonicalMagicFormulaRepository:
    def __init__(self, database: Path):
        self.database = database.resolve()

    @contextmanager
    def connection(self, *, write=False):
        # mode=rw never accidentally creates a database; Alembic owns schema creation.
        conn = sqlite3.connect(
            self.database.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.commit()
        except BaseException:
            if write:
                conn.rollback()
            raise
        finally:
            conn.close()

    def register_issuer(self, *, cvm_code, cnpj, display_name, slug, issuer_id=None) -> dict:
        code, tax_id = canonical_identity(cvm_code, cnpj)
        with self.connection(write=True) as conn:
            rows = conn.execute(
                "SELECT * FROM magic_formula_issuers WHERE cvm_code=? OR cnpj=?", (code, tax_id)
            ).fetchall()
            if rows:
                if len(rows) != 1 or rows[0]["cvm_code"] != code or rows[0]["cnpj"] != tax_id:
                    raise ValueError("ISSUER_IDENTITY_CONFLICT")
                if issuer_id is not None and issuer_id != rows[0]["issuer_id"]:
                    raise ValueError("ISSUER_IDENTITY_CONFLICT")
                return dict(rows[0])
            identity = str(UUID(issuer_id)) if issuer_id else str(uuid4())
            conn.execute(
                "INSERT INTO magic_formula_issuers VALUES (?,?,?,?,?)",
                (identity, code, tax_id, display_name, slug),
            )
            return dict(
                issuer_id=identity, cvm_code=code, cnpj=tax_id, display_name=display_name, slug=slug
            )

    def read_snapshot(self, snapshot_id: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM magic_formula_fundamentals_snapshots WHERE id=?", (snapshot_id,)
            ).fetchone()
            return dict(row) if row else None

    def adopt_existing_snapshot(self, snapshot_id: str, issuer_id: str) -> None:
        """Metadata-only adoption; financially immutable and idempotent."""
        with self.connection(write=True) as conn:
            row = conn.execute(
                "SELECT * FROM magic_formula_fundamentals_snapshots WHERE id=?", (snapshot_id,)
            ).fetchone()
            issuer = conn.execute(
                "SELECT * FROM magic_formula_issuers WHERE issuer_id=?", (issuer_id,)
            ).fetchone()
            if row is None or issuer is None or row["adapter_version"] != ADAPTER_VERSION:
                raise ValueError("MISSING_V2_SNAPSHOT_OR_ISSUER")
            metrics = json.loads(row["metrics_json"])
            if str(int(metrics["cvm_code"])).zfill(6) != issuer["cvm_code"]:
                raise ValueError("SNAPSHOT_ISSUER_MISMATCH")
            if row["issuer_id"] == issuer_id and metrics.get("issuer_id") == issuer_id:
                return
            if conn.execute(
                "SELECT 1 FROM magic_formula_formal_qa WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone():
                raise ValueError("VALIDATED_ARTIFACT_IMMUTABLE")
            metrics.pop("validation_status", None)
            metrics["issuer_id"] = issuer_id
            conn.execute(
                "UPDATE magic_formula_fundamentals_snapshots "
                "SET issuer_id=?, metrics_json=? WHERE id=?",
                (issuer_id, json.dumps(metrics, ensure_ascii=False), snapshot_id),
            )

    def register_golden(self, fixture: dict) -> str:
        # Incomplete evidence must be retainable for a REVIEW_REQUIRED decision.
        # Identity/schema defects cannot be associated with a financial artifact.
        errors = tuple(
            error
            for error in golden_contract_errors(fixture)
            if not error.startswith("MISSING_") and error != "GOLDEN_NOT_READY"
        )
        if errors:
            raise ValueError(",".join(errors))
        fixture_hash = digest(fixture)
        issuer = fixture["issuer"]
        with self.connection(write=True) as conn:
            row = conn.execute(
                "SELECT * FROM magic_formula_issuers WHERE issuer_id=?", (issuer["issuer_id"],)
            ).fetchone()
            if row is None or (row["cvm_code"], row["cnpj"]) != canonical_identity(
                issuer["cvm_code"],
                issuer["cnpj"],
            ):
                raise ValueError("GOLDEN_ISSUER_MISMATCH")
            conn.execute(
                "INSERT OR IGNORE INTO magic_formula_golden_fixtures VALUES (?,?,?,?,?,?,?,?)",
                (
                    fixture_hash,
                    issuer["issuer_id"],
                    fixture["reference_date"],
                    fixture["reference"]["adapter_version"],
                    fixture["schema_version"],
                    fixture["methodology_version"],
                    json.dumps(fixture, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return fixture_hash

    def validate_snapshot(self, snapshot_id: str, fixture_hash: str) -> str:
        """Recover all dimensions from evidence; callers cannot supply PASS flags."""
        first = self.read_snapshot(snapshot_id)
        second = self.read_snapshot(snapshot_id)  # prior connection has been closed
        if first is None or second is None:
            raise ValueError("MISSING_SNAPSHOT")
        with self.connection() as conn:
            stored = conn.execute(
                "SELECT fixture_json FROM magic_formula_golden_fixtures WHERE fixture_hash=?",
                (fixture_hash,),
            ).fetchone()
        if stored is None:
            raise ValueError("MISSING_GOLDEN")
        fixture = json.loads(stored[0])
        if fixture["issuer"]["issuer_id"] != second["issuer_id"] or (
            fixture["reference_date"] != second["financial_reference_date"]
            or fixture["reference"]["adapter_version"] != second["adapter_version"]
        ):
            raise ValueError("QA_ARTIFACT_IDENTITY_MISMATCH")
        dimensions = evaluate_formal_qa(fixture, second, readback_matches=first == second)
        final = final_qa_status(dimensions)
        fingerprint = snapshot_digest(second)
        evidence = json.dumps([asdict(d) for d in dimensions], ensure_ascii=False)
        with self.connection(write=True) as conn:
            current = dict(
                conn.execute(
                    "SELECT * FROM magic_formula_fundamentals_snapshots WHERE id=?", (snapshot_id,)
                ).fetchone()
            )
            if snapshot_digest(current) != fingerprint:
                raise ValueError("SNAPSHOT_CHANGED_DURING_QA")
            previous = conn.execute(
                "SELECT * FROM magic_formula_formal_qa "
                "WHERE snapshot_id=? ORDER BY rowid DESC LIMIT 1",
                (snapshot_id,),
            ).fetchone()
            if (
                previous
                and previous["snapshot_digest"] == fingerprint
                and (
                    previous["fixture_hash"] == fixture_hash
                    and previous["evidence_json"] == evidence
                )
            ):
                return previous["id"]
            qa_id = str(uuid4())
            columns = (
                "id",
                "snapshot_id",
                "issuer_id",
                "adapter_version",
                "reference_date",
                "snapshot_digest",
                "fixture_hash",
                "final_status",
                *DIMENSIONS,
                "evidence_json",
                "validated_at",
            )
            values = (
                qa_id,
                snapshot_id,
                second["issuer_id"],
                second["adapter_version"],
                second["financial_reference_date"],
                fingerprint,
                fixture_hash,
                final.value,
                *(d.status.value for d in dimensions),
                evidence,
                datetime.now(UTC).isoformat(),
            )
            conn.execute(
                f"INSERT INTO magic_formula_formal_qa ({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                values,
            )
            # DB trigger projects final_status into the sole validation column atomically.
            return qa_id

    def eligibility(
        self, issuer_id: str, reference_date: str, *, snapshot_id: str | None = None
    ) -> EligibilityDecision:
        with self.connection() as conn:
            if snapshot_id is None:
                row = conn.execute(
                    "SELECT * FROM magic_formula_fundamentals_snapshots "
                    "WHERE issuer_id=? AND financial_reference_date=? "
                    "AND adapter_version=? ORDER BY created_at DESC LIMIT 1",
                    (issuer_id, reference_date, ADAPTER_VERSION),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM magic_formula_fundamentals_snapshots WHERE id=?", (snapshot_id,)
                ).fetchone()
            snapshot = dict(row) if row else None
            qa = fixture = None
            if snapshot:
                row = conn.execute(
                    "SELECT * FROM magic_formula_formal_qa WHERE snapshot_id=? "
                    "ORDER BY rowid DESC LIMIT 1",
                    (snapshot["id"],),
                ).fetchone()
                if row:
                    qa = dict(row)
                    qa["dimensions"] = json.loads(qa["evidence_json"])
                    stored = conn.execute(
                        "SELECT fixture_json FROM magic_formula_golden_fixtures "
                        "WHERE fixture_hash=?",
                        (qa["fixture_hash"],),
                    ).fetchone()
                    fixture = json.loads(stored[0]) if stored else None
            return is_ranking_eligible(
                issuer_id=issuer_id,
                reference_date=reference_date,
                snapshot=snapshot,
                qa=qa,
                fixture=fixture,
            )
