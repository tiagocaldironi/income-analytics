"""Validate a proposal in a fresh process, including raw lines and public provider."""

import argparse
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

from income_analytics.application.historical_security_identity import (
    EXCHANGE_DIRECTORY_POLICY,
    recover_price,
    recover_price_from_exchange_identity,
)
from income_analytics.application.magic_formula_preview import build_preview
from income_analytics.application.magic_formula_universe import coverage
from income_analytics.infrastructure.b3_cotahist_market_data import B3CotahistMarketDataProvider
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)


def extract_page(pdf_python, pdf, page):
    code = (
        "import sys,pdfplumber; sys.stdout.reconfigure(encoding='utf8'); "
        "doc=pdfplumber.open(sys.argv[1]); "
        "print(doc.pages[int(sys.argv[2])-1].extract_text()); doc.close()"
    )
    return subprocess.check_output([pdf_python, "-c", code, str(pdf), str(page)], encoding="utf8")


def run(output, evidence_directory, pdf_python):
    def load(name):
        return json.loads((output / name).read_text(encoding="utf8"))

    before, candidate, index = (
        load("before.json"),
        load("candidate.json"),
        load("recovery-raw-index.json"),
    )
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    assert repository.read(before["universe_snapshot_id"]) == before
    assert candidate["ranking_status"] == "INACTIVE"
    assert candidate["tool_status"] == "VALIDATION_REQUIRED"
    assert candidate["coverage"] == coverage(candidate["issuers"])
    recovered = set(candidate["identity_recovery_run"]["recovered_issuers"])
    originals = {i["issuer_id"]: i for i in before["issuers"]}
    assert set(originals) == {i["issuer_id"] for i in candidate["issuers"]}
    archive_path = (
        Path("data/cotahist") / candidate["identity_recovery_run"]["source_manifest"]["file"]
    )
    assert (
        hashlib.sha256(archive_path.read_bytes()).hexdigest()
        == candidate["identity_recovery_run"]["source_manifest"]["sha256"]
    )
    provider = B3CotahistMarketDataProvider(cache_directory=Path("data/cotahist"))
    details = []
    for issuer in candidate["issuers"]:
        original = originals[issuer["issuer_id"]]
        if issuer["issuer_id"] not in recovered:
            assert issuer == original
            continue
        security = issuer["securities"][0]
        identity = security["identity_resolution"]
        acquisition = identity["directory_acquisition"]
        directory_raw = (evidence_directory / acquisition["file"]).read_bytes()
        assert hashlib.sha256(directory_raw).hexdigest() == acquisition["sha256"]
        assert json.loads(directory_raw) == identity["current_directory"]
        if identity["policy_version"] == EXCHANGE_DIRECTORY_POLICY:
            proof = identity["exchange_identity"]
            assert hashlib.sha256(directory_raw).hexdigest() == proof["source_sha256"]
            repeated = recover_price_from_exchange_identity(
                original,
                proof,
                identity["current_directory"],
                list(reversed(index[security["ticker"]])),
                candidate["reference_date"],
            )
        else:
            proof = identity["offer"]
            pdf = evidence_directory / proof["source_file"]
            assert hashlib.sha256(pdf.read_bytes()).hexdigest() == proof["source_sha256"]
            # Independent PDF extractor, separate from pypdf used by acquisition.
            cover = extract_page(pdf_python, pdf, 1)
            assert proof["ticker"] in cover and proof["isin"] in cover
            cnpjs = [
                re.sub(r"\D", "", c)
                for c in re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", cover)
            ]
            assert cnpjs == [issuer["cnpj"]]
            final_page = extract_page(pdf_python, pdf, proof["date_page"])
            months = (
                "janeiro fevereiro março abril maio junho julho agosto setembro outubro "
                "novembro dezembro"
            ).split()
            signed_date = date.fromisoformat(proof["document_date"])
            assert (
                f"{signed_date.day} de {months[signed_date.month - 1]} de {signed_date.year}"
                in " ".join(final_page.split())
            )
            repeated = recover_price(
                original,
                proof,
                identity["current_directory"],
                list(reversed(index[security["ticker"]])),
                candidate["reference_date"],
            )
        repeated["securities"][0]["identity_resolution"]["directory_acquisition"] = identity[
            "directory_acquisition"
        ]
        assert repeated == issuer
        quote = provider.price_evidence_on(
            security["ticker"], date.fromisoformat(candidate["reference_date"])
        )
        assert quote.price == Decimal(security["price"])
        assert quote.effective_date.isoformat() == security["effective_market_date"]
        filename, member, line = security["price_source_reference"].split("|")
        with ZipFile(archive_path) as archive, archive.open(member) as stream:
            raw = next(
                raw for number, raw in enumerate(stream, 1) if number == int(line.split("=")[1])
            )
        assert raw[12:24].decode().strip() == security["ticker"]
        assert raw[230:242].decode().strip() == security["isin"]
        assert raw[24:27] == b"010"
        assert Decimal(raw[108:121].decode()) / 100 == Decimal(security["price"])
        assert (
            date.fromisoformat(raw[2:10].decode()).isoformat() == security["effective_market_date"]
        )
        for field in (
            "accounting_readiness",
            "historical_shares_unit_resolution",
            "issuer_id",
            "cnpj",
            "cvm_code",
            "canonical_status",
            "canonical_ranking_eligible",
        ):
            assert issuer[field] == original[field]
        details.append(
            {
                "issuer_id": issuer["issuer_id"],
                "ticker": security["ticker"],
                "price": security["price"],
                "effective_date": security["effective_market_date"],
                "source_reference": security["price_source_reference"],
            }
        )
    preview = build_preview(candidate)
    reversed_candidate = deepcopy(candidate)
    reversed_candidate["issuers"].reverse()
    assert preview["items"] == build_preview(reversed_candidate)["items"]
    assert len([i for i in candidate["issuers"] if i["canonical_status"] == "RESOLVED"]) == 5
    candidate["identity_recovery_run"]["independent_readback"] = "PASS"
    validated = output / "validated-candidate.json"
    validated.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf8")
    report = {
        "status": "PASS",
        "validated_candidate_sha256": hashlib.sha256(validated.read_bytes()).hexdigest(),
        "snapshot_id": candidate["universe_snapshot_id"],
        "recovered": details,
        "golden_five_regression": "PASS",
        "lineage": "PASS",
        "determinism": "PASS",
        "preview": preview["coverage"],
        "ranking_gate": preview["ranking_gate"],
        "ranking_status": preview["ranking_status"],
    }
    (output / "readback-report.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("evidence_directory", type=Path)
    parser.add_argument("--pdf-python", required=True)
    args = parser.parse_args()
    run(args.output, args.evidence_directory, args.pdf_python)
