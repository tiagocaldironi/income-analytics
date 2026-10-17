# Magic Formula — Publishable Universe Gate, Phase 1

Phase 1 discovery/readiness gate: **PASS**. This is not publication approval.
The measured universe contains 360 candidate issuers, of which 307 are
methodologically eligible and 5 have complete data readiness (5/307 = 1.63%).
`TOOL_STATUS = VALIDATION_REQUIRED`; `RANKING_STATUS = INACTIVE`.
No market ranking was executed or published by discovery.

## Persisted result and scope

- Universe snapshot: `22db1605-56e5-48ed-985b-4b611dba3a5d`.
- Store: `data/magic_formula/universe_snapshots.db`.
- Type: `CANDIDATE_PUBLISHABLE_UNIVERSE`.
- Reference date: `2025-12-31`.
- Methodology: `MAGIC_FORMULA_STOCKS_V1` (unchanged).
- Universe policy: `MAGIC_FORMULA_UNIVERSE_CVM_FCA_V1`.
- Validated sample reference: ranking artifact `921b4bfa-d99c-464f-a0ac-2668be1daefb`.
- Export: `tmp/universe-gate-phase1/real/universe-snapshot.json`.
- Measurements: `tmp/universe-gate-phase1/real/run-summary.json`.
- Independent audit: `tmp/universe-gate-phase1/independent-readback.json`.

The existing ranking artifact supplies the frozen reference and regression anchors;
its issuer list does not supply universe membership. No ranking method is called.

This universe means issuers evidenced by the pinned 2025 FCA with B3 exchange
equity or units at the reference. It does not claim to include every CVM entity or
every instrument traded in Brazil. Debt-only, non-B3/non-exchange instruments and
conclusively expired/future securities are outside this boundary. Unknown validity
is retained and fails readiness. The snapshot includes discarded-record counts.

## Source provenance and reproducibility

| Pinned official archive | SHA-256 |
| --- | --- |
| `data/cvm/fca_cia_aberta_2025.zip` | `dbbbda515a98d402ff0b0fb2808d15f3d81b029e0c61de8b95655323604d1192` |
| `data/cvm/dfp_cia_aberta_2025.zip` | `de8b7be1cdae032a402ab33916015c74fdc30f0bc64be3f38a4b5dd1d43f6d79` |
| `data/cotahist/COTAHIST_A2025.ZIP` | `6cc0ad851c8f605ca30418acac48be81f1767f6ed05b4f563772d06ae448047d` |

FCA general records supply CVM identity, issuer name, structured economic sector,
registration category/status and their dates. FCA securities supply ticker, class,
preferred subclass, unit composition, listing dates and document identity.
COTAHIST supplies historical price, currency and ISIN when available.
Every retained item has an archive/member/physical-line locator. The snapshot
preserves original raw capital quantities, account amounts/scales and source hashes.

Versioned test excerpts are in `tests/fixtures/cvm/universe_discovery_v1` with a
manifest and reconstruction notes. Full FCA is preserved; excerpted DFP/COTAHIST
records preserve original bytes and physical line numbers using blank padding.

Replay from pinned local sources:

```powershell
python scripts/discover_magic_formula_universe.py --database income_analytics.db --ranking-database data/magic_formula/validation_rankings.db --universe-database data/magic_formula/universe_snapshots.db --output tmp/universe-gate-phase1/replay
```

A replay creates a new immutable snapshot UUID/time. With the same source and
canonical evidence, issuer IDs, composition, statuses, reasons and coverage are
identical. Reversed ingestion was checked against the entire issuer document.

## Identity and sector policy

The economic unit is the issuer, grouped by normalized CNPJ and checked against
CVM code. Existing canonical UUIDs are reused on an exact identity match. New
candidate UUIDs are deterministic UUID5 identifiers from the CVM/CNPJ pair, stored
only in the universe artifact; no canonical issuer rows are created. CVM code,
CNPJ and tickers remain attributes. Securities remain children of their issuer.
Conflicting CVM/CNPJ claims or ambiguous records fail closed; unresolved issuer IDs
are not fabricated. Petrobras contains PETR3 and PETR4 under one issuer.

Sector classification uses only FCA `Setor_Atividade`, retaining its original
granularity and source. The versioned policy recognizes structured financial
categories: Bancos; Seguradoras e Corretoras; Intermediação Financeira; Crédito
Imobiliário; Arrendamento Mercantil; Securitização de Recebíveis. A structured
`Emp. Adm. Part. - ` prefix preserves the stated sector of the holding. These
categories produce `FINANCIAL_SECTOR`; issuer names and tickers are never classifiers.

