"""Extract unchanged official CSV rows from locally cached CVM archives.

Run explicitly; fixture updates require reviewing the resulting diff.
No accounting adapter or generated expected metrics are used here.
"""

import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests/fixtures/cvm/phase2_v1"
ISSUERS = {
    "027189": ["Votorantim Cimentos", "construction materials"],
    "004170": ["Vale", "mining"],
    "024813": ["Localiza Fleet", "vehicle rental"],
    "020915": ["MRV", "homebuilding"],
    "023264": ["Ambev", "beverages"],
}
manifest = {
    "version": 1,
    "issuers": ISSUERS,
    "datasets": {},
    "provenance": (
        "Unchanged row excerpts from existing data/cvm official archive cache; "
        "original retrieval timestamp unavailable."
    ),
}
for kind, date in [("DFP", "2025-12-31"), ("ITR", "2025-09-30")]:
    filename = f"{kind.lower()}_cia_aberta_2025.zip"
    payload = (ROOT / "data/cvm" / filename).read_bytes()
    entry = {
        "url": f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{kind}/DADOS/{filename}",
        "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "reference_date": date,
        "members": {},
    }
    with ZipFile(io.BytesIO(payload)) as archive:
        for statement in ("DRE", "BPA", "BPP"):
            name = f"{kind.lower()}_cia_aberta_{statement}_con_2025.csv"
            lines = archive.read(name).decode("latin1").splitlines(keepends=True)
            selected = [lines[0]]
            for line in lines[1:]:
                row = next(csv.DictReader([lines[0], line], delimiter=";"))
                if row["CD_CVM"] in ISSUERS and row["DT_REFER"] == date:
                    selected.append(line)
            content = "".join(selected).encode("latin1")
            (OUT / name).write_bytes(content)
            entry["members"][name] = {
                "sha256": hashlib.sha256(content).hexdigest(),
                "rows": len(selected) - 1,
            }
    manifest["datasets"][kind] = entry
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf8")
