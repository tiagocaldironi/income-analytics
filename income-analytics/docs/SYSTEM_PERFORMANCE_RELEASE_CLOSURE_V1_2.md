# System Performance Release Closure V1.2

**Status: PASS.** The two `finding_engine_v2` blockers are fixed at shared price-resolution boundaries. The full suite passes (863/863), financial analytics payloads remain unchanged, and the release is ready.

## Cause and correction

`PortfolioSession` caches market prices by asset for binary as-of lookup. The cache was not refreshed when the source `_market_prices` list was replaced, so removed historical rows remained eligible. In the missing-history test, the requested date was **2026-06-25** and the only raw candidates were BRTEST at **R$82 on 2026-09-23** and USTEST at **R$18 on 2026-09-23**. The stale index still contained BRTEST at **R$75 on 2026-06-25** and USTEST at **R$25 on 2026-06-25**; those removed rows were selected. Coverage became 1 and country concentration was reported as `WORSENING` with comparison value 0.75. After the fix, no candidate is selected for 2026-06-25, coverage is 0, and findings report `UNKNOWN` with `INSUFFICIENT_COMPARISON_VALUATION`.

In the undated-price test, the raw history was empty, but the same stale dated rows were selected before the test reached `Asset.current_price = R$500`. After rebuilding the index, there are no historical candidates and coverage is 0. An explicit historical `as_of` projection can no longer fall back to an undated current price. A current projection with no date still uses that R$500 value, preserving current valuation behavior.

No future quote was selected by the old `bisect_right` date boundary: the observed bad selections were stale, dated 2026-06-25 records. After the change, future quotes remain excluded and the derived index is rebuilt when its source list is replaced or resized. Dated historical projections also suppress `Asset.current_price` fallback. Changes are in [portfolio_session.py](../src/income_analytics/application/portfolio_session.py) and [portfolio_projector.py](../src/income_analytics/domain/projectors/portfolio_projector.py).

## Temporal golden cases

All passed: latest quote before the requested date (09/01 chosen over 11/01 for 10/01); future-only quote rejected; undated current quote rejected for historical coverage; exact-date quote accepted; first/last lookup boundaries; and missing history produces `UNKNOWN`. Tests are in [test_portfolio_projector.py](../tests/unit/domain/projectors/test_portfolio_projector.py) and the existing finding contracts remain unchanged in [test_finding_engine_v2.py](../tests/application/test_finding_engine_v2.py).

## Release verification

| Check | Result |
| --- | --- |
| Finding and temporal tests | 30/30 PASS |
| Performance regression tests | 55/55 PASS |
| Full suite (`PYTHONPATH=src;.`) | 863/863 PASS, 0 failures, 0 errors, 0 unexpected skips |
| Ruff / `git diff --check` | PASS / PASS |
| Runtime HTTP | PASS; analytics, dashboard, holdings, root and static JavaScript returned 200 |
| Golden analytics payloads | All four byte-identical; TWR semantics and Magic Formula unchanged |

The final 1-cold + 10-warm analytics run produced p95 values of 557 ms for wealth evolution, 444 ms for wealth explanation, 316 ms for portfolio performance, and 104 ms for performance comparison. With only ten warm samples, nearest-rank p95 is the maximum, making that estimate sensitive to a single tail request. Two runs observed wealth-evolution maxima of 547 and 557 ms; a follow-up 30-warm sample measured p95 **475 ms** and maximum **494 ms**. The earlier approved V1.1 sample was 496 ms p95. No broad analytics optimization was reopened; the larger sample confirms the endpoint remains within budget.

Holdings p95 was 10,64 ms; dashboard p95 was 14,36 ms. Dashboard payload was 101.112 bytes versus the previous reference of approximately 92 KB; recorded as an observation without evidence of functional or latency regression. Concurrent portfolio-performance tails remain observed at approximately 596/945/965 ms for concurrency 1/2/4 and are non-blocking under this release specification.

## Final gate

`ANALYTICS_ENGINE_OPTIMIZED=YES` · `SYSTEM_PERFORMANCE_RELEASE_GATE=PASS` · `APPLICATION_PERFORMANCE_RELEASE_READY=YES`

**Next: stop performance optimization and use the application.** Supporting audit, before/after payload hashes, benchmarks, test manifest and gate details are in [`docs/appendices/system_performance_release_closure_v1_2/`](appendices/system_performance_release_closure_v1_2/).
