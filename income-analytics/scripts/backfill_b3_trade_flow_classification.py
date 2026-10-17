"""Safely classify confirmed B3 BUY/SELL events as internal activity.

Run without --apply to inspect the candidate and ambiguous counts. Applying
creates a SQLite backup and updates only events with complete B3 trade evidence.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import unicodedata
from datetime import UTC, datetime
from pathlib import Path


def normalize(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "").upper())
    return "".join(ch for ch in normalized if ch.isalnum())


def is_confirmed_trade(row: sqlite3.Row, metadata: dict[str, object]) -> bool:
    expected_direction = {"BUY": "CREDITO", "SELL": "DEBITO"}.get(row["event_type"])
    return bool(
        row["event_type"] in {"BUY", "SELL"}
        and metadata.get("capital_flow_type") == "UNKNOWN"
        and metadata.get("source") == "B3_MOVEMENT_STATEMENT"
        and normalize(metadata.get("original_movement")) == "TRANSFERENCIALIQUIDACAO"
        and normalize(metadata.get("direction")) == expected_direction
        and metadata.get("quantity_status") == "COMPLETE"
        and metadata.get("financial_status") == "COMPLETE"
        and row["quantity"] is not None
        and row["unit_price"] is not None
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("income_analytics.db"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.database.exists():
        raise SystemExit(f"Banco não encontrado: {args.database}")

    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT id,event_type,quantity,unit_price,metadata_json FROM financial_events "
        "WHERE event_type IN ('BUY','SELL')"
    ).fetchall()
    unknown: list[tuple[sqlite3.Row, dict[str, object]]] = []
    for row in rows:
        metadata = json.loads(row["metadata_json"] or "{}")
        if metadata.get("capital_flow_type", "UNKNOWN") == "UNKNOWN":
            unknown.append((row, metadata))
    candidates = [(row, metadata) for row, metadata in unknown if is_confirmed_trade(row, metadata)]
    b3_unknown = [
        (row, metadata) for row, metadata in unknown
        if metadata.get("source") == "B3_MOVEMENT_STATEMENT"
    ]
    ambiguous_b3 = len(b3_unknown) - len(candidates)
    other_unknown = len(unknown) - len(b3_unknown)

    backup_path = None
    changed = 0
    if args.apply and candidates:
        backup_dir = args.database.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / (
            f"{args.database.stem}-before-b3-flow-backfill-"
            f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.db"
        )
        backup = sqlite3.connect(backup_path)
        connection.backup(backup)
        backup.close()
        with connection:
            for row, metadata in candidates:
                metadata["capital_flow_type"] = "INTERNAL_TRANSFER"
                connection.execute(
                    "UPDATE financial_events SET metadata_json=? WHERE id=?",
                    (json.dumps(metadata, ensure_ascii=False), row["id"]),
                )
                changed += 1
    connection.close()
    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "total_unknown_before": len(unknown),
        "reclassified": changed,
        "would_reclassify": len(candidates) if not args.apply else 0,
        "still_unknown": len(unknown) - changed,
        "ambiguous_b3": ambiguous_b3,
        "other_unknown": other_unknown,
        "backup": str(backup_path) if backup_path else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
