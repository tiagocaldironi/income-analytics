"""Independently validate the V3 batch candidate against before and raw sources."""

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path, before_dir: Path, evidence_dir: Path):
    before = json.loads((before_dir / "snapshot-before.json").read_text(encoding="utf-8"))
    inventory = json.loads((before_dir / "before-inventory.json").read_text(encoding="utf-8"))
    candidate = json.loads((output / "candidate.json").read_text(encoding="utf-8"))
    run_data = candidate["identity_recovery_run"]
    assert run_data["parent_id"] == before["universe_snapshot_id"] == inventory["snapshot_id"]
    cases = run_data["case_results"]
    assert len(cases) == inventory["price_only_blockers"] == 36
    assert len({c["blocker_id"] for c in cases}) == 36
    assert all(
        c["terminal_status"]
        in {
            "RECOVERED",
            "IDENTITY_CONFIRMED_PRICE_UNAVAILABLE",
            "NO_TRADE_ON_REFERENCE_DATE",
            "NOT_LISTED_ON_REFERENCE_DATE",
            "DELISTED_BEFORE_REFERENCE_DATE",
            "SOURCE_GAP",
            "AMBIGUOUS_IDENTITY",
            "UNRESOLVED",
        }
        for c in cases
    )
    assert sum(run_data["terminal_status_counts"].values()) == 36
    before_by_id = {i["issuer_id"]: i for i in before["issuers"]}
    after_by_id = {i["issuer_id"]: i for i in candidate["issuers"]}
    recovered = [c for c in cases if c["terminal_status"] == "RECOVERED"]
    assert len(recovered) == 5
    zip_path = Path("data/cotahist/COTAHIST_A2025.ZIP")
    assert sha(zip_path) == run_data["cotahist_manifest"]["sha256"]
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    response_by_cvm = {r["cvm_code"]: r for r in manifest["responses"]}
    changed_issuers = set()
    for case in cases:
        old = before_by_id[case["blocker_id"]]
        new = after_by_id[case["blocker_id"]]
        if case["terminal_status"] != "RECOVERED":
            assert new == old, f"Unrecovered issuer changed: {old['cvm_code']}"
            continue
        changed_issuers.add(old["issuer_id"])
        response = response_by_cvm[old["cvm_code"]]
        b3path = evidence_dir / response["file"]
        assert sha(b3path) == response["sha256"]
        directory = json.loads(b3path.read_text(encoding="utf-8"))
        assert directory["cnpj"] == old["cnpj"]
        assert int(directory["codeCVM"]) == int(old["cvm_code"])
        assert directory["status"] == "A" and directory["hasQuotation"] == "S"
        assert len(new["securities"]) == len(old["securities"])
        for old_security, new_security in zip(old["securities"], new["securities"]):
            if new_security.get("identity_resolution") is None:
                assert new_security == old_security
                continue
            proof = new_security["identity_resolution"]["exchange_identity"]
            assert (
                proof["cnpj"] == old["cnpj"] and proof["share_class"] == old_security["share_class"]
            )
            assert (
                proof["ticker"] == new_security["ticker"] and proof["isin"] == new_security["isin"]
            )
            assert any(
                x.get("code") == proof["ticker"] and x.get("isin") == proof["isin"]
                for x in directory.get("otherCodes", [])
            )
            assert new_security["identity_resolution"]["price_field"] == "PREULT"
            assert new_security["identity_resolution"]["confidence"] == "HIGH"
            assert (
                new_security["identity_resolution"]["source_document_sha256"] == response["sha256"]
            )
            source_ref = new_security["price_source_reference"]
            line_no = int(source_ref.rsplit("line=", 1)[1])
            with ZipFile(zip_path) as archive:
                member = next(x for x in archive.namelist() if x.upper().endswith(".TXT"))
                with archive.open(member) as stream:
                    raw_line = next(line for n, line in enumerate(stream, 1) if n == line_no)
            assert raw_line[:2] == b"01"
            assert raw_line[2:10].decode() == new_security["effective_market_date"].replace("-", "")
            assert raw_line[12:24].decode("latin1").strip() == new_security["ticker"]
            assert raw_line[24:27] == b"010"
            assert (
                raw_line[108:121].decode()
                == new_security["identity_resolution"]["price_evidence"]["raw_price"]
            )
            assert raw_line[230:242].decode("latin1").strip() == new_security["isin"]
            assert (
                new_security["price"]
                == new_security["identity_resolution"]["price_evidence"]["price"]
            )
        for key in (
            "accounting_readiness",
            "historical_shares_unit_resolution",
            "financials",
            "fundamentals",
        ):
            if key in old:
                assert new.get(key) == old[key]
    assert changed_issuers == {c["blocker_id"] for c in recovered}
    assert candidate["ranking_status"] == "INACTIVE"
    assert candidate["tool_status"] == "VALIDATION_REQUIRED"
    assert candidate["methodology_version"] == before["methodology_version"]
    assert candidate["ranking"] == before["ranking"] if "ranking" in before else True
    validated = copy.deepcopy(candidate)
    validated["identity_recovery_run"]["dry_run"] = False
    validated["identity_recovery_run"]["independent_readback"] = "PASS"
    validated["created_at"] = datetime.now(timezone.utc).isoformat()
    raw = json.dumps(validated, ensure_ascii=False, indent=2).encode("utf-8")
    (output / "validated-candidate.json").write_bytes(raw)
    report = {
        "status": "PASS",
        "before_snapshot_id": before["universe_snapshot_id"],
        "validated_candidate_sha256": hashlib.sha256(raw).hexdigest(),
        "blockers_read_back": len(cases),
        "recovered": len(recovered),
        "unrecovered_unchanged": 31,
        "source_prices_verified_from_raw_cotahist": len(recovered),
        "b3_directory_hashes_verified": len(recovered),
        "ranking_status": candidate["ranking_status"],
        "tool_status": candidate["tool_status"],
        "cotahist_sha256": sha(zip_path),
    }
    (output / "readback-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("before", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    run(args.output, args.before, args.evidence)
