# Historical Valuation & TWR Reconstruction V1 Discovery

## Existing reconstruction capability

`PortfolioProjector.project_as_of` reconstructs positions from all financial events whose `effective_date` is on or before the requested date. `PortfolioSession.projection(as_of=...)` supplies the latest persisted quote on or before that date and derives fixed-income values through `FixedIncomeValuationEngine`. `BaseCurrencyValuationProjector` applies persisted FX observations on or before the same date.

This is reconstruction as-of already; no historical snapshot is required. `PortfolioHistory` is also derived on demand, but its existing serialization hides an entire point when any position lacks a quote. That makes partial, useful coverage invisible.

## Local data coverage at audit time

| Source | Available range | Consequence |
| --- | --- | --- |
| Financial events | 2023-01-02 to 2026-09-11 | Positions can be reconstructed economically. |
| Brazilian stock/FII prices | 2026-09-07 to 2026-09-23 | Earlier listed valuations cannot be reconstructed from the local cache. |
| Crypto prices | 2026-09-23 only | Earlier crypto values are unavailable. |
| US stock/REIT prices | 2026-09-22 to 2026-09-23 | Earlier foreign-equity values are unavailable. |
| USD/BRL FX | 2026-09-22 only | Foreign values before that date are unavailable in BRL. |
| CDI | 2026-04-07 to 2026-09-22 | Existing fixed-income contract valuation can be reconstructed where contract inputs allow it. |
| Pension / real estate | no local records | No coverage impact in this dataset. |

## TWR conclusion

The shared `PerformanceProjector` already uses economic external-flow dates and no look-ahead quotes. Full-portfolio TWR for the requested long period remains correctly unavailable because the opening and boundary valuations are incomplete. Partial TWR is not introduced: the locally valuated universe changes materially as price and FX history begins in September, so a partial universe would not remain constant across required boundaries.

## Implementation decision

Extend the existing as-of projection with a read-only historical reconstruction service. It returns valued wealth, unvalued positions, a defensible status, and issues per point. It deliberately omits a monetary coverage percentage where an unvalued position has no defensible valuation. The evolution endpoint will use this service and never call a provider.
