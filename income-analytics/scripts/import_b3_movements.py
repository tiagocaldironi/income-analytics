"""Client for the auditable B3 import API.

Usage: python scripts/import_b3_movements.py report.xlsx --preview
       python scripts/import_b3_movements.py report.xlsx --apply
"""

from __future__ import annotations

import argparse
import json
from base64 import b64encode
from pathlib import Path
from urllib.request import Request, urlopen

API = "http://127.0.0.1:8000/api"


def post(path: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        f"{API}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urlopen(request).read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Prévia/aplicação auditável de relatório B3")
    parser.add_argument("file", type=Path)
    parser.add_argument("--report-type", choices=("NEGOTIATION", "MOVEMENT"))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--preview", action="store_true")
    action.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    preview = post(
        "/imports/b3/preview",
        {
            "workbook_base64": b64encode(args.file.read_bytes()).decode(),
            "file_name": args.file.name,
            "report_type": args.report_type,
        },
    )
    print(json.dumps(preview, ensure_ascii=False, indent=2, default=str))
    if not args.apply:
        return
    counts = preview["counts"]
    if counts["review_required"] or counts["invalid"]:
        raise SystemExit("Prévia requer revisão; nenhum lançamento foi aplicado.")
    print(
        json.dumps(
            post(f"/imports/b3/{preview['batch_id']}/apply", {}),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
