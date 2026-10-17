"""Canonical issuer, immutable golden and snapshot-bound dimensional QA."""

import json

import sqlalchemy as sa

from alembic import op

revision = "0016_magic_formula_canonical_contract"
down_revision = "0015_magic_formula_fundamentals_snapshots"
branch_labels = None
depends_on = None

V2 = "CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE"


def upgrade() -> None:
    op.add_column(
        "magic_formula_fundamentals_snapshots",
        sa.Column(
            "methodology_version",
            sa.String(64),
            nullable=False,
            server_default="MAGIC_FORMULA_STOCKS_V1",
        ),
    )
    op.execute("""CREATE TABLE magic_formula_issuers (
        issuer_id TEXT PRIMARY KEY, cvm_code TEXT NOT NULL UNIQUE,
        cnpj TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, slug TEXT NOT NULL
    )""")
    op.execute("""CREATE TABLE magic_formula_contract_migrations (
        snapshot_id TEXT PRIMARY KEY REFERENCES magic_formula_fundamentals_snapshots(id),
        old_issuer_id TEXT NOT NULL, old_validation_status TEXT NOT NULL,
        old_metrics_json TEXT NOT NULL, migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    op.execute("""CREATE TABLE magic_formula_golden_fixtures (
        fixture_hash TEXT PRIMARY KEY, issuer_id TEXT NOT NULL REFERENCES magic_formula_issuers,
        reference_date TEXT NOT NULL, adapter_version TEXT NOT NULL,
        schema_version TEXT NOT NULL, methodology_version TEXT NOT NULL,
        fixture_json TEXT NOT NULL, registered_at TEXT NOT NULL
    )""")
    op.execute("""CREATE TABLE magic_formula_formal_qa (
        id TEXT PRIMARY KEY,
        snapshot_id TEXT NOT NULL REFERENCES magic_formula_fundamentals_snapshots(id),
        issuer_id TEXT NOT NULL REFERENCES magic_formula_issuers,
        adapter_version TEXT NOT NULL, reference_date TEXT NOT NULL,
        snapshot_digest TEXT NOT NULL,
        fixture_hash TEXT NOT NULL REFERENCES magic_formula_golden_fixtures,
        final_status TEXT NOT NULL CHECK(final_status IN ('PASS','FAIL','REVIEW_REQUIRED')),
        accounting TEXT NOT NULL CHECK(accounting IN ('PASS','FAIL','REVIEW_REQUIRED')),
        security TEXT NOT NULL CHECK(security IN ('PASS','FAIL','REVIEW_REQUIRED')),
        capital TEXT NOT NULL CHECK(capital IN ('PASS','FAIL','REVIEW_REQUIRED')),
        market TEXT NOT NULL CHECK(market IN ('PASS','FAIL','REVIEW_REQUIRED')),
        market_cap TEXT NOT NULL CHECK(market_cap IN ('PASS','FAIL','REVIEW_REQUIRED')),
        derived TEXT NOT NULL CHECK(derived IN ('PASS','FAIL','REVIEW_REQUIRED')),
        lineage TEXT NOT NULL CHECK(lineage IN ('PASS','FAIL','REVIEW_REQUIRED')),
        snapshot_readback TEXT NOT NULL
            CHECK(snapshot_readback IN ('PASS','FAIL','REVIEW_REQUIRED')),
        evidence_json TEXT NOT NULL, validated_at TEXT NOT NULL,
        CHECK(final_status != 'PASS' OR (
            accounting='PASS' AND security='PASS' AND capital='PASS' AND market='PASS'
            AND market_cap='PASS' AND derived='PASS' AND lineage='PASS'
            AND snapshot_readback='PASS'))
    )""")
    op.execute("CREATE INDEX ix_mf_qa_snapshot ON magic_formula_formal_qa(snapshot_id)")
    op.execute("""CREATE TRIGGER mf_snapshot_canonical_issuer
        BEFORE INSERT ON magic_formula_fundamentals_snapshots
        WHEN NOT EXISTS (SELECT 1 FROM magic_formula_issuers WHERE issuer_id=NEW.issuer_id)
        BEGIN SELECT RAISE(ABORT,'CANONICAL_ISSUER_REQUIRED'); END""")
    # Preserve the old decision as history, never turn the aggregate QA into eight PASSes.
    bind = op.get_bind()
    rows = (
        bind.execute(
            sa.text(
                "SELECT id, issuer_id, validation_status, metrics_json "
                "FROM magic_formula_fundamentals_snapshots WHERE adapter_version=:v"
            ),
            {"v": V2},
        )
        .mappings()
        .all()
    )
    for row in rows:
        op.execute(
            sa.text("""INSERT INTO magic_formula_contract_migrations
            (snapshot_id, old_issuer_id, old_validation_status, old_metrics_json)
            VALUES (:id,:issuer_id,:validation_status,:metrics_json)""").bindparams(**dict(row))
        )
        metrics = json.loads(row["metrics_json"])
        metrics.pop("validation_status", None)
        bind.execute(
            sa.text("""UPDATE magic_formula_fundamentals_snapshots
            SET metrics_json=:metrics, validation_status=:status WHERE id=:id"""),
            {
                "id": row["id"],
                "metrics": json.dumps(metrics, ensure_ascii=False),
                "status": "REVIEW_REQUIRED"
                if row["validation_status"] == "PASS"
                else row["validation_status"],
            },
        )
    # A PASS can only be projected from the latest decision for this exact artifact.
    for action in ("INSERT", "UPDATE"):
        op.execute(f"""CREATE TRIGGER mf_snapshot_pass_{action.lower()}
            BEFORE {action} ON magic_formula_fundamentals_snapshots
            WHEN NEW.validation_status='PASS' AND NOT EXISTS (
                SELECT 1 FROM magic_formula_formal_qa q
                WHERE q.snapshot_id=NEW.id AND q.issuer_id=NEW.issuer_id
                AND q.adapter_version=NEW.adapter_version
                AND q.reference_date=NEW.financial_reference_date AND q.final_status='PASS'
                AND q.rowid=(SELECT MAX(rowid) FROM magic_formula_formal_qa
                             WHERE snapshot_id=NEW.id))
            BEGIN SELECT RAISE(ABORT,'PASS_REQUIRES_SNAPSHOT_BOUND_QA'); END""")
        op.execute(f"""CREATE TRIGGER mf_snapshot_status_{action.lower()}
            BEFORE {action} ON magic_formula_fundamentals_snapshots
            WHEN NEW.validation_status NOT IN ('PASS','FAIL','REVIEW_REQUIRED','NOT_VALIDATED')
            OR json_type(NEW.metrics_json,'$.validation_status') IS NOT NULL
            BEGIN SELECT RAISE(ABORT,'NON_CANONICAL_VALIDATION_STATUS'); END""")
    op.execute("""CREATE TRIGGER mf_qa_identity BEFORE INSERT ON magic_formula_formal_qa
        WHEN NOT EXISTS (
            SELECT 1 FROM magic_formula_fundamentals_snapshots s
            JOIN magic_formula_golden_fixtures g ON g.fixture_hash=NEW.fixture_hash
            WHERE s.id=NEW.snapshot_id AND s.issuer_id=NEW.issuer_id
            AND s.adapter_version=NEW.adapter_version
            AND s.financial_reference_date=NEW.reference_date
            AND g.issuer_id=NEW.issuer_id AND g.reference_date=NEW.reference_date
            AND g.adapter_version=NEW.adapter_version
        ) BEGIN SELECT RAISE(ABORT,'QA_ARTIFACT_IDENTITY_MISMATCH'); END""")
    op.execute("""CREATE TRIGGER mf_qa_project_status AFTER INSERT ON magic_formula_formal_qa
        BEGIN UPDATE magic_formula_fundamentals_snapshots SET validation_status=NEW.final_status
        WHERE id=NEW.snapshot_id; END""")
    op.execute("""CREATE TRIGGER mf_snapshot_sealed BEFORE UPDATE OF
        issuer_id, financial_reference_date, market_reference_date, adapter_version,
        methodology_version, metrics_json, lineage_json, normalization_status,
        statement_type, statement_scope ON magic_formula_fundamentals_snapshots
        WHEN EXISTS (SELECT 1 FROM magic_formula_formal_qa WHERE snapshot_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'VALIDATED_ARTIFACT_IMMUTABLE'); END""")
    for table in ("magic_formula_formal_qa", "magic_formula_golden_fixtures"):
        for action in ("UPDATE", "DELETE"):
            op.execute(f"""CREATE TRIGGER {table}_{action.lower()}
                BEFORE {action} ON {table}
                BEGIN SELECT RAISE(ABORT,'EVIDENCE_IMMUTABLE'); END""")


def downgrade() -> None:
    # Dropping immutable QA would destroy approval provenance. Restore a pre-upgrade backup instead.
    raise RuntimeError("Canonical QA migration is forward-only; restore an audited backup.")
