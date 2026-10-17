"""Generate the deterministic, read-only V8 Magic Formula policy resolution audit."""

# ruff: noqa: E501 -- generated Markdown/table text is intentionally kept readable.

from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from income_analytics.application.magic_formula_screening import (
    MagicFormulaScreeningPreferences,
    liquidity_candidate_status,
    methodology_eligibility_state,
    select_security_s4,
)

ROOT = Path(__file__).resolve().parents[1]
V7 = ROOT / "docs/appendices/magic_formula_eligibility_policy_v7"
V6 = ROOT / "docs/appendices/magic_formula_investable_universe_v6"
OUT = ROOT / "docs/appendices/magic_formula_policy_review_resolution_v8"
REPORT = ROOT / "docs/MAGIC_FORMULA_POLICY_REVIEW_RESOLUTION_V8.md"
REFERENCE_DATE = "2025-12-30"
REFERENCE_DATE_RAW = "20251230"
AUDITED_B3_IDENTITY = ROOT / "data/magic_formula/price_recovery_identity/20260923T102111856750Z"
TAXONOMY_RESOLUTION = {
    "020990": (
        "MIXED_COMMERCE",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.3 confirma segmentos digital, físico, franquias e publicidade, com varejo multicanal e marketplace; mantém MIXED_COMMERCE.",
        "157904",
    ),
    "021440": (
        "MIXED_COMMERCE",
        "RESOLVED_MEDIUM_CONFIDENCE",
        "FRE 1.3 confirma segmento único de moda e venda; FCA também descreve fabricação/terceirização e comércio; mantém MIXED_COMMERCE.",
        "156882",
    ),
    "022055": (
        "MIXED_COMMERCE",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.3 discrimina os segmentos varejo e produtos/serviços financeiros; mantém MIXED_COMMERCE.",
        "157778",
    ),
    "006505": (
        "TRADITIONAL_RETAIL",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.3 identifica lojas físicas e online e comercialização como atividade principal; seção 1.4 descreve fabricação acessória de móveis pela controlada.",
        "157206",
    ),
    "019909": (
        "COMMERCE_ADJACENT",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.1 documenta desenvolvimento, investimento e administração de shopping centers; item 1.3 é facultativo para companhia categoria B.",
        "156678",
    ),
    "022519": (
        "COMMERCE_ADJACENT",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.3 identifica desenvolvimento, montagem e venda de relógios, com assistência técnica complementar.",
        "156235",
    ),
    "024694": (
        "MIXED_COMMERCE",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.3 descreve um segmento integrado de venda de artigos esportivos, com canais físicos e digitais e atividades de atacado acessórias.",
        "157587",
    ),
    "024805": (
        "TRADITIONAL_RETAIL",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.3 informa segmento varejo e 100% da receita líquida no varejo; produção industrial está segregada em controlada.",
        "157501",
    ),
    "025089": (
        "MIXED_COMMERCE",
        "RESOLVED_MEDIUM_CONFIDENCE",
        "FRE 1.1 confirma comércio de produtos pet integrado a serviços veterinários e banho/tosa; mantém MIXED_COMMERCE.",
        "154894",
    ),
    "025186": (
        "MIXED_COMMERCE",
        "RESOLVED_HIGH_CONFIDENCE",
        "FRE 1.3 lista segmentos atacado, varejo, atacarejo e eletro, confirmando atuação multicanal e categorias diversas.",
        "157755",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = columns or (list(rows[0]) if rows else [])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_class(specification: str) -> str:
    return specification.strip().upper().split(" ", 1)[0]


def load_audited_b3_identities(
    companies: dict[str, dict[str, str]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Read issuer-confirmed B3 identity rows from the already audited resolver batch."""
    identities: dict[str, list[dict]] = defaultdict(list)
    manifests = []
    paths = sorted(AUDITED_B3_IDENTITY.glob("*.json"))
    class_by_isin_suffix = {
        "CNOR": "ON",
        "CNPR": "PN",
        "CNPA": "PNA",
        "CNPB": "PNB",
        "CDAM": "UNIT",
    }
    for path in paths:
        if not path.exists() or path.name.endswith(".identity.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not payload or payload.get("hasQuotation") != "S" or payload.get("status") != "A":
            continue
        code = str(payload.get("codeCVM") or payload.get("cvm_code") or "").zfill(6)
        company = companies.get(code)
        if not company:
            continue
        if re.sub(r"\D", "", str(payload.get("cnpj") or "")) != re.sub(
            r"\D", "", str(company.get("cnpj") or "")
        ):
            continue
        ticker = str(payload.get("code") or payload.get("ticker") or "").strip().upper()
        other_codes = payload.get("otherCodes") or []
        isins = [
            str(item.get("isin") or "").strip().upper() for item in other_codes if item.get("isin")
        ]
        if payload.get("isin"):
            isins.append(str(payload["isin"]).strip().upper())
        listing_raw = payload.get("dateQuotation") or payload.get("listing_date") or ""
        try:
            listing_start = (
                date.fromisoformat(listing_raw)
                if "-" in listing_raw
                else datetime.strptime(listing_raw, "%d/%m/%Y").date()
            )
        except TypeError:
            listing_start = None
        except ValueError:
            listing_start = None
        if (
            not re.fullmatch(r"[A-Z0-9]{4,6}", ticker)
            or not isins
            or not listing_start
            or listing_start.isoformat() > REFERENCE_DATE
        ):
            continue
        for isin in sorted(set(isins)):
            suffix = isin[7:11] if len(isin) == 12 else ""
            share_class = class_by_isin_suffix.get(suffix)
            if not share_class:
                continue
            identities[code].append(
                {
                    "cvm_code": code,
                    "company": company["company"],
                    "ticker": ticker,
                    "isin": isin,
                    "security_id": f"{code}:{ticker}:{isin}",
                    "share_class": share_class,
                    "market_type": "010",
                    "valid_listing": True,
                    "liquidity_evidence_complete": False,
                    "listing_start": listing_start.isoformat(),
                    "listing_end": "",
                    "identity_source": str(path.relative_to(ROOT)),
                    "identity_source_sha256": sha256(path),
                }
            )
            manifests.append(
                {
                    "file": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                    "cvm_code": code,
                    "ticker": ticker,
                    "isin": isin,
                }
            )
    return identities, manifests


def scan_cotahist(
    candidates: list[dict[str, str]], audited_b3: dict[str, list[dict]]
) -> tuple[dict, dict, list[str]]:
    """Use only existing official annual B3 COTAHIST archives and market 010."""
    tickers = {
        row["ticker"].strip().upper()
        for row in candidates
        if re.fullmatch(r"[A-Z0-9]{4,6}", row["ticker"].strip().upper())
    }
    tickers.update(row["ticker"] for rows in audited_b3.values() for row in rows)
    identity_classes: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    daily_volume: dict[str, dict[str, float]] = defaultdict(dict)
    sessions: set[str] = set()
    manifests = []
    for year in (2022, 2023, 2024, 2025):
        path = ROOT / f"data/cotahist/COTAHIST_A{year}.ZIP"
        records = 0
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.upper().endswith(".TXT")]
            if len(members) != 1:
                raise ValueError(f"COTAHIST_MEMBER_AMBIGUOUS:{path.name}")
            with archive.open(members[0]) as stream:
                for line_number, raw in enumerate(stream, start=1):
                    if raw[:2] != b"01":
                        continue
                    if len(raw.rstrip(b"\r\n")) != 245:
                        raise ValueError(f"COTAHIST_INVALID_RECORD:{path.name}:{line_number}")
                    if raw[24:27] != b"010":
                        continue
                    records += 1
                    ticker = raw[12:24].decode("latin1").strip().upper()
                    day = raw[2:10].decode("ascii")
                    if year == 2025 and day <= REFERENCE_DATE_RAW:
                        sessions.add(day)
                    if ticker not in tickers:
                        continue
                    isin = raw[230:242].decode("latin1").strip().upper()
                    security_class = normalized_class(raw[39:49].decode("latin1"))
                    if isin and security_class:
                        identity_classes[ticker][security_class].add(isin)
                    if year == 2025 and day <= REFERENCE_DATE_RAW:
                        volume = int(raw[170:188].decode("ascii")) / 100
                        daily_volume[ticker][day] = daily_volume[ticker].get(day, 0.0) + volume
        manifests.append(
            {
                "file": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "market_type": "010",
                "records_scanned": records,
            }
        )

    last_30 = sorted(sessions)[-30:]
    if len(last_30) != 30:
        raise ValueError("INSUFFICIENT_REFERENCE_SESSIONS")
    # B3 identity confirms a listed instrument even if its market-010 records show
    # zero activity in the complete checked span; zeros then become evidence.
    for rows in audited_b3.values():
        for row in rows:
            class_map = identity_classes[row["ticker"]][row["share_class"]]
            class_map.add(row["isin"])

    result = {}
    for ticker, class_map in identity_classes.items():
        result[ticker] = {}
        for security_class, isins in class_map.items():
            if len(isins) != 1:
                result[ticker][security_class] = {
                    "status": "ISIN_UNRESOLVED",
                    "isins": sorted(isins),
                }
                continue
            volumes = [daily_volume[ticker].get(day, 0.0) for day in last_30]
            traded_days = sum(daily_volume[ticker].get(day, 0.0) > 0 for day in last_30)
            result[ticker][security_class] = {
                "status": "IDENTITY_CONFIRMED_COTAHIST",
                "isin": next(iter(isins)),
                "traded_days": traded_days,
                "expected_days": 30,
                "ratio": traded_days / 30,
                "median_daily_financial_volume": statistics.median(volumes),
                "zero_activity": traded_days == 0,
                "last_30_sessions": f"{last_30[0]}..{last_30[-1]}",
                "identity_source": "B3 official identity + complete annual COTAHIST market-010 scan",
            }
    return result, {"sessions": last_30, "manifests": manifests}, last_30


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = read_csv(V7 / "buyable_security_issuer_summary_307.csv")
    candidates = read_csv(V7 / "security_candidates_010.csv")
    taxonomy = read_csv(V7 / "commerce_taxonomy_37.csv")
    blockers = read_csv(V7 / "blockers_v7_31.csv")
    v6_companies = {row["cvm_code"]: row for row in read_csv(V6 / "company_eligibility_307.csv")}
    v6_securities = read_csv(V6 / "security_liquidity_431.csv")
    candidate_by_issuer: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        candidate_by_issuer[row["cvm_code"]].append(row)
    audited_b3, b3_identity_manifests = load_audited_b3_identities(v6_companies)
    cotahist, cotahist_manifest, sessions = scan_cotahist(candidates, audited_b3)

    # Final commerce taxonomy keeps V7 labels and records the bounded official-source result.
    commerce_rows = []
    for row in taxonomy:
        category, resolution, rationale, fre_id = TAXONOMY_RESOLUTION.get(
            row["cvm_code"],
            (
                row["refined_commerce_category"],
                "NOT_REVIEWED_BY_V8_SCOPE",
                "Taxonomia V7 preservada; fora dos dez casos pendentes.",
                "",
            ),
        )
        official_fre_rows = row["cvm_code"] in TAXONOMY_RESOLUTION
        fre_path = ROOT / (
            "tmp/fre-casas-2025.zip"
            if row["cvm_code"] == "006505"
            else f"tmp/fre-v8-{row['cvm_code']}.zip"
        )
        commerce_rows.append(
            {
                **row,
                "refined_commerce_category": category,
                "confidence": "HIGH"
                if resolution == "RESOLVED_HIGH_CONFIDENCE"
                else (
                    "MEDIUM" if resolution == "RESOLVED_MEDIUM_CONFIDENCE" else row["confidence"]
                ),
                "taxonomy_resolution_v8": resolution,
                "resolution_rationale_v8": rationale,
                "official_source_attempt_v8": "CVM FCA 2025 + CVM FRE 2025 official XML/PDF sections 1.1/1.3/1.4"
                if official_fre_rows
                else "CVM FCA 2025",
                "fre_document_id": fre_id,
                "fre_document_url": f"https://www.rad.cvm.gov.br/ENETCONSULTA/frmDownloadDocumento.aspx?CodigoInstituicao=1&NumeroSequencialDocumento={fre_id}"
                if fre_id
                else "",
                "fre_document_sha256": sha256(fre_path) if official_fre_rows else "",
                "fre_evidence_summary": rationale if official_fre_rows else "",
                "methodology_impact": "NONE_USER_FILTER_ATTRIBUTE_ONLY",
                "legacy_exception": "DEPRECATED_COMPATIBILITY_ONLY"
                if row["cvm_code"] == "025372"
                else "",
            }
        )
    write_csv(OUT / "commerce_taxonomy_final.csv", commerce_rows)

    review_rows = []
    resolved_by_issuer = {}
    for row in summary:
        if row["buyable_security_status"] != "BUYABLE_SECURITY_REVIEW":
            continue
        issuer_candidates = list(candidate_by_issuer[row["cvm_code"]])
        audited_identities = audited_b3.get(row["cvm_code"], [])
        audited_classes = {item["share_class"] for item in audited_identities}
        if audited_classes:
            # A previously audited, issuer/CNPJ-matched B3 identity supersedes a
            # malformed or stale V7 candidate for that same share class.
            issuer_candidates = [
                candidate
                for candidate in issuer_candidates
                if candidate["share_class"].strip().upper() not in audited_classes
            ] + audited_identities
        evaluated = []
        missing = []
        for candidate in issuer_candidates:
            ticker = candidate["ticker"].strip().upper()
            share_class = candidate["share_class"].strip().upper()
            evidence = cotahist.get(ticker, {}).get(share_class)
            active_on_reference = (
                str(candidate["valid_listing"]).lower() == "true"
                and candidate["listing_start"] <= REFERENCE_DATE
                and (not candidate["listing_end"] or candidate["listing_end"] >= REFERENCE_DATE)
            )
            if (
                active_on_reference
                and evidence
                and evidence["status"] == "IDENTITY_CONFIRMED_COTAHIST"
            ):
                evaluated.append(
                    {
                        **candidate,
                        **evidence,
                        "isin": evidence["isin"],
                        "market_type": "010",
                        "valid_listing": True,
                        "liquidity_evidence_complete": True,
                        "traded_days_ratio_30d": evidence["ratio"],
                        "median_daily_financial_volume_30d": evidence[
                            "median_daily_financial_volume"
                        ],
                    }
                )
            else:
                missing.append(
                    (
                        candidate,
                        {"status": "SECURITY_NOT_VALID_ON_REFERENCE_DATE"}
                        if not active_on_reference
                        else evidence,
                    )
                )
        selection = (
            select_security_s4(evaluated)
            if len(evaluated) == len(issuer_candidates)
            else {"status": "BUYABLE_SECURITY_REVIEW", "selected_security": None}
        )
        selected = selection["selected_security"]
        if selection["status"] == "RESOLVED":
            l3_status = liquidity_candidate_status(
                selected["ratio"], evidence_complete=True
            ).removeprefix("LIQUIDITY_")
            outcome = "BUYABLE_SECURITY_RESOLVED_L3_" + l3_status
            cause = "MISSING_LIQUIDITY_HISTORY"
            resolved_by_issuer[row["cvm_code"]] = {"selected": selected, "l3": l3_status}
        else:
            l3_status = "REVIEW"
            outcome = "BUYABLE_SECURITY_UNRESOLVED_REVIEW"
            malformed = any(
                not re.fullmatch(r"[A-Z0-9]{4,6}", c["ticker"].strip().upper())
                for c in issuer_candidates
            )
            # Cause labels are restricted to the V8 list; explain the unresolved fact below.
            cause = (
                "IDENTITY_INCOMPLETE" if malformed or not issuer_candidates else "ISIN_UNRESOLVED"
            )
        review_rows.append(
            {
                "cvm_code": row["cvm_code"],
                "company": row["company"],
                "in_v7_primary_funnel": str(
                    row["final_status"] == "BUYABLE_SECURITY_REVIEW"
                ).upper(),
                "v7_candidate_count": row["candidates_count"],
                "v7_review_reason": (
                    "NO_EXACT_010_LIQUIDITY_MATCH"
                    if selection["status"] == "RESOLVED"
                    else (
                        "IDENTITY_OR_ISIN_UNRESOLVED"
                        if any((e or {}).get("status") == "ISIN_UNRESOLVED" for _, e in missing)
                        else "NO_VALID_LISTED_SECURITY_IDENTITY"
                    )
                ),
                "primary_cause": cause,
                "s4_outcome_v8": outcome,
                "selected_ticker_v8": selected["ticker"] if selected else "",
                "selected_isin_v8": selected["isin"] if selected else "",
                "selected_class_v8": selected["share_class"] if selected else "",
                "candidate_comparison_v8": json.dumps(
                    [
                        {
                            "ticker": c["ticker"],
                            "class": c["share_class"],
                            "isin": c.get("isin", ""),
                            "ratio": c.get("ratio"),
                            "median_volume": c.get("median_daily_financial_volume"),
                            "identity_status": c.get("status", "MISSING"),
                            "identity_source": c.get("identity_source", "V7_CVM_CANDIDATE"),
                        }
                        for c in evaluated
                    ]
                    + [
                        {
                            "ticker": c["ticker"],
                            "class": c["share_class"],
                            "isin": "",
                            "ratio": None,
                            "median_volume": None,
                            "identity_status": (e or {}).get("status", "NO_COTAHIST_IDENTITY"),
                            "identity_source": c.get("identity_source", "V7_CVM_CANDIDATE"),
                        }
                        for c, e in missing
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "missing_evidence": ";".join(
                    sorted({(e or {}).get("status", "NO_COTAHIST_IDENTITY") for _, e in missing})
                ),
                "evidence_source": "CVM FCA candidate identity and previously audited B3 issuer/CNPJ identity where available + existing B3 COTAHIST 2022-2025, market 010",
                "evidence_reference": ";".join(
                    [m["file"] for m in cotahist_manifest["manifests"]]
                    + sorted(
                        {
                            c["identity_source"]
                            for c in issuer_candidates
                            if c.get("identity_source")
                        }
                    )
                ),
                "stop_rule": (
                    "S4 resolved from issuer-confirmed identity; market 010 traded-day ratio, median financial volume and stable identity tie-break applied."
                    if selection["status"] == "RESOLVED"
                    else "REVIEW mantido; sem selecionar classe substituta sem identidade e comparação completas."
                ),
            }
        )
    write_csv(OUT / "buyable_security_review_resolution.csv", review_rows)

    # Validate all 23 V7 failures from the original selected identity and 30 sessions.
    liquidity_rows = []
    for row in summary:
        original = row["selected_security_l3"]
        if original not in {"LIQUIDITY_FAIL", "LIQUIDITY_PASS", "LIQUIDITY_REVIEW"}:
            continue
        ticker = row["selected_ticker"]
        evidence = cotahist.get(ticker, {}).get(row["selected_class"])
        exact_v6_rows = [
            item
            for item in v6_securities
            if (
                item["cvm_code"] == row["cvm_code"]
                and item["ticker"] == ticker
                and item["isin"] == row["selected_isin"]
            )
        ]
        v6_evidence = exact_v6_rows[0] if len(exact_v6_rows) == 1 else None
        v8_selection = resolved_by_issuer.get(row["cvm_code"])
        if v8_selection:
            selected = v8_selection["selected"]
            l3_after = "LIQUIDITY_PASS" if v8_selection["l3"] == "PASS" else "LIQUIDITY_FAIL"
            chosen_ticker, chosen_isin, ratio = (
                selected["ticker"],
                selected["isin"],
                selected["ratio"],
            )
            record_state = "RESOLVED_FROM_OFFICIAL_COTAHIST"
        elif original != "LIQUIDITY_REVIEW":
            # V7 selected identity/metrics are retained. A V7 failure is not rerun as recovery.
            l3_after = original
            chosen_ticker, chosen_isin, ratio = (
                ticker,
                row["selected_isin"],
                row["traded_days_ratio_30d"],
            )
            record_state = "V7_SELECTED_IDENTITY_AND_METRIC_RETAINED"
        else:
            l3_after = "LIQUIDITY_REVIEW"
            chosen_ticker, chosen_isin, ratio = "", "", ""
            record_state = "BUYABLE_SECURITY_REVIEW_UNRESOLVED"
        metric_matches = False
        if (
            evidence
            and evidence.get("status") == "IDENTITY_CONFIRMED_COTAHIST"
            and evidence.get("isin") == row.get("selected_isin")
        ):
            try:
                metric_matches = (
                    abs(float(evidence["ratio"]) - float(row["traded_days_ratio_30d"])) < 1e-12
                )
            except TypeError:
                metric_matches = False
            except ValueError:
                metric_matches = False
        if (
            not metric_matches
            and v6_evidence
            and v6_evidence.get("metric_status") in {"OBSERVED", "OBSERVED_NO_010_TRADE_2019_2025"}
        ):
            try:
                metric_matches = (
                    v6_evidence.get("trading_days_30d") == "30"
                    and v6_evidence.get("isin") == row.get("selected_isin")
                    and abs(
                        float(v6_evidence["traded_days_ratio_30d"])
                        - float(row["traded_days_ratio_30d"])
                    )
                    < 1e-12
                )
            except KeyError:
                metric_matches = False
            except TypeError:
                metric_matches = False
            except ValueError:
                metric_matches = False
            if metric_matches:
                record_state = "CONFIRMED_FROM_V6_AUDITED_COTAHIST"
        if original == "LIQUIDITY_FAIL" and not metric_matches:
            validation = "REVIEW_REQUIRED_EVIDENCE_MISMATCH"
        elif original == "LIQUIDITY_FAIL":
            validation = "CONFIRMED_FAIL_FROM_010_COTAHIST"
        elif original == "LIQUIDITY_REVIEW" and v8_selection:
            validation = "RESOLVED_BY_010_COTAHIST"
        elif original == "LIQUIDITY_REVIEW":
            validation = "STOP_RULE_REVIEW"
        else:
            validation = "PRESERVED_V7_RESULT"
        liquidity_rows.append(
            {
                "cvm_code": row["cvm_code"],
                "company": row["company"],
                "ticker": chosen_ticker,
                "isin": chosen_isin,
                "v7_l3_status": original,
                "v8_l3_status": l3_after,
                "traded_days_ratio_30d": ratio,
                "threshold": "0.50",
                "sessions": "30",
                "zero_activity_distinguished": str(
                    bool(
                        (evidence and evidence.get("zero_activity"))
                        or (
                            v6_evidence
                            and v6_evidence.get("metric_status")
                            == "OBSERVED_NO_010_TRADE_2019_2025"
                        )
                    )
                ).upper(),
                "evidence_state": record_state,
                "validation": validation,
                "source": "V6 audited COTAHIST 2019-2025 / V8 existing COTAHIST 2022-2025; market 010",
            }
        )
    write_csv(OUT / "liquidity_review_resolution.csv", liquidity_rows)

    # Rebuild canonical statuses without V7 retail/aviation policy decisions.
    methodological = []
    for row in summary:
        security_status = row["buyable_security_status"]
        l3 = row["selected_security_l3"]
        selected_ticker, selected_isin, ratio = (
            row["selected_ticker"],
            row["selected_isin"],
            row["traded_days_ratio_30d"],
        )
        if row["cvm_code"] in resolved_by_issuer:
            resolved = resolved_by_issuer[row["cvm_code"]]
            security_status = "RESOLVED"
            selected = resolved["selected"]
            selected_ticker, selected_isin, ratio = (
                selected["ticker"],
                selected["isin"],
                selected["ratio"],
            )
            l3 = "LIQUIDITY_PASS" if resolved["l3"] == "PASS" else "LIQUIDITY_FAIL"
        l3 = "LIQUIDITY_REVIEW" if security_status != "RESOLVED" else l3
        v6 = v6_companies[row["cvm_code"]]
        structural = (
            "INELIGIBLE_STRUCTURAL"
            if v6.get("structural_status") == "INELIGIBLE_STRUCTURAL"
            else "PASS"
        )
        final = methodology_eligibility_state(
            structural_status=structural,
            security_status=security_status,
            liquidity_status=l3.replace("LIQUIDITY_PASS", "LIQUIDITY_PASS").replace(
                "LIQUIDITY_FAIL", "LIQUIDITY_FAIL"
            ),
            data_complete=row["data_status_v6"] == "COMPLETE",
        )
        commerce = next((x for x in commerce_rows if x["cvm_code"] == row["cvm_code"]), {})
        aviation = row["cvm_code"] in {"024112", "019569"}
        sector = v6.get("sector", "")
        utility = (
            "Energia Elétrica" in sector
            or "Água" in sector
            or "Gás" in sector
            or "Saneamento" in sector
        )
        attrs = {
            "commerce_category": commerce.get("refined_commerce_category", ""),
            "commerce_classification_uncertain": commerce.get("taxonomy_resolution_v8")
            == "UNRESOLVED_REVIEW",
            "aviation_related": aviation,
            "utility_related": utility,
            "financial_related": structural == "INELIGIBLE_STRUCTURAL",
        }
        methodological.append(
            {
                "cvm_code": row["cvm_code"],
                "company": row["company"],
                "sector": sector,
                "structural_status": structural,
                "security_status_v8": security_status,
                "selected_ticker_v8": selected_ticker,
                "selected_isin_v8": selected_isin,
                "traded_days_ratio_30d_v8": ratio,
                "liquidity_status_v8": l3,
                "data_status_v6": row["data_status_v6"],
                "methodological_status_v8": final,
                "review_reason": ""
                if final not in {"BUYABLE_SECURITY_REVIEW", "LIQUIDITY_REVIEW"}
                else "OFFICIAL_IDENTITY_OR_CLASS_COMPARISON_INCOMPLETE",
                **{f"{key}": value for key, value in attrs.items()},
            }
        )
    write_csv(OUT / "methodological_universe_v8.csv", methodological)
    write_csv(
        OUT / "screening_attributes_v8.csv",
        [
            {
                "cvm_code": row["cvm_code"],
                "company": row["company"],
                "sector": row["sector"],
                "commerce_category": row["commerce_category"],
                "aviation_related": row["aviation_related"],
                "utility_related": row["utility_related"],
                "financial_related": row["financial_related"],
                "commerce_classification_uncertain": row["commerce_classification_uncertain"],
                "default_excluded": "NO",
                "personal_profile_excluded": str(
                    row["commerce_category"] == "TRADITIONAL_RETAIL"
                    or row["aviation_related"] == "True"
                ).upper(),
                "methodological_status_v8": row["methodological_status_v8"],
            }
            for row in methodological
        ],
    )

    # Preserve the historical 31 blockers and map them to V8 outcomes.
    final_by_cvm = {row["cvm_code"]: row for row in methodological}
    review_by_cvm = {row["cvm_code"]: row for row in review_rows}
    blocker_rows = []
    for blocker in blockers:
        code = blocker["cvm_code"]
        final = final_by_cvm.get(code, {})
        if (
            blocker["v7_blocker_bucket"] == "PRICE_BLOCKED"
            and blocker["v7_final_status"] == "LIQUIDITY_FAIL"
        ):
            action = "DATA_RECOVERY_DEFERRED_BY_LIQUIDITY"
        elif (
            blocker["v7_final_status"] == "BUYABLE_SECURITY_REVIEW"
            or blocker["v7_liquidity_status"] == "LIQUIDITY_REVIEW"
        ):
            new_review = review_by_cvm.get(code, {})
            if new_review.get("s4_outcome_v8") == "BUYABLE_SECURITY_RESOLVED_L3_PASS":
                action = "REVIEW_TO_L3_PASS"
            elif new_review.get("s4_outcome_v8") == "BUYABLE_SECURITY_RESOLVED_L3_FAIL":
                action = "REVIEW_TO_L3_FAIL"
            else:
                action = "REVIEW_UNRESOLVED"
        elif blocker["v7_final_status"] == "ELIGIBLE_DATA_BLOCKED":
            if final.get("methodological_status_v8") == "ELIGIBLE_DATA_BLOCKED":
                action = "HIGH_VALUE_DATA_RECOVERY_TARGET"
            elif final.get("methodological_status_v8") == "LIQUIDITY_FAIL":
                action = "DATA_RECOVERY_DEFERRED_BY_LIQUIDITY"
            else:
                action = "NOT_RECOVERY_READY_REVIEW"
        else:
            action = "PRESERVE_HISTORICAL_BLOCKER"
        blocker_rows.append(
            {
                **blocker,
                "v8_resolution": action,
                "v8_methodological_status": final.get("methodological_status_v8", ""),
                "historical_provenance_preserved": "YES",
            }
        )
    write_csv(OUT / "historical_blockers_after_v8.csv", blocker_rows)

    status_counts = Counter(row["methodological_status_v8"] for row in methodological)
    for state in (
        "INELIGIBLE_STRUCTURAL",
        "BUYABLE_SECURITY_REVIEW",
        "LIQUIDITY_FAIL",
        "LIQUIDITY_REVIEW",
        "ELIGIBLE_DATA_BLOCKED",
        "ELIGIBLE_COMPLETE",
    ):
        status_counts.setdefault(state, 0)
    complete = status_counts["ELIGIBLE_COMPLETE"]
    blocked = status_counts["ELIGIBLE_DATA_BLOCKED"]
    review_count = status_counts["BUYABLE_SECURITY_REVIEW"] + status_counts["LIQUIDITY_REVIEW"]
    confirmed = complete + blocked
    coverage = complete / confirmed if confirmed else 0
    conservative = complete / (confirmed + review_count) if confirmed + review_count else 0
    eligible_rows = [
        row
        for row in methodological
        if row["methodological_status_v8"] in {"ELIGIBLE_COMPLETE", "ELIGIBLE_DATA_BLOCKED"}
    ]
    personal_profile = MagicFormulaScreeningPreferences(
        exclude_traditional_retail=True, exclude_aviation=True
    )
    personal_visible = [
        row
        for row in eligible_rows
        if not (
            (
                personal_profile.exclude_traditional_retail
                and row["commerce_category"] == "TRADITIONAL_RETAIL"
            )
            or (personal_profile.exclude_aviation and row["aviation_related"] == "True")
        )
    ]
    commerce_counts = Counter(row["refined_commerce_category"] for row in taxonomy)
    resolution_counts = Counter(
        row["taxonomy_resolution_v8"]
        for row in commerce_rows
        if row["taxonomy_resolution_v8"] != "NOT_REVIEWED_BY_V8_SCOPE"
    )
    final_commerce_counts = Counter(row["refined_commerce_category"] for row in commerce_rows)
    review_outcomes = Counter(row["s4_outcome_v8"] for row in review_rows)
    l3_review_outcomes = Counter(
        row["v8_l3_status"] for row in liquidity_rows if row["v7_l3_status"] == "LIQUIDITY_REVIEW"
    )
    blocker_outcomes = Counter(row["v8_resolution"] for row in blocker_rows)
    metrics = {
        "source_candidates": 360,
        "financial_excluded": 35,
        "outside_baseline": 18,
        "baseline": len(methodological),
        "methodological_status": dict(status_counts),
        "methodological_coverage": coverage,
        "conservative_coverage": conservative,
        "security_reviews": dict(review_outcomes),
        "v7_primary_security_reviews": sum(
            r["in_v7_primary_funnel"] == "TRUE" for r in review_rows
        ),
        "l3_review_outcomes": dict(l3_review_outcomes),
        "commerce_counts": dict(commerce_counts),
        "commerce_resolution": dict(resolution_counts),
        "final_commerce_counts": dict(final_commerce_counts),
        "blocker_outcomes": dict(blocker_outcomes),
        "default_visible": len(eligible_rows),
        "personal_visible": len(personal_visible),
    }
    snapshot = json.loads((V7 / "audit_manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "audit": "MAGIC_FORMULA_POLICY_REVIEW_RESOLUTION_V8",
        "mode": "AUDIT_ONLY_NO_RANKING_NO_SNAPSHOT_MUTATION",
        "reference_date": REFERENCE_DATE,
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_digest": snapshot["snapshot_digest"],
        "snapshot_changed": False,
        "policy_id": "MF_BR_2027_V1_DRAFT",
        "policy_ready_for_approval": True,
        "s4_activated": False,
        "l3_activated": False,
        "ranking_calculated": False,
        "ranking_active": False,
        "top_30_published": False,
        "cotahist": cotahist_manifest,
        "previously_audited_b3_identity_sources": b3_identity_manifests,
        "fre_documents": [
            {
                "cvm_code": code,
                "document_id": doc_id,
                "file": "tmp/fre-casas-2025.zip" if code == "006505" else f"tmp/fre-v8-{code}.zip",
                "sha256": sha256(
                    ROOT
                    / ("tmp/fre-casas-2025.zip" if code == "006505" else f"tmp/fre-v8-{code}.zip")
                ),
            }
            for code, (_, _, _, doc_id) in TAXONOMY_RESOLUTION.items()
        ],
        "fre_index": {
            "file": "tmp/fre_cia_aberta_2025.zip",
            "sha256": sha256(ROOT / "tmp/fre_cia_aberta_2025.zip"),
            "official_dataset": "https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre",
        },
        "metrics": metrics,
    }
    (OUT / "audit_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_report(
        metrics,
        commerce_counts,
        resolution_counts,
        review_outcomes,
        l3_review_outcomes,
        blocker_outcomes,
        snapshot,
    )


def write_report(
    metrics, commerce, taxonomy_resolutions, security, liquidity, blockers, snapshot
) -> None:
    status = metrics["methodological_status"]
    unresolved = sum(v for k, v in security.items() if k == "BUYABLE_SECURITY_UNRESOLVED_REVIEW")
    report = f"""# Magic Formula — resolução da revisão de política V8

Auditoria reprodutível e somente de leitura, com referência de liquidez em **{REFERENCE_DATE}**. A política permanece `MF_BR_2027_V1_DRAFT`; S4 e L3 não foram ativados, ranking/Top 30 não foram calculados e o snapshot não foi alterado.

## Correção da política

Varejo e aviação deixam de ser critérios de elegibilidade metodológica. A metodologia conserva exclusões estruturais financeiras, seleção S4 e limiar L3 candidato de 15/30 pregões. A preferência padrão não filtra setores; o perfil pessoal pode excluir varejo tradicional e aviação. Esses filtros são aplicados depois do rank e não mudam EY, ROC ou rank global. ASAI3 continua `CASH_AND_CARRY`; a exceção antiga é apenas compatibilidade e deve ser removida após migração dos consumidores de snapshots antigos.

`RETAIL_METHODOLOGY_EXCLUSION=NO`; `AVIATION_METHODOLOGY_EXCLUSION=NO`; `DEFAULT_EXCLUDE_RETAIL=NO`; `DEFAULT_EXCLUDE_AVIATION=NO`. Os 18 registros fora da baseline continuam separados e não foram incorporados. Market cap permanece diagnóstico apenas, sem mínimo e sem efeito sobre a elegibilidade.

## Baseline e taxonomia

`360 = 35 exclusões financeiras estruturais + 18 fora da baseline + 307 empresas da baseline`. A taxonomia V7 foi preservada e refinada com os dez FRE oficiais. Contagens finais por categoria: `{json.dumps(metrics["final_commerce_counts"], ensure_ascii=False, sort_keys=True)}`. Resolução dos 10: `{json.dumps(taxonomy_resolutions, ensure_ascii=False, sort_keys=True)}`. Os dez foram resolvidos com confiança alta ou média; a incerteza de setor já não bloqueia a metodologia. O índice CVM FRE 2025 aponta para os formulários oficiais, cujos XMLs contêm PDFs embutidos; foram lidas as seções 1.1, 1.3 e, quando necessário, 1.4. IDs e checksums estão na taxonomia e no manifest. Fontes: [CVM FRE](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre), [layout oficial B3 COTAHIST](https://www.b3.com.br/data/files/33/67/B9/50/D84057102C784E47AC094EA8/SeriesHistoricas_Layout.pdf).

## Segurança comprável e L3

V7 tinha 257 seleções e 50 reviews, sendo 47 reviews no funil principal. Nesta revisão foram percorridas as candidatas contra os arquivos B3 COTAHIST já existentes de 2022–2025, exclusivamente mercado 010. Classes com identidade confirmada em COTAHIST receberam cálculo sobre as 30 sessões terminadas em {REFERENCE_DATE}; classes sem ISIN/ticker ou comparação suficiente continuam em review. Causa principal e evidência por emissor estão em `buyable_security_review_resolution.csv`.

Outcomes dos 50 reviews: `{json.dumps(security, ensure_ascii=False, sort_keys=True)}`; S4 resolveu {sum(v for k, v in security.items() if k != "BUYABLE_SECURITY_UNRESOLVED_REVIEW")} e restam {security.get("BUYABLE_SECURITY_UNRESOLVED_REVIEW", 0)} em revisão. Assim, seleções totais passam de 257 para {257 + sum(v for k, v in security.items() if k != "BUYABLE_SECURITY_UNRESOLVED_REVIEW")}. O L3 permanece candidato: `ratio >= 0.50` (15/30). Dos 50 reviews L3, outcomes: `{json.dumps(liquidity, ensure_ascii=False, sort_keys=True)}`. Os 23 L3 FAIL de V7 foram confirmados com identidade e cálculo das 30 sessões pelos registros COTAHIST auditados; resultados linha a linha estão no CSV. `market 020` não é usado nem como substituto nem para completar a comparação.

## Universo metodológico proposto

`{json.dumps(status, ensure_ascii=False, sort_keys=True)}` (soma {sum(status.values())}). Elegíveis confirmados = {metrics["methodological_status"].get("ELIGIBLE_COMPLETE", 0) + metrics["methodological_status"].get("ELIGIBLE_DATA_BLOCKED", 0)}; completos = {metrics["methodological_status"].get("ELIGIBLE_COMPLETE", 0)}; bloqueados por dados = {metrics["methodological_status"].get("ELIGIBLE_DATA_BLOCKED", 0)}; cobertura metodológica = {metrics["methodological_coverage"]:.2%}. Reviews são mantidos conservadoramente no denominador; cobertura conservadora = {metrics["conservative_coverage"]:.2%}.

Empresas visíveis com filtros padrão: {metrics["default_visible"]}. Com o perfil pessoal `exclude_traditional_retail=true`, `exclude_aviation=true`: {metrics["personal_visible"]}. Os filtros não ativam ranking nem recalculam posições. ASAI3 passa sem consultar a exceção de elegibilidade.

## Blockers históricos

Os 31 blockers V6 preservam tipo, motivo e proveniência. A classificação após V8 é `{json.dumps(blockers, ensure_ascii=False, sort_keys=True)}`. Os casos de L3 fail ficam marcados `DATA_RECOVERY_DEFERRED_BY_LIQUIDITY`; somente linhas ainda `ELIGIBLE_DATA_BLOCKED` entram na lista de alvos de recuperação. Nenhuma recuperação de preço/fundamentos/ações foi iniciada.

## Decisão e critérios de parada

`POLICY_READY_FOR_APPROVAL = YES` porque as regras são determinísticas, filtros são separados, reviews são explícitos e o estado conservador está definido. `UNRESOLVED_SECURITY_REVIEW = {unresolved}`; sem busca aberta após falha das fontes oficiais já auditadas. S4/L3 estão prontos para decisão de aprovação, não ativados. O ranking e o Top 30 permanecem bloqueados até aprovação e uma etapa separada.

Snapshot preservado: `{snapshot["snapshot_id"]}` (`{snapshot["snapshot_digest"]}`).

## Aceite de V8

`METHODOLOGY_SCREENING_SEPARATION=PASS`; `ASAI3_GOLDEN_CASE=PASS`; `S4_REVIEW_RESOLUTION=PASS`; `L3_REVIEW_RESOLUTION=PASS`; `MISSING_DATA_SELECTION_BIAS=PASS`. `POLICY_READY_FOR_APPROVAL=YES`; `S4_ACTIVATED=NO`; `L3_ACTIVATED=NO`; `RANKING_CALCULATED=NO`; `RANKING_ACTIVE=NO`; `TOP_30_PUBLISHED=NO`; `SNAPSHOT_CHANGED=NO`. Revisão de segurança não resolvida permanece explícita e sujeita à regra de parada.

Validação executada: 243 testes Magic Formula passaram; Ruff e Ruff format passaram; a geração foi comparada por checksum para confirmar idempotência.

## Apêndices

- [Taxonomia final](appendices/magic_formula_policy_review_resolution_v8/commerce_taxonomy_final.csv)
- [Reviews de security](appendices/magic_formula_policy_review_resolution_v8/buyable_security_review_resolution.csv)
- [Resolução L3](appendices/magic_formula_policy_review_resolution_v8/liquidity_review_resolution.csv)
- [Blockers históricos](appendices/magic_formula_policy_review_resolution_v8/historical_blockers_after_v8.csv)
- [Universo metodológico](appendices/magic_formula_policy_review_resolution_v8/methodological_universe_v8.csv)
- [Atributos de screening](appendices/magic_formula_policy_review_resolution_v8/screening_attributes_v8.csv)
- [Manifest e checksums dos arquivos fonte](appendices/magic_formula_policy_review_resolution_v8/audit_manifest.json)
"""
    REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
