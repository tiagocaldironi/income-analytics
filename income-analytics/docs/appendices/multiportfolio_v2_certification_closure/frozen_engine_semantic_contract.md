# MF_BR_2027_V1 frozen-engine semantic contract

Contract version: `MF_BR_2027_V1_FROZEN_ENGINE_SEMANTICS_V1`.

This records behavior supported by the activated V9.2 policy, V12.2 published ranking artifacts, production code, and executable regression evidence. The historical hashes in `tests/fixtures/cvm/shares_unit_v1/manifest.json` are not proof of the current source's historical equivalence. The prospective baseline protects the implementation described here from this point forward.

## Authority and canonical output

The policy authority is `MF_BR_2027_V1`, fingerprint `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac`, from `docs/appendices/magic_formula_v9_2/policy_definition.json`, `policy_fingerprint.json`, `activation_record.json` and `activation_gates.json`. V12.2 publishes snapshot `mf-f1ee50809c83979ba221d84e`, ranking hash `f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3`, and 165 issuer rows. The V2 reconciliation binds the same output to canonical result SHA-256 `162c1b2f8856ae7d88cf5809d9418395464d0b2042bf6177fb48141e5b4fcf6a`. A raw SHA-256 of the published snapshot artifact additionally protects every saved EY, ROC, EY rank, ROC rank, and global rank value.

## Frozen behavior

| Rule | Contract |
|---|---|
| Market 010 / 020 | S4 candidates and historical reference prices use B3 market `010`. `exact_price_candidate` requires exact date, ISIN, class, and market `010`. Market `020` cannot substitute when `010` is missing; that case remains missing/review. |
| Issuer and security identity | Ranking is issuer-level: each ranked issuer has one canonical row and one global rank. ON, PN, and UNIT listings are securities belonging to an issuer, not separate issuer fundamentals. |
| UNIT economics | A UNIT is one valid buyable-security candidate. It is not added as a second issuer or repeated as an extra share-capital component. Where CVM DFP quantities need scaling, only explicit matching same-document XML and PDF unit evidence authorizes a multiplier; quantity magnitude and issuer name never infer units. |
| Share classes | ON and PN remain distinct. A class is mapped through CVM FCA/DFP evidence; class quantities or prices are not used as proxies for another class. Multiple positive classes contribute using their own price. Missing price for a required positive class makes the aggregate market-cap diagnostic unresolved. |
| Issued / treasury | Outstanding shares are issued less treasury, independently for ON and PN. The explicit quantity multiplier applies to both values before subtraction. Treasury greater than issued, source conflicts, or unresolved units fail closed. |
| S4 security selection | Valid listings in market `010` are ordered by 30-session traded-days ratio descending, then median daily financial volume descending, then stable ISIN/ticker/security identity ascending. Price availability, EY, ROC, rank, personal screening, and portfolio position are not inputs. |
| L3 liquidity | L3 passes with at least 15 traded sessions out of 30 (ratio >= 0.50). Missing/incomplete evidence is REVIEW. Financial volume is not a minimum threshold; it is only S4's tie-breaker. S4/L3 definitions remain bound by the unchanged V9.2 policy fingerprint. |
| Market-cap diagnostics | No minimum market-cap policy exists (`minimum_market_cap_brl = NONE`). Market cap is diagnostic/evidence for valuation inputs; coverage or a small market cap does not independently exclude an otherwise eligible issuer. |
| Structural sector policy | The existing financial structural exclusions remain active: banks, brokers, financial intermediation, insurers, leasing, real-estate credit, and receivables securitization. Retail and aviation are not methodology exclusions; optional screening runs after canonical rank and preserves global rank. Utilities receive no new exclusion. |
| Ranking inputs and tie behavior | The existing issuer-level engine calculates EY and ROC on eligible normalized issuer snapshots, dense-ranks each metric, adds the two ranks, then assigns competition global rank with stable company identity as tie policy. This baseline does not alter formulas or methodology. |

## Critical assertions A–O

| Assertion | Result | Evidence |
|---|---|---|
| A. Market 010 remains canonical | PASS | V9.2 policy fingerprint and exact-price helper; goldens `MF-FE-010-MARKET`. |
| B. Market 020 never substitutes | PASS | Helper returns policy-incompatible missing result; golden `MF-FE-020-NO-MARKET-SUBSTITUTION`; V7 regression `test_market_020_is_never_a_buyable_010_candidate`. |
| C. UNIT is not double-counted | PASS | Security selection treats a UNIT as one candidate; outstanding capital contains only ON/PN; historical unit tests 011–013; golden `MF-FE-UNIT-ONE-SECURITY`. |
| D. Ranking is issuer-level | PASS | Canonical snapshot has 165 unique `company_id` rows for 165 ranked companies; immutable artifact hash asserted. |
| E. Security selection is independent from EY/ROC/rank | PASS | S4 helper reads only listing/market/liquidity metrics and stable identity; V1 tests 008–011; golden `MF-FE-S4-INDEPENDENCE`. |
| F. Share-class selection is deterministic | PASS | Explicit FCA class mapping; S4 stable tie-break; class-specific market-cap inputs; V7 selection tests and class aggregation golden. |
| G. Treasury shares are subtracted | PASS | Formula `OUTSTANDING = ISSUED_SHARES - TREASURY_SHARES` class by class; unit 013 and golden `MF-FE-TREASURY-AND-UNIT-SCALE`. |
| H. Market cap is not a methodology filter | PASS | Policy minimum is null; market-cap resolver reports readiness/coverage without excluding; golden `MF-FE-POLICY-AND-RANKING-INVARIANTS`. |
| I. No minimum market cap was added | PASS | Activated policy and fingerprint encode `minimum_brl: null`; test V1-05. |
| J. No minimum financial volume was added | PASS | V9.2 says volume is not a threshold; S4 uses it only after frequency tie; golden policy and selection cases. |
| K. S4 unchanged | PASS | Current S4 criteria and tie-breaker match V9.2 activated artifact/fingerprint and V7 tests. |
| L. L3 unchanged | PASS | L3 remains 15/30, 0.50 threshold; V9.2 activation artifact and threshold tests. |
| M. Retail/aviation remain screening-only | PASS | Methodology defaults do not exclude either; display filtering is downstream and global ranks remain unchanged; V1/V8 tests. |
| N. Utilities remain included | PASS | No new utilities exclusion in policy; Energia Elétrica structural decision is PASS. |
| O. Financial structural exclusions remain | PASS | Existing financial sectors remain structural exclusions; Banks decision is `INELIGIBLE_STRUCTURAL`. |

## Audited implementation dependency closure

The prospective baseline hashes the declared source set in `frozen_engine_baseline_v2.json`. It covers the issuer ranking/formula and contract; canonical ranking and its read path; market-010 universe and COTAHIST selection; CVM security/capital parsing; explicit historical unit resolution; class aggregation/market-cap diagnostics; S4/L3 and downstream screening; and formal QA/readback. The protected paths are explicit in the deterministic baseline generator, sorted by repository-relative POSIX path, and use raw file bytes.

The executable behavior matrix is `frozen_engine_semantic_goldens.json`. Every golden includes its rule ID, rule source, deterministic input, expected behavior, and rationale. The old historical hash assertion has been replaced with a preservation check; the old manifest remains untouched as unresolved evidence.
