"""Read the pinned official CVM/B3 archives once for universe discovery/readiness."""

import csv
import hashlib
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper
from pathlib import Path
from zipfile import ZipFile

from income_analytics.application.cvm_magic_formula_normalization import RULES


def csv_records(path: Path, member: str):
    with ZipFile(path) as archive:
        with archive.open(member) as stream:
            reader = csv.DictReader(TextIOWrapper(stream, encoding="latin1"), delimiter=";")
            for row in reader:
                row["source_reference"] = f"{path.name}|{member}|line={reader.line_num}"
                yield row


def discovery_sources(cvm_directory: Path, year: int):
    path = cvm_directory / f"fca_cia_aberta_{year}.zip"
    return (
        list(csv_records(path, f"fca_cia_aberta_geral_{year}.csv")),
        list(csv_records(path, f"fca_cia_aberta_valor_mobiliario_{year}.csv")),
    )


def readiness_sources(cvm_directory: Path, market_directory: Path, reference: str, tickers):
    end = date.fromisoformat(reference)
    start = end - timedelta(days=7)
    dfp = cvm_directory / f"dfp_cia_aberta_{end.year}.zip"
    accounts = []
    for statement in ("BPA", "BPP", "DRE"):
        codes = {
            code for rule in RULES if rule.statement == statement for code in rule.account_codes
        }
        for row in csv_records(dfp, f"dfp_cia_aberta_{statement}_con_{end.year}.csv"):
            if row["CD_CONTA"] in codes and row["ORDEM_EXERC"] == "ÚLTIMO":
                accounts.append(dict(row, statement=statement, statement_scope="CONSOLIDATED"))
    capital = list(csv_records(dfp, f"dfp_cia_aberta_composicao_capital_{end.year}.csv"))
    quotes = []
    path = market_directory / f"COTAHIST_A{end.year}.ZIP"
    with ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.upper().endswith(".TXT")]
        if len(members) != 1:
            raise ValueError("AMBIGUOUS_COTAHIST_MEMBER")
        member = members[0]
        with archive.open(member) as stream:
            for line_number, raw in enumerate(stream, 1):
                if raw[:2] != b"01":
                    continue
                ticker = raw[12:24].decode("latin1").strip()
                if ticker not in tickers:
                    continue
                effective = date.fromisoformat(raw[2:10].decode("ascii"))
                if not start <= effective <= end:
                    continue
                try:
                    price = str(Decimal(raw[108:121].decode("ascii")) / 100)
                except ValueError, InvalidOperation:
                    price = None
                quotes.append(
                    dict(
                        ticker=ticker,
                        effective_date=effective.isoformat(),
                        price=price,
                        isin=raw[230:242].decode("latin1").strip() or None,
                        currency=raw[52:56].decode("latin1").strip(),
                        source_reference=f"{path.name}|{member}|line={line_number}",
                    )
                )
    return accounts, capital, quotes


def source_manifest(cvm_directory: Path, market_directory: Path, year: int):
    paths = (
        cvm_directory / f"fca_cia_aberta_{year}.zip",
        cvm_directory / f"dfp_cia_aberta_{year}.zip",
        market_directory / f"COTAHIST_A{year}.ZIP",
    )
    return [
        dict(
            file=path.name,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            bytes=path.stat().st_size,
        )
        for path in paths
    ]
