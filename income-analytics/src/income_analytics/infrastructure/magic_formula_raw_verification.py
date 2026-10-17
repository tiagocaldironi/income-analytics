"""Relocate serialized golden evidence in original local CVM/B3 archives.

Every locator must identify exactly one applicable raw record. No snapshot or
expected metric participates in record selection. Duplicate filings are errors.
"""

from __future__ import annotations

import csv
import hashlib
from datetime import date, timedelta
from decimal import Decimal
from io import TextIOWrapper
from pathlib import Path
from zipfile import ZipFile


def require(condition, label):
    if not condition:
        raise ValueError("GOLDEN_EVIDENCE_DEFECT:" + label)


class OfficialRawVerifier:
    def __init__(self, cvm_directory: Path, market_directory: Path):
        self.cvm_directory = cvm_directory
        self.market_directory = market_directory
        self._csv_cache = {}

    def csv_rows(self, archive_name, member):
        require(Path(archive_name).name == archive_name, "ARCHIVE_NAME")
        key = (archive_name, member)
        if key not in self._csv_cache:
            with ZipFile(self.cvm_directory / archive_name) as archive:
                require(archive.namelist().count(member) == 1, "CSV_MEMBER")
                with archive.open(member) as source:
                    self._csv_cache[key] = list(
                        csv.DictReader(TextIOWrapper(source, encoding="latin1"), delimiter=";")
                    )
        return self._csv_cache[key]

    def quotes(self, reference: str, tickers: tuple[str, ...]):
        """Read original physical line numbers, closing prices and ISIN (231..242)."""
        end = date.fromisoformat(reference)
        start = end - timedelta(days=7)
        archive_name = f"COTAHIST_A{end.year}.ZIP"
        result = []
        with ZipFile(self.market_directory / archive_name) as archive:
            members = [m for m in archive.namelist() if m.upper().endswith(".TXT")]
            require(len(members) == 1, "COTAHIST_MEMBER")
            member = members[0]
            with archive.open(member) as source:
                for line, raw in enumerate(source, 1):
                    if raw[:2] != b"01":
                        continue
                    ticker = raw[12:24].decode("latin1").strip()
                    if ticker not in tickers:
                        continue
                    effective = date.fromisoformat(raw[2:10].decode("ascii"))
                    if not start <= effective <= end:
                        continue
                    price = Decimal(raw[108:121].decode("ascii")) / 100
                    locator = (
                        f"{archive_name}|{member}|line={line}|date={effective:%Y%m%d}"
                        f"|ticker={ticker}|close={price}"
                    )
                    result.append(
                        dict(
                            ticker=ticker,
                            effective_date=effective.isoformat(),
                            price=str(price),
                            record_reference=locator,
                            isin=raw[230:242].decode("ascii").strip(),
                            currency=raw[52:56].decode("latin1").strip(),
                            raw_sha256=hashlib.sha256(raw).hexdigest(),
                        )
                    )
        return result

    @staticmethod
    def one(rows, locator):
        require(len(rows) == 1, f"LOCATOR_COUNT:{len(rows)}:{locator}")
        return rows[0]

    def verify(self, fixture):
        receipts = []

        def receipt(kind, locator, row):
            from income_analytics.application.magic_formula_contract import digest

            receipts.append(
                dict(kind=kind, locator=locator, applicable_records=1, record_digest=digest(row))
            )

        for group in fixture["accounting"].values():
            for c in group["components"]:
                locator = c["source_reference"]
                archive, code, ref, scope, statement, account, start, end = locator.split("|")
                require(scope == "CONSOLIDATED", "SCOPE")
                require(
                    code == fixture["issuer"]["cvm_code"]
                    and ref == fixture["reference_date"] == c["reference_date"]
                    and scope == c["statement_scope"]
                    and statement == c["statement_name"]
                    and account == c["account_code"]
                    and start == (c["period_start"] or "")
                    and end == c["period_end"],
                    "ACCOUNTING_LOCATOR_IDENTITY",
                )
                member = f"dfp_cia_aberta_{statement}_con_{ref[:4]}.csv"
                rows = [
                    r
                    for r in self.csv_rows(archive, member)
                    if r["CD_CVM"].zfill(6) == code
                    and r["DT_REFER"] == ref
                    and r["CD_CONTA"] == account
                    and r["ORDEM_EXERC"] == "ÚLTIMO"
                    and (r.get("DT_INI_EXERC") or "") == start
                    and (r.get("DT_FIM_EXERC") or ref) == end
                ]
                row = self.one(rows, locator)
                require(
                    "".join(x for x in row["CNPJ_CIA"] if x.isdigit()) == fixture["issuer"]["cnpj"],
                    "ACCOUNTING_CNPJ",
                )
                require(row["DS_CONTA"] == c["account_description"], "ACCOUNT_DESCRIPTION")
                require(
                    Decimal(row["VL_CONTA"].replace(",", ".")) == Decimal(c["raw_value"]),
                    "RAW_ACCOUNT_VALUE",
                )
                scales = {"MIL": ("THOUSAND", 1000), "UNIDADE": ("UNIT", 1)}
                require(row["ESCALA_MOEDA"] in scales, "RAW_SCALE")
                scale, multiplier = scales[row["ESCALA_MOEDA"]]
                require(
                    c["currency_scale"] == scale
                    and c["currency"] == "BRL"
                    and Decimal(c["normalization_multiplier"]) == multiplier,
                    "SCALE",
                )
                require(
                    Decimal(c["raw_value"]) * multiplier == Decimal(c["normalized_expected_value"]),
                    "NORMALIZED_COMPONENT",
                )
                receipt("accounting", locator, row)

        for security in fixture["security"]:
            locator = security["fca_source_reference"]
            archive, member, cnpj, ref, form, ticker = locator.split("|")
            rows = [
                r
                for r in self.csv_rows(archive, member)
                if r["CNPJ_Companhia"] == cnpj
                and r["Data_Referencia"] == ref
                and r["ID_Documento"] == form
                and r["Codigo_Negociacao"] == ticker
            ]
            row = self.one(rows, locator)
            require(
                "".join(x for x in cnpj if x.isdigit())
                == security["cnpj"]
                == fixture["issuer"]["cnpj"],
                "FCA_CNPJ",
            )
            require(security["issuer_id"] == fixture["issuer"]["issuer_id"], "FCA_ISSUER")
            descriptor = "ordin" if security["share_class"] == "ON" else "prefer"
            require(descriptor in row["Valor_Mobiliario"].casefold(), "FCA_CLASS")
            require(
                (row["Data_Inicio_Negociacao"] or None) == security["valid_from"]
                and (row["Data_Fim_Negociacao"] or None) == security["valid_to"],
                "FCA_VALIDITY",
            )
            require(
                ref <= fixture["reference_date"]
                and security["valid_from"] <= fixture["reference_date"]
                and (
                    security["valid_to"] is None
                    or security["valid_to"] >= fixture["reference_date"]
                ),
                "FCA_APPLICABILITY",
            )
            receipt("security", locator, row)

        for c in fixture["capital"]["securities"]:
            for key, value_key in (
                ("issued_source_reference", "issued_or_integralized_shares"),
                ("treasury_source_reference", "treasury_shares"),
            ):
                locator = c[key]
                source, cnpj, ref, share_class, kind, column = locator.split("|")
                archive, member = source.split(":", 1)
                rows = [
                    r
                    for r in self.csv_rows(archive, member)
                    if r["CNPJ_CIA"] == cnpj and r["DT_REFER"] == ref
                ]
                row = self.one(rows, locator)
                prefix = "QT_ACAO_ORDIN_" if share_class == "ON" else "QT_ACAO_PREF_"
                suffix = "CAP_INTEGR" if key == "issued_source_reference" else "TESOURO"
                require(
                    column == prefix + suffix and share_class == c["share_class"],
                    "CAPITAL_CLASS_COLUMN",
                )
                require(
                    kind
                    == ("ISSUED_SHARES" if key == "issued_source_reference" else "TREASURY_SHARES"),
                    "CAPITAL_SEMANTICS",
                )
                require(
                    "".join(x for x in cnpj if x.isdigit()) == fixture["issuer"]["cnpj"]
                    and ref == fixture["reference_date"],
                    "CAPITAL_IDENTITY",
                )
                require(
                    Decimal(row[column].replace(",", ".")) == Decimal(c[value_key]), "CAPITAL_VALUE"
                )
                receipt("capital", locator, row)
            outstanding = Decimal(c["issued_or_integralized_shares"]) - Decimal(
                c["treasury_shares"]
            )
            require(
                outstanding == Decimal(c["outstanding_shares"]) == Decimal(c["normalized_quantity"])
                and c["quantity_unit"] == "UNIT"
                and Decimal(c["quantity_multiplier"]) == 1,
                "OUTSTANDING",
            )

        quotes = self.quotes(
            fixture["reference_date"], tuple(p["ticker"] for p in fixture["prices"])
        )
        for p in fixture["prices"]:
            applicable = [
                q
                for q in quotes
                if q["ticker"] == p["ticker"] and q["effective_date"] == p["effective_date"]
            ]
            q = self.one(applicable, p["record_reference"])
            require(
                q["record_reference"] == p["record_reference"]
                and Decimal(q["price"]) == Decimal(p["price"]),
                "COTAHIST_LOCATOR_VALUE",
            )
            require(q["currency"] == "R$" and p["currency"] == "BRL", "COTAHIST_CURRENCY")
            require(
                p["effective_date"]
                == max(x["effective_date"] for x in quotes if x["ticker"] == p["ticker"]),
                "LATEST_CLOSE",
            )
            s = self.one(
                [s for s in fixture["security"] if s["ticker"] == p["ticker"]], p["ticker"]
            )
            if q["isin"]:
                require(p.get("isin") == s.get("isin") == q["isin"], "ISIN")
                require(s["isin_source_reference"] == p["record_reference"], "ISIN_SOURCE")
            receipt("market", p["record_reference"], q)
        return receipts
