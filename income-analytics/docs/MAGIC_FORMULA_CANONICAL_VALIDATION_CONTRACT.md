# Magic Formula — Canonical Validation Contract

## Scope and outcome

Implemented on 2026-09-16. Adapter remains
`CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE`; methodology remains
`MAGIC_FORMULA_STOCKS_V1`. No accounting rule or financial expected was changed.
The four existing V2 artifacts were adopted, not rematerialized. Petrobras remains
absent. Individual eligibility does not release the ranking.

## Impact analysis and worktree baseline

Before edits, the worktree was already dirty on
`codex/financial-projection-foundation`, HEAD
`5a9f7ca7215c14463061e963502e95ae863ca536`. Magic Formula modules, documents,
fixtures and migrations were untracked; shared database/API files had earlier edits.
The full inventory and source hashes are retained locally in
`tmp/canonical-contract-baseline/git-status-before.txt` and `hashes-before.json`.
A SQLite backup was captured at `tmp/canonical-contract-baseline/before.db`.
Original golden files are retained in that directory's `golden-before` subdirectory.
No reset, commit, broad cleanup or replacement of the database was performed.

Plan executed: inventory/backup; define identity and evidence contracts; add schema
and invariants; implement dimensional QA and eligibility; rehearse on a database
copy; test; apply the metadata-only migration; reopen and verify real persistence.

## Canonical issuer identity

`magic_formula_issuers` stores an internal UUID (`issuer_id`), normalized six-digit
`cvm_code`, fourteen-digit `cnpj`, `display_name` and presentation `slug`.
UUIDs are independently allocated and retained. Ticker, name, class and slug never
create the key. A CVM-code/CNPJ pair resolves an existing identity; disagreement on
either identifier is a conflict, not an alias fallback. Securities remain separate.
New snapshot writes require a registered UUID. Raw CVM parser DTO identifiers are
source locators, not persisted canonical issuer identities.

## Golden schema

Schema: `MAGIC_FORMULA_GOLDEN_V2`, following the project's named version convention.
The envelope contains:

- `schema_version`, `methodology_version`, `fixture_status`, `reference_date`;
- `issuer`: UUID, CVM code, CNPJ, display name and slug;
- `reference`: financial/market dates, effective price date and adapter version;
- `accounting`: metric rule plus original account-level components;
- `security`: explicit FCA identity, class, validity, form and source locator;
- `capital`: issued/treasury/outstanding quantities, units, derivation and locators;
- `prices`: COTAHIST ZIP/TXT/line/date/ticker/price locators;
- `expected`: independent accounting and derived expected amounts.

Existing accounting, prices and expected objects are unchanged. Source references
remain intact. Legacy identity values and the old fixture hash are retained as
provenance. `evidence_status` becomes `fixture_status`; fixtures stay
`READY_FOR_VALIDATION`, which describes evidence readiness, not a second approval.
`magic_formula_golden_fixtures` stores immutable content addressed by SHA-256.
Incomplete evidence may be registered for review; invalid identity/schema cannot.
The builder now requires a canonical issuer. The section gate uses the same
contract and the actual `prices`/`expected` section names.

## Snapshot and single validation authority

A snapshot is the financial artifact identified by its existing ID, canonical
issuer, financial and market reference dates, adapter, methodology, metrics and
lineage. `methodology_version` is an explicit structured column.
`validation_status` is authoritative only in the structured column:
`NOT_VALIDATED`, `PASS`, `FAIL`, `REVIEW_REQUIRED`.

New writes remove `metrics_json.validation_status` and cannot directly request
PASS. The migration removes it from existing V2 payloads. Historical V1 payloads
remain archival and ineligible, and cannot be used to infer a canonical decision.
After a formal decision, the snapshot's identity, dates, metrics and lineage are
sealed against modification. Corrections require a new artifact and new QA.

## Formal QA and validation

`magic_formula_formal_qa` is append-only. Every decision includes:
`id` (qa_decision_id), `snapshot_id`, `issuer_id`, `adapter_version`, `reference_date`,
`validated_at`, `snapshot_digest`, `fixture_hash`, eight dimensional statuses,
`final_status`, and dimension-specific `evidence_json`.

The required dimensions are accounting, security, capital, market, market_cap,
derived, lineage and snapshot_readback. All eight require explicit evidence.
A missing locator/value yields REVIEW_REQUIRED; demonstrated disagreement yields
FAIL. Final PASS requires all eight PASS. The repository accepts artifact IDs,
not caller-supplied dimension PASS flags.

QA checks recoverable golden/component evidence and compares it to the snapshot.
Accounting checks cover raw scale conversion and aggregate equality. Security and
capital checks cover issuer/class mapping, FCA locators/validity, issued/treasury
references and outstanding derivation. Market checks cover deterministic COTAHIST
locators, positive prices and temporal compatibility. Derived checks use independent
golden inputs, never alter expected values or production financial amounts.
Read-back closes and reopens SQLite connections and checks artifact stability.
The artifact hash excludes only mutable validation status, while including metrics,
lineage, identity, dates, methodology and adapter.

