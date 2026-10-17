# Magic Formula investable universe and liquidity — V6

**Audited:** 2026-10-13 · **Reference date:** 2025-12-31 · **Price date:** 2025-12-30 · **Snapshot:** `ed8a9235-ee14-4a97-93fd-0dbcd87113fb` · **Policy draft:** `MF_BR_2027_V1_DRAFT` (audit-only)

## 1. Executive summary

The V5 baseline contains **307 companies**, of which **185/307 = 60.26%** have complete data. After the user-policy scenarios, **269** remain eligible; **156/269 = 57.99%** have complete data and **113** remain data-blocked. Missing prices or fundamentals were never treated as ineligibility.

The requested 307 is an already structurally classified baseline, not the unfiltered company-source table: the snapshot has 360 candidate records, including 35 existing financial-sector exclusions and 18 records outside the V6 baseline that require source/base-sector review. All 307 baseline companies classify as listed on the reference date. The 307 primary states sum exactly to 307. Liquidity and market-cap thresholds are simulations only. **No rank was calculated, no Top 30 was generated, and no production policy or snapshot was activated.**

The central data limitation is that liquidity evidence is per exact ticker+ISIN, while a company can have another class that is investible. The nine no-trade blockers therefore distinguish target-class stale/no-trade status from issuer-level ability to trade another class.

## 2. Raw universe

The immutable input is snapshot `ed8a9235-ee14-4a97-93fd-0dbcd87113fb` created `2026-10-12T19:12:56.069873+00:00`. Its `360` records divide into the V6 baseline (307), existing financial exclusions (35) and outside-baseline review (18). Raw V5 coverage is **185/307 = 60.26%**; blocked raw baseline rows: **122/307**.

The V6 audit adds only read-only identity records confirmed by V4/V5 so historic liquidity can be matched by ticker and ISIN; it does not persist identity or price changes.

## 3. Existing eligibility rules

| Rule | Configuration / scope | Implementation source | Status | Reason |
|---|---|---|---|---|
| Exclusão estrutural financeira | Arrendamento Mercantil, Bancos, Crédito Imobiliário, Intermediação Financeira, Securitização de Recebíveis, Seguradoras e Corretoras | src/income_analytics/application/magic_formula_universe.py:classify_candidates | EXISTING_AND_UNCHANGED | Comparabilidade contábil de EY/ROC |
| Varejo | Comércio (Atacado e Varejo) | Aplicada apenas nesta auditoria | AUDIT_CONFIGURATION_ONLY_NOT_ACTIVATED_IN_PRODUCTION | Proxy amplo de setor CVM; requer decisão de granularidade |
| Aviação | 019569, 024112 | Configuração declarativa por CVM | AUDIT_CONFIGURATION_ONLY_NOT_ACTIVATED_IN_PRODUCTION | Preferência adicional do usuário |
| Utilities | Energia, saneamento, água e gás | Sem exclusão encontrada | PASS / decisão não presumida | Permanecem no universo |
| Mínimo de valor de mercado | Nenhum | Não encontrado na política | Sem regra ativa | Simulações apenas |
| Liquidez | Nenhuma | Cenários L0–L7 | Sem regra ativa | Simulações apenas |
| Preço de referência | Mercado 010 | COTAHIST / auditoria V4–V6 | Regra preservada | Mercado 020 não substitui 010 |
| Listagem | valid_from / valid_to e data de referência | Auditada por security/emissor | Data-base 2025-12-31 | Não é filtro de disponibilidade de dados |

## 4. Structural exclusions

Within the 307 V6 baseline, **0** new structural exclusions were made; all 307 had already passed the existing core classification. The **35** structural financial exclusions belong to the source snapshot's 360-candidate funnel and are itemized in [the exclusion appendix](appendices/magic_formula_investable_universe_v6/structural_financial_exclusions_35.csv). The existing categories are banks, insurers/brokers, financial intermediation, real-estate credit, leasing and receivables securitization. No exclusion was broadened in V6.

Utilities are not structurally excluded. The baseline contains 30 electric-utility issuers, 7 issuers in the combined water/sanitation/gas CVM category, 3 identified as gas from company name, and 9 telecom-adjacent regulated issuers. The combined CVM category cannot cleanly separate water, sanitation and gas, so it remains an explicit classification ambiguity for a later decision.

## 5. User policy

