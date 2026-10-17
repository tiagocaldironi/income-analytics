"""Append-only SQLite validation artifacts, separate from canonical fundamentals."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from income_analytics.application.magic_formula_contract import digest
from income_analytics.application.magic_formula_ranking_validation import (
    compare_independent_qa,
    validate_frozen_sample,
)


class MagicFormulaRankingRepository:
    def __init__(self, database: Path):
        self.database = database.resolve()

    def initialize(self):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connection(write=True, create=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS magic_formula_ranking_artifacts (
                artifact_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('FROZEN_SAMPLE','RANKING_SNAPSHOT')),
                document_json TEXT NOT NULL CHECK(json_valid(document_json)),
                document_digest TEXT NOT NULL,
                CHECK(json_extract(document_json,'$.universe_type')='VALIDATION_SAMPLE')
            )""")
            for event in ("UPDATE", "DELETE"):
                conn.execute(f"""CREATE TRIGGER IF NOT EXISTS ranking_no_{event.lower()}
                    BEFORE {event} ON magic_formula_ranking_artifacts
                    BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_RANKING_ARTIFACT'); END""")

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

    def _insert(self, artifact_id, kind, document):
        with self.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO magic_formula_ranking_artifacts VALUES (?,?,?,?)",
                (artifact_id, kind, json.dumps(document, ensure_ascii=False), digest(document)),
            )

    def save_sample(self, sample, canonical_repository):
        validate_frozen_sample(canonical_repository, sample)
        self._insert(sample["sample_id"], "FROZEN_SAMPLE", sample)

    def read(self, artifact_id):
        with self.connection() as conn:
            row = conn.execute(
                "SELECT document_json,document_digest "
                "FROM magic_formula_ranking_artifacts WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise ValueError("MISSING_RANKING_ARTIFACT")
        document = json.loads(row[0])
        if digest(document) != row[1]:
            raise ValueError("RANKING_ARTIFACT_DIGEST_MISMATCH")
        return document

    def save_ranking(self, document, canonical_repository):
        sample = self.read(document["sample_id"])
        inputs = validate_frozen_sample(canonical_repository, sample)
        if document["sample_digest"] != digest(sample) or document["inputs"] != inputs:
            raise ValueError("RANKING_SAMPLE_MISMATCH")
        for key in (
            "universe_type",
            "reference_date",
            "methodology_version",
            "adapter_version",
            "tie_policy",
        ):
            if document[key] != sample[key]:
                raise ValueError("RANKING_CONTRACT_MISMATCH:" + key)
        qa = compare_independent_qa(inputs, document["items"])
        if qa != document["independent_qa"] or document["status"] != "PASS":
            raise ValueError("RANKING_QA_MISMATCH")
        if (
            document["tool_status"] != "VALIDATION_REQUIRED"
            or document["ranking_status"] != "INACTIVE"
        ):
            raise ValueError("PUBLICATION_FORBIDDEN")
        expected_coverage = dict(
            total_considered=5, resolved=5, eligible=5, ranked=5, excluded=0, unresolved=0
        )
        if document["coverage"] != expected_coverage:
            raise ValueError("COVERAGE_MISMATCH")
        by_issuer = {i["issuer_id"]: i for i in inputs}
        for item in document["items"]:
            source = by_issuer[item["issuer_id"]]
            for key, target in (
                ("fundamentals_snapshot_id", "snapshot_id"),
                ("formal_qa_id", "qa_id"),
                ("fundamentals_snapshot_digest", "snapshot_digest"),
            ):
                if item[key] != source[target]:
                    raise ValueError("RANKING_LINEAGE_MISMATCH")
            for key in ("adapter_version", "methodology_version"):
                if item[key] != sample[key]:
                    raise ValueError("RANKING_LINEAGE_VERSION_MISMATCH")
        self._insert(document["ranking_snapshot_id"], "RANKING_SNAPSHOT", document)
