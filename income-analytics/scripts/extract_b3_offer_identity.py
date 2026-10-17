"""Extract labelled identity from a B3 offer notice; no price or manual mapping."""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader


def extract(path):
    reader = PdfReader(path)
    text = [
        unicodedata.normalize("NFKD", p.extract_text()).encode("ascii", "ignore").decode()
        for p in reader.pages
    ]
    cover = " ".join(text[0].split())
    cnpjs = re.findall(r"CNPJ[^0-9]{0,20}(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", cover)
    isins = re.findall(r"Codigo ISIN:\s*[^A-Z0-9]*([A-Z]{2}[A-Z0-9]{9}\d)", cover)
    tickers = re.findall(r"Codigo de negociacao na B3:\s*[^A-Z0-9]*([A-Z]{4}\d{1,2})", cover)
    months = (
        "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro"
    ).split()
    dates = re.findall(r"(\d{1,2}) de (" + "|".join(months) + r") de (\d{4})", text[-1])
    if not (len(cnpjs) == len(isins) == len(tickers) == len(dates) == 1):
        raise ValueError("AMBIGUOUS_OFFER_IDENTITY")
    if "acoes ordinarias" not in cover.lower() or "acoes preferenciais" in cover.lower():
        raise ValueError("UNSUPPORTED_OFFER_CLASS")
    day, month, year = dates[0]
    return {
        "schema_version": "B3_OFFER_IDENTITY_V1",
        "cnpj": re.sub(r"\D", "", cnpjs[0]),
        "isin": isins[0],
        "ticker": tickers[0],
        "share_class": "ON",
        "document_date": f"{year}-{months.index(month) + 1:02d}-{int(day):02d}",
        "source_file": path.name,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "identity_page": 1,
        "date_page": len(reader.pages),
        "extraction_method": "LABELLED_OFFER_COVER_AND_SIGNED_DATE_V1",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    result = extract(args.source)
    args.source.with_suffix(".identity.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result, indent=2))