The audit-only user policy excludes 36 CVM issuers classified as `Comércio (Atacado e Varejo)` and two airline issuers (CVM 019569, 024112). This sector is a coarse proxy: it also captures wholesale, distributors, shopping/commerce-adjacent businesses. The 36 are therefore reported as *policy proxy matches*, not a claim that every one is a pure retailer. The complete CVM list is in the company appendix; matched issuer codes: 020990, 022357, 025895, 022608, 019909, 021008, 022519, 025046, 025682, 024694, 025518, 025259, 025089, 025933, 025330, 023507, 025658, 025186, 025461, 006505, 024805, 024295, 025747, 020346, 014826, 022470, 021440, 020494, 008672, 022055, 005258, 025453, 004537, 009342, 008133, 025038.

Technology, industry, commodities, construction, education, health, services, logistics and agribusiness were not newly excluded. The exception is centrally declared in `MagicFormulaUniversePolicy`; it is not an inline ticker branch.

## 6. ASAI3 exception

**Company:** Sendas Distribuidora (Assaí) · **Ticker:** ASAI3 · **Base policy:** retail-sector exclusion · **Exception:** `ALLOW_RETAIL_EXCLUSION_EXCEPTION` · **Final user-policy status:** eligible. The exception is represented by issuer CVM 025372 and ticker ASAI3. The issuer remains data-blocked by missing accounting data; the exception changes policy eligibility only.

## 7. Listing eligibility

All **307/307** baseline issuers are `LISTED_ON_REFERENCE_DATE` under the security validity-date assessment at 2025-12-31. No baseline issuer was removed for listing status. Uncertain identity cases remain individually visible and are not silently filtered.

## 8. Security eligibility

The audit has 431 security rows across the 307 companies; 86 companies have multiple securities, 74 have multiple share classes, and 8 have UNIT securities. The unit of ranking remains the economic issuer. Issuer market cap sums the positive ON/PN issued-minus-treasury amount times the price of that same class; all positive classes require an available reference price. Units are not counted twice. A specific share-class purchase policy remains undecided.

Market type **010** remains the only eligible source for reference prices. 020 is not a fallback. The 31 price blockers and class-level provenance are in the [blocker](appendices/magic_formula_investable_universe_v6/price_blockers_31.csv) and [security liquidity](appendices/magic_formula_investable_universe_v6/security_liquidity_431.csv) appendices.

## 9. Liquidity distribution

The scan used B3 annual COTAHIST archives 2019–2025 and all 250 reference-year sessions through 2025-12-30; the trailing 30-window is 30 sessions. Financial volume is COTAHIST VOLTOT (fixed positions 171–188), divided by 100, aggregated by exact security/date, market 010. Median volume includes zero-volume sessions. These metrics measure trading opportunity and do not estimate spread or execution slippage.

| Metric | Observed / total | P10 | P25 | P50 | P75 | P90 |
|---|---|---|---|---|---|---|
| Pregões com negócio / 30 (fração) | 330/431 securities | 0.1666666666666666666666666667 | 1.00 | 1.00 | 1.00 | 1.00 |
| Pregões com negócio / 90 (fração) | 330/431 securities | 0.1644444444444444444444444445 | 0.9361111111111111111111111111 | 1.00 | 1.00 | 1.00 |
| Mediana volume financeiro diário 30 sessões | 330/431 securities | R$ 0,00 | R$ 20.279,75 | R$ 1.035.477,00 | R$ 21.435.579,25 | R$ 109.641.305,35 |
| Mediana volume financeiro diário 90 sessões | 330/431 securities | R$ 0,00 | R$ 14.624,38 | R$ 700.730,70 | R$ 19.433.905,75 | R$ 86.370.241,55 |
| Dias corridos desde último negócio | 314/431 securities | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

For `days_since_last_trade`, the observed distribution has a mass at zero because most securities traded on the reference date; securities with no matched trade remain missing rather than being assigned an artificial number. The full exact-security table and archive SHA-256 manifests are attached in the appendices.

## 10. Liquidity scenarios

A company is a confirmed pass when at least one separately measured identified class satisfies the scenario. Class volumes are never summed. Missing identity/liquidity evidence produces REVIEW; REVIEW is retained in the conservative denominator and is not an exclusion. L5/L6 use R$100k and R$500k median daily volume respectively; no scenario is activated.