SQL constraints/triggers bind QA to the same snapshot/issuer/date/adapter and golden.
A trigger projects the latest QA final status into the snapshot column atomically.
PASS without a matching latest formal QA is rejected. QA and golden records cannot
be updated/deleted through the schema. Revalidation appends history; a later FAIL
or REVIEW_REQUIRED revokes eligibility rather than retaining an earlier PASS.
Legacy `company_normalization_validations` and its aggregate PASSes remain history;
they do not authorize validation or resolution.

## Resolution and ranking eligibility

There is no independently writable `issuer_status` field. RESOLVED is a canonical,
reproducible projection of the stored artifact and latest bound QA, exposed by
`CanonicalMagicFormulaRepository.eligibility` and the one
`is_ranking_eligible` policy. Provenance is the returned snapshot ID and QA ID.
It survives process/session restart because all inputs are persisted.

Eligibility requires valid golden identity/schema, the correct issuer and snapshot,
column PASS, all eight QA dimensions PASS, matching hashes, approved adapter and
methodology, and compatible financial/market dates. Financial eligibility requires
finite complete metrics, positive EBIT/market cap/EV/invested capital/EY/ROC,
VALID normalization and consolidated DFP. ITR is not treated as annual EBIT/TTM.
Negative/missing/nonfinite values never receive a zero fallback.

Failures report explicit reasons, including MISSING_GOLDEN,
MISSING_VALIDATED_SNAPSHOT, MISSING_FORMAL_QA, QA_NOT_PASS, QA_SNAPSHOT_MISMATCH,
ADAPTER_VERSION_MISMATCH, REFERENCE_DATE_MISMATCH, ISSUER_NOT_RESOLVED and
FINANCIAL_INELIGIBILITY. Evidence resolution and economic eligibility are distinct:
a fully validated artifact can still fail financial eligibility.

The activation gate delegates to this policy. The ranking service requires the
canonical repository and release gate before using its existing arithmetic; the
release gate remains closed. No ranking was executed. The API still returns empty
items, now with the consistent status VALIDATION_REQUIRED. No AVAILABLE promotion.

## Migration and compatibility

Alembic `0016_magic_formula_canonical_contract` adds the canonical tables and
methodology column. Existing V2 column PASS values are initially demoted to
REVIEW_REQUIRED, with their prior status, issuer and full metrics JSON saved in
`magic_formula_contract_migrations`. No aggregate QA is converted into dimensions.

`scripts/migrate_magic_formula_contract.py` explicitly requires a database path
and fixture directory. It selects exactly one existing V2 per sample issuer/CVM
code/date, registers the UUID, adopts identity metadata, versions the fixture,
persists content-addressed evidence, evaluates dimensional QA and reopens for
eligibility read-back. Repeating this operation is idempotent: the same artifact
and evidence keep the same decision ID. It never creates a financial snapshot.

The migration is forward-only to avoid silently deleting QA provenance. Restore
an audited pre-upgrade backup for rollback. Do not use the old rematerialization
script to migrate identities or approvals: its legacy callers now fail the
canonical identity requirement and require an explicit future adaptation.

The original four V1s, debug V1, old QA history and all non-Magic-Formula data were
retained. All nine existing snapshots kept their financial amounts and byte-exact
lineage. No snapshot ID was added or removed. New generic snapshot writes require
canonical identities; Phase 2 integration tests now register identities from CVM
code/CNPJ before persistence.

## Verified local read-back

Reference: 2025-12-31. Each row has eight dimensional PASSes, column PASS,
RESOLVED and individual ranking eligibility true; this does not open publication.

| Issuer | Canonical issuer_id | Existing snapshot_id | qa_decision_id |
|---|---|---|---|
| WEG | eb89bcc0-8295-45c6-91c7-8832ce58d76f | 56cffb48-edf2-493c-a775-de1aacab5685 | c5dcc8c5-f45f-431d-b1b9-5d53538d1482 |
| Suzano | 66ed46ae-3438-4bc9-a945-c4b7ba9df9b0 | 5efdb7bf-4433-45f9-b06c-38e09bd7baa5 | a8334600-73b8-4adc-bd56-2ab5ea277df1 |
| Rumo | e9b5b58f-ba9f-4708-8b45-c70315d588b9 | a827520a-f34b-4cb9-87ae-83d0b94a09ba | ec0a71e2-b3c8-4bb5-808c-120221cffe25 |
| Telefônica | e8e1f3bd-eab1-4ed0-a503-ced7d797d03e | d97ee807-7299-41b2-9026-d6ec7f926d70 | 09afeef3-23da-4d37-96fa-0dd7a216bfb7 |

