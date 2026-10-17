# ruff: noqa: E501
"""Render the V6 audit JSON and reproducible CSV appendices as a Markdown report."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

AUDIT_PATH = Path("tmp/magic-formula-investable-v6/v6-audit.json")
OUTPUT_DIR = Path("docs/appendices/magic_formula_investable_universe_v6")
REPORT_PATH = Path("docs/MAGIC_FORMULA_INVESTABLE_UNIVERSE_AND_LIQUIDITY_V6.md")


def money(value: str | None) -> str:
    if value is None:
        return "—"
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percent(numerator: int, denominator: int) -> str:
    return (
        f"{numerator}/{denominator} = {100 * numerator / denominator:.2f}%" if denominator else "—"
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend(
        "| " + " | ".join(str(item).replace("|", "\\|") for item in row) + " |" for row in rows
    )
    return "\n".join(lines)


def render() -> None:
    data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "company_eligibility_307.csv", data["company_rows"])
    write_csv(OUTPUT_DIR / "security_liquidity_431.csv", data["security_rows"])
    write_csv(
        OUTPUT_DIR / "structural_financial_exclusions_35.csv", data["structural_exclusion_rows"]
    )
    write_csv(OUTPUT_DIR / "price_blockers_31.csv", data["blockers"]["rows"])
    (OUTPUT_DIR / "audit_source_manifests.json").write_text(
        json.dumps(data["source_manifests"], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    raw = data["raw_universe"]
    user = data["user_policy"]
    liq = data["liquidity"]
    mcap = data["market_cap"]
    complete = raw["raw_complete"]
    baseline = raw["v5_baseline_companies"]
    user_complete = user["complete"]
    scenarios = liq["scenarios"]

    current_rules = data["current_eligibility_rules"]
    rule_rows = [
        [
            "Exclusão estrutural financeira",
            ", ".join(current_rules["core_financial_exclusions"]),
            current_rules["core_implementation"],
            current_rules["core_status"],
            "Comparabilidade contábil de EY/ROC",
        ],
        [
            "Varejo",
            ", ".join(current_rules["user_retail_rule"]),
            "Aplicada apenas nesta auditoria",
            current_rules["user_policy_status"],
            "Proxy amplo de setor CVM; requer decisão de granularidade",
        ],
        [
            "Aviação",
            ", ".join(current_rules["user_aviation_cvm_codes"]),
            "Configuração declarativa por CVM",
            current_rules["user_policy_status"],
            "Preferência adicional do usuário",
        ],
        [
            "Utilities",
            "Energia, saneamento, água e gás",
            "Sem exclusão encontrada",
            "PASS / decisão não presumida",
            "Permanecem no universo",
        ],
        [
            "Mínimo de valor de mercado",
            "Nenhum",
            "Não encontrado na política",
            "Sem regra ativa",
            "Simulações apenas",
        ],
        ["Liquidez", "Nenhuma", "Cenários L0–L7", "Sem regra ativa", "Simulações apenas"],
        [
            "Preço de referência",
            "Mercado 010",
            "COTAHIST / auditoria V4–V6",
            "Regra preservada",
            "Mercado 020 não substitui 010",
        ],
        [
            "Listagem",
            "valid_from / valid_to e data de referência",
            "Auditada por security/emissor",
            "Data-base 2025-12-31",
            "Não é filtro de disponibilidade de dados",
        ],
    ]

    stage_rows = [
        [
            "Raw V5 baseline",
            baseline,
            "—",
            complete,
            baseline - complete,
            percent(complete, baseline),
        ],
        [
            "Structural (dentro da baseline V6)",
            data["structural_eligible"],
            0,
            complete,
            data["structural_eligible"] - complete,
            percent(complete, data["structural_eligible"]),
        ],
        [
            "Política do usuário",
            user["eligible"],
            baseline - user["eligible"],
            user_complete,
            user["blocked"],
            percent(user_complete, user["eligible"]),
        ],
    ]
    for name, scenario in scenarios.items():
        stage_rows.append(
            [
                name,
                scenario["investable_confirmed_pass"],
                scenario["liquidity_scenario_fail_review_only"],
                scenario["complete_among_confirmed_pass"],
                scenario["blocked_among_confirmed_pass"],
                f"{scenario['coverage_confirmed_pass']} confirmed-pass; {scenario['coverage_if_review_retained']} mantendo REVIEW",
            ]
        )

    liquidity_dist_rows = []
    metric_labels = {
        "traded_days_ratio_30d": "Pregões com negócio / 30 (fração)",
        "traded_days_ratio_90d": "Pregões com negócio / 90 (fração)",
        "median_daily_financial_volume_30d": "Mediana volume financeiro diário 30 sessões",
        "median_daily_financial_volume_90d": "Mediana volume financeiro diário 90 sessões",
        "calendar_days_since_last_trade": "Dias corridos desde último negócio",
    }
    for metric, label in metric_labels.items():
        q = liq["distributions"][metric]
        vals = [q[k] for k in ("p10", "p25", "p50", "p75", "p90")]
        if "volume" in metric:
            vals = [money(v) for v in vals]
        liquidity_dist_rows.append([label, f"{q['n']}/{q['total']} securities", *vals])

    liquidity_scenario_rows = []
    labels = {
        "L0": "Sem filtro",
        "L1": "Negociou ≤7 dias corridos",
        "L2": "Negociou ≤30 dias corridos",
        "L3": "≥50% dos 30 pregões",
        "L4": "≥80% dos 30 pregões",
        "L5": "Mediana ≥R$100 mil/dia",
        "L6": "Mediana ≥R$500 mil/dia",
        "L7": "Recência ≤30d + ratio ≥50% + ≥R$100 mil/dia",
    }
    for name, s in scenarios.items():
        liquidity_scenario_rows.append(
            [
                name,
                labels[name],
                s["investable_confirmed_pass"],
                s["liquidity_scenario_fail_review_only"],
                s["liquidity_review_unknown"],
                s["complete_among_confirmed_pass"],
                s["blocked_among_confirmed_pass"],
                s["coverage_confirmed_pass"],
                f"{s['coverage_if_review_retained']} ({s['review_retained_denominator']} mantidas)",
            ]
        )

    cap_rows = []
    for k in ("R$500M", "R$1B", "R$5B", "P25", "P50", "P75"):
        s = mcap["scenarios"][k]
        cap_rows.append(
            [
                k,
                money(s["threshold_brl"]),
                s["companies_pass"],
                s["companies_fail_in_scenario_only"],
                s["market_cap_unknown_review"],
                s["complete_pass"],
                s["blocked_pass"],
                s["coverage_pass"],
                s["coverage_retaining_unknown"],
            ]
        )

    blocker_rows = []
    for kind in (
        "SOURCE_GAP",
        "SECURITY_TYPE_NOT_COVERED",
        "NO_TRADE_ON_REFERENCE_DATE",
        "UNRESOLVED",
    ):
        rows = [r for r in data["blockers"]["rows"] if r["blocker_type"] == kind]
        l1 = Counter(r["scenario_L1"] for r in rows)
        l2 = Counter(r["scenario_L2"] for r in rows)
        status = Counter(r["primary_status"] for r in rows)
        blocked = sum(r["data_status"] == "BLOCKED" for r in rows)
        blocker_rows.append(
            [
                kind,
                len(rows),
                sum(r["structural_status"] == "INELIGIBLE_STRUCTURAL" for r in rows),
                sum(r["user_policy_status"] == "INELIGIBLE_USER_POLICY" for r in rows),
                f"{l1['PASS']} PASS / {l1['FAIL']} FAIL / {l1['REVIEW']} REVIEW",
                f"{l2['PASS']} PASS / {l2['FAIL']} FAIL / {l2['REVIEW']} REVIEW",
                blocked,
                "; ".join(f"{k}: {v}" for k, v in sorted(status.items())),
            ]
        )

    no_trade_rows = []
    for blocker in [
        r for r in data["blockers"]["rows"] if r["blocker_type"] == "NO_TRADE_ON_REFERENCE_DATE"
    ]:
        target = blocker["securities"]
        sec_rows = [
            r
            for r in data["security_rows"]
            if r["cvm_code"] == blocker["cvm_code"]
            and r["ticker"] in target
            and r["metric_status"] == "OBSERVED"
        ]
        for sec in sec_rows:
            no_trade_rows.append(
                [
                    blocker["company"],
                    sec["ticker"],
                    sec["last_trade_date"],
                    sec["calendar_days_since_last_trade"],
                    sec["trading_days_since_last_trade"],
                    sec["traded_days_ratio_30d"],
                    sec["traded_days_ratio_90d"],
                    money(sec["median_daily_financial_volume_30d"]),
                    sec["scenario_L1"],
                    sec["scenario_L2"],
                    blocker["scenario_L1"],
                    blocker["scenario_L2"],
                ]
            )

    capq = mcap["distribution_brl"]
    utility_counts = data["utilities"]["counts"]
    sec = data["securities"]
    status_rows = [[k, v] for k, v in data["primary_status_counts"].items()]
    policy_codes = user["retail_exclusion_cvm_codes"]

    parts = [
        "# Magic Formula investable universe and liquidity — V6",
        "",
        f"**Audited:** 2026-10-13 · **Reference date:** {data['reference_date']} · **Price date:** {data['price_reference_date']} · **Snapshot:** `{data['snapshot_id']}` · **Policy draft:** `{data['policy_version']}` (audit-only)",
        "",
        "## 1. Executive summary",
        "",
        f"The V5 baseline contains **{baseline} companies**, of which **{complete}/{baseline} = {raw['raw_coverage']}** have complete data. After the user-policy scenarios, **{user['eligible']}** remain eligible; **{user_complete}/{user['eligible']} = {user['coverage']}** have complete data and **{user['blocked']}** remain data-blocked. Missing prices or fundamentals were never treated as ineligibility.",
        "",
        "The requested 307 is an already structurally classified baseline, not the unfiltered company-source table: the snapshot has 360 candidate records, including 35 existing financial-sector exclusions and 18 records outside the V6 baseline that require source/base-sector review. All 307 baseline companies classify as listed on the reference date. The 307 primary states sum exactly to 307. Liquidity and market-cap thresholds are simulations only. **No rank was calculated, no Top 30 was generated, and no production policy or snapshot was activated.**",
        "",
        "The central data limitation is that liquidity evidence is per exact ticker+ISIN, while a company can have another class that is investible. The nine no-trade blockers therefore distinguish target-class stale/no-trade status from issuer-level ability to trade another class.",
        "",
        "## 2. Raw universe",
        "",
        f"The immutable input is snapshot `{data['snapshot_id']}` created `{data['snapshot_created_at']}`. Its `{raw['source_candidate_records']}` records divide into the V6 baseline ({baseline}), existing financial exclusions ({raw['existing_structural_financial_exclusions']}) and outside-baseline review ({raw['outside_v6_base_sector_or_identity_review']}). Raw V5 coverage is **{complete}/{baseline} = {raw['raw_coverage']}**; blocked raw baseline rows: **{baseline - complete}/{baseline}**.",
        "",
        "The V6 audit adds only read-only identity records confirmed by V4/V5 so historic liquidity can be matched by ticker and ISIN; it does not persist identity or price changes.",
        "",
        "## 3. Existing eligibility rules",
        "",
        table(
            ["Rule", "Configuration / scope", "Implementation source", "Status", "Reason"],
            rule_rows,
        ),
        "",
        "## 4. Structural exclusions",
        "",
        "Within the 307 V6 baseline, **0** new structural exclusions were made; all 307 had already passed the existing core classification. The **35** structural financial exclusions belong to the source snapshot's 360-candidate funnel and are itemized in [the exclusion appendix](appendices/magic_formula_investable_universe_v6/structural_financial_exclusions_35.csv). The existing categories are banks, insurers/brokers, financial intermediation, real-estate credit, leasing and receivables securitization. No exclusion was broadened in V6.",
        "",
        f"Utilities are not structurally excluded. The baseline contains {utility_counts.get('ELECTRIC_UTILITY', 0)} electric-utility issuers, {utility_counts.get('WATER_SANITATION_GAS_MIXED_CLASSIFICATION', 0)} issuers in the combined water/sanitation/gas CVM category, {utility_counts.get('GAS_NAMED_IN_COMPANY', 0)} identified as gas from company name, and {utility_counts.get('OTHER_REGULATED_ADJACENT_TELECOM', 0)} telecom-adjacent regulated issuers. The combined CVM category cannot cleanly separate water, sanitation and gas, so it remains an explicit classification ambiguity for a later decision.",
        "",
        "## 5. User policy",
        "",
        f"The audit-only user policy excludes 36 CVM issuers classified as `Comércio (Atacado e Varejo)` and two airline issuers (CVM {', '.join(current_rules['user_aviation_cvm_codes'])}). This sector is a coarse proxy: it also captures wholesale, distributors, shopping/commerce-adjacent businesses. The 36 are therefore reported as *policy proxy matches*, not a claim that every one is a pure retailer. The complete CVM list is in the company appendix; matched issuer codes: {', '.join(policy_codes)}.",
        "",
        "Technology, industry, commodities, construction, education, health, services, logistics and agribusiness were not newly excluded. The exception is centrally declared in `MagicFormulaUniversePolicy`; it is not an inline ticker branch.",
        "",
        "## 6. ASAI3 exception",
        "",
        "**Company:** Sendas Distribuidora (Assaí) · **Ticker:** ASAI3 · **Base policy:** retail-sector exclusion · **Exception:** `ALLOW_RETAIL_EXCLUSION_EXCEPTION` · **Final user-policy status:** eligible. The exception is represented by issuer CVM 025372 and ticker ASAI3. The issuer remains data-blocked by missing accounting data; the exception changes policy eligibility only.",
        "",
        "## 7. Listing eligibility",
        "",
        f"All **{sum(data['listing_counts'].values())}/{baseline}** baseline issuers are `LISTED_ON_REFERENCE_DATE` under the security validity-date assessment at {data['reference_date']}. No baseline issuer was removed for listing status. Uncertain identity cases remain individually visible and are not silently filtered.",
        "",
        "## 8. Security eligibility",
        "",
        f"The audit has {sec['security_rows']} security rows across the 307 companies; {sec['companies_with_multiple_securities']} companies have multiple securities, {sec['companies_with_multiple_share_classes']} have multiple share classes, and {sec['units_present']} have UNIT securities. The unit of ranking remains the economic issuer. Issuer market cap sums the positive ON/PN issued-minus-treasury amount times the price of that same class; all positive classes require an available reference price. Units are not counted twice. A specific share-class purchase policy remains undecided.",
        "",
        "Market type **010** remains the only eligible source for reference prices. 020 is not a fallback. The 31 price blockers and class-level provenance are in the [blocker](appendices/magic_formula_investable_universe_v6/price_blockers_31.csv) and [security liquidity](appendices/magic_formula_investable_universe_v6/security_liquidity_431.csv) appendices.",
        "",
        "## 9. Liquidity distribution",
        "",
        f"The scan used B3 annual COTAHIST archives 2019–2025 and all {liq['session_count_2025_through_reference']} reference-year sessions through {data['price_reference_date']}; the trailing 30-window is {len(liq['sessions_last30'])} sessions. Financial volume is COTAHIST VOLTOT (fixed positions 171–188), divided by 100, aggregated by exact security/date, market 010. Median volume includes zero-volume sessions. These metrics measure trading opportunity and do not estimate spread or execution slippage.",
        "",
        table(
            ["Metric", "Observed / total", "P10", "P25", "P50", "P75", "P90"], liquidity_dist_rows
        ),
        "",
        "For `days_since_last_trade`, the observed distribution has a mass at zero because most securities traded on the reference date; securities with no matched trade remain missing rather than being assigned an artificial number. The full exact-security table and archive SHA-256 manifests are attached in the appendices.",
        "",
        "## 10. Liquidity scenarios",
        "",
        "A company is a confirmed pass when at least one separately measured identified class satisfies the scenario. Class volumes are never summed. Missing identity/liquidity evidence produces REVIEW; REVIEW is retained in the conservative denominator and is not an exclusion. L5/L6 use R$100k and R$500k median daily volume respectively; no scenario is activated.",
        "",
        table(
            [
                "Scenario",
                "Rule",
                "PASS",
                "FAIL (scenario only)",
                "REVIEW",
                "Complete among PASS",
                "Blocked among PASS",
                "Coverage among PASS",
                "Coverage if REVIEW retained",
            ],
            liquidity_scenario_rows,
        ),
        "",
        "The higher confirmed-pass coverage in stricter scenarios is a selection effect, not a goal or evidence for adopting that filter. Retaining REVIEW gives the decision-conservative coverage shown in the last column.",
        "",
        "## 11. Market-cap distribution",
        "",
        f"There is **no current minimum-market-cap rule** in the audited universe policy. For the 269 user-policy eligible issuers, issuer-level market cap is calculable for **{mcap['available_companies']}/269**, with **{mcap['unknown_companies_review']}/269** left in review. The distribution (N={capq['n']}) is P10 {money(capq['p10'])}, P25 {money(capq['p25'])}, median {money(capq['p50'])}, P75 {money(capq['p75'])}, P90 {money(capq['p90'])}.",
        "",
        "Only explicit normalized outstanding quantities carrying `MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1` lineage are used; the raw CVM quantities are not trusted merely because a field says `UNIT`. The snapshot and existing official-document evidence are read only. Any issuer with a missing class price, unresolved unit or incomplete class consolidation remains unknown/review.",
        "",
        table(
            [
                "Scenario",
                "Cut",
                "PASS",
                "Below cut",
                "Unknown / REVIEW",
                "Complete among PASS",
                "Blocked among PASS",
                "Coverage among PASS",
                "Complete / (PASS + unknown)",
            ],
            cap_rows,
        ),
        "",
        "All size cuts and percentiles are analytical scenarios only. Their coverage can be high because the cut may remove blocked issuers; no threshold was selected from the resulting coverage.",
        "",
        "## 12. Coverage by stage",
        "",
        table(
            ["Stage", "Companies", "Removed at stage", "Complete", "Blocked", "Coverage"],
            stage_rows,
        ),
        "",
        "The canonical status distribution is:",
        "",
        table(["Primary status", "Companies"], status_rows),
        "",
        "These five states sum to 307. `LIQUIDITY_REVIEW` does not mean excluded. The status prioritizes unresolved identity first, explicit user policy next, then marks eligible issuers for liquidity review when representative 30-session metrics are missing or below the L3 frequency threshold; the scenario tables remain the auditable source for each L0–L7 result.",
        "",
        "## 13. Current blocker cross-analysis",
        "",
        "All 31 blockers are cross-referenced by structural/user policy, data status and the company-level L1/L2 scenarios. None was structurally or user-policy excluded in this baseline. Scenario FAIL is simulation only; unresolved evidence is REVIEW.",
        "",
        table(
            [
                "Blocker type",
                "Count",
                "Structural excluded",
                "User-policy excluded",
                "L1 company result",
                "L2 company result",
                "Data-blocked",
                "Primary status",
            ],
            blocker_rows,
        ),
        "",
        "The 14 SOURCE_GAP cases all remain eligible under the core/user filters; 11 are liquidity REVIEW and 3 pass L1/L2 through another identified class. Of the three SECURITY_TYPE_NOT_COVERED cases, 2 remain liquidity REVIEW and 1 passes L1/L2 through an alternate identified class. This does not repair their price-source blocker. All five unresolved issuers remain `IDENTITY_UNRESOLVED`, retained and not silently excluded.",
        "",
        "The following table reports the exact V4 target security for each of the nine no-trade blockers. The last two columns are issuer-level results when another class is available; a company PASS does not make the target security's stale price current or liquid.",
        "",
        table(
            [
                "Company",
                "Target security",
                "Last trade",
                "Calendar gap",
                "Trading sessions since",
                "30d traded ratio",
                "90d traded ratio",
                "30d median volume",
                "Security L1",
                "Security L2",
                "Issuer L1",
                "Issuer L2",
            ],
            no_trade_rows,
        ),
        "",
        "## 14. Investable-universe scenarios",
        "",
        "L0–L7 counts above define the prospective universe only if a later policy explicitly adopts the scenario. For L1/L2, no issuer is confirmed FAIL because some cases lack resolved identity and remain REVIEW. For L3–L7, only confirmed failures leave the scenario's pass set; REVIEW remains visible. Data completeness is evaluated after eligibility, preserving blocked issuers in denominators unless an explicitly approved structural/user/liquidity rule removes them.",
        "",
        "## 15. Recommendations",
        "",
        "Keep ranking inactive. Decide the retail taxonomy before using the 36-issuer CVM sector proxy; decide which share class is buyable when an issuer has multiple classes; and choose a liquidity rule only from execution/investability needs, with REVIEW treatment specified. Keep missing data separate from eligibility. Treat the displayed sensitivity as evidence for those policy decisions, never as a coverage optimization target.",
        "",
        "## 16. Decisions still required",
        "",
        "- Whether the entire CVM `Comércio (Atacado e Varejo)` category is the intended retail exclusion, including wholesale/distributor and commerce-adjacent issuers.\n- How to treat unresolved liquidity identity and companies with multiple classes when no share-class execution policy exists.\n- Whether to define a minimum market cap, and if so its economic rationale and reference date.\n- Whether the current 18 outside-baseline source records need a separate identity/base-sector adjudication before future universe expansion.\n- Preserve the existing unit-evidence, COTAHIST and reference-date lineage when a later ranking snapshot is considered.",
        "",
        "## Audit constraints and artifacts",
        "",
        f"`ranking_calculated={data['ranking_calculated']}`, `ranking_active={data['ranking_active']}`, `ranking_blocked={data['ranking_blocked']}`, `top_30_published={data['top_30_published']}`, `methodology_changed={data['methodology_changed']}`.",
        "",
        "Appendices: [all 307 issuer decisions](appendices/magic_formula_investable_universe_v6/company_eligibility_307.csv), [all 431 class-level liquidity records](appendices/magic_formula_investable_universe_v6/security_liquidity_431.csv), [all 35 existing financial exclusions](appendices/magic_formula_investable_universe_v6/structural_financial_exclusions_35.csv), [all 31 blockers](appendices/magic_formula_investable_universe_v6/price_blockers_31.csv), and [COTAHIST archive manifests](appendices/magic_formula_investable_universe_v6/audit_source_manifests.json). A few company display names contain the replacement character already present in the source snapshot; identifiers, CVM codes and security identities are the audit keys.",
        "",
        "The audit script is read-only against the SQLite snapshot and writes only under `tmp/magic-formula-investable-v6`; the appendices and this report are generated from its JSON output.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    render()