| Scenario | Rule | PASS | FAIL (scenario only) | REVIEW | Complete among PASS | Blocked among PASS | Coverage among PASS | Coverage if REVIEW retained |
|---|---|---|---|---|---|---|---|---|
| L0 | Sem filtro | 269 | 0 | 0 | 156 | 113 | 57.99% | 57.99% (269 mantidas) |
| L1 | Negociou ≤7 dias corridos | 219 | 0 | 50 | 156 | 63 | 71.23% | 57.99% (269 mantidas) |
| L2 | Negociou ≤30 dias corridos | 221 | 0 | 48 | 156 | 65 | 70.59% | 57.99% (269 mantidas) |
| L3 | ≥50% dos 30 pregões | 208 | 7 | 54 | 152 | 56 | 73.08% | 58.02% (262 mantidas) |
| L4 | ≥80% dos 30 pregões | 202 | 10 | 57 | 151 | 51 | 74.75% | 58.30% (259 mantidas) |
| L5 | Mediana ≥R$100 mil/dia | 163 | 41 | 65 | 129 | 34 | 79.14% | 56.58% (228 mantidas) |
| L6 | Mediana ≥R$500 mil/dia | 142 | 59 | 68 | 115 | 27 | 80.99% | 54.76% (210 mantidas) |
| L7 | Recência ≤30d + ratio ≥50% + ≥R$100 mil/dia | 163 | 41 | 65 | 129 | 34 | 79.14% | 56.58% (228 mantidas) |

The higher confirmed-pass coverage in stricter scenarios is a selection effect, not a goal or evidence for adopting that filter. Retaining REVIEW gives the decision-conservative coverage shown in the last column.

## 11. Market-cap distribution

There is **no current minimum-market-cap rule** in the audited universe policy. For the 269 user-policy eligible issuers, issuer-level market cap is calculable for **163/269**, with **106/269** left in review. The distribution (N=163) is P10 R$ 91.623.063,77, P25 R$ 462.315.854,82, median R$ 2.958.909.534,00, P75 R$ 8.105.507.403,44, P90 R$ 30.269.099.571,92.

Only explicit normalized outstanding quantities carrying `MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1` lineage are used; the raw CVM quantities are not trusted merely because a field says `UNIT`. The snapshot and existing official-document evidence are read only. Any issuer with a missing class price, unresolved unit or incomplete class consolidation remains unknown/review.

| Scenario | Cut | PASS | Below cut | Unknown / REVIEW | Complete among PASS | Blocked among PASS | Coverage among PASS | Complete / (PASS + unknown) |
|---|---|---|---|---|---|---|---|---|
| R$500M | R$ 500.000.000,00 | 120 | 43 | 106 | 113 | 7 | 94.17% | 50.00% |
| R$1B | R$ 1.000.000.000,00 | 108 | 55 | 106 | 101 | 7 | 93.52% | 47.20% |
| R$5B | R$ 5.000.000.000,00 | 61 | 102 | 106 | 56 | 5 | 91.80% | 33.53% |
| P25 | R$ 462.315.854,82 | 122 | 41 | 106 | 115 | 7 | 94.26% | 50.44% |
| P50 | R$ 2.958.909.534,00 | 82 | 81 | 106 | 76 | 6 | 92.68% | 40.43% |
| P75 | R$ 8.105.507.403,44 | 41 | 122 | 106 | 37 | 4 | 90.24% | 25.17% |

All size cuts and percentiles are analytical scenarios only. Their coverage can be high because the cut may remove blocked issuers; no threshold was selected from the resulting coverage.

## 12. Coverage by stage

| Stage | Companies | Removed at stage | Complete | Blocked | Coverage |
|---|---|---|---|---|---|
| Raw V5 baseline | 307 | — | 185 | 122 | 185/307 = 60.26% |
| Structural (dentro da baseline V6) | 307 | 0 | 185 | 122 | 185/307 = 60.26% |
| Política do usuário | 269 | 38 | 156 | 113 | 156/269 = 57.99% |
| L0 | 269 | 0 | 156 | 113 | 57.99% confirmed-pass; 57.99% mantendo REVIEW |
| L1 | 219 | 0 | 156 | 63 | 71.23% confirmed-pass; 57.99% mantendo REVIEW |
| L2 | 221 | 0 | 156 | 65 | 70.59% confirmed-pass; 57.99% mantendo REVIEW |
| L3 | 208 | 7 | 152 | 56 | 73.08% confirmed-pass; 58.02% mantendo REVIEW |
| L4 | 202 | 10 | 151 | 51 | 74.75% confirmed-pass; 58.30% mantendo REVIEW |
| L5 | 163 | 41 | 129 | 34 | 79.14% confirmed-pass; 56.58% mantendo REVIEW |
| L6 | 142 | 59 | 115 | 27 | 80.99% confirmed-pass; 54.76% mantendo REVIEW |
| L7 | 163 | 41 | 129 | 34 | 79.14% confirmed-pass; 56.58% mantendo REVIEW |