Explicit operating-sector categories in the policy are non-financial. Unknown
categories, including `Sem Setor Principal` and the market-exchange category,
remain `REVIEW_REQUIRED`; no new methodological exclusion is invented. Utilities
are not excluded by this discovery policy. Methodology eligibility is independent
of data availability: missing shares, prices or accounts do not exclude an issuer.

## Reference and readiness rules

Accounting and capital must both match 2025-12-31. Annual consolidated DRE must
cover 2025-01-01 through 2025-12-31. Price is the latest official close on or before
the requested date, within seven calendar days. Future prices cannot be selected.
Requested and effective dates are stored separately for every security. Competing
latest quotes, identity conflicts and temporal conflicts require review.

Archive vintage is explicitly `RETROSPECTIVE_PINNED_ARCHIVES_NOT_POINT_IN_TIME_BACKTEST`.
These annual filings permit a retrospective reference-date evaluation; no claim is
made that all published filings were available on 2025-12-31. Historical status
changes after the reference are not silently projected backward.

Accounting readiness checks the unchanged Accounting Registry: EBIT (DRE 3.05),
cash (BPA 1.01.01), debt ST/LT (BPP 2.01.04/2.02.01), operating current assets
(BPA 1.01.03 + 1.01.04), operating current liabilities (BPP 2.01.02) and net fixed
assets (BPA 1.02.03). Missing/nonfinite values remain missing; duplicates, wrong
periods, identity mismatches or unknown monetary scales do not pass.

Complete raw components are `NORMALIZATION_REQUIRED` for new issuers; they count
as accounting availability, not as new normalized fundamentals snapshots.
Already validated canonical evidence gives `AVAILABLE`. No broad normalization
or financial metrics are materialized in this phase.

Security readiness requires valid historical mapping for every positive issued
share class. Ambiguous preferred subclasses and unresolved unit decomposition fail
closed. A quoted unit may count as price availability without resolving class
mapping or issuer market cap. The relevant price tickers are explicit in the artifact.

Capital readiness requires matching reference, finite valid issued/treasury
quantities and proven quantity scale. DFP composition has no universal scale
proof; no unit is guessed from magnitude. Existing resolved canonical evidence is
reused generically only when class, date, issued/treasury quantities, UNIT and
multiplier 1 match exactly. There is no issuer-name exception. Other complete raw
capital rows remain `UNIT_UNRESOLVED` until that proof exists.

`FULL_DATA_READY` requires all dimensions, including identity. It is a Phase 1
readiness measurement; it does not grant production ranking eligibility or bypass
the canonical validation contract.

## Coverage

The cumulative funnel requires every previous stage:

| Stage | Issuers |
| --- | ---: |
| TOTAL_CANDIDATE_ISSUERS | 360 |
| METHODOLOGY_ELIGIBLE | 307 |
| IDENTITY_RESOLVED | 307 |
| ACCOUNTING_READY | 256 |
| SECURITY_READY | 226 |
| CAPITAL_READY | 5 |
| MARKET_PRICE_READY | 5 |
| FULL_DATA_READY | 5 |

Independent coverage avoids attributing an upstream capital gap to price absence:

| Dimension | Numerator / denominator | Coverage |
| --- | ---: | ---: |
| Methodology | 307 / 360 | 85.28% |
| Identity | 307 / 307 | 100.00% |
| Accounting components | 256 / 307 | 83.39% |
| Security mapping | 269 / 307 | 87.62% |
| Capital | 5 / 307 | 1.63% |
| Historical price | 230 / 307 | 74.92% |
| Complete data | 5 / 307 | 1.63% |

Methodology partition: 307 eligible + 35 excluded + 18 sector review = 360.
Primary status partition: 5 ELIGIBLE + 296 DATA_GAP + 35 EXCLUDED + 24 REVIEW_REQUIRED
= 360. Review comprises 18 sector cases plus 6 temporal cases among methodology
eligible issuers. Financial exclusion reason: `FINANCIAL_SECTOR = 35`.

Data-reason incidence among the 307 methodology-eligible issuers overlaps:

| Reason | Issuers |
| --- | ---: |
| UNIT_UNRESOLVED | 282 |
| NO_REFERENCE_PRICE | 77 |
| NO_ACCOUNTING_DATA | 51 |
| NO_VALID_SECURITY | 38 |
| NO_CAPITAL_DATA | 20 |
| TEMPORAL_CONFLICT | 6 |
| UNRESOLVED_IDENTITY | 0 |

These counts must not be added as distinct issuers. For reconciliation, a stable
lexicographic first reason assigns each non-ready eligible issuer once:
51 NO_ACCOUNTING_DATA + 50 NO_REFERENCE_PRICE + 18 NO_VALID_SECURITY +
183 UNIT_UNRESOLVED = 302 = 307 eligible - 5 complete. This ordering is only an
audit partition; prioritization uses overlapping incidence, not the first reason.

