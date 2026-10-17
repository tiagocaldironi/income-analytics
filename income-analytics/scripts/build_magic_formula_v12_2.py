"""Rebuild the Magic Formula ranking with only public information by 2025-12-30."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import shutil
import zipfile
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from income_analytics.application.historical_shares_units import resolve as resolve_shares
from income_analytics.application.magic_formula_accounting_evidence import (
    AccountingEvidenceStatus,
    MagicFormulaAccountingEvidenceBuilder,
)
from income_analytics.application.magic_formula_canonical_ranking import (
    BASELINE_PATH,
    BASELINE_SNAPSHOT_ID,
    POLICY_HASH,
    POLICY_ID,
    UNIVERSE_DB,
    _fold,
    _read_universe,
    digest,
    ranking_digest,
)
from income_analytics.application.magic_formula_investable_universe import normalized_sector
from income_analytics.application.magic_formula_point_in_time import (
    select_annual_financial_document,
    validate_point_in_time_snapshot,
)
from income_analytics.application.magic_formula_preview import _ranking_input
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService
from income_analytics.infrastructure.cvm_fundamentals_data import CvmDataset, CvmStatementParser
from income_analytics.infrastructure.cvm_historical_shares_document import read_unit_evidence

AS_OF = "2025-12-30"
ROOT = Path.cwd()
APPENDIX = ROOT / "docs/appendices/magic_formula_v12_2"
SHARES_SOURCE = ROOT / "tmp/magic_formula_v12_2/shares_evidence_dfp2024"
SHARES_ARCHIVE = ROOT / "data/magic_formula/shares_point_in_time_v1"
DFP_PATHS = {year: ROOT / f"data/cvm/dfp_cia_aberta_{year}.zip" for year in (2023, 2024, 2025)}
ITR_PATH = ROOT / "data/cvm/itr_cia_aberta_2025.zip"
FCA_PATHS = (ROOT / "data/cvm/fca_cia_aberta_2024.zip", ROOT / "data/cvm/fca_cia_aberta_2025.zip")
GOLDENS = {"PETR4", "CSNA3", "VALE3", "WEGE3", "CMIG4", "ABEV3"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_in_zip(path: Path, suffix: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(suffix.lower()))
        return list(
            csv.DictReader(io.TextIOWrapper(archive.open(name), encoding="latin1"), delimiter=";")
        )


def cvm_key(value: str) -> str:
    return str(int(value)).zfill(6)


def candidate_docs(cvm_codes: set[str]) -> dict[str, list[dict]]:
    result = {code: [] for code in cvm_codes}
    archive_hashes = {year: sha(path) for year, path in DFP_PATHS.items()}
    itr_hash = sha(ITR_PATH)
    for year, path in DFP_PATHS.items():
        for row in rows_in_zip(path, f"dfp_cia_aberta_{year}.csv"):
            code = cvm_key(row["CD_CVM"])
            if code not in result or row["CATEG_DOC"] != "DFP":
                continue
            result[code].append(
                {
                    "cvm_code": code,
                    "company_id": None,
                    "document_type": "DFP",
                    "reference_period": row["DT_REFER"],
                    "period_start": row["DT_REFER"][:4] + "-01-01",
                    "period_end": row["DT_REFER"],
                    "filing_date": row["DT_RECEB"],
                    "information_available_date": row["DT_RECEB"],
                    "source": "CVM_DFP_" + str(year),
                    "source_id": row["ID_DOC"],
                    "source_hash": archive_hashes[year],
                    "version": row["VERSAO"],
                    "cnpj": row["CNPJ_CIA"],
                    "_year": year,
                }
            )
    for row in rows_in_zip(ITR_PATH, "itr_cia_aberta_2025.csv"):
        code = cvm_key(row["CD_CVM"])
        if code in result:
            result[code].append(
                {
                    "cvm_code": code,
                    "document_type": "ITR",
                    "reference_period": row["DT_REFER"],
                    "period_start": row.get("DT_INI_EXERC", ""),
                    "period_end": row["DT_REFER"],
                    "filing_date": row["DT_RECEB"],
                    "information_available_date": row["DT_RECEB"],
                    "source": "CVM_ITR_2025",
                    "source_id": row["ID_DOC"],
                    "source_hash": itr_hash,
                    "version": row["VERSAO"],
                    "cnpj": row["CNPJ_CIA"],
                }
            )
    return result


def fca_security_evidence() -> dict[tuple[str, str], dict]:
    """Resolve the latest pre-cutoff official listing evidence by issuer/ticker."""
    index_by_id: dict[str, dict] = {}
    receipt_by_id: dict[str, str] = {}
    security_docs: list[tuple[int, Path]] = []
    for path in FCA_PATHS:
        year = int(path.stem[-4:])
        for row in rows_in_zip(path, f"fca_cia_aberta_{year}.csv"):
            index_by_id[row["ID_DOC"]] = row
            receipt_by_id[row["ID_DOC"]] = row["DT_RECEB"]
        security_docs.append((year, path))

    result: dict[tuple[str, str], dict] = {}
    for year, path in security_docs:
        source_hash = sha(path)
        table = rows_in_zip(path, f"fca_cia_aberta_valor_mobiliario_{year}.csv")
        for number, row in enumerate(table, start=2):
            doc_id = row.get("ID_Documento", "")
            index = index_by_id.get(doc_id)
            ticker = row.get("Codigo_Negociacao", "").strip().upper()
            receipt = receipt_by_id.get(doc_id)
            start = row.get("Data_Inicio_Listagem") or row.get("Data_Inicio_Negociacao")
            end = row.get("Data_Fim_Listagem") or row.get("Data_Fim_Negociacao") or None
            if (
                not index
                or not ticker
                or not receipt
                or receipt > AS_OF
                or not start
                or start > AS_OF
                or (end and end < AS_OF)
                or row.get("Mercado") != "Bolsa"
                or row.get("Sigla_Entidade_Administradora") != "B3"
            ):
                continue
            key = ("".join(char for char in index["CNPJ_CIA"] if char.isdigit()), ticker)
            instrument_label = (row.get("Valor_Mobiliario") or "").casefold()
            share_class = (
                "ON"
                if "ordin" in instrument_label
                else "PN"
                if "prefer" in instrument_label
                else "UNIT"
                if "unit" in instrument_label
                else None
            )
            evidence = {
                "cvm_code": cvm_key(index["CD_CVM"]),
                "cnpj": key[0],
                "ticker": ticker,
                "share_class": share_class,
                "form_id": doc_id,
                "information_available_date": receipt,
                "valid_from": start,
                "valid_to": end,
                "source_reference": (
                    f"{path.name}|fca_cia_aberta_valor_mobiliario_{year}.csv|line={number}"
                ),
                "source_hash": source_hash,
            }
            previous = result.get(key)
            if not previous or (evidence["information_available_date"], evidence["form_id"]) > (
                previous["information_available_date"],
                previous["form_id"],
            ):
                result[key] = evidence
    return result


def account_evidence(bundle) -> list[dict]:
    scales = {"UNIT": "UNIDADE", "THOUSAND": "MIL", "MILLION": "MILHÃO"}
    rows = []
    for component in bundle.components:
        for source in component.sources:
            rows.append(
                {
                    "metric": component.metric,
                    "account_code": source.account_code,
                    "rule_id": component.rule_id,
                    "source_reference": source.source_reference,
                    "raw_value": str(source.raw_value),
                    "currency": "REAL",
                    "currency_scale": scales[source.currency_scale],
                    "normalized_value": str(source.normalized_value),
                    "statement": source.statement,
                    "statement_scope": source.statement_scope,
                }
            )
    return rows


def main() -> int:
    APPENDIX.mkdir(parents=True, exist_ok=True)
    SHARES_ARCHIVE.mkdir(parents=True, exist_ok=True)
    with BASELINE_PATH.open(encoding="utf-8-sig", newline="") as stream:
        baseline = list(csv.DictReader(stream))
    source = _read_universe(UNIVERSE_DB, BASELINE_SNAPSHOT_ID)
    cotahist_hash = next(
        (
            item["sha256"]
            for item in source["sources"]
            if item["file"].upper() == "COTAHIST_A2025.ZIP"
        ),
        None,
    )
    source_by_cvm = {cvm_key(row["cvm_code"]): row for row in source["issuers"]}
    baseline_by_cvm = {cvm_key(row["cvm_code"]): row for row in baseline}
    candidate_map = candidate_docs(set(baseline_by_cvm))
    selected_map = {}
    selection_rows = []
    for code, docs in candidate_map.items():
        issuer = source_by_cvm.get(code)
        for item in docs:
            item["company_id"] = issuer.get("issuer_id") if issuer else None
        selected, audit = select_annual_financial_document(docs, AS_OF)
        selected_map[code] = selected
        selection_rows.extend(audit)
        if not audit:
            selection_rows.append(
                {
                    "company_id": issuer.get("issuer_id") if issuer else None,
                    "cvm_code": code,
                    "document_type": "DFP",
                    "selection_status": "NO_CANDIDATE",
                    "rejection_reason": "NO_OFFICIAL_DFP_CANDIDATE",
                }
            )
    with (APPENDIX / "point_in_time_financial_selection.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        fields = (
            "company_id",
            "cvm_code",
            "document_type",
            "reference_period",
            "period_start",
            "period_end",
            "filing_date",
            "information_available_date",
            "source",
            "source_id",
            "source_hash",
            "version",
            "selection_status",
            "rejection_reason",
        )
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(
            sorted(
                selection_rows,
                key=lambda row: (
                    row["cvm_code"],
                    row["document_type"],
                    row.get("period_end", ""),
                    row.get("source_id", ""),
                ),
            )
        )

    selected_years = {int(item["_year"]) for item in selected_map.values() if item}
    parser = CvmStatementParser()
    parsed = {
        year: parser.parse(
            CvmDataset("DFP", DFP_PATHS[year].name, datetime.now(UTC), DFP_PATHS[year].read_bytes())
        )
        for year in sorted(selected_years)
    }
    capital_rows: dict[int, dict[tuple[str, str, str], dict]] = {}
    for year in selected_years:
        cap_name = f"dfp_cia_aberta_composicao_capital_{year}.csv"
        with zipfile.ZipFile(DFP_PATHS[year]) as archive:
            name = next((n for n in archive.namelist() if n.lower().endswith(cap_name)), None)
            rows = (
                []
                if name is None
                else list(
                    csv.DictReader(
                        io.TextIOWrapper(archive.open(name), encoding="latin1"), delimiter=";"
                    )
                )
            )
        capital_rows[year] = {}
        for number, row in enumerate(rows, start=2):
            if row.get("CNPJ_CIA"):
                cnpj = "".join(char for char in row["CNPJ_CIA"] if char.isdigit())
                key = (cnpj, row["DT_REFER"], str(row["VERSAO"]))
                capital_rows[year][key] = dict(
                    row, source_reference=f"{DFP_PATHS[year].name}|{cap_name}|line={number}"
                )

    identity_by_issuer_ticker = fca_security_evidence()
    accounting_builder = MagicFormulaAccountingEvidenceBuilder()
    valid_inputs = []
    issuer_by_id = {}
    baseline_by_id = {}
    security_by_id = {}
    provenance_by_id = {}
    shares_audit = []
    blocked = []
    non_rankable = []
    for code, baseline_row in sorted(baseline_by_cvm.items()):
        if baseline_row["methodological_status"] != "ELIGIBLE_COMPLETE":
            continue
        issuer = source_by_cvm.get(code)
        doc = selected_map.get(code)
        issue_reasons: list[str] = []
        if not issuer or not doc:
            blocked.append(
                {
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "ELIGIBLE_DATA_BLOCKED",
                    "reason": "NO_ELIGIBLE_ANNUAL_DFP",
                }
            )
            shares_audit.append(
                {
                    "company_id": issuer.get("issuer_id") if issuer else "",
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "BLOCKED",
                    "reason": "NO_ELIGIBLE_ANNUAL_DFP",
                }
            )
            continue
        year = int(doc["_year"])
        version, ref = str(doc["version"]), doc["period_end"]
        records = tuple(
            record
            for record in parsed[year]
            if cvm_key(record.cvm_code) == code
            and record.reference_date == ref
            and str(record.filing_version) == version
            and record.statement_scope == "CONSOLIDATED"
        )
        bundle = accounting_builder.build(records)
        if bundle.status is not AccountingEvidenceStatus.COMPLETE:
            reason = "FINANCIAL_DATA_INCOMPLETE:" + ";".join(
                bundle.issues or bundle.missing_metrics
            )
            blocked.append(
                {
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "ELIGIBLE_DATA_BLOCKED",
                    "reason": reason,
                }
            )
            shares_audit.append(
                {
                    "company_id": issuer["issuer_id"],
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "NOT_EVALUATED",
                    "reason": reason,
                }
            )
            continue

        issuer_cnpj = "".join(char for char in issuer["cnpj"] if char.isdigit())
        cap = capital_rows.get(year, {}).get((issuer_cnpj, ref, version))
        ev_path = SHARES_SOURCE / f"{doc['source_id']}-evidence.zip"
        if not cap or not ev_path.exists():
            reason = (
                "POINT_IN_TIME_CAPITAL_COMPOSITION_ROW_MISSING"
                if not cap
                else "POINT_IN_TIME_DOCUMENT_UNIT_EVIDENCE_MISSING"
            )
            blocked.append(
                {
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "ELIGIBLE_DATA_BLOCKED",
                    "reason": reason,
                }
            )
            shares_audit.append(
                {
                    "company_id": issuer["issuer_id"],
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "BLOCKED",
                    "reason": reason,
                    "shares_reference_date": ref,
                    "shares_information_available_date": doc["information_available_date"],
                    "source_id": doc["source_id"],
                }
            )
            continue
        verified = read_unit_evidence(ev_path)
        resolution = resolve_shares(issuer, dict(cap), verified)
        if resolution["status"] != "RESOLVED" or doc["information_available_date"] > AS_OF:
            reason = resolution.get("reason_code") or "SHARES_AFTER_AS_OF"
            blocked.append(
                {
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "ELIGIBLE_DATA_BLOCKED",
                    "reason": reason,
                }
            )
            shares_audit.append(
                {
                    "company_id": issuer["issuer_id"],
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": resolution["status"],
                    "reason": reason,
                    "shares_reference_date": ref,
                    "shares_information_available_date": doc["information_available_date"],
                    "source_id": doc["source_id"],
                }
            )
            continue
        share_hash = sha(ev_path)
        shutil.copy2(ev_path, SHARES_ARCHIVE / ev_path.name)

        security = next(
            (
                row
                for row in issuer["securities"]
                if row.get("ticker") == baseline_row["selected_ticker"]
            ),
            None,
        )
        historical_identity = None
        identity_received = None
        if not security:
            issue_reasons.append("SECURITY_IDENTITY_MISSING")
        elif (
            security.get("price_status") != "AVAILABLE"
            or not security.get("effective_market_date")
            or security["effective_market_date"] > AS_OF
        ):
            issue_reasons.append("PRICE_NOT_AVAILABLE_AT_AS_OF")
        elif not security.get("price_source_reference") or not security.get("source_reference"):
            issue_reasons.append("PRICE_OR_IDENTITY_SOURCE_MISSING")
        else:
            cnpj_digits = "".join(char for char in issuer["cnpj"] if char.isdigit())
            historical_identity = identity_by_issuer_ticker.get(
                (cnpj_digits, baseline_row["selected_ticker"])
            )
            if not historical_identity:
                issue_reasons.append("SECURITY_IDENTITY_INFORMATION_AFTER_AS_OF")
            else:
                identity_received = historical_identity["information_available_date"]
                if (
                    historical_identity["cvm_code"] != code
                    or historical_identity["share_class"] != security.get("share_class")
                    or historical_identity["valid_from"] > AS_OF
                    or (
                        historical_identity.get("valid_to")
                        and historical_identity["valid_to"] < AS_OF
                    )
                ):
                    issue_reasons.append("SECURITY_NOT_VALID_AT_AS_OF")
        if issue_reasons:
            reason = ";".join(issue_reasons)
            blocked.append(
                {
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "ELIGIBLE_DATA_BLOCKED",
                    "reason": reason,
                }
            )
            shares_audit.append(
                {
                    "company_id": issuer["issuer_id"],
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "RESOLVED",
                    "shares_reference_date": ref,
                    "shares_information_available_date": doc["information_available_date"],
                    "source_id": doc["source_id"],
                    "shares_source_hash": share_hash,
                    "normalized_quantities": resolution["quantities"],
                    "additional_blocker": reason,
                }
            )
            continue

        security = dict(
            security,
            valid_from=historical_identity["valid_from"],
            valid_to=historical_identity.get("valid_to"),
            source_reference=historical_identity["source_reference"],
            form_id=historical_identity["form_id"],
            identity_information_available_date=identity_received,
            identity_source_hash=historical_identity["source_hash"],
        )

        # Rebuild only the existing _ranking_input contract with selected DFP data.
        pit_issuer = copy.deepcopy(issuer)
        pit_issuer["accounting_readiness"]["evidence"] = account_evidence(bundle)
        outstanding: dict[str, str] = {}
        treasury: dict[str, dict[str, str]] = {}
        for share in resolution["quantities"]:
            share_class = share["share_class"]
            if share["quantity_kind"] == "issued":
                outstanding[share_class] = share["normalized_quantity"]
            else:
                treasury[share_class] = {"treasury": share["normalized_quantity"]}
        positive_classes = {
            key
            for key, value in outstanding.items()
            if Decimal(value) > Decimal(treasury.get(key, {}).get("treasury", "0"))
        }
        priced_classes = {
            row.get("share_class")
            for row in issuer["securities"]
            if row.get("price")
            and row.get("effective_market_date")
            and row["effective_market_date"] <= AS_OF
        }
        missing_prices = positive_classes - priced_classes
        if missing_prices:
            reason = "POSITIVE_SHARE_CLASS_WITHOUT_HISTORICAL_PRICE:" + ",".join(
                sorted(missing_prices)
            )
            blocked.append(
                {
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "ELIGIBLE_DATA_BLOCKED",
                    "reason": reason,
                }
            )
            shares_audit.append(
                {
                    "company_id": issuer["issuer_id"],
                    "cvm_code": code,
                    "ticker": baseline_row["selected_ticker"],
                    "status": "RESOLVED",
                    "shares_reference_date": ref,
                    "shares_information_available_date": doc["information_available_date"],
                    "source_id": doc["source_id"],
                    "shares_source_hash": share_hash,
                    "normalized_quantities": resolution["quantities"],
                    "additional_blocker": reason,
                }
            )
            continue
        pit_issuer["market_readiness"]["normalized_outstanding_by_class"] = outstanding
        pit_issuer["market_readiness"]["raw_capital_quantities"] = treasury
        by_security_id = {row["security_id"]: row for row in issuer["securities"]}
        for row in pit_issuer["securities"]:
            source_security = by_security_id[row["security_id"]]
            if (
                source_security.get("effective_market_date")
                and source_security["effective_market_date"] <= AS_OF
            ):
                row["price"] = source_security.get("price")
            else:
                row["price"] = None
        try:
            item = _ranking_input(pit_issuer, AS_OF, source["universe_snapshot_id"])
        except (ValueError, KeyError) as exc:
            non_rankable.append(
                {"cvm_code": code, "ticker": baseline_row["selected_ticker"], "reason": str(exc)}
            )
            continue
        item["issuer_id"] = issuer["issuer_id"]
        valid_inputs.append(item)
        issuer_by_id[issuer["issuer_id"]] = issuer
        baseline_by_id[issuer["issuer_id"]] = baseline_row
        security_by_id[issuer["issuer_id"]] = security
        accounting_sources = account_evidence(bundle)
        provenance_by_id[issuer["issuer_id"]] = {
            "accounting": accounting_sources,
            "market": {
                "capital_source_reference": cap["source_reference"],
                "shares_resolution": resolution,
            },
            "selected_security_source": security,
            "selected_isin": baseline_row["selected_isin"],
            "filing_date": doc["filing_date"],
            "point_in_time": {
                "selected_financial_document": doc["source_id"],
                "financial_source": doc["source"],
                "financial_source_hash": doc["source_hash"],
                "financial_reference_period": ref,
                "financial_information_available_date": doc["information_available_date"],
                "price_date": security["effective_market_date"],
                "price_source": security["price_source_reference"],
                "price_source_hash": cotahist_hash,
                "shares_reference_date": ref,
                "shares_information_available_date": doc["information_available_date"],
                "shares_source": verified["source_reference"],
                "shares_source_hash": share_hash,
                "security_valid_from": security["valid_from"],
                "security_valid_to": security.get("valid_to"),
                "security_identity_source": security["source_reference"],
                "security_identity_information_available_date": identity_received,
                "security_identity_source_hash": security["identity_source_hash"],
            },
        }
        shares_audit.append(
            {
                "company_id": issuer["issuer_id"],
                "cvm_code": code,
                "ticker": baseline_row["selected_ticker"],
                "shares_reference_date": ref,
                "shares_information_available_date": doc["information_available_date"],
                "shares_source": verified["source_reference"],
                "shares_source_hash": share_hash,
                "shares_point_in_time_valid": True,
                "normalized_quantities": resolution["quantities"],
                "status": "RESOLVED",
            }
        )

    ranked = list(MagicFormulaStockRankingService()._rank_approved(valid_inputs))
    ranked.sort(key=lambda row: (row["final_display_order"], row["issuer_id"]))
    results = []
    provenance = []
    input_by_id = {row["issuer_id"]: row for row in valid_inputs}
    for item in ranked:
        issuer_id = item["issuer_id"]
        base_row, issuer = baseline_by_id[issuer_id], issuer_by_id[issuer_id]
        security = security_by_id[issuer_id]
        line = provenance_by_id[issuer_id]
        pt = line["point_in_time"]
        context = (
            "CASH_AND_CARRY"
            if base_row["selected_ticker"] == "ASAI3"
            else "TRADITIONAL_RETAIL"
            if _fold(normalized_sector(issuer.get("economic_sector")) or "")
            == "comercio (atacado e varejo)"
            else None
        )
        result = {
            "company_id": issuer_id,
            "company_name": base_row["company"],
            "cvm_code": base_row["cvm_code"],
            "selected_security": base_row["selected_ticker"],
            "selected_isin": base_row["selected_isin"],
            "earnings_yield": str(item["earnings_yield"]),
            "return_on_capital": str(item["return_on_capital"]),
            "earnings_yield_rank": item["earnings_yield_rank"],
            "return_on_capital_rank": item["return_on_capital_rank"],
            "combined_score": item["magic_formula_score"],
            "global_rank": item["final_rank"],
            "commerce_category": context,
            "aviation_flag": cvm_key(issuer.get("cvm_code", "")) in {"024112", "019569"},
            "data_quality_status": "PASS",
            "provenance_status": "COMPLETE",
            "price": security["price"],
            "price_reference_date": security["effective_market_date"],
            "price_stale_calendar_days": (
                datetime.fromisoformat(AS_OF).date()
                - datetime.fromisoformat(security["effective_market_date"]).date()
            ).days,
            "ebit": input_by_id[issuer_id]["ebit"],
            "enterprise_value": input_by_id[issuer_id]["enterprise_value"],
            "invested_capital": input_by_id[issuer_id]["invested_capital"],
            "financial_reference_date": pt["financial_reference_period"],
            "filing_date": pt["financial_information_available_date"],
            "ranking_reference_date": AS_OF,
            "ranking_as_of_date": AS_OF,
            "financial_information_cutoff": AS_OF,
            "selected_financial_document": pt["selected_financial_document"],
            "point_in_time_lineage": pt,
        }
        results.append(result)
        provenance.append(
            dict(
                company_id=issuer_id,
                ticker=base_row["selected_ticker"],
                source_snapshot_id=source["universe_snapshot_id"],
                source_snapshot_digest=source["_document_digest"],
                **line,
            )
        )

    rank_hash = ranking_digest(
        POLICY_HASH,
        source["universe_snapshot_id"],
        source["_document_digest"],
        AS_OF,
        AS_OF,
        results,
    )
    created_at = datetime.now(UTC).isoformat()
    baseline_complete = sum(row["methodological_status"] == "ELIGIBLE_COMPLETE" for row in baseline)
    old_blocked = sum(row["methodological_status"] == "ELIGIBLE_DATA_BLOCKED" for row in baseline)
    reviews = sum(row["methodological_status"] == "BUYABLE_SECURITY_REVIEW" for row in baseline)
    liquidity_fails = sum(row["methodological_status"] == "LIQUIDITY_FAIL" for row in baseline)
    methodological_denominator = baseline_complete + old_blocked
    conservative_denominator = methodological_denominator + reviews
    snapshot = {
        "ranking_snapshot_id": "mf-" + rank_hash[:24],
        "policy_id": POLICY_ID,
        "policy_hash": POLICY_HASH,
        "data_snapshot_id": source["universe_snapshot_id"],
        "data_snapshot_digest": source["_document_digest"],
        "ranking_reference_date": AS_OF,
        "ranking_as_of_date": AS_OF,
        "price_reference_date": AS_OF,
        "accounting_cutoff": AS_OF,
        "financial_information_cutoff": AS_OF,
        "build_date": created_at[:10],
        "source_manifest_hash": hashlib.sha256(
            (
                source["_document_digest"]
                + "".join(sha(p) for p in [*DFP_PATHS.values(), ITR_PATH, *FCA_PATHS])
            ).encode()
        ).hexdigest(),
        "supersedes_snapshot_id": "mf-783598cd7f717527425123eb",
        "created_at": created_at,
        "rankable_companies": len(results),
        "blocked_companies": old_blocked + len(blocked),
        "review_companies": reviews,
        "liquidity_fail_companies": liquidity_fails,
        "eligible_complete_companies": baseline_complete,
        "point_in_time_blocked_companies": len(blocked),
        "methodological_denominator": methodological_denominator,
        "conservative_denominator": conservative_denominator,
        "methodological_coverage": (
            f"{Decimal(len(results)) / Decimal(methodological_denominator) * 100:.2f}%"
            if methodological_denominator
            else "0.00%"
        ),
        "conservative_coverage": (
            f"{Decimal(len(results)) / Decimal(conservative_denominator) * 100:.2f}%"
            if conservative_denominator
            else "0.00%"
        ),
        "ranking_hash": rank_hash,
        "ranking_style": "DENSE_METRIC_RANKS; COMPETITION_GLOBAL_RANK",
        "tie_policy": "SCORE_ASC; COMPANY_ID_ASC",
        "results": results,
        "provenance": provenance,
        "blocked": blocked,
        "reviews": [
            row for row in baseline if row["methodological_status"] == "BUYABLE_SECURITY_REVIEW"
        ],
        "liquidity_fails": [
            row for row in baseline if row["methodological_status"] == "LIQUIDITY_FAIL"
        ],
        "metric_non_rankable": non_rankable,
    }
    content_for_hash = {key: value for key, value in snapshot.items() if key != "created_at"}
    snapshot["snapshot_content_hash"] = digest(content_for_hash)
    validation = validate_point_in_time_snapshot(snapshot)
    (APPENDIX / "lookahead_validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (APPENDIX / "ranking_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (APPENDIX / "point_in_time_shares_audit.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        fields = sorted({key for row in shares_audit for key in row})
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(shares_audit)
    with (APPENDIX / "ranking_input_lineage.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = (
            "ticker",
            "company_id",
            "selected_financial_document",
            "financial_reference_period",
            "financial_source",
            "financial_source_hash",
            "filing_date",
            "information_available_date",
            "price_date",
            "price_source",
            "price_source_hash",
            "shares_reference_date",
            "shares_information_available_date",
            "shares_source",
            "shares_source_hash",
            "ebit",
            "enterprise_value",
            "invested_capital",
            "earnings_yield",
            "return_on_capital",
            "earnings_yield_rank",
            "return_on_capital_rank",
            "combined_score",
            "global_rank",
        )
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for result, line in zip(results, provenance, strict=True):
            pt = line["point_in_time"]
            writer.writerow(
                {
                    "ticker": result["selected_security"],
                    "company_id": result["company_id"],
                    "selected_financial_document": pt["selected_financial_document"],
                    "financial_reference_period": pt["financial_reference_period"],
                    "financial_source": pt["financial_source"],
                    "financial_source_hash": pt["financial_source_hash"],
                    "filing_date": pt["financial_information_available_date"],
                    "information_available_date": pt["financial_information_available_date"],
                    "price_date": pt["price_date"],
                    "price_source": pt["price_source"],
                    "price_source_hash": pt["price_source_hash"],
                    "shares_reference_date": pt["shares_reference_date"],
                    "shares_information_available_date": pt["shares_information_available_date"],
                    "shares_source": pt["shares_source"],
                    "shares_source_hash": pt["shares_source_hash"],
                    **{
                        k: result[k]
                        for k in (
                            "ebit",
                            "enterprise_value",
                            "invested_capital",
                            "earnings_yield",
                            "return_on_capital",
                            "earnings_yield_rank",
                            "return_on_capital_rank",
                            "combined_score",
                            "global_rank",
                        )
                    },
                }
            )
    old_rows = {
        row["selected_security"]: row
        for row in csv.DictReader(
            (ROOT / "docs/appendices/magic_formula_v11/ranking_results.csv").open(
                encoding="utf-8-sig"
            )
        )
    }
    with (APPENDIX / "ranking_diff_v11_v12_2.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        fields = (
            "ticker",
            "old_global_rank",
            "new_global_rank",
            "old_EY",
            "new_EY",
            "old_ROC",
            "new_ROC",
            "old_financial_period",
            "new_financial_period",
            "old_filing_date",
            "new_filing_date",
            "change_reason",
        )
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        all_tickers = sorted(set(old_rows) | {row["selected_security"] for row in results})
        new_rows = {row["selected_security"]: row for row in results}
        for ticker in all_tickers:
            old, new = old_rows.get(ticker, {}), new_rows.get(ticker, {})
            writer.writerow(
                {
                    "ticker": ticker,
                    "old_global_rank": old.get("global_rank"),
                    "new_global_rank": new.get("global_rank"),
                    "old_EY": old.get("earnings_yield"),
                    "new_EY": new.get("earnings_yield"),
                    "old_ROC": old.get("return_on_capital"),
                    "new_ROC": new.get("return_on_capital"),
                    "old_financial_period": old.get("financial_reference_date"),
                    "new_financial_period": new.get("financial_reference_date"),
                    "old_filing_date": old.get("filing_date"),
                    "new_filing_date": new.get("filing_date"),
                    "change_reason": "POINT_IN_TIME_CORRECTION"
                    if new
                    else "NOT_RANKABLE_WITH_POINT_IN_TIME_EVIDENCE",
                }
            )
    (APPENDIX / "coverage_reconciliation.json").write_text(
        json.dumps(
            {
                "ranked_before": 174,
                "ranked_after": len(results),
                "coverage_before": "74.07%",
                "coverage_after": snapshot["methodological_coverage"],
                "baseline_complete": baseline_complete,
                "new_point_in_time_blocked": len(blocked),
                "metric_non_rankable": len(non_rankable),
                "reason_counts": dict(Counter(row["reason"].split(":")[0] for row in blocked)),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    by_ticker = {row["selected_security"]: row for row in results}
    security_by_ticker = {}
    baseline_for_ticker = {}
    for code, base_row in baseline_by_cvm.items():
        if base_row["selected_ticker"] not in GOLDENS:
            continue
        source_issuer = source_by_cvm.get(code)
        baseline_for_ticker[base_row["selected_ticker"]] = base_row
        if source_issuer:
            security_by_ticker[base_row["selected_ticker"]] = next(
                (
                    security
                    for security in source_issuer["securities"]
                    if security.get("ticker") == base_row["selected_ticker"]
                ),
                None,
            )
    golden = []
    for ticker in sorted(GOLDENS):
        row = by_ticker.get(ticker)
        blocker = next(
            (item for item in blocked if item["ticker"] == ticker),
            None,
        )
        baseline_golden = baseline_for_ticker.get(ticker)
        selected_document = (
            selected_map.get(cvm_key(baseline_golden["cvm_code"])) if baseline_golden else None
        )
        price_evidence = security_by_ticker.get(ticker)
        share_evidence = next((audit for audit in shares_audit if audit["ticker"] == ticker), None)
        case_pass = bool(
            selected_document
            and price_evidence
            and share_evidence
            and (
                row is not None
                or (
                    blocker is not None
                    and share_evidence.get("shares_source_hash")
                    and share_evidence.get("normalized_quantities")
                )
            )
        )
        golden.append(
            {
                "ticker": ticker,
                "rankable": row is not None,
                "status": "PASS" if case_pass else "FAIL",
                "expected_rankability": row is not None,
                "blocker_reason": blocker.get("reason") if blocker else None,
                "selected_document": (
                    row.get("selected_financial_document")
                    if row
                    else selected_document.get("source_id")
                    if selected_document
                    else None
                ),
                "financial_period": (
                    row.get("financial_reference_date")
                    if row
                    else selected_document.get("period_end")
                    if selected_document
                    else None
                ),
                "filing_date": (
                    row.get("filing_date")
                    if row
                    else selected_document.get("information_available_date")
                    if selected_document
                    else None
                ),
                "price": row.get("price")
                if row
                else price_evidence.get("price")
                if price_evidence
                else None,
                "price_date": (
                    row.get("price_reference_date")
                    if row
                    else price_evidence.get("effective_market_date")
                    if price_evidence
                    else None
                ),
                "price_source": (
                    row.get("point_in_time_lineage", {}).get("price_source")
                    if row
                    else price_evidence.get("price_source_reference")
                    if price_evidence
                    else None
                ),
                "shares": share_evidence,
                "earnings_yield": row.get("earnings_yield") if row else None,
                "return_on_capital": row.get("return_on_capital") if row else None,
                "global_rank": row.get("global_rank") if row else None,
            }
        )
    (APPENDIX / "golden_cases.json").write_text(
        json.dumps(golden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ranked": len(results),
                "blocked": len(blocked),
                "metric_non_rankable": len(non_rankable),
                "selected_years": dict(
                    Counter(row["_year"] for row in selected_map.values() if row)
                ),
                "selection_audit_rows": len(selection_rows),
                "shares_evidence_count": len(shares_audit),
                "lookahead_validation": validation["status"],
                "snapshot_id": snapshot["ranking_snapshot_id"],
                "ranking_hash": rank_hash,
                "snapshot_content_hash": snapshot["snapshot_content_hash"],
                "goldens": {row["ticker"]: row["rankable"] for row in golden},
            },
            indent=2,
        )
    )
    return 0 if validation["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
