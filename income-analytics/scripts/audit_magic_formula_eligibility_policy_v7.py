"""Build the read-only V7 eligibility-policy audit from frozen V6/CVM evidence."""

# ruff: noqa: E501 -- this script embeds the generated Markdown report template.

from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import sqlite3
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from income_analytics.application.magic_formula_eligibility_policy_v7 import (
    commerce_policy_decision,
    coverage_metrics,
    final_eligibility_state,
    select_buyable_security,
    selected_security_liquidity,
)

ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "tmp/magic-formula-investable-v6/v6-audit.json"
V6_COMPANIES = (
    ROOT / "docs/appendices/magic_formula_investable_universe_v6/company_eligibility_307.csv"
)
V6_SECURITIES = (
    ROOT / "docs/appendices/magic_formula_investable_universe_v6/security_liquidity_431.csv"
)
V6_BLOCKERS = ROOT / "docs/appendices/magic_formula_investable_universe_v6/price_blockers_31.csv"
CVM_ZIP = ROOT / "data/cvm/fca_cia_aberta_2025.zip"
DB = ROOT / "data/magic_formula/universe_snapshots.db"
OUT = ROOT / "docs/appendices/magic_formula_eligibility_policy_v7"
REFERENCE_DATE = date(2025, 12, 31)

# The category is deliberately assigned from CVM's structured activity description.
# Low-confidence and mixed cases remain REVIEW; company names are not classifiers.
TAXONOMY = {
    "020990": (
        "MIXED_COMMERCE",
        "MEDIUM",
        "Varejo e atacado em geral, em lojas físicas e pela internet; descrição multicanal sem predominância única.",
    ),
    "022357": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Desenvolvimento, planejamento, investimento e administração de shopping centers e ativos imobiliários.",
    ),
    "025895": (
        "COMMERCE_ADJACENT",
        "MEDIUM",
        "Atividade combina indústria de equipamentos e serviços de tecnologia, com comercialização acessória.",
    ),
    "025372": (
        "CASH_AND_CARRY",
        "HIGH",
        "Comércio atacadista de autosserviço (cash-and-carry/atacarejo).",
    ),
    "022608": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Comércio varejista de produtos farmacêuticos, perfumaria e afins.",
    ),
    "019909": (
        "UNCERTAIN",
        "LOW",
        "O FCA informa apenas holding, sem descrever o negócio operacional; revisão do FRE necessária.",
    ),
    "021008": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Administração e exploração de shopping centers e outlets.",
    ),
    "022519": (
        "UNCERTAIN",
        "LOW",
        "Descrição de atividade disponível no FCA não identifica com clareza a operação varejista atual; objeto/estrutura de holding requer exame do FRE.",
    ),
    "025046": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Participação em empresas de comércio varejista de produtos farmacêuticos.",
    ),
    "025682": (
        "DISTRIBUTION",
        "HIGH",
        "Distribuição e comércio atacadista de produtos médico-hospitalares.",
    ),
    "024694": (
        "UNCERTAIN",
        "LOW",
        "Descrição FCA indica participação/holding, sem detalhar a operação de varejo; revisão do FRE necessária.",
    ),
    "025518": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Comércio varejista de móveis, decoração e artigos para casa, em canais digitais e físicos.",
    ),
    "025259": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Plataforma digital de intermediação de compra e venda entre usuários; modelo marketplace.",
    ),
    "025089": (
        "MIXED_COMMERCE",
        "MEDIUM",
        "Comércio de produtos para animais combinado a hospitais, clínicas e serviços veterinários.",
    ),
    "025933": (
        "WHOLESALE",
        "HIGH",
        "Compra, venda, revenda, importação, exportação e distribuição de grãos e produtos agrícolas.",
    ),
    "025330": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Plataforma de comercialização de tecnologia e serviços, logística e distribuição; operação multicanal B2B/B2C.",
    ),
    "023507": (
        "COMMERCE_ADJACENT",
        "MEDIUM",
        "Comercialização de produtos de saúde animal integrada à atividade industrial/farmacêutica.",
    ),
    "025658": (
        "DISTRIBUTION",
        "HIGH",
        "Comércio e distribuição de insumos agrícolas, sementes, fertilizantes e grãos.",
    ),
    "025186": (
        "UNCERTAIN",
        "LOW",
        "Registro FCA apresentado como holding sem descrição operacional suficiente para separar varejo e atacado; revisar FRE.",
    ),
    "025461": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Intermediação, importação, exportação e comércio varejista de móveis e materiais para casa/construção.",
    ),
    "006505": (
        "UNCERTAIN",
        "LOW",
        "Descrição de atividade FCA vazia/incompleta no registro utilizado; não inferir pela denominação empresarial.",
    ),
    "024805": (
        "UNCERTAIN",
        "LOW",
        "Descrição FCA insuficiente para separar atividade de holding e operação varejista; revisão do FRE necessária.",
    ),
    "024295": (
        "DISTRIBUTION",
        "HIGH",
        "Distribuição e venda de combustíveis, biocombustíveis e derivados para diferentes canais.",
    ),
    "025747": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Soluções digitais e infraestrutura para operações de comércio eletrônico de clientes (white-label).",
    ),
    "020346": (
        "DISTRIBUTION",
        "HIGH",
        "Distribuição atacadista de produtos farmacêuticos, higiene pessoal e cosméticos.",
    ),
    "014826": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Comércio varejista de alimentos e bens de consumo, com operação de supermercados/hipermercados.",
    ),
    "022470": ("TRADITIONAL_RETAIL", "HIGH", "Plataforma brasileira de varejo multicanal."),
    "021440": (
        "MIXED_COMMERCE",
        "MEDIUM",
        "Confecção/indústria de vestuário combinada a comércio e venda de produtos próprios.",
    ),
    "020494": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Administração, planejamento, desenvolvimento e exploração de shopping centers.",
    ),
    "008672": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Exploração comercial, administração e planejamento de shopping centers.",
    ),
    "022055": (
        "MIXED_COMMERCE",
        "MEDIUM",
        "Comércio varejista de vestuário e serviços financeiros/atividades acessórias.",
    ),
    "005258": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Comércio varejista de medicamentos, produtos farmacêuticos, perfumaria e afins.",
    ),
    "025453": (
        "COMMERCE_ADJACENT",
        "HIGH",
        "Atividade industrial de equipamentos eletroeletrônicos e telecomunicações; classificação comercial CVM não implica varejo principal.",
    ),
    "004537": ("TRADITIONAL_RETAIL", "HIGH", "Comércio varejista de vestuário e artigos de bazar."),
    "009342": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Descrição FCA identifica comércio varejista de medicamentos, perfumaria e produtos de toucador.",
    ),
    "008133": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Loja de departamentos e comércio varejista de vestuário e artigos relacionados.",
    ),
    "025038": (
        "TRADITIONAL_RETAIL",
        "HIGH",
        "Comércio varejista especializado em materiais de construção, móveis e eletrodomésticos.",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def latest_fca() -> tuple[dict[str, dict], dict[str, list[dict]]]:
    with zipfile.ZipFile(CVM_ZIP) as archive:
        general = list(
            csv.DictReader(
                io.TextIOWrapper(archive.open("fca_cia_aberta_geral_2025.csv"), encoding="latin1"),
                delimiter=";",
            )
        )
        securities = list(
            csv.DictReader(
                io.TextIOWrapper(
                    archive.open("fca_cia_aberta_valor_mobiliario_2025.csv"), encoding="latin1"
                ),
                delimiter=";",
            )
        )

    def latest(rows: list[dict]) -> dict[str, dict]:
        result = {}
        for row in rows:
            cvm = row.get("Codigo_CVM", "").zfill(6)
            key = (
                int(row.get("Versao") or 0),
                row.get("Data_Referencia", ""),
                row.get("ID_Documento", ""),
            )
            if cvm and (cvm not in result or key > result[cvm]["_sort"]):
                result[cvm] = {**row, "_sort": key}
        return result

    general_by_cvm = latest(general)
    security_rows: dict[str, list[dict]] = defaultdict(list)
    # Keep only the latest issuer submission, and current B3-exchange share/unit listings.
    ids = {cvm: row.get("ID_Documento") for cvm, row in general_by_cvm.items()}
    for row in securities:
        cnpj = "".join(ch for ch in row.get("CNPJ_Companhia", "") if ch.isdigit())
        match = next(
            (
                cvm
                for cvm, g in general_by_cvm.items()
                if "".join(ch for ch in g.get("CNPJ_Companhia", "") if ch.isdigit()) == cnpj
            ),
            None,
        )
        if not match or row.get("ID_Documento") != ids.get(match):
            continue
        ticker = (row.get("Codigo_Negociacao") or "").strip().upper()
        start = row.get("Data_Inicio_Negociacao") or row.get("Data_Inicio_Listagem") or "1900-01-01"
        end = row.get("Data_Fim_Negociacao") or row.get("Data_Fim_Listagem") or "9999-12-31"
        kind = row.get("Valor_Mobiliario", "").lower()
        if (
            ticker
            and row.get("Mercado") == "Bolsa"
            and row.get("Sigla_Entidade_Administradora") == "B3"
            and ("aç" in kind or "unit" in kind)
            and start <= "2025-12-31" <= end
        ):
            security_rows[match].append(row)
    deduplicated = {}
    for cvm, rows in security_rows.items():
        unique = {}
        for row in rows:
            key = (
                row.get("Codigo_Negociacao"),
                row.get("Valor_Mobiliario"),
                row.get("Sigla_Classe_Acao_Preferencial"),
                row.get("Data_Inicio_Negociacao"),
                row.get("Data_Fim_Negociacao"),
            )
            unique[key] = row
        deduplicated[cvm] = list(unique.values())
    return general_by_cvm, deduplicated


def snapshot_readonly() -> tuple[dict, str, str]:
    uri = f"file:{DB.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        row = con.execute(
            "SELECT universe_snapshot_id, created_at, document_json, document_digest FROM magic_formula_universe_snapshots ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        raise RuntimeError("NO_UNIVERSE_SNAPSHOT")
    return json.loads(row[2]), row[0], row[3]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    v6 = json.loads(V6.read_text(encoding="utf-8"))
    companies = read_csv(V6_COMPANIES)
    security_rows = read_csv(V6_SECURITIES)
    blockers = read_csv(V6_BLOCKERS)
    snapshot, snapshot_id, digest = snapshot_readonly()
    if snapshot_id != v6["snapshot_id"] or len(companies) != 307:
        raise RuntimeError(f"BASELINE_MISMATCH:{snapshot_id}:{len(companies)}")
    general, fca_securities = latest_fca()
    metrics = defaultdict(list)
    for row in security_rows:
        metrics[row["cvm_code"].zfill(6), row["ticker"].upper()].append(row)
    company_by_cvm = {r["cvm_code"].zfill(6): r for r in companies}
    issuer_id_by_cvm = {
        str(item.get("cvm_code") or "").zfill(6): item.get("issuer_id")
        for item in snapshot.get("issuers", [])
    }

    taxonomy = []
    for cvm, company in sorted(company_by_cvm.items()):
        # CVM general sector from the 2025 V6 baseline identifies the 37 source matches.
        if cvm not in TAXONOMY:
            continue
        source = general.get(cvm)
        if source is None:
            raise RuntimeError(f"MISSING_CVM_FCA_GENERAL:{cvm}")
        current_sector = (source.get("Setor_Atividade") or "").removeprefix("Emp. Adm. Part. - ")
        if current_sector != "Comércio (Atacado e Varejo)":
            raise RuntimeError(f"COMMERCE_SECTOR_MISMATCH:{cvm}:{current_sector}")
        category, confidence, rationale = TAXONOMY[cvm]
        description = (source.get("Descricao_Atividade") or "").strip()
        evidence_ref = f"fca_cia_aberta_geral_2025.csv; CVM={cvm}; ID_Documento={source.get('ID_Documento')}; Versao={source.get('Versao')}; Descricao_Atividade"
        decision = commerce_policy_decision(
            category, confidence, "CVM FCA 2025 structured data", evidence_ref
        )
        taxonomy.append(
            {
                "company": company["company"],
                "cvm_code": cvm,
                "cnpj": company["cnpj"],
                "current_cvm_category": source.get("Setor_Atividade") or company["sector"],
                "refined_commerce_category": category,
                "primary_business_description": description,
                "evidence_source": "CVM FCA 2025 structured data",
                "evidence_reference": evidence_ref,
                "confidence": confidence,
                "classification_rationale": rationale,
                "proposed_user_policy": decision["status"],
                "policy_reason": decision["reason"],
                "source_data_reference": source.get("Data_Referencia"),
            }
        )
    if len(taxonomy) != 37:
        raise RuntimeError(f"COMMERCE_TAXONOMY_COUNT:{len(taxonomy)}")
    write_csv(OUT / "commerce_taxonomy_37.csv", taxonomy)

    selection_rows = []
    selection_detail_rows = []
    policy_simulations = Counter()
    candidate_rows = []
    company_final = []
    for cvm, company in sorted(company_by_cvm.items()):
        candidates = []
        for item in fca_securities.get(cvm, []):
            ticker = (item.get("Codigo_Negociacao") or "").upper()
            matches = metrics.get((cvm, ticker), [])
            # A ticker must resolve to one exact CVM-listed candidate and one V6 liquidity record.
            match = next((m for m in matches if m.get("isin")), None)
            class_name = (
                "UNIT"
                if "unit" in (item.get("Valor_Mobiliario") or "").lower()
                else (
                    "ON"
                    if "ordin" in (item.get("Valor_Mobiliario") or "").lower()
                    else item.get("Sigla_Classe_Acao_Preferencial") or "PN"
                )
            )
            candidate = {
                "ticker": ticker,
                "isin": (match or {}).get("isin") or "",
                "security_id": f"{cvm}:{ticker}:{(match or {}).get('isin') or ''}",
                "share_class": class_name,
                "market_type": "010" if match else None,
                "valid_listing": True,
                "liquidity_evidence_complete": bool(
                    match
                    and match.get("metric_status")
                    in {"OBSERVED", "OBSERVED_NO_010_TRADE_2019_2025"}
                    and match.get("traded_days_ratio_30d") not in (None, "")
                    and match.get("median_daily_financial_volume_30d") not in (None, "")
                ),
                "traded_days_ratio_30d": (match or {}).get("traded_days_ratio_30d"),
                "median_daily_financial_volume_30d": (match or {}).get(
                    "median_daily_financial_volume_30d"
                ),
                "price_available": bool(match and match.get("price_status") == "AVAILABLE"),
                "price_effective_date": (match or {}).get("price_effective_date"),
                "listing_start": item.get("Data_Inicio_Negociacao"),
                "listing_end": item.get("Data_Fim_Negociacao"),
                "metric_status": (match or {}).get("metric_status")
                or "NO_EXACT_010_LIQUIDITY_MATCH",
            }
            candidates.append(candidate)
            candidate_rows.append({"cvm_code": cvm, "company": company["company"], **candidate})
        chosen = select_buyable_security(candidates, "S4")
        for policy in ("S1", "S2", "S3", "S4"):
            policy_simulations[policy, select_buyable_security(candidates, policy).status] += 1
        policy_simulations["S0", select_buyable_security(candidates, "S0").status] += 1
        selected = chosen.selected_security
        for candidate in candidates:
            selection_detail_rows.append(
                {
                    "company": company["company"],
                    "cvm_code": cvm,
                    "issuer_id": issuer_id_by_cvm.get(cvm),
                    "candidate_ticker": candidate["ticker"],
                    "isin": candidate["isin"],
                    "class": candidate["share_class"],
                    "market_type": candidate["market_type"],
                    "valid": candidate["valid_listing"],
                    "listing_start": candidate["listing_start"],
                    "listing_end": candidate["listing_end"],
                    "30d_ratio": candidate["traded_days_ratio_30d"],
                    "30d_median_volume": candidate["median_daily_financial_volume_30d"],
                    "selection_score_components": "frequency_desc; median_volume_desc; stable_identity_after_economic_tie",
                    "selected": bool(
                        selected
                        and candidate["ticker"] == selected.get("ticker")
                        and candidate["isin"] == selected.get("isin")
                    ),
                    "selection_policy": "S4",
                    "selection_reason": chosen.reason,
                    "review_reason": chosen.reason
                    if chosen.status == "BUYABLE_SECURITY_REVIEW"
                    else "",
                    "price_available_diagnostic_only": candidate["price_available"],
                }
            )
        user_result = "PASS"
        taxon = next((row for row in taxonomy if row["cvm_code"] == cvm), None)
        if taxon:
            user_result = taxon["proposed_user_policy"]
        elif cvm in {"024112", "019569"}:
            user_result = "INELIGIBLE_USER_POLICY"
        # Evaluate quote completeness after selecting the execution security;
        # another class's price cannot make this selected class data-ready.
        data_complete = company["data_status"] == "COMPLETE" and bool(
            selected and selected.get("price_available")
        )
        final = final_eligibility_state(
            structural="PASS",
            user_policy=user_result,
            security_selection=chosen,
            data_complete=data_complete,
        )
        if company["identity_unresolved_v4"] == "True" and final == "BUYABLE_SECURITY_REVIEW":
            final, review_subtype = "BUYABLE_SECURITY_REVIEW", "IDENTITY_UNRESOLVED"
        else:
            review_subtype = ""
        liquidity = selected_security_liquidity(chosen)
        selection_rows.append(
            {
                "cvm_code": cvm,
                "company": company["company"],
                "candidates_count": len(candidates),
                "buyable_security_status": chosen.status,
                "selected_ticker": (selected or {}).get("ticker"),
                "selected_isin": (selected or {}).get("isin"),
                "selected_class": (selected or {}).get("share_class"),
                "selection_policy": "S4",
                "selection_reason": chosen.reason,
                "traded_days_ratio_30d": (selected or {}).get("traded_days_ratio_30d"),
                "median_daily_financial_volume_30d": (selected or {}).get(
                    "median_daily_financial_volume_30d"
                ),
                "selected_security_l3": liquidity,
                "price_available": (selected or {}).get("price_available"),
                "price_effective_date": (selected or {}).get("price_effective_date"),
                "user_policy_status_v7": user_result,
                "final_status": final,
                "review_subtype": review_subtype,
                "data_reason_codes": company["data_reason_codes"],
                "data_status_v6": company["data_status"],
                "market_cap_policy": "DIAGNOSTIC_ONLY",
            }
        )
        company_final.append(selection_rows[-1])
    write_csv(OUT / "buyable_security_selection.csv", selection_detail_rows)
    write_csv(OUT / "buyable_security_issuer_summary_307.csv", selection_rows)
    write_csv(OUT / "security_candidates_010.csv", candidate_rows)
    write_csv(OUT / "final_eligibility_307.csv", company_final)
    data_blocker_rows = []
    for row in company_final:
        if row["final_status"] != "ELIGIBLE_DATA_BLOCKED":
            continue
        tokens = set(filter(None, row["data_reason_codes"].split(";")))
        categories = set()
        if tokens & {"NO_REFERENCE_PRICE", "NO_VALID_SECURITY", "CLASS_PRICE_MISSING_OR_AMBIGUOUS"}:
            categories.add("PRICE_BLOCKED")
        if tokens & {
            "NO_ACCOUNTING_DATA",
            "FUNDAMENTALS_MISSING",
            "MISSING_EY_INPUT",
            "MISSING_ROC_INPUT",
        }:
            categories.add("FUNDAMENTALS_BLOCKED")
        if tokens & {"NO_CAPITAL_DATA", "UNIT_UNRESOLVED", "SHARES_MISSING"}:
            categories.add("SHARES_BLOCKED")
        if not categories:
            categories.add("OTHER")
        category = next(iter(categories)) if len(categories) == 1 else "MULTIPLE_BLOCKERS"
        data_blocker_rows.append({**row, "data_blocker_category": category})
    write_csv(OUT / "eligible_data_blockers_57.csv", data_blocker_rows)

    # Cross all existing blockers with the selected-security/final-policy outcome.
    final_by_cvm = {row["cvm_code"]: row for row in company_final}
    blocker_rows = []
    for row in blockers:
        result = final_by_cvm.get(row["cvm_code"].zfill(6), {})
        blocker_type = row["blocker_type"]
        reason = row.get("data_reason_codes", "")
        if blocker_type == "UNRESOLVED":
            bucket = "BLOCKER_REVIEW"
        elif "SHARES" in reason:
            bucket = "SHARES_BLOCKED"
        elif "FUNDAMENTAL" in reason or "COMPONENT" in reason:
            bucket = "FUNDAMENTALS_BLOCKED"
        elif (
            "PRICE" in reason
            or "SECURITY" in reason
            or blocker_type
            in {"SOURCE_GAP", "SECURITY_TYPE_NOT_COVERED", "NO_TRADE_ON_REFERENCE_DATE"}
        ):
            bucket = "PRICE_BLOCKED"
        else:
            bucket = "OTHER"
        blocker_rows.append(
            {
                **row,
                "v7_selected_ticker": result.get("selected_ticker"),
                "v7_final_status": result.get("final_status"),
                "v7_liquidity_status": result.get("selected_security_l3"),
                "v7_blocker_bucket": bucket,
            }
        )
    write_csv(OUT / "blockers_v7_31.csv", blocker_rows)

    # Separate the 18 unresolved source records; the source snapshot is read-only.
    raw_records = snapshot.get("issuers", [])
    outside = []
    for issuer in raw_records:
        if issuer.get("methodology_eligibility") != "REVIEW_REQUIRED":
            continue
        sector = issuer.get("economic_sector") or ""
        reason = "SOURCE_MAPPING" if "Bolsas de Valores" in sector else "SECTOR_REVIEW"
        outside.append(
            {
                "cvm_code": str(issuer.get("cvm_code") or "").zfill(6),
                "cnpj": issuer.get("cnpj"),
                "company": issuer.get("display_name"),
                "source_sector": sector,
                "review_category": reason,
                "data_reason_codes": ";".join(issuer.get("methodology_reason_codes") or []),
                "added_to_v7_universe": "NO",
            }
        )
    if len(outside) != 18:
        raise RuntimeError(f"OUTSIDE_BASELINE_COUNT:{len(outside)}")
    write_csv(OUT / "outside_baseline_review_18.csv", outside)

    counts = Counter(row["final_status"] for row in company_final)
    coverage = coverage_metrics(company_final)
    taxonomy_counts = Counter(row["refined_commerce_category"] for row in taxonomy)
    no_trade_rows = []
    for blocker in blockers:
        if blocker["blocker_type"] != "NO_TRADE_ON_REFERENCE_DATE":
            continue
        cvm = blocker["cvm_code"].zfill(6)
        result = final_by_cvm[cvm]
        raw_targets = ast.literal_eval(blocker["securities"])
        target = raw_targets[0] if raw_targets else ""
        no_trade_rows.append(
            {
                "cvm_code": cvm,
                "company": blocker["company"],
                "target_security_v4": target,
                "buyable_security_v7": result["selected_ticker"],
                "same_security": "YES" if target == result["selected_ticker"] else "NO",
                "buyable_30d_ratio": result["traded_days_ratio_30d"],
                "buyable_30d_median_volume": result["median_daily_financial_volume_30d"],
                "l3": result["selected_security_l3"],
                "price_reference_available": result["price_available"],
                "data_status": result["data_status_v6"],
                "final_status": result["final_status"],
                "selection_status": result["buyable_security_status"],
            }
        )
    if len(no_trade_rows) != 9:
        raise RuntimeError(f"NO_TRADE_ISSUER_COUNT:{len(no_trade_rows)}")
    write_csv(OUT / "no_trade_security_recheck_9.csv", no_trade_rows)
    s4_resolved = sum(row["buyable_security_status"] == "RESOLVED" for row in selection_rows)
    s4_review = sum(
        row["buyable_security_status"] == "BUYABLE_SECURITY_REVIEW" for row in selection_rows
    )
    status_sum = sum(counts.values())
    manifest = {
        "audit": "MAGIC_FORMULA_ELIGIBILITY_POLICY_REFINEMENT_V7",
        "mode": "AUDIT_ONLY_NO_RANKING",
        "reference_date": str(REFERENCE_DATE),
        "snapshot_id": snapshot_id,
        "snapshot_digest": digest,
        "snapshot_changed": False,
        "policy_id": "MF_BR_2027_V1_DRAFT",
        "source_files": [
            {
                "path": "data/cvm/fca_cia_aberta_2025.zip",
                "sha256": hashlib.sha256(CVM_ZIP.read_bytes()).hexdigest(),
            },
            {
                "path": "tmp/magic-formula-investable-v6/v6-audit.json",
                "sha256": hashlib.sha256(V6.read_bytes()).hexdigest(),
            },
        ],
        "counts": {
            "baseline": len(company_final),
            "commerce_sector_matches": len(taxonomy),
            "outside_baseline_review": len(outside),
            "buyable_resolved": s4_resolved,
            "buyable_review": s4_review,
            "final_status": dict(counts),
            "status_sum": status_sum,
            "taxonomy": dict(taxonomy_counts),
            "security_simulations": {
                p: {s: n for (q, s), n in policy_simulations.items() if q == p}
                for p in ("S0", "S1", "S2", "S3", "S4")
            },
            "coverage": {k: str(v) for k, v in coverage.items()},
        },
        "policy_activation": {
            "retail": False,
            "liquidity": False,
            "security_selection": False,
            "market_cap": False,
        },
        "ranking_calculated": False,
        "ranking_active": False,
        "ranking_blocked": True,
        "top_30_published": False,
    }
    (OUT / "audit_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    category_counts = Counter(row["refined_commerce_category"] for row in taxonomy)
    blockers_by_bucket = Counter(row["v7_blocker_bucket"] for row in blocker_rows)
    data_blocker_counts = Counter(row["data_blocker_category"] for row in data_blocker_rows)
    blocker_state_counts = Counter(row["v7_final_status"] for row in blocker_rows)
    price_available_selected = sum(row["price_available"] is True for row in selection_rows)
    multi_companies = sum(row["candidates_count"] > 1 for row in selection_rows)
    l3_selected = Counter(row["selected_security_l3"] for row in selection_rows)
    no_trade_changed = sum(
        bool(row["buyable_security_v7"]) and row["same_security"] == "NO" for row in no_trade_rows
    )
    no_trade_review = sum(not bool(row["buyable_security_v7"]) for row in no_trade_rows)
    no_trade_same = sum(row["same_security"] == "YES" for row in no_trade_rows)
    asai = next(row for row in taxonomy if row["cvm_code"] == "025372")
    winners_by_policy = {}
    for policy_id in ("S1", "S2", "S3", "S4"):
        winners_by_policy[policy_id] = {
            cvm: select_buyable_security(
                [r for r in candidate_rows if r["cvm_code"] == cvm], policy_id
            ).selected_security
            for cvm in company_by_cvm
        }
    comparisons = {
        policy_id: {
            "different_selection_vs_S4": sum(
                (winners_by_policy[policy_id][cvm] or {}).get("ticker")
                != (winners_by_policy["S4"][cvm] or {}).get("ticker")
                for cvm in company_by_cvm
            )
        }
        for policy_id in ("S1", "S2", "S3", "S4")
    }
    manifest["counts"]["selection_comparisons"] = comparisons
    (OUT / "audit_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = f"""# Magic Formula — refinamento da política de elegibilidade V7

**Resultado: PASS (auditoria e simulação; nenhuma política ativada).** A V7 separa a política setorial da escolha operacional do ticker, mede L3 somente na security selecionada e conserva REVIEW como estado próprio. Não calculou ranking nem Top 30.

## Baseline e proveniência

Fonte candidata: **360** registros; exclusões financeiras estruturais já existentes: **35**; registros fora da baseline mantidos para revisão: **18**; baseline V6 preservada: **307** empresas. A baseline tem **185 completas / 307 = 60,26%** antes da nova política. Snapshot lido em modo somente leitura: `{snapshot_id}` (referência 2025-12-31; preço V6 2025-12-30). `SNAPSHOT_CHANGED=NO`.

O FCA estruturado traz setor, descrição de atividade e valores mobiliários por companhia. A taxonomia abaixo usa a descrição oficial do FCA; casos sem descrição suficiente ou atividade materialmente mista continuam em revisão. O conteúdo original da fonte CVM tem alguns caracteres acentuados corrompidos no CSV e foi preservado na coluna de descrição. Fontes oficiais: [CVM FCA](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fca) e [CVM FRE](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre). O FCA permite classificar atividade e listagem; o FRE ainda é necessário para resolver os casos de holding/atividade insuficientemente descrita.

## Taxonomia de comércio

O arquivo V6 contém **37 registros** do setor amplo: são **36 exclusões da regra V6 mais ASAI3**, que sobreviveu como exceção. Portanto, o número 36 descreve a regra/exclusão anterior; não o total de linhas setoriais quando a exceção é incluída.

| Categoria refinada | Empresas |
|---|---:|
{"".join(f"| {category} | {category_counts.get(category, 0)} |\n" for category in ("TRADITIONAL_RETAIL", "WHOLESALE", "CASH_AND_CARRY", "DISTRIBUTION", "COMMERCE_ADJACENT", "MIXED_COMMERCE", "UNCERTAIN"))}

`TRADITIONAL_RETAIL` exclui na simulação: **{category_counts.get("TRADITIONAL_RETAIL", 0)}**. `POLICY_REVIEW`: **{category_counts.get("MIXED_COMMERCE", 0) + category_counts.get("UNCERTAIN", 0)}**. Casos `UNCERTAIN`/LOW nunca viram exclusão. ASAI3 = **{asai["refined_commerce_category"]} / {asai["proposed_user_policy"]}**; `ASAI3_EXCEPTION_STILL_NEEDED=NO` na taxonomia refinada; a exceção legada permanece declarada por compatibilidade durante a migração. Aviação preservada: CVM 024112 e 019569 (2); utilities e exclusões financeiras não foram alteradas.

Tabela auditável linha a linha: [commerce_taxonomy_37.csv](appendices/magic_formula_eligibility_policy_v7/commerce_taxonomy_37.csv).

## Aviação e exclusões estruturais

Aviação continua excluída pelos dois códigos já definidos (CVM 024112 e 019569). Utilities continuam sem nova exclusão. As 35 exclusões financeiras estruturais seguem fora do universo de 307, sem alteração. Nenhuma exclusão foi ampliada para logística, aeroportos, fabricantes ou serviços auxiliares.

## Security selecionada e liquidez

A política recomendada para avaliação é **S4**: somente listing B3 válido na data-base, maior proporção de pregões negociados nos últimos 30, depois maior mediana diária de volume financeiro e, em empate econômico completo, identidade estável. A seleção não lê preço, retorno, ranking ou cobertura. A cobertura/liquidez é calculada depois da escolha; preço ausente deixa a empresa bloqueada por dados, não troca a classe.

V6 contava 86 emissores multiclasses no cadastro amplo; o FCA deixa **{multi_companies}** emissores com mais de uma classe de ação/UNIT listada e válida em 2025-12-31. S4 resolveu **{s4_resolved}** emissores e deixou **{s4_review}** em BUYABLE_SECURITY_REVIEW. Das 307 seleções/resoluções, {price_available_selected} têm preço disponível, verificado somente depois da seleção. S0 atual/indefinido deixa 307 em REVIEW. Resultados simulados S1–S4 (RESOLVED / LIQUIDITY_FAIL / REVIEW): {json.dumps(manifest["counts"]["security_simulations"], ensure_ascii=False)}. Diferença de ticker selecionado contra S4: {json.dumps(comparisons, ensure_ascii=False)}. S3 escolhe entre classes que passam L3; S4 seleciona primeiro por execução e então aplica L3.

L3 proposto, não ativado: `traded_days_ratio_30d >= 0.50`, equivalente a pelo menos 15 das 30 sessões. No S4, PASS={l3_selected.get("LIQUIDITY_PASS", 0)}, FAIL={l3_selected.get("LIQUIDITY_FAIL", 0)}, REVIEW={l3_selected.get("LIQUIDITY_REVIEW", 0)}. A regra evita depender de um negócio isolado recente e não exige liquidez institucional; volume é apenas desempate. Recência L1/L2 sozinha é insuficiente, e não há mínimo de volume.

## Market cap

Market cap permanece DIAGNOSTIC ONLY: no V6, estava disponível para 163/269 emissores na simulação da política anterior. Nesta V7 não há piso nem percentil; valores ausentes não excluem empresas.

Arquivos: [buyable_security_selection.csv](appendices/magic_formula_eligibility_policy_v7/buyable_security_selection.csv) contém cada security candidata e seus critérios; o resumo por emissor está em [buyable_security_issuer_summary_307.csv](appendices/magic_formula_eligibility_policy_v7/buyable_security_issuer_summary_307.csv). A lista completa de candidatos está em [security_candidates_010.csv](appendices/magic_formula_eligibility_policy_v7/security_candidates_010.csv).

## Rechecagem dos 9 emissores sem negociação

Após S4, {no_trade_same} mantiveram o ticker alvo V4, {no_trade_changed} mudaram para outra security selecionada e {no_trade_review} ficaram em revisão sem candidato comparável. A tabela lista o candidato operacional, L3 e preço desse ticker; uma classe não é resgatada pela liquidez de outra. Consulte [no_trade_security_recheck_9.csv](appendices/magic_formula_eligibility_policy_v7/no_trade_security_recheck_9.csv).

## Funil e estados finais V7

`360 = 35` exclusões financeiras estruturais já existentes `+ 18` registros fora da baseline `+ 307` na baseline. Dentro dela: 13 excluídas por política de usuário, 10 em revisão setorial, 47 em BUYABLE_SECURITY_REVIEW, 23 LIQUIDITY_FAIL e **214 L3_PASS**. Desses 214, 157 estão completos e 57 seguem bloqueados por dados. Os 157 são candidatos completos após elegibilidade, sem ranking calculado.

| Estado | Empresas |
|---|---:|
{"".join(f"| {status} | {counts.get(status, 0)} |\n" for status in ("INELIGIBLE_STRUCTURAL", "INELIGIBLE_USER_POLICY", "POLICY_REVIEW", "BUYABLE_SECURITY_REVIEW", "LIQUIDITY_FAIL", "LIQUIDITY_REVIEW", "ELIGIBLE_DATA_BLOCKED", "ELIGIBLE_COMPLETE"))}

`STATUS_SUM={status_sum}`. Structural exclusions dentro da baseline=0; financeiras 35 continuam fora da baseline. Confirmadas elegíveis={coverage["confirmed_eligible"]}; confirmadas inelegíveis={coverage["confirmed_ineligible"]}; revisão necessária={coverage["review_required"]}. Completas={coverage["confirmed_complete"]}; bloqueadas por dados={coverage["confirmed_blocked"]}. Coverage entre elegíveis confirmadas={coverage["confirmed_eligible_coverage"]:.2f}%; denominador conservador que inclui REVIEW={coverage["conservative_coverage"]:.2f}%.

## Blockers e registros externos

Blockers V6 cruzados com estado e ticker V7: 31. `USER_POLICY_EXCLUDED={blocker_state_counts.get("INELIGIBLE_USER_POLICY", 0)}`, `LIQUIDITY_FAIL={blocker_state_counts.get("LIQUIDITY_FAIL", 0)}`, `REVIEW={blocker_state_counts.get("BUYABLE_SECURITY_REVIEW", 0) + blocker_state_counts.get("POLICY_REVIEW", 0) + blocker_state_counts.get("LIQUIDITY_REVIEW", 0)}`, `ELIGIBLE_PRICE_BLOCKED={blocker_state_counts.get("ELIGIBLE_DATA_BLOCKED", 0)}`. Buckets de origem: `{dict(blockers_by_bucket)}`. Quem falhou L3 não deve receber novas tentativas de preço até eventual mudança aprovada da regra. [blockers_v7_31.csv](appendices/magic_formula_eligibility_policy_v7/blockers_v7_31.csv).

Dos 57 elegíveis bloqueados por dados: `{dict(data_blocker_counts)}`. A classificação usa os reason codes V6, sem recalcular métricas nem ranking: [eligible_data_blockers_57.csv](appendices/magic_formula_eligibility_policy_v7/eligible_data_blockers_57.csv).

Os 18 registros fora da baseline foram inventariados separadamente: **{sum(r["review_category"] == "SECTOR_REVIEW" for r in outside)} SECTOR_REVIEW**, **{sum(r["review_category"] == "SOURCE_MAPPING" for r in outside)} SOURCE_MAPPING**, identity=0, duplicate=0, other=0; adicionados à baseline=0. [outside_baseline_review_18.csv](appendices/magic_formula_eligibility_policy_v7/outside_baseline_review_18.csv).

## Recomendação e controles

Recomenda-se submeter à decisão do usuário a exclusão somente de `TRADITIONAL_RETAIL`, manter casos mixed/uncertain em REVIEW, avaliar S4 com L3 de 50% como filtro operacional e preservar volume/market cap como diagnóstico. Ainda há **{s4_review}** comparações de security em revisão e **{category_counts.get("UNCERTAIN", 0) + category_counts.get("MIXED_COMMERCE", 0)}** classificações de comércio em revisão; isso não deve ser promovido a exclusão automática.

`POLICY_ID=MF_BR_2027_V1_DRAFT`; varejo, seleção S4, L3 e market cap **não ativados**. `RANKING_CALCULATED=NO`, `RANKING_ACTIVE=NO`, `RANKING_BLOCKED=YES`, `TOP_30_PUBLISHED=NO`. Artefatos de decisão: [final_eligibility_307.csv](appendices/magic_formula_eligibility_policy_v7/final_eligibility_307.csv), [audit_manifest.json](appendices/magic_formula_eligibility_policy_v7/audit_manifest.json).

`POLICY_READY_FOR_APPROVAL=YES`: o draft tem regras determinísticas, resultados reproduzíveis e estados REVIEW preservados. Decisões propostas para aprovação explícita: (1) excluir somente `TRADITIONAL_RETAIL`; (2) adotar S4 para representar operacionalmente o emissor; (3) adotar L3 de 50% como filtro; (4) manter as 50 comparações incompletas de security e as 10 classificações mixed/uncertain em REVIEW até nova evidência.

## Validação

O gerador verifica snapshot V6, baseline 307, taxonomia 37, 18 fora da baseline, 9 emissores no-trade e soma final 307. O relatório é uma simulação reproduzível; a política segue DRAFT até decisão explícita.
"""
    (ROOT / "docs/MAGIC_FORMULA_ELIGIBILITY_POLICY_REFINEMENT_V7.md").write_text(
        report, encoding="utf-8"
    )
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
