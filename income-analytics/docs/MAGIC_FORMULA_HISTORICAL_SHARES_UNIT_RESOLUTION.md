# Historical Shares Unit Resolution — Phase 2

`HISTORICAL_SHARES_UNIT_SPIKE = PASS`, with document-bound generalization.
271 of 282 pending units were resolved; 11 remain unavailable at the source.
Complete data readiness increased from 5 to 178 issuers (178/307 = 57.98%).
This result does not authorize publication or ranking.

## Root cause and documentary evidence

The prior `UNIT_UNRESOLVED` status was justified: the pinned CVM DFP capital CSV
contains raw ON/PN issued and treasury quantities but omits their economic scale.
The official dataset layout declares `bigint`, precision 19, scale 0; this is a
numeric storage type, not evidence that a reported quantity means individual shares.
The quantity fields' description/domain are blank and there is no share-unit column.

The original CVM document **does preserve the missing metadata**. It is accessible
through `LINK_DOC` in the annual DFP document index, matched by CNPJ, reference and
version. Its main XML contains `DadosDFP/EscalaQtdAcoes`; the descriptor contains
`CodigoEscalaQuantidade`; the rendered capital page names `Unidades` or `Mil`.
This is a source-export metadata gap and a missing enrichment rule, not a decimal
parser error or metadata silently discarded from a CSV column.

| Requested diagnostic | Finding |
| --- | --- |
| SOURCE_DATASET | CVM DFP, capital composition and original document package |
| SOURCE_FILE | `dfp_cia_aberta_2025.zip/dfp_cia_aberta_composicao_capital_2025.csv` |
| SOURCE_FIELD | `QT_ACAO_ORDIN_CAP_INTEGR`, `QT_ACAO_PREF_CAP_INTEGR`, `QT_ACAO_ORDIN_TESOURO`, `QT_ACAO_PREF_TESOURO` |
| SOURCE_UNIT_FIELD | Absent from CSV; `DadosDFP/EscalaQtdAcoes` in original XML, `CodigoEscalaQuantidade` in descriptor |
| CURRENT_PARSER_BEHAVIOR | Decimal raw quantities; no guessed multiplier |
| CURRENT_REASON_FOR_UNRESOLVED | No matching canonical capital-unit proof in Phase 1 |
| SOURCE_UNIT_SEMANTICS | Explicit individual shares or thousands of shares, selected per document |

Official evidence:

