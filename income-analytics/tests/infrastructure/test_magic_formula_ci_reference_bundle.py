"""Approved CVM reference only; no fallback to unverified market snapshots."""

import hashlib
import json
import runpy
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pytest

from income_analytics.application.magic_formula_canonical_ranking import _dfp_filing_dates

ROOT = Path(__file__).resolve().parents[2]
TOOLS = runpy.run_path(str(ROOT / "ci/magic_formula_references.py"))


@pytest.fixture
def reference_directory() -> Iterator[Path]:
    # The runner's pytest basetemp is a sibling of TEMP, not its descendant.
    # Provision exclusively beneath the actual TEMP boundary enforced by CI.
    with TemporaryDirectory(prefix="cvm-reference-") as directory:
        yield Path(directory)


def test_receipt_index_matches_independent_historical_source() -> None:
    raw = TOOLS["verified_payload"]("cvm-dfp-2025-index")
    assert hashlib.sha256(raw).hexdigest() == (
        "a99e5d1db1c0f62bf1090452a41ed7df8bd3b20ecd2df699ccd16c8fc963cc94"
    )
    assert raw.splitlines()[0].decode("latin-1") == (
        "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;CATEG_DOC;ID_DOC;DT_RECEB;LINK_DOC"
    )


def test_index_provisioning_is_deterministic_and_readable(reference_directory: Path) -> None:
    first = TOOLS["provision_receipt_index"](reference_directory / "first-index-only.zip")
    second = TOOLS["provision_receipt_index"](reference_directory / "second-index-only.zip")
    assert first.read_bytes() == second.read_bytes()
    with ZipFile(first) as archive:
        assert archive.namelist() == ["dfp_cia_aberta_2025.csv"]
        assert archive.read(archive.namelist()[0]) == TOOLS["verified_payload"](
            "cvm-dfp-2025-index"
        )
    dates = _dfp_filing_dates(first)
    assert dates
    assert all(len(code) == 6 and date for code, date in dates.items())


def test_provisioning_never_overwrites_existing_files(reference_directory: Path) -> None:
    target = reference_directory / "existing.zip"
    target.write_bytes(b"preserve")
    with pytest.raises(ValueError, match="REFERENCE_DESTINATION_EXISTS"):
        TOOLS["provision_receipt_index"](target)
    assert target.read_bytes() == b"preserve"


def test_reference_digest_mismatch_is_explicit(tmp_path: Path, monkeypatch) -> None:
    manifest = json.loads(TOOLS["PROVENANCE"].read_text(encoding="utf-8"))
    reference = next(row for row in manifest["references"] if row["id"] == "cvm-dfp-2025-index")
    reference["fixture"]["sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setitem(TOOLS["verified_payload"].__globals__, "PROVENANCE", path)
    with pytest.raises(ValueError, match="REFERENCE_DIGEST_MISMATCH"):
        TOOLS["verified_payload"]("cvm-dfp-2025-index")


def test_missing_reference_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    original = Path.read_bytes

    def missing(path: Path) -> bytes:
        if path.name == "dfp_cia_aberta_2025.csv.gz":
            raise FileNotFoundError(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", missing)
    with pytest.raises(ValueError, match="REFERENCE_MISSING:cvm-dfp-2025-index"):
        TOOLS["verified_payload"]("cvm-dfp-2025-index")


def test_provisioning_rejects_non_temporary_destination() -> None:
    with pytest.raises(ValueError, match="REFERENCE_DESTINATION_NOT_TEMPORARY"):
        TOOLS["provision_receipt_index"](ROOT / "forbidden-reference.zip")


@pytest.mark.parametrize("reference", ["ranking-v12.2", "universe-v8", "universe-v9.2"])
def test_unapproved_references_are_rejected(reference: str) -> None:
    with pytest.raises(ValueError, match="REFERENCE_NOT_APPROVED"):
        TOOLS["verified_payload"](reference)