Top blockers are quantity-unit proof (282/307 = 91.86%), historical price
(77/307 = 25.08%), and accounting components (51/307 = 16.61%). Their overlap means
solving one blocker does not automatically produce the same number of ready issuers.

## Golden-five regression and independent read-back

All five were discovered from FCA, remained methodology eligible/data ready, and
retained their canonical UUID, snapshot, formal QA and RESOLVED projection:

| Issuer | Existing snapshot ID | Existing formal QA ID |
| --- | --- | --- |
| Petrobras | `6d5dd506-9023-4862-81eb-067cb0bc3cf2` | `f2ed0dc5-f34a-41c7-b162-cb389187a2f3` |
| WEG | `56cffb48-edf2-493c-a775-de1aacab5685` | `c5dcc8c5-f45f-431d-b1b9-5d53538d1482` |
| Suzano | `5efdb7bf-4433-45f9-b06c-38e09bd7baa5` | `a8334600-73b8-4adc-bd56-2ab5ea277df1` |
| Rumo | `a827520a-f34b-4cb9-87ae-83d0b94a09ba` | `ec0a71e2-b3c8-4bb5-808c-120221cffe25` |
| Telefônica | `d97ee807-7299-41b2-9026-d6ec7f926d70` | `09afeef3-23da-4d37-96fa-0dd7a216bfb7` |

Universe persistence commits and closes each SQLite connection. A fresh repository
connection then checks digest and coverage. After that process exited, an independent
process reopened the store and compared the full document with the export, including
issuer counts, IDs, statuses, reason codes and coverage: PASS.

The same independent process compared all canonical table rows to the pre-phase
backup `tmp/universe-gate-phase1/before.db`: exact equality. Counts remain 5 issuers,
5 goldens, 10 snapshots (5 legacy + 5 V2), and 5 QA decisions. Thus metrics, lineage,
validation and QA are unchanged. Shared before/after digest:
`ad06071aac9e8802cb2aa6b045a2a881e8c25ed9a86deae9b17ab2ab6c5846fd`.
New connections also reran each canonical eligibility projection: all five remain
RESOLVED and eligible. Ranking artifact count remains two (frozen sample + prior
validation result); no new ranking artifact was generated.

The universe store prohibits UPDATE/DELETE via immutable triggers, validates coverage
before insertion, and rejects publication/tool-state changes in saved documents.

## Golden validation path and future production data path

The golden path remains deep validation against the five approved reference cases,
including financial comparisons, lineage, canonical snapshots and eight formal QA
dimensions. It detects pipeline regressions and must stay unchanged.

The future production path should apply the validated adapter automatically to
source-resolved issuers and produce machine-verifiable dimension checks, source
digests, anomaly records and read-back evidence per run. Manual review should focus
on exceptions, ambiguous identities/mappings, unsupported accounting and new rules.
It should not require writing eight manual QA decisions for every issuer.

That future separation requires an explicitly reviewed production quality contract
and publication gate. This phase implements neither new canonical approvals nor a
shortcut around the current golden-based eligibility contract. Readiness flags
cannot be used to activate public ranking. The first next step is proving historical
quantity units at scale from authoritative dated evidence, followed by rerunning this
same coverage policy to measure the gain.

## Performance and verification

| Operation | Measured duration |
| --- | ---: |
| Discovery, FCA parsing and source hashes | 0.864 s |
| Classification and canonical context | 0.056 s |
| Accounting/capital/price source reading and readiness | 11.601 s |
| Reversed-ingestion determinism check | 0.167 s |
| Persistence, close and read-back | 0.238 s |

Readiness is the largest measured phase. Annual archive scanning/decompression is
included in that time; finer profiling was not performed, so no per-loader hotspot
claim or premature optimization is made.

All UNIVERSE-001 through UNIVERSE-018 scenarios are covered in
`tests/application/test_magic_formula_universe.py` (25 passing test cases, including
negative values/ambiguity, unknown sectors, units, checksum and immutability checks).
The relevant regression suite passed **170 tests, zero failures**, in 69.88 seconds:

```powershell
python -m pytest tests/application tests/infrastructure/test_b3_cotahist_market_data.py -q --basetemp tmp/universe-gate-phase1/pytest-regression -p no:cacheprovider --junitxml tmp/universe-gate-phase1/tests.xml
```

The first targeted invocation hit permission errors in the system pytest temporary
directory. Using the project-local test directory resolved that environment issue;
the completed targeted and regression runs both passed.

Changed Python files: Ruff PASS, zero findings. Global scoped check
`ruff check src tests scripts alembic`: 71 pre-existing findings, including 20 in
the previously known Magic Formula files. They were not corrected. Their source
files match the pre-phase hash baseline. Logs: `tmp/universe-gate-phase1/tests.log`,
`tests.xml`, `global-lint.json`, `pre-existing-lint.json`.