- [CVM DFP metadata](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/META/meta_dfp_cia_aberta_txt.zip), preserved in `tests/fixtures/cvm/shares_unit_v1`.
- [CVM circular 02/2011, section 1(a)](https://www.gov.br/cvm/pt-br/assuntos/noticias/2011/oficio-circular-cvm-sep-n002-2011---orientacoes-gerais-sobre-o-preenchimento-dos-formularios-dfp-e-itr-29f5c5651de24daf90fe91da46a95fca/), which distinguishes share scale chosen for the filing from monetary scale.
- Exact historical documents from the CSV's `LINK_DOC`, with URL, document ID,
  version, reference, original ZIP/XML/PDF hashes and capital-page text retained.

The existing `CvmCapitalCompositionParser`, `CvmCapitalStructureAdapter`,
Accounting Registry, canonical contract and ranking engine remain unchanged.
Phase 1's universe source reader also remains unchanged. The new source reader
`cvm_historical_shares_document.py` enriches the unit evidence outside those contracts.

## Frozen stratified sample

The sample was selected before generalization from the 282 eligible issuers with
`UNIT_UNRESOLVED`: 25 new cases plus all five controls, total 30. Greedy feature
coverage with stable UUID tie-breaking covers sector, ON/ON+PN/PN/units, multiple
securities, treasury presence, total-assets terciles (plus unknown) and different
raw digit patterns. The raw quantities' size is used only to diversify the sample.
No multiplier or status is derived from that size.

`tmp/shares-unit-phase2/sample.json` records the selection and strata.
The versioned fixture copy and manifest are in `tests/fixtures/cvm/shares_unit_v1`.
All 30 cases resolved in sample validation (23 Unidade, 7 Mil), with zero unresolved/review cases after
retrying transient CVM download errors. Both literal unit categories occur. The
sample approval artifact is `tmp/shares-unit-phase2/sample-accepted` and predates
the expanded acquisition.

Cross-evidence compares the source CSV with original document XML, descriptor and
PDF. These are distinct representations of the same filing, not independent
economic observations. They supply the missing explicit unit directly; there is no
need to infer it through present-day B3 quantities or expected market capitalization.
FCA remains the independent historical security/class mapping source. No current B3
quantity replaces a historical quantity and no corporate-action adjustment is made.

## Versioned rule and boundaries

`MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1` implements `EXPLICIT_SOURCE_UNIT` only.
No dataset-wide default, magnitude inference or issuer-specific exception is used.

Resolution requires all of the following:

1. CVM code, CNPJ, date and version agree across CSV and original document.
2. Main XML and descriptor agree on the quantity-scale code.
3. That code agrees with the literal PDF label: 1/Unidades or 2/Mil.
4. PDF quantities for ON, PN, totals and treasury match their XML counterparts.
5. XML class quantities match the original CSV raw amounts.
6. Issued/treasury quantities are finite and nonnegative, treasury does not exceed
   issued, and Decimal multiplication produces an integral number of shares.

Multiplier 1 maps explicitly declared individual shares; multiplier 1000 maps
explicitly declared thousands. Missing evidence stays `UNIT_UNRESOLVED`, conflicting
identity/quantity/metadata becomes `REVIEW_REQUIRED`, and unsupported/missing
document structure becomes `SOURCE_SCHEMA_ERROR`. Only `RESOLVED` may provide
normalized capital quantities. Archive digest conflicts abort rather than pass.

Outstanding remains `(issued - treasury)` per ON/PN class. Units are not treated as
shares and are never added to underlying class totals. The existing security/unit
mapping and historical price gates remain intact. Resolving quantity scale does
not repair an unknown unit composition or missing class price.

Amounts declared in thousands retain `source_precision = THOUSAND_SHARES`. Their
normalization preserves the disclosed precision and does not reconstruct any
unreported sub-thousand remainder. This limitation is explicit in lineage.

## Lineage and persistence

Each resolution preserves issuer UUID, class, quantity kind, reference date, raw
quantity, raw unit metadata, multiplier, normalized integral quantity, method,
policy version, dataset, source file, CSV locator and original-document locator.
Document evidence includes ID, URL, acquisition time, hashes, XML code and the full
capital-page text. Unknown cases retain their missing-evidence reason.

Resolution and readiness are attached to a new immutable UniverseSnapshot. The
original Phase 1 snapshot is not edited. Methodology eligibility, canonical
resolution, financial snapshots, golden fixtures and formal QA are not rewritten.
`FULL_DATA_READY` remains a discovery/readiness result, not permission to rank.

Persistence committed and closed its connections. After that process exited, a
separate process opened fresh connections, compared every resolution and coverage
field and compared canonical tables with `tmp/shares-unit-phase2/before.db`: PASS.
Detailed final measurements, sample rows, gap transitions and audit outcome follow.

## Reproduction

```powershell
python scripts/sample_historical_shares_units.py --universe-id 22db1605-56e5-48ed-985b-4b611dba3a5d --output tmp/shares-unit-phase2/sample.json
# Run the collector in an environment containing pypdf; validate this sample first.
python scripts/fetch_historical_shares_documents.py --sample tmp/shares-unit-phase2/sample.json --output tmp/shares-unit-phase2/documents
python scripts/validate_historical_shares_units.py --universe-id 22db1605-56e5-48ed-985b-4b611dba3a5d --sample-path tmp/shares-unit-phase2/sample.json --evidence-directory tmp/shares-unit-phase2/documents --output tmp/shares-unit-phase2/sample-accepted
```

Only after sample acceptance may collection expand with `--count 282`; the same
validator applies the rule to every pending eligible issuer, requiring each one's
own matching evidence. `--persist` creates the new snapshot. The collector uses
three concurrent requests and caches acquired documents. Network errors are retained
as acquisition failures and cannot supply a unit.

`TOOL_STATUS = VALIDATION_REQUIRED`; `RANKING_STATUS = INACTIVE` throughout.

## Final persisted evidence

- Phase 2 universe snapshot: `f63e9ed8-8103-4f2b-970b-925fd1c2e0e7`.
- Parent Phase 1 snapshot: `22db1605-56e5-48ed-985b-4b611dba3a5d` (unchanged).
- Store: `data/magic_formula/universe_snapshots.db`.
- Durable source evidence: `data/magic_formula/shares_unit_v1` (276 documents,
  acquisition manifest and frozen sample).
- Export and measured run: `tmp/shares-unit-phase2/real`.
- Independent read-back: `tmp/shares-unit-phase2/independent-readback.json`.
- [All 30 sample cases, raw quantities, multipliers and normalized outstanding](../tmp/shares-unit-phase2/sample-results.md).
- Complete per-issuer proof URLs, hashes, XML field locators and PDF capital page
  are embedded in each resolution in the persisted snapshot.

The first expanded collection obtained 227 documents and recorded 60 failures.
A second pass reused the cache and recovered 49, leaving 11 failures. No failure
was converted into a default unit. The 276 available documents comprise all five
controls and 271 newly resolved issuers: 180 declare individual shares and 96
declare thousands. There were no conflicting-unit or unsupported-schema decisions
among those documents; `UNIT_REVIEW_REQUIRED_AFTER = 0`.

Generalization is `DOCUMENT_BOUND_ONLY`: the same rule was evaluated for all 282
pending issuers, but each needed its own evidence. A sample-level observation of
code 1 or 2 was not used as a substitute for a missing document/PDF label.

Two sample examples demonstrate why size is not a rule: Aliperti reports 6,250 ON
shares in Unidades (multiplier 1), while Tekno reports 1,587 ON in Mil (multiplier
1000). LPS reports 147,555 issued ON and 10,267 treasury ON in Mil, giving
137,288,000 outstanding. These values follow the explicit source labels.

Petrobras remains exactly 7,442,231,382 PETR3/ON and 5,446,501,379 PETR4/PN,
with zero treasury in both classes. All five controls retain their original
canonical financial amounts, source lineage, snapshots, QA and eligibility.

## Before and after coverage

Independent dimensions are measured over the 307 methodology-eligible issuers:

| Dimension | Before | After | After coverage |
| --- | ---: | ---: | ---: |
| Identity resolved | 307 | 307 | 307/307 = 100% |
| Accounting components ready | 256 | 256 | 256/307 = 83.39% |
| Security mapping ready | 269 | 269 | 269/307 = 87.62% |
| Capital ready | 5 | 276 | 276/307 = 89.90% |
| Historical price ready | 230 | 230 | 230/307 = 74.92% |
| Full data ready | 5 | 178 | 178/307 = 57.98% |

The cumulative funnel, requiring every previous stage, is distinct:

| Stage | Before | After |
| --- | ---: | ---: |
| Candidate issuers | 360 | 360 |
| Methodology eligible | 307 | 307 |
| Identity resolved | 307 | 307 |
| Accounting ready | 256 | 256 |
| Security ready | 226 | 226 |
| Capital ready | 5 | 216 |
| Market price ready | 5 | 178 |
| Full data ready | 5 | 178 |

Capital + security + price readiness, without the accounting requirement, reaches
190 issuers. This measures ability to form the class-specific sum of outstanding
shares times historical price; no new fundamental snapshot or ranking is produced.
173 issuers gained full readiness; the other 98 newly resolved units retain another
gap. Methodology remains 307 eligible, 35 excluded, and 18 sector-review cases.

## Gap migration and unresolved cases

Reason incidence overlaps; the counts below must not be summed as distinct issuers.

| Reason | Before | After |
| --- | ---: | ---: |
| UNIT_UNRESOLVED | 282 | 11 |
| NO_REFERENCE_PRICE | 77 | 77 |
| NO_ACCOUNTING_DATA | 51 | 51 |
| NO_VALID_SECURITY | 38 | 38 |
| NO_CAPITAL_DATA | 20 | 20 |
| TEMPORAL_CONFLICT | 6 | 6 |

Top three remaining blockers: historical price (77), accounting (51), security
mapping (38). Primary status partition: 178 ELIGIBLE + 123 DATA_GAP + 35 EXCLUDED +
24 REVIEW_REQUIRED = 360. The 24 review cases are pre-existing sector/temporal
cases; no unit-review case was added.

The deterministic primary-gap convention is the first sorted reason, as in Phase 1.
Transitions among eligible issuers are: UNIT_UNRESOLVED to no gap: 173; unchanged
UNIT_UNRESOLVED: 10; unchanged accounting: 51; unchanged reference price: 50;
unchanged security: 18; no gap to no gap: 5. The complete per-issuer before/after
reason arrays are persisted. A unit may disappear without changing the primary gap
because price/accounting/security already preceded it in this audit ordering.
The after primary-gap partition totals 129 = 307 - 178, with no double counting.

The 11 unresolved units are source-acquisition gaps, not inferred scale conflicts:

| Issuer | CVM document ID |
| --- | --- |
| Méliuz | 155473 |
| Grazziotin | 155360 |
| Armac | 155869 |
| Log Commercial Properties | 154714 |
| Renova Energia | 155951 |
| Eternit | 155704 |
| Cury | 155237 |
| Aeris | 155464 |
| Unifique | 155459 |
| Usiminas | 154757 |
| Bemobi | 155508 |

The acquisition manifest preserves the exact errors: seven server responses
reporting insufficient disk space, two HTTP 500 responses, one invalid/incomplete
ZIP, and one connection timeout. The disk-space message came from the CVM response;
it was not a local disk failure. All remain blocked until valid evidence is obtained.

## Independent audit, tests and performance

`UNIT_RESOLUTION_READBACK = PASS`; `DETERMINISM_STATUS = PASS`;
`LINEAGE_STATUS = PASS`; `GOLDEN_FIVE_REGRESSION = PASS`.
The independent process compared the entire stored document to its export and
reapplied readiness from its stored resolutions to the unchanged parent snapshot.
It also checked all canonical table rows before/after for exact equality and reran
the five eligibility projections in new connections. Counts remain 5 issuers,
5 golden fixtures, 10 financial snapshots and 5 formal QA decisions.

Canonical before/after digest:
`ad06071aac9e8802cb2aa6b045a2a881e8c25ed9a86deae9b17ab2ab6c5846fd`.
Resolution-lineage digest:
`38583b5a3d2ef77afccee9f35955f7c1f291fca15b0704f609f4af26c752953a`.

All SHARES-UNIT-001 through SHARES-UNIT-020 requirements have test coverage, including
official fixtures, class/treasury preservation, unknown/conflicting evidence,
determinism, persistence, no ranking call, and frozen engine/contract hashes.
The final relevant regression suite passed **201 tests, zero failures**, in 165.20 s:

```powershell
python -m pytest tests/application tests/infrastructure/test_b3_cotahist_market_data.py -q --basetemp tmp/shares-unit-phase2/pytest-final -p no:cacheprovider --junitxml tmp/shares-unit-phase2/tests-final.xml
```

| Operation | Measured runtime |
| --- | ---: |
| Final sample validation | 5.108 s |
| Full-universe resolution against available evidence | 49.277 s |
| Coverage and gap recomputation | 0.082 s |
| First expanded acquisition/extraction pass | 2100.420 s |
| Retry pass, including cache reuse | 555.186 s |

Acquisition/extraction dominates elapsed time. No financial inference or broad
normalization was introduced to bypass this cost. Sampling and acquisition are
recorded separately from unit-policy and coverage runtime.

Changed Python files: Ruff PASS, zero findings. Global `src tests scripts alembic`
lint remains at 71 pre-existing findings, preserved. Evidence is in
`tmp/shares-unit-phase2/tests-final.log`, `tests-final.xml` and `global-lint-final.json`.
The six new Python files are the policy, source reader, three CLI scripts and tests.
This phase also adds fixtures, source evidence and this report, and appends Phase 2
results to the Phase 1 report. All earlier source/engine/contract/golden files match
their pre-phase hashes. No reset, commit or ranking publication occurred.

`OPEN_DEFECTS = 0` known implementation defects; 11 external acquisition gaps remain.
Recommended next action: address the 77 historical-price gaps, then accounting (51)
and security mapping (38), while retrying the 11 unavailable CVM documents once the
source service recovers. Public ranking stays inactive until a separate production
quality/publication gate is approved.