The canonical status distribution is:

| Primary status | Companies |
|---|---|
| ELIGIBLE_COMPLETE | 152 |
| ELIGIBLE_DATA_BLOCKED | 56 |
| IDENTITY_UNRESOLVED | 5 |
| INELIGIBLE_USER_POLICY | 38 |
| LIQUIDITY_REVIEW | 56 |

These five states sum to 307. `LIQUIDITY_REVIEW` does not mean excluded. The status prioritizes unresolved identity first, explicit user policy next, then marks eligible issuers for liquidity review when representative 30-session metrics are missing or below the L3 frequency threshold; the scenario tables remain the auditable source for each L0–L7 result.

## 13. Current blocker cross-analysis

All 31 blockers are cross-referenced by structural/user policy, data status and the company-level L1/L2 scenarios. None was structurally or user-policy excluded in this baseline. Scenario FAIL is simulation only; unresolved evidence is REVIEW.

| Blocker type | Count | Structural excluded | User-policy excluded | L1 company result | L2 company result | Data-blocked | Primary status |
|---|---|---|---|---|---|---|---|
| SOURCE_GAP | 14 | 0 | 0 | 3 PASS / 0 FAIL / 11 REVIEW | 3 PASS / 0 FAIL / 11 REVIEW | 14 | ELIGIBLE_DATA_BLOCKED: 3; LIQUIDITY_REVIEW: 11 |
| SECURITY_TYPE_NOT_COVERED | 3 | 0 | 0 | 1 PASS / 0 FAIL / 2 REVIEW | 1 PASS / 0 FAIL / 2 REVIEW | 3 | ELIGIBLE_DATA_BLOCKED: 1; LIQUIDITY_REVIEW: 2 |
| NO_TRADE_ON_REFERENCE_DATE | 9 | 0 | 0 | 7 PASS / 0 FAIL / 2 REVIEW | 9 PASS / 0 FAIL / 0 REVIEW | 9 | ELIGIBLE_DATA_BLOCKED: 4; LIQUIDITY_REVIEW: 5 |
| UNRESOLVED | 5 | 0 | 0 | 0 PASS / 0 FAIL / 5 REVIEW | 0 PASS / 0 FAIL / 5 REVIEW | 5 | IDENTITY_UNRESOLVED: 5 |

The 14 SOURCE_GAP cases all remain eligible under the core/user filters; 11 are liquidity REVIEW and 3 pass L1/L2 through another identified class. Of the three SECURITY_TYPE_NOT_COVERED cases, 2 remain liquidity REVIEW and 1 passes L1/L2 through an alternate identified class. This does not repair their price-source blocker. All five unresolved issuers remain `IDENTITY_UNRESOLVED`, retained and not silently excluded.

The following table reports the exact V4 target security for each of the nine no-trade blockers. The last two columns are issuer-level results when another class is available; a company PASS does not make the target security's stale price current or liquid.

