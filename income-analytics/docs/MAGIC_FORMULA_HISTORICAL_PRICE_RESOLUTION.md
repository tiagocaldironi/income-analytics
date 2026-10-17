# Historical Market Price Coverage — Phase 3

Reference date: 2025-12-31. Parent universe:
`f63e9ed8-8103-4f2b-970b-925fd1c2e0e7`.

## Policy and evidence

`MAGIC_FORMULA_HISTORICAL_PRICE_V1` resolves each temporal security separately.
It uses the latest official close on or before the requested date, within the
existing seven-calendar-day window and the security's validity interval.
The requested date remains unchanged. PREULT is parsed from bytes 108:121 with
Decimal division by 100; BRL is normalized from the source currency `R$`.
Missing, invalid, ambiguous, future and out-of-window prices cannot resolve.
No ticker alias, current-price proxy, manual price or issuer exception is used.

The full annual archive `COTAHIST_A2025.ZIP` was scanned, with SHA256:
`6cc0ad851c8f605ca30418acac48be81f1767f6ed05b4f563772d06ae448047d`.
Its original download timestamp is unavailable and is not reconstructed.
Raw record locators retain archive, member and original line number. Each
resolution also retains issuer/security IDs, FCA reference, temporal validity,
requested/effective dates, raw/normalized price, policy and decision.

The deterministic sample consists of 25 gap issuers and five canonical controls,
selected across sector, ON/PN/UNIT, multiple securities, source-window absence
and recent security validity. The saved sample precedes provider comparison.
Its first public-provider comparison took 392.057 seconds. Full raw diagnosis
took 12.505 seconds. These are distinct operations, not a pipeline benchmark.

## Findings and limits

All 77 gap issuers lack at least one required security's price in the approved
window. Target-security observations comprise 34 tickers with records outside
the window, 56 without an annual record, and 15 with a window record. These
105 observations are security counts, not disjoint issuer counts.

`SOURCE_DATA_GAP` means absence for the pinned ticker and approved window in
this archive. It does not prove that the issuer never traded under another
ticker. The available FCA alternative-security investigation did not establish
a usable replacement: DTCY is recorded in a different trading venue, and FIEI3
ended before the reference date. Neither is used to manufacture readiness.
Unproved corporate-action/ticker histories remain an evidence limitation.

CRTE3 has ON and PN FCA rows sharing a security identifier (source lines 41
and 43). The read-back verifier keys evidence by issuer, security, class and
source reference so it preserves both rows. This existing source/identity
conflict remains for security review; no identity or class was rewritten.

No implementation correction or new resolved issuer is established. All
readiness decisions and financial data are therefore preserved from Phase 2.
Units, share counts, accounting, ranking engine and canonical QA are unchanged.

## Before and after

| Independent dimension | Before | After |
| --- | ---: | ---: |
| Methodology eligible | 307 | 307 |
| Accounting ready | 256 | 256 |
| Security ready | 269 | 269 |
| Capital ready | 276 | 276 |
| Price ready | 230 | 230 |
| Full data ready | 178 | 178 |
| No reference price | 77 | 77 |

Full coverage remains 57.98%. The cumulative security funnel count 226 is
different from the independent security-ready count 269.

| Disjoint missing dimensions | Issuers |
| --- | ---: |
| Accounting | 12 |
| Accounting + capital | 10 |
| Accounting + security | 2 |
| Capital | 10 |
| Price | 38 |
| Price + accounting | 14 |
| Price + accounting + capital | 7 |
| Price + accounting + security | 3 |
| Price + accounting + security + capital | 3 |
| Price + security | 12 |
| None (ready) | 178 |
| Security | 17 |
| Security + capital | 1 |

The partition sums to 307. Price-only blockers are 38, giving a theoretical
maximum of 216 full-ready issuers if only price is fixed. This is not achieved
coverage. Top incidence: price 77, accounting 51, security 38. Top isolated
marginal gains: price 38, security 17, accounting 12. No primary gap migrates.

