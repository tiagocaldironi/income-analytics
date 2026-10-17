"""Fixed-width source parsing and absence evidence on complete archives."""

import hashlib
from zipfile import ZipFile

import pytest

from income_analytics.infrastructure.historical_price_audit_source import scan_archive


def test_official_close_offset_lineage_and_complete_absence(tmp_path):
    row = bytearray(b" " * 245)
    row[:2] = b"01"
    row[2:10] = b"20251230"
    row[12:24] = b"TEST3       "
    row[24:27] = b"010"
    row[52:56] = b"R$  "
    row[108:121] = b"0000000003257"
    path = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(path, "w") as archive:
        archive.writestr("COTAHIST_A2025.TXT", b"00HEADER\n" + row + b"\n99TRAILER\n")
    rows, manifest = scan_archive(path, {"TEST3", "MISSING3"})
    assert rows["TEST3"][0]["price"] == "32.57"
    assert rows["TEST3"][0]["source_reference"].endswith("|line=2")
    assert "MISSING3" not in rows
    assert manifest["scan_complete"] is True
    assert manifest["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_multiple_members_cannot_prove_absence(tmp_path):
    path = tmp_path / "ambiguous.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("one.txt", "")
        archive.writestr("two.txt", "")
    with pytest.raises(ValueError, match="AMBIGUOUS_COTAHIST_MEMBER"):
        scan_archive(path, {"TEST3"})