| Company | Target security | Last trade | Calendar gap | Trading sessions since | 30d traded ratio | 90d traded ratio | 30d median volume | Security L1 | Security L2 | Issuer L1 | Issuer L2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EMAE - EMPRESA METROP.AGUAS ENERGIA S.A. | EMAE3 | 2025-08-18 | 134 | 93 | 0 | 0 | R$ 0,00 | FAIL | FAIL | PASS | PASS |
| PLASCAR PARTICIPACOES INDUSTRIAIS S.A. | PLAS3 | 2025-12-23 | 7 | 3 | 0.4 | 0.4 | R$ 0,00 | PASS | PASS | PASS | PASS |
| CIA MELHORAMENTOS DE SAO PAULO | MSPA4 | 2025-12-11 | 19 | 11 | 0.1666666666666666666666666667 | 0.1222222222222222222222222222 | R$ 0,00 | FAIL | PASS | REVIEW | PASS |
| CIA MELHORAMENTOS DE SAO PAULO | MSPA3 | 2025-11-28 | 32 | 20 | 0.06666666666666666666666666667 | 0.08888888888888888888888888889 | R$ 0,00 | FAIL | FAIL | REVIEW | PASS |
| BAUMER S.A. | BALM3 | 2025-12-18 | 12 | 6 | 0.1333333333333333333333333333 | 0.2 | R$ 0,00 | FAIL | PASS | PASS | PASS |
| KARSTEN S.A. | CTKA3 | 2025-12-03 | 27 | 17 | 0.2 | 0.1111111111111111111111111111 | R$ 0,00 | FAIL | PASS | PASS | PASS |
| TEXTIL RENAUXVIEW S.A. | TXRX3 | 2025-12-19 | 11 | 5 | 0.03333333333333333333333333333 | 0.01111111111111111111111111111 | R$ 0,00 | FAIL | PASS | PASS | PASS |
| WETZEL S.A. | MWET3 | 2025-12-05 | 25 | 15 | 0.1333333333333333333333333333 | 0.1444444444444444444444444444 | R$ 0,00 | FAIL | PASS | PASS | PASS |
| METISA METALURGICA TIMBOENSE S.A. | MTSA3 | 2025-06-23 | 190 | 133 | 0 | 0 | R$ 0,00 | FAIL | FAIL | PASS | PASS |
| JOSAPAR-JOAQUIM OLIVEIRA S.A. - PARTICIP | JOPA4 | 2025-01-10 | 354 | 243 | 0 | 0 | R$ 0,00 | FAIL | FAIL | REVIEW | PASS |
| JOSAPAR-JOAQUIM OLIVEIRA S.A. - PARTICIP | JOPA3 | 2025-12-17 | 13 | 7 | 0.1 | 0.1111111111111111111111111111 | R$ 0,00 | FAIL | PASS | REVIEW | PASS |

## 14. Investable-universe scenarios

L0–L7 counts above define the prospective universe only if a later policy explicitly adopts the scenario. For L1/L2, no issuer is confirmed FAIL because some cases lack resolved identity and remain REVIEW. For L3–L7, only confirmed failures leave the scenario's pass set; REVIEW remains visible. Data completeness is evaluated after eligibility, preserving blocked issuers in denominators unless an explicitly approved structural/user/liquidity rule removes them.

## 15. Recommendations

Keep ranking inactive. Decide the retail taxonomy before using the 36-issuer CVM sector proxy; decide which share class is buyable when an issuer has multiple classes; and choose a liquidity rule only from execution/investability needs, with REVIEW treatment specified. Keep missing data separate from eligibility. Treat the displayed sensitivity as evidence for those policy decisions, never as a coverage optimization target.

## 16. Decisions still required

- Whether the entire CVM `Comércio (Atacado e Varejo)` category is the intended retail exclusion, including wholesale/distributor and commerce-adjacent issuers.
- How to treat unresolved liquidity identity and companies with multiple classes when no share-class execution policy exists.
- Whether to define a minimum market cap, and if so its economic rationale and reference date.
- Whether the current 18 outside-baseline source records need a separate identity/base-sector adjudication before future universe expansion.
- Preserve the existing unit-evidence, COTAHIST and reference-date lineage when a later ranking snapshot is considered.

## Audit constraints and artifacts

`ranking_calculated=False`, `ranking_active=False`, `ranking_blocked=True`, `top_30_published=False`, `methodology_changed=False`.

Appendices: [all 307 issuer decisions](appendices/magic_formula_investable_universe_v6/company_eligibility_307.csv), [all 431 class-level liquidity records](appendices/magic_formula_investable_universe_v6/security_liquidity_431.csv), [all 35 existing financial exclusions](appendices/magic_formula_investable_universe_v6/structural_financial_exclusions_35.csv), [all 31 blockers](appendices/magic_formula_investable_universe_v6/price_blockers_31.csv), and [COTAHIST archive manifests](appendices/magic_formula_investable_universe_v6/audit_source_manifests.json). A few company display names contain the replacement character already present in the source snapshot; identifiers, CVM codes and security identities are the audit keys.

The audit script is read-only against the SQLite snapshot and writes only under `tmp/magic-formula-investable-v6`; the appendices and this report are generated from its JSON output.
