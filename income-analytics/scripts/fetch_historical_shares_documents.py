"""Acquire exact CVM document links from a frozen sample; retain original evidence.

Run with a Python environment containing pypdf. This collector never resolves units.
"""

import argparse
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen
from zipfile import ZIP_DEFLATED, ZipFile, is_zipfile

from pypdf import PdfReader


def fetch(item, output):
    start = perf_counter()
    document = item["document"]
    identifier = document["ID_DOC"]
    url = document["LINK_DOC"].replace("http://", "https://", 1)
    original = output / (identifier + ".zip")
    try:
        excerpt = output / (identifier + "-evidence.zip")
        if excerpt.exists():
            with ZipFile(excerpt) as archive:
                cached = json.loads(archive.read("evidence.json"))
            if cached["document_id"] != identifier or cached["url"] != url:
                raise ValueError("CACHED_DOCUMENT_IDENTITY_CONFLICT")
            return dict(cached, cache_hit=True, cache_read_seconds=perf_counter() - start)
        if not original.exists() or not is_zipfile(original):
            with urlopen(
                Request(url, headers={"User-Agent": "IncomeAnalytics validation research"}),
                timeout=90,
            ) as response:
                data = response.read()
            if not data.startswith(b"PK"):
                raise ValueError(
                    "SOURCE_DOCUMENT_NOT_ZIP:" + data[:200].decode("utf8", errors="replace")
                )
            original.write_bytes(data)
        data = original.read_bytes()
        with ZipFile(io.BytesIO(data)) as archive:
            main = [
                n
                for n in archive.namelist()
                if n.endswith(".xml")
                and "DFP" in n
                and n != "FormularioDemonstracaoFinanceiraDFP.xml"
            ]
            pdf = [n for n in archive.namelist() if n.endswith(".pdf")]
            if len(main) != 1 or len(pdf) != 1:
                raise ValueError("AMBIGUOUS_DOCUMENT_MEMBERS")
            pdf_bytes = archive.read(pdf[0])
            reader = PdfReader(io.BytesIO(pdf_bytes))
            capital_pages = []
            for index, page in enumerate(reader.pages[:8]):
                text = page.extract_text()
                if "Do Capital Integralizado" in text and "Em Tesouraria" in text:
                    capital_pages.append(dict(page_number=index + 1, text=text))
            if len(capital_pages) != 1:
                raise ValueError("CAPITAL_PAGE_NOT_UNIQUE")
            evidence = dict(
                issuer_id=item["issuer_id"],
                document_id=identifier,
                url=url,
                retrieved_at=datetime.now(UTC).isoformat(),
                original_sha256=hashlib.sha256(data).hexdigest(),
                main_xml_member=main[0],
                descriptor_member="FormularioDemonstracaoFinanceiraDFP.xml",
                pdf_member=pdf[0],
                pdf_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
                pdf_capital_page=capital_pages[0],
                duration_seconds=perf_counter() - start,
                status="ACQUIRED",
            )
            members = {
                n: archive.read(n) for n in (main[0], "FormularioDemonstracaoFinanceiraDFP.xml")
            }
            evidence["member_sha256"] = {
                n: hashlib.sha256(b).hexdigest() for n, b in members.items()
            }
        with ZipFile(excerpt, "w", ZIP_DEFLATED) as archive:
            for name, content in members.items():
                archive.writestr(name, content)
            archive.writestr("evidence.json", json.dumps(evidence, ensure_ascii=False, indent=2))
        return evidence
    except Exception as error:
        return dict(
            issuer_id=item["issuer_id"],
            document_id=identifier,
            url=url,
            status="ACQUISITION_FAILED",
            error=str(error),
            duration_seconds=perf_counter() - start,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sample = json.loads(args.sample.read_text(encoding="utf8"))
    start = perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch, item, args.output) for item in sample["issuers"]]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(result["document_id"], result["status"], result.get("error", ""), flush=True)
    (args.output / "acquisition.json").write_text(
        json.dumps(
            dict(
                duration_seconds=perf_counter() - start,
                documents=sorted(results, key=lambda r: r["issuer_id"]),
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
