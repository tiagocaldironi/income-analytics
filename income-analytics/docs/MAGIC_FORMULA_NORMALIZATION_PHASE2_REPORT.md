# Magic Formula Stocks — Phase 2 Integration Gate

## Status

- Accounting integration: automated offline coverage implemented.
- DEV_STATUS: `HUMAN_REVIEW_REQUIRED`
- TOOL_STATUS: `VALIDATION_REQUIRED`
- Ranking remains disabled. Accounting validation does not satisfy the independent
  capital/security/price/component release gate.

## Reproducible coverage

`tests/application/test_magic_formula_phase2_integration.py` exercises both DFP
2025-12-31 and ITR 2025-09-30 for Votorantim Cimentos, Vale, Localiza Fleet, MRV and
Ambev, the five-sector sample documented in the real-data validation report.
Versioned source excerpts and provenance are in `tests/fixtures/cvm/phase2_v1`.
They retain official rows from the existing archive cache; its original retrieval
timestamp is unknown. SHA-256 pins both source archives and excerpt bytes.

| Check | Automated evidence |
|---|---|
| Clean database | Real Alembic base-to-head upgrade, current revision and snapshot unique constraint |
| 0014-to-current | Seed an import audit row at 0014, copy database, upgrade copy, verify row and unchanged original |
| Official DFP and ITR | Source hash verification, production ZIP parser, explicit consolidated issuer/date and YTD selection |
| Five-sector normalization | All seven metric mappings, fixed EBIT expectations, BRL thousand scale, eight component lineage entries |
| Assembler and persistence | Fresh-connection reads, Decimal metrics and complete lineage round trip, identical snapshot id on repeat |
| Validation persistence | Expected/actual/difference/PASS reloaded from database |
| Rejection checks | Missing component, duplicate account, mixed scope/issuer/date/type, mismatched period end, unknown scale |
| ITR ambiguity | Quarter plus YTD rejected instead of summed; no TTM construction |
| Ranking gate | Five accounting-valid issuers with unresolved capital remain VALIDATION_REQUIRED and zero ranked |

The adapter now requires exactly one row per required account and consistent
statement type/period end. Existing accepted V2 metric formulas are unchanged;
ambiguous or incomplete inputs fail closed.

Assembler tests use a synthetic market cap solely for persistence integration.
No market/security evidence or multisector RESOLVED status is fabricated. The
separate blockers in `MAGIC_FORMULA_MULTISECTOR_RESOLUTION_REPORT.md` remain.

Run offline:

```powershell
python -m pytest tests/application -q -p no:cacheprovider --basetemp=tmp/pytest-phase2-review
```
