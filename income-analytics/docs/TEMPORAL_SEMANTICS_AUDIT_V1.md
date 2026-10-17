# Temporal Semantics Audit V1

Audit completed on 2026-09-23 against the local portfolio database and the portfolio, valuation, performance, recurring, and dashboard read-model paths. No production data was changed.

## Executive result

| Question | Result |
| --- | --- |
| `TEMPORAL_SEMANTICS` | `PASS` |
| Was `created_at` incorrectly used as an economic date? | `NO` |
| Was `updated_at` incorrectly used as an economic date? | `NO` |
| Were retroactive transactions already supported correctly? | `YES` |
| Did corrections become necessary? | `NO` |

`PortfolioProjector.project_as_of` includes events and prices only when their `effective_date` is on or before the requested date. It uses `registered_at` only as a deterministic tiebreaker for events sharing an economic date. `PerformanceProjector` applies the same date rule to flows.

## Temporal matrix

| Domain | Economic date | Technical timestamp | Historical calculation field | Status | Correction |
| --- | --- | --- | --- | --- | --- |
| Trades, deposits, withdrawals, paid income | `FinancialEvent.effective_date` | `occurred_at`, `registered_at` | `effective_date` | `CORRECT_ECONOMIC_USE` | None |
| Event ordering | `effective_date` | `registered_at` | effective date, then registration only on ties | `CORRECT_TECHNICAL_USE` | None |
| Listed market prices | `MarketPrice.effective_date` | `registered_at`, `price_timestamp` | latest quote with date `<= as_of` | `CORRECT_ECONOMIC_USE` | None |
| Fixed income | `application_date` | `created_at` | contract date and dated benchmark references | `CORRECT_ECONOMIC_USE` | None |
| FX | `FxRateObservation.effective_date` | none persisted | latest rate on or before `as_of` | `CORRECT_ECONOMIC_USE` | None |
| Benchmark / CDI / IPCA / TR | `effective_date` | none persisted | reference date constrained by `as_of` | `CORRECT_ECONOMIC_USE` | None |
| Pension reported balance | `reported_balance_date` | asset creation time | reported balance date | `CORRECT_ECONOMIC_USE` | None |
| Real estate | `acquisition_date`, `valuation_date` | asset creation time | acquisition then valuation date | `CORRECT_ECONOMIC_USE` | None |
| Recurrences | `next_execution_date` | event registration time | occurrence effective date | `CORRECT_ECONOMIC_USE` | None |
| Portfolio history | event / price `effective_date` | none | reconstructed on demand | `CORRECT_ECONOMIC_USE` | None |
| Dashboard snapshot | current-state rebuild time | `calculated_at` | current projection only | `CORRECT_TECHNICAL_USE` | None |
| Magic Formula artifacts | reporting/reference dates | creation/update times | isolated from portfolio history | `NOT_APPLICABLE` | None |

## As-of and Entender

`as_of(D)` means the economic portfolio state at the end of calendar date `D`; it never means records whose creation timestamp is at or before `D`.

Entender opening wealth is `as_of(start_date)` and closing wealth is `as_of(end_date)`. Interval events are `(start_date, end_date]`; an event on the opening date belongs to opening wealth and is not counted again as a period flow.

Observed period: `2026-01-01` through `2026-12-31`.

Observed opening wealth: `R$ 0,00`.

Observed closing wealth: `R$ 90.706,87`.

**Root cause of opening zero:** positions are economically present in the historical projection, but the local database has no eligible historical market prices at `2026-01-01` (the stored market-price range starts at `2026-09-07`) and no FX rates sufficient to value foreign positions on that date. The base-currency valuation exposes a partial market value of zero and `complete = false`. This is a historical-valuation data-quality gap; it is not evidence that assets did not exist, and `created_at` is not involved.

Entender returns `PARTIAL_VALUATION_COVERAGE` for this condition. The displayed zero is the marked value available at that date, not a claim that the position set was empty. Do not use current price or registration time as a historical fallback.

## Snapshots and cache

`PortfolioHistory` is reconstructed from source events and prices on demand, so a late imported transaction is reflected in affected as-of calculations. The persisted dashboard snapshot is a current-state read model; `calculated_at` is its rebuild timestamp, not an as-known-at date. Portfolio write and import routes rebuild it, and an explicit rebuild endpoint exists. No stale historical snapshot cache was found.

## Local legacy-data evidence

| Dataset | Records | Missing economic date |
| --- | ---: | ---: |
| Financial events | 810 | 0 |
| Market prices | 70 | 0 |
| Fixed-income contracts | 2 | 0 missing `application_date` |
| Pension details | 0 | n/a |
| Real-estate details | 0 | n/a |

Financial-event economic dates range from `2023-01-02` through `2026-09-11`. Market prices range from `2026-09-07` through `2026-09-23`; that narrow range explains the missing historical valuation coverage. No record was silently backfilled from `created_at`.

## Retroactive validation

| Scenario | Result | Evidence |
| --- | --- | --- |
| Retroactive BUY and future as-of | `PASS` | explicit regression test |
| Retroactive SELL | `PASS` | before/after-sale assertions |
| Registration-time irrelevance | `PASS` | identical economics with timestamps one year apart |
| Retroactive fixed income | `PASS` | application date drives contract value |
| Historical market price imported later | `PASS` | reference date drives valuation |
| Paid income and Entender | `PASS` | retroactive income included in period |
| Pension balance date | `PASS` | balance starts at report date |
| Real-estate valuation date | `PASS` | 2026 estimate is not applied to 2020 |
| Recurring occurrence | `PASS` | event effective date remains scheduled date |
| TWR economic flows | `PASS` | dated flow/performance regression |
| Derived-history cache invalidation | `PASS` | explanation is rebuilt from source streams |
| Missing valuation versus missing asset | `PASS` | position remains; completeness becomes false |

## Issues and corrections

No incorrect use of `created_at` or `updated_at` as an economic date was found. No production code, query, cache/snapshot behavior, migration, or data migration required correction.

The only observed gap is data quality: historical market-price and FX coverage is insufficient to construct a complete opening valuation for the observed period. It must remain distinct from asset existence and be addressed through dated source recovery, not a timestamp fallback.

Files added: this report and `tests/application/test_temporal_semantics.py`.

## Validation

```text
pytest tests/application/test_temporal_semantics.py tests/application/test_wealth_explanation.py tests/application/test_fixed_income_assets.py tests/application/test_recurring_execution.py tests/acceptance/test_portfolio_timeline_mvp.py tests/acceptance/test_portfolio_performance_mvp.py -q
28 passed
```

## Final assessment

| Assessment | Result |
| --- | --- |
| `ECONOMIC_TIME_MODEL` | `PASS` |
| `RETROACTIVE_OPERATIONS` | `PASS` |
| `AS_OF_PORTFOLIO` | `PASS` |
| `ENTENDER_TEMPORALITY` | `PASS` |
| `TWR_TEMPORALITY` | `PASS` |
| `CACHE_INVALIDATION` | `PASS` |
| `NO_LOOKAHEAD` | `PASS` |
| `REGRESSION` | `PASS` |