## Validation and reproducibility

The initial immutable audit snapshot is
`c9fa8807-bbc6-4d43-a7a1-9cabd5a88209`; a fresh process read it successfully and
verified exact equality of every issuer payload with the parent. This includes
the Golden Five's financial values and lineage. Its provider comparison covers
the sample only; it must not be treated as proof of full provider coverage.

`scripts/validate_historical_prices.py` resumes the full provider comparison
using the frozen inputs in `tmp/historical-price-phase3`. After its process
exits, run `scripts/readback_historical_prices.py` independently. The latter
requires provider evidence for every audited ticker and compares the persisted
snapshot, parent payloads and reordered coverage arithmetic.

The broad regression run passed 135 tests, zero failed, including historical
shares units, canonical contract, ranking engine, price policy and raw archive
reader. Changed-file Ruff checks passed. Global Ruff reported 53 existing
findings outside this phase; no unrelated lint was corrected.

PRICE-001–008 are covered by date, Decimal, source and rejection policy tests;
PRICE-015–019 by order and gap arithmetic tests. Full-run read-back checks cover
persisted evidence, policy and issuer payload regression. The existing shares,
canonical and engine suites provide the protected-contract regressions.
One additional required-preferred-class regression subsequently passed with the
20-test price suite, giving 136 distinct passing tests across this selection.

| Contract | Evidence |
| --- | --- |
| PRICE-001, 002, 006 | Previous-day policy test retains requested/effective dates and exact Decimal |
| PRICE-003, 004, 008 | Stale/future/other ticker and validity rejection tests |
| PRICE-005 | Complete fixed-width archive test checks original record line |
| PRICE-007 | Missing-source/record tests retain null price |
| PRICE-009, 010 | Separate-class and required-preferred-class readiness regressions |
| PRICE-011 | Historical shares unit regression prevents double counting |
| PRICE-012, 013 | New-database price test preserves source reference and policy |
| PRICE-014 | Parent/child entire issuer payload equality; Golden Five remain full-ready |
| PRICE-015 | Reversed-price-input test; independent-process reversal in final read-back |
| PRICE-016–019 | Universe coverage suite, disjoint partition, marginal-price calculation |
| PRICE-020 | Exact parent/child issuer equality preserves all primary reasons |
| PRICE-021 | Universe fixture forbids ranking calls; repository rejects public status |
| PRICE-022–024 | Frozen-code hashes and ranking/canonical/shares regression suites |
| PRICE-025 | Generic security/date policy; no issuer-specific resolution branches |

The full public-provider comparison completed for all 123 distinct tickers in
the 77 gap issuers and five controls. Final immutable snapshot:
`6d418683-6c09-4cfd-a67b-a4cc54718ddd`.

After the writer exited, `scripts/readback_historical_prices.py` passed in a
fresh process: source archive hash, entire parent/child issuer equality,
provider-versus-raw price/absence evidence, five full-ready controls, reversed
input resolution, reversed issuer arithmetic, and a second independent database
round-trip. Its machine-readable evidence is
`tmp/historical-price-phase3/readback-report.json`; the full per-security audit
is persisted in the immutable universe database.

## Gate

The price audit is validated with source gaps. Zero new issuers were resolved;
the 77 pinned-ticker/window gaps and the CRTE3 source/identity review remain.
This is not approval to publish a ranking.

`RANKING_GATE = BLOCKED`
`TOOL_STATUS = VALIDATION_REQUIRED`
`RANKING_STATUS = INACTIVE`

Next priority is to investigate source/temporal evidence for the 38 price-only
blockers. A new provider requires a separate
scope decision; accounting is not automatically the next phase.

Existing worktree changes were preserved. This phase adds the price policy,
raw audit reader, audit/read-back scripts and their tests, updates these two
gate documents, and persists audit artifacts. No reset or commit was made.