No implementation defect remains known in this Phase 1 scope. The 302 eligible
issuers without complete readiness and 18 sector reviews are measured data/policy
gaps, not a claim of publication readiness.

## Worktree and final state

Pre-existing changes were preserved; pre-phase source/test/script/document hashes
remained equal. This phase adds the universe policy, source reader, separate artifact
repository, CLI, tests, official fixture bundle and this report. It adds one real
universe artifact plus audit outputs; it does not modify existing methodology,
ranking engine, canonical contract, registry or golden files. No reset or commit.

`PUBLISHABLE_UNIVERSE_GATE = PASS` (Phase 1 discovery/readiness only).
`GOLDEN_FIVE_DISCOVERED = 5/5`; `GOLDEN_FIVE_DATA_READY = 5/5`.
`GOLDEN_FIVE_REGRESSION = PASS`; `UNIVERSE_READBACK_STATUS = PASS`.
`DUPLICATE_ISSUER_STATUS = PASS`; `REFERENCE_DATE_POLICY_STATUS = PASS`.
`DETERMINISM_STATUS = PASS`; `LINEAGE_STATUS = PASS`; `OPEN_DEFECTS = 0`.
`TOOL_STATUS = VALIDATION_REQUIRED`; `RANKING_STATUS = INACTIVE`.

Recommended next action: resolve authoritative historical share-unit evidence for
the 282 affected eligible issuers, then remeasure coverage before proposing a
production publication gate. Keep the 77 price and 51 accounting gaps visible.

## Phase 2 update — historical share units

The Phase 1 measurements above remain the historical baseline. Phase 2 recovered
explicit quantity-scale metadata from the original CVM DFP XML, descriptor and
capital-page PDF, linked to the same CSV issuer/date/version/quantities. The rule
`MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1` uses each document's declared unit, with
no magnitude inference, issuer exception or dataset-wide default.

The stratified sample (25 pending issuers plus five controls) passed before expanded
application. 271 of the 282 pending units resolved; 11 remain source-acquisition
gaps. All five canonical cases and existing financial/QA artifacts are unchanged.

New immutable universe snapshot: `f63e9ed8-8103-4f2b-970b-925fd1c2e0e7`.
Read-back in an independent process: PASS. Methodology eligibility: unchanged.

| Independent dimension | Phase 1 | Phase 2 |
| --- | ---: | ---: |
| Capital ready | 5/307 | 276/307 (89.90%) |
| Price ready | 230/307 | 230/307 (74.92%) |
| Accounting ready | 256/307 | 256/307 (83.39%) |
| Full data ready | 5/307 | 178/307 (57.98%) |

Cumulative funnel: 360 → 307 → 307 → 256 → 226 → 216 → 178 → 178.
Capital/security/price readiness without accounting: 190 issuers.
Top remaining gaps: NO_REFERENCE_PRICE 77; NO_ACCOUNTING_DATA 51;
NO_VALID_SECURITY 38. UNIT_UNRESOLVED is now 11; NO_CAPITAL_DATA remains 20.

Final regression: 201 tests passed, zero failed; changed-file lint PASS, with 71
pre-existing global findings preserved. `TOOL_STATUS = VALIDATION_REQUIRED`;
`RANKING_STATUS = INACTIVE`. No market ranking was executed.

See [Phase 2 evidence, sample, policy, before/after coverage and audit](MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_RESOLUTION.md).

## Phase 3 — historical price audit validated with source gaps

The complete annual COTAHIST scan found no demonstrated readiness correction
for the 77 price gaps at 2025-12-31 under the existing seven-day policy.
Price readiness remains 230/307 and full readiness 178/307 (57.98%).
There are 38 price-only blockers: fixing price alone has a theoretical ceiling
of 216 full-ready issuers, not 255. The next isolated marginal blockers are
security (17) and accounting (12).

The sample audit persisted as `c9fa8807-bbc6-4d43-a7a1-9cabd5a88209` and passed
independent-process read-back with all issuer payloads unchanged. The full
comparison subsequently completed for 123 tickers; consolidated snapshot
`6d418683-6c09-4cfd-a67b-a4cc54718ddd` passed fresh-process read-back, provider
agreement, reordered resolution and a second database round-trip. Golden Five
remain 5/5 full-ready, with financial data and lineage unchanged. Regression:
136 distinct tests passed; changed-file lint passed; 53 unrelated global lint
findings remain. The FCA class/identity conflict for CRTE3 remains for review.
See [Phase 3 evidence and validation limits](MAGIC_FORMULA_HISTORICAL_PRICE_RESOLUTION.md).
The publication gate remains blocked; no public ranking was executed.
