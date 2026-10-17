"""Archive current B3 identity responses for investigation, never authorize history."""

import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetDetail/"


def collect(issuer, output):
    params = {"codeCVM": str(int(issuer["cvm_code"])), "language": "pt-br"}
    url = ENDPOINT + base64.b64encode(json.dumps(params).encode()).decode()
    result = {
        "issuer_id": issuer["issuer_id"],
        "cvm_code": issuer["cvm_code"],
        "expected_cnpj": issuer["cnpj"],
        "url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "historical_mapping_approved": False,
    }
    try:
        with urlopen(url, timeout=30) as response:
            raw = response.read()
        document = json.loads(raw)
        filename = issuer["cvm_code"] + ".json"
        (output / filename).write_bytes(raw)

        def digits(value):
            return "".join(c for c in str(value) if c.isdigit())

        matched = (
            isinstance(document, dict)
            and digits(document.get("cnpj")) == digits(issuer["cnpj"])
            and digits(document.get("codeCVM")).lstrip("0")
            == digits(issuer["cvm_code"]).lstrip("0")
        )
        result.update(
            file=filename,
            sha256=hashlib.sha256(raw).hexdigest(),
            identity_match=matched,
            status="CURRENT_IDENTITY_MATCH" if matched else "IDENTITY_UNCONFIRMED",
        )
    except Exception as error:
        result.update(status="FETCH_FAILED", error=f"{type(error).__name__}: {error}")
    return result


def run():
    source = ROOT / "tmp/price-recovery-phase1/price-only-blockers.json"
    document = json.loads(source.read_text(encoding="utf8"))
    output = (
        ROOT
        / "data/magic_formula/price_recovery_identity"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda issuer: collect(issuer, output), document["blockers"]))
    manifest = {
        "schema_version": "B3_CURRENT_IDENTITY_EVIDENCE_V1",
        "scope": "DISCOVERY_ONLY_NOT_HISTORICAL_AUTHORIZATION",
        "baseline_snapshot_id": document["baseline_snapshot_id"],
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "responses": sorted(results, key=lambda item: item["cvm_code"]),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
    print(output)
    print(
        {
            status: sum(r["status"] == status for r in results)
            for status in sorted({r["status"] for r in results})
        }
    )


if __name__ == "__main__":
    run()
