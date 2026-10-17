"""Immutable, separately persisted candidate-universe snapshots."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from income_analytics.application.magic_formula_contract import digest
from income_analytics.application.magic_formula_universe import coverage


class MagicFormulaUniverseRepository:
    def __init__(self, database: Path):
        self.database = database.resolve()

    @contextmanager
    def connection(self, *, write=False, create=False):
        mode = "rwc" if create else "rw" if write else "ro"
        conn = sqlite3.connect(self.database.as_uri() + "?mode=" + mode, uri=True)
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connection(write=True, create=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS magic_formula_universe_snapshots (
                universe_snapshot_id TEXT PRIMARY KEY, reference_date TEXT NOT NULL,
                universe_policy_version TEXT NOT NULL, created_at TEXT NOT NULL,
                document_json TEXT NOT NULL CHECK(json_valid(document_json)),
                document_digest TEXT NOT NULL
            )""")
            for operation in ("UPDATE", "DELETE"):
                conn.execute(f"""CREATE TRIGGER IF NOT EXISTS universe_no_{operation.lower()}
                    BEFORE {operation} ON magic_formula_universe_snapshots
                    BEGIN SELECT RAISE(ABORT,'IMMUTABLE_UNIVERSE_SNAPSHOT'); END""")

    def save(self, document):
        if document["coverage"] != coverage(document["issuers"]):
            raise ValueError("UNIVERSE_COVERAGE_MISMATCH")
        if document["universe_type"] != "CANDIDATE_PUBLISHABLE_UNIVERSE":
            raise ValueError("UNIVERSE_TYPE_MISMATCH")
        if (
            document["tool_status"] != "VALIDATION_REQUIRED"
            or document["ranking_status"] != "INACTIVE"
        ):
            raise ValueError("PUBLICATION_FORBIDDEN")
        with self.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO magic_formula_universe_snapshots VALUES (?,?,?,?,?,?)",
                (
                    document["universe_snapshot_id"],
                    document["reference_date"],
                    document["universe_policy_version"],
                    document["created_at"],
                    json.dumps(document, ensure_ascii=False),
                    digest(document),
                ),
            )

    def read(self, snapshot_id):
        with self.connection() as conn:
            row = conn.execute(
                "SELECT document_json,document_digest "
                "FROM magic_formula_universe_snapshots WHERE universe_snapshot_id=?",
                (snapshot_id,),
            ).fetchone()
        if row is None:
            raise ValueError("MISSING_UNIVERSE_SNAPSHOT")
        document = json.loads(row[0])
        if digest(document) != row[1] or coverage(document["issuers"]) != document["coverage"]:
            raise ValueError("UNIVERSE_READBACK_MISMATCH")
        return document

    def latest(self):
        with self.connection() as conn:
            row = conn.execute(
                "SELECT universe_snapshot_id FROM magic_formula_universe_snapshots "
                # rowid is SQLite's append sequence for this immutable table:
                # UPDATE and DELETE are blocked, so timestamp ties follow insertion order.
                "ORDER BY created_at DESC, rowid DESC LIMIT 1"
            ).fetchone()
        if row is None:
            raise ValueError("MISSING_UNIVERSE_SNAPSHOT")
        return self.read(row[0])
