# CI/CD stabilization — November 2026

## Measured baseline

Hosted run [44845305903](https://github.com/tiagocaldironi/income-analytics/actions/runs/44845305903)
completed the required `CI / Engineering` gate in 9m24s. Its full Python diagnostic took
8m16s and held the matrix job needed by the engineering summary. Full Python collected
1,677 tests; the engineering and financial scopes selected 1,365 and 214 respectively,
so 1,579 executions were repeated across those three invocations. The financial subset
is now evaluated from the full Python inventory/JUnit rather than run a second time.
Ruff and mypy findings are also each collected once; the quality non-regression gate
consumes those same-run reports and still checks the pinned versions, diagnostic
identities, accepted typing inventory and Ruff exception inventory.

The same run recorded 1,648 passed, 15 failed, 9 errors and 5 skipped in the full suite.
All 22 Magic Formula historical failures/errors remain classified as historical
certification cases and continue to appear in the full/financial diagnostics. The
dedicated Magic Formula functional gate contains only its hermetic tests; those cases
remain in the full and financial selections.

The hosted Magic Formula job in that run duplicated all 34 frontend suites because its
governance dispatch fell through to the legacy Node runner. The corrected dispatch ran
283 Magic Formula tests locally: 283 passed, 0 failed, 0 errors, 0 skipped.

## Baseline A recovery

The original Actions artifact `12890060783` from run `40856571402` is no longer
downloadable. Its original package SHA-256 is
`5fe747f55179b82e166761cd7c8adca0a643123bc809086c716e19ee0ddd38b2`; its embedded
manifest SHA-256 is `008b349f9a2f17332292fdf0cad2fd690a5d00ef21a37e8f7e0124ce367cee04`.
An independent two-build reconstruction from the exact approved source commit matched
both recorded hashes. Those original pins were preserved in
[`ci/baseline-a.json`](../../../ci/baseline-a.json).

The reconstructed bytes are stored as assets in the prerelease
[`ci-baseline-a-cc71b0be`](https://github.com/tiagocaldironi/income-analytics/releases/tag/ci-baseline-a-cc71b0be),
explicitly labelled a staging rollback fixture. Local API recovery verified the source
run, original successful Engineering and Reproducible build jobs, tag target commit,
asset digests, embedded manifest and package bytes. No new financial baseline or
production release was created.

## Post-change measurements

Hosted core workflow [45052306207](https://github.com/tiagocaldironi/income-analytics/actions/runs/45052306207)
completed on head `4170f6b7ec24e38dfe74900fc7be171f135997c6`. The required
`CI / Engineering` status became successful 6m29s after the workflow started, down from
9m24s in the baseline run: 2m55s (31.0%) faster. The complete core workflow, including
premerge staging, completed in 8m22s. The isolated full Python workflow
[45052306254](https://github.com/tiagocaldironi/income-analytics/actions/runs/45052306254)
completed its diagnostic execution in 7m39s and financial evaluation in another 1m01s
(10m01s total elapsed, including queue time); neither job gates `CI / Engineering`.

The hosted core run passed Python engineering (1,371 passed), Magic Formula certification
(283 passed), Runtime, Frontend, Operational readiness, Reproducible build, Ruff,
Quality non-regression, Security baseline and `CI / Engineering`. Raw mypy diagnostics
still report existing debt; the unchanged quality non-regression evaluation passed. The
dedicated Formula job ran in 3m18s, without the previous duplicate frontend suites. The
hosted full Python diagnostic remains visible and failed with 1,654 passed, 15 failed,
9 errors and 5 skipped; the financial projection derived from that same JUnit/inventory remains
`FINANCIAL_BLOCKED` with mandatory coverage verified and production unauthorized. Its
blockers are historical provenance and frozen reference review items, and its scoped
release assessment recorded 411 passed with no scoped failures. No historical failures,
financial controls or release policies were waived.

Premerge staging passed in the same run using the pinned historical A package and the
candidate package in disposable Windows staging. Known-good A validation, offline
installation, backup, restore, rollback, health and cleanup passed. The incompatible
schema case remained safely blocked; promotion remained blocked, financial release
remained blocked and production remained unauthorized. The recovered A package SHA-256
matched `5fe747f55179b82e166761cd7c8adca0a643123bc809086c716e19ee0ddd38b2`.

The Python engineering job restored its setup-python pip cache successfully. The measured
workflow durations include runner queue time and can vary with runner load and cache state.
