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

Hosted PR results are required before reporting an after-time or claiming CI/staging
acceptance. The local Formula gate and source recovery above validate only those two
components; they do not constitute hosted staging evidence. Record the PR run URL, gate
duration, total workflow duration, diagnostic duration, selected test counts, cache
information and staging outcome here after hosted validation completes.
