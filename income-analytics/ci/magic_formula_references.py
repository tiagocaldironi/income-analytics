"""Verify approved local references; never download or rebuild historical data."""

import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "docs/engineering/cicd-assessment/magic_formula_reference_provenance.json"


def verified_payload(reference_id: str) -> bytes:
    """Reject pending references before opening any candidate source file."""
    manifest = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    reference = next(item for item in manifest["references"] if item["id"] == reference_id)
    if reference["state"] != "VERIFIED" or not reference["ci_approved"]:
        raise ValueError(f"REFERENCE_NOT_APPROVED:{reference_id}")
    path = (ROOT / reference["fixture"]["path"]).resolve()
    if not path.is_relative_to(ROOT / "tests/fixtures/cvm"):
        raise ValueError("REFERENCE_PATH_FORBIDDEN")
    try:
        payload = path.read_bytes()
    except FileNotFoundError as error:
        raise ValueError(f"REFERENCE_MISSING:{reference_id}") from error
    if hashlib.sha256(payload).hexdigest() != reference["fixture"]["sha256"]:
        raise ValueError(f"REFERENCE_DIGEST_MISMATCH:{reference_id}")
    raw = gzip.decompress(payload)
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError(f"REFERENCE_CONTENT_MISMATCH:{reference_id}")
    return raw


def provision_receipt_index(destination: Path) -> Path:
    """Create a derivative, index-only test ZIP in an unused temporary path.

    This is not the complete official DFP archive and must not be used to
    rebuild accounting evidence or claim that archive's SHA-256.
    """
    target = destination.resolve()
    if not target.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError("REFERENCE_DESTINATION_NOT_TEMPORARY")
    if target.exists():
        raise ValueError("REFERENCE_DESTINATION_EXISTS")
    payload = verified_payload("cvm-dfp-2025-index")
    member = ZipInfo("dfp_cia_aberta_2025.csv", date_time=(1980, 1, 1, 0, 0, 0))
    member.compress_type = ZIP_DEFLATED
    with ZipFile(target, "x") as archive:
        archive.writestr(member, payload)
    return target
