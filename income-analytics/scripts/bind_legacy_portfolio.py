"""Explicit operator-only legacy binding. Default is dry-run; never imported by HTTP."""

import argparse
import hashlib
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from uuid import UUID, uuid4


def bind_legacy(
    database: Path,
    portfolio_id: str,
    owner_id: str,
    firebase_uid: str,
    *,
    project_id: str,
    actor: str,
    reason: str,
    apply: bool = False,
    maintenance: bool = False,
    backup_directory: Path | None = None,
):
    """Confirmed operator supplies UUIDs, expected Firebase subject and a private audit reason.

    No ownership is inferred from email, portfolio name or first login. Ambiguous
    shared assets with manual prices are refused instead of guessing provenance.
    """
    UUID(portfolio_id)
    UUID(owner_id)
    UUID(actor)
    if not actor.strip() or not reason.strip():
        raise ValueError("Explicit operator and confirmation reason required")
    database = database.resolve(strict=True)
    mode = "rw" if apply else "ro"
    with closing(sqlite3.connect(database.as_uri() + f"?mode={mode}", uri=True)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        if apply:
            if not maintenance or backup_directory is None:
                raise ValueError(
                    "Apply requires maintenance window and consistent backup directory"
                )
            db.execute("BEGIN IMMEDIATE")
        try:
            user = db.execute("SELECT status FROM users WHERE id=?", (owner_id,)).fetchone()
            identity = db.execute(
                "SELECT approved_methods FROM auth_identities "
                "WHERE user_id=? AND subject=? AND issuer=?",
                (owner_id, firebase_uid, "https://securetoken.google.com/" + project_id),
            ).fetchone()
            if user != ("ACTIVE",) or identity is None or not json.loads(identity[0]):
                raise ValueError("Expected verified internal user/Firebase identity not found")
            wallet = db.execute(
                "SELECT owner_user_id FROM portfolios WHERE id=?", (portfolio_id,)
            ).fetchone()
            if wallet is None:
                raise ValueError("Portfolio not found")
            if wallet[0] == owner_id:
                return {"status": "already_owned", "changed": False}
            if wallet[0] is not None:
                raise ValueError("Ownership transfer is forbidden by this tool")
            # A shared legacy manual price has no trustworthy private owner.
            # Require explicit provenance remediation in another reviewed change.
            ambiguous = db.execute(
                "SELECT 1 FROM portfolio_assets mine "
                "JOIN portfolio_assets other ON other.asset_id=mine.asset_id "
                "JOIN market_prices p ON p.asset_id=mine.asset_id "
                "WHERE mine.portfolio_id=? AND other.portfolio_id != mine.portfolio_id "
                "AND (p.provider IS NULL OR p.provider NOT IN "
                "('brapi','brapi_public','b3_cotahist','B3_COTAHIST','b3_etf',"
                "'yahoo_finance','coingecko','twelve_data')) LIMIT 1",
                (portfolio_id,),
            ).fetchone()
            if ambiguous:
                raise ValueError("Ambiguous legacy manual prices require provenance review first")
            if not apply:
                return {"status": "dry_run_ready", "changed": False}
            backup_directory = backup_directory.resolve()
            backup_directory.mkdir(parents=True, exist_ok=True)
            backup = backup_directory / f"before-owner-binding-{uuid4().hex}.db"
            # A separate read connection can back up while BEGIN IMMEDIATE holds
            # a writer reservation, before this transaction changes ownership.
            with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(backup)) as destination:
                    source.backup(destination)
                    if destination.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                        raise ValueError("Backup integrity failed")
            db.execute(
                "UPDATE portfolios SET owner_user_id=? WHERE id=? AND owner_user_id IS NULL",
                (owner_id, portfolio_id),
            )
            # Do not store email, token, ledger data or free-form private reason.
            # The operator's full signed evidence belongs in the private change record.
            db.execute(
                "INSERT INTO security_audit(id,actor_id,action,resource_id,"
                "created_at,evidence_ref) "
                "VALUES (?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    actor,
                    "LEGACY_OWNER_BOUND",
                    portfolio_id,
                    int(time.time()),
                    hashlib.sha256(reason.encode()).hexdigest(),
                ),
            )
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Foreign key integrity failed")
            db.commit()
            return {"status": "bound", "changed": True, "backup": str(backup)}
        except Exception:
            if apply:
                db.rollback()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--firebase-uid", required=True)
    parser.add_argument("--firebase-project-id", required=True)
    parser.add_argument("--confirmed-by", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--maintenance", action="store_true")
    parser.add_argument("--backup-directory", type=Path)
    args = parser.parse_args()
    result = bind_legacy(
        args.database,
        args.portfolio_id,
        args.owner_id,
        args.firebase_uid,
        project_id=args.firebase_project_id,
        actor=args.confirmed_by,
        reason=args.reason,
        apply=args.apply,
        maintenance=args.maintenance,
        backup_directory=args.backup_directory,
    )
    print(json.dumps(result))