Petrobras: MISSING_GOLDEN, MISSING_VALIDATED_SNAPSHOT, MISSING_FORMAL_QA,
NOT_RESOLVED, NOT_RANKING_ELIGIBLE. No issuer/fixture/snapshot/QA was created for it.
Validated/resolved issuers: four. Ranking gate BLOCKED; ranking INACTIVE.
The older recovery and multisector reports describe historical states and are
superseded by this contract for the four migrated V2 artifacts.

## Tests and lint

`test_magic_formula_canonical_contract.py` covers CONTRACT-001 through CONTRACT-015,
including cross-snapshot QA rejection, missing/invalid evidence, reference and
adapter mismatches, nonfinite/missing metrics, immutable artifacts, fresh-session
read-back, idempotent adoption of four artifacts and closed publication.
The existing CVM/market/security/monetary/Phase 2 regression suite is retained.

Relevant run before production adoption: 75 passed, zero failed/skipped.
Ruff passes on all files modified in this phase. Of the original 30 lint findings,
the 10 in the modified ranking module were corrected locally. The remaining 20
are outside this phase's modified files: 17 in the old rematerialization script,
two in migration 0015 and one in the legacy golden comparator. No broad autofix.

## Remaining limitations and next action

The canonical contract does not reconstruct Petrobras, expand sector/universe
coverage, implement a ranking snapshot or approve production ranking. The four
fixture units and locators are issuer-specific historical evidence, not a universal
shares-scale inference. Formal QA checks the retained golden/snapshot evidence;
this phase does not download new source archives or convert legacy aggregate QA
into source proof. The previous state recovery separately verified these locators
against the cached official archives.

Next: review this migration/evidence contract, then authorize a separate Petrobras
recovery and final ranking activation phase. Keep the current gate closed.

## Finalization after real local migration

Migration applied: `0016_magic_formula_canonical_contract`, without errors.
The migration process exited and all repository connections were closed. A new
Python process then read issuer, stored/file golden, snapshot, bound dimensional
QA and canonical resolution/eligibility twice using independent connections.
Both read-backs matched. Fixture and snapshot hashes matched the QA bindings;
all four V2 JSON payloads had no validation_status field.

Financial regression compared exact stored values for EBIT, cash, short/long debt,
net debt, OCA/OCL/NWC, fixed assets, invested capital, market cap, EV, EY and ROC.
All values matched the before.db backup. Snapshot lineage remained byte-identical;
golden accounting/prices/expected and original capital evidence fields were
preserved, except the explicitly migrated issuer identity metadata.
No other existing table changed, except Alembic revision and the authorized V2
snapshot metadata. All nine original snapshot IDs remain present.

Post-migration test command:

```powershell
python -m pytest tests/application tests/infrastructure/test_b3_cotahist_market_data.py -q -p no:cacheprovider --basetemp=tmp/pytest-canonical-contract-final
```

Result: **92 passed, 0 failed, 0 skipped**. No ranking calculation was invoked.
Final Ruff check: **0 findings in the 13 changed Python files**; **20 pre-existing
findings** remain in unchanged relevant files (0015: 2; old rematerializer: 17;
legacy golden comparator: 1). No global cleanup was performed.

Final read-back evidence: `tmp/canonical-contract-baseline/final-readback.json`.
Dimensional migration evidence: `tmp/canonical-contract-baseline/migration-result.json`.
Lint details: `tmp/canonical-contract-baseline/final-lint.json`.
Backup: `tmp/canonical-contract-baseline/before.db`.

### Pre-existing versus this phase

PRE_EXISTING_CHANGES: full dirty-worktree inventory recorded before edits in
`git-status-before.txt`; shared database.py/models.py and the accounting adapter
have the same hashes as at phase start. HEAD and branch are unchanged. No commit.

NEW_CHANGES_THIS_PHASE:

- New `application/magic_formula_contract.py` and `magic_formula_formal_qa.py`.
- New `infrastructure/magic_formula_contract_repository.py`.
- New Alembic migration 0016 and `scripts/migrate_magic_formula_contract.py`.
- New `tests/application/test_magic_formula_canonical_contract.py`.
- Targeted updates to snapshot repository, golden builder, lineage/activation gates,
  ranking entry guard, investment-tools status and Phase 2 integration identity setup.
- Versioned envelopes/identities in four golden JSON files; no expected value change.
- This contract report and local audit artifacts/backup.
- Applied local schema, four issuer identities, four immutable golden records and
  four snapshot-bound dimensional QA decisions; existing V2 metadata normalized.

Consistency defects remaining within the four migrated V2 artifacts: none found.
Legacy V1 and aggregate-QA records remain historical only. Petrobras remains an
intentional missing-artifact negative control. Ranking publication remains blocked.
Next action is review of this completed migration report; no further phase started.
