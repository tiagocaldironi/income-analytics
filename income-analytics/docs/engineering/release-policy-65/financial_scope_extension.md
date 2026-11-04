# Additive financial selection for the PR62 candidate

The initial assessment found that Treasury and executable-contribution tests ran
in Engineering/full Python, but their modules were absent from the explicit
Financial selection. This was a coverage-classification gap, not a reason to
waive financial certification or to stop running the tests in Engineering.

`ci/test-groups.json` now additionally selects these real modules for Financial:

- `tests/api/test_treasury.py`
- `tests/application/test_treasury.py`
- `tests/infrastructure/test_treasury_revisions.py`
- `tests/application/test_executable_contribution.py`
- `tests/application/test_global_contribution_allocator.py`
- `tests/api/test_b3_import_contract.py`

They remain selected in Engineering as before. Six routing regression controls
verify the dual selection and financial-critical classification. The financial
evaluator already rejects unexpected failures, missing mandatory coverage and
any skipped case; none of these rules was changed or weakened.

The actual expanded local Financial run reports **181 passed / 15 failed /
9 errors / 0 skipped**, including 77 additional passing cases. Mandatory coverage
is verified, with no unexpected failures. The original 24 failed/error cases
remain executed and blocked; the old 104-pass checkpoint is not represented as
Treasury financial certification. This run was made in the isolated worktree
before committing this additive scope change; the resulting commit requires its
own hosted CI evidence. No application code, financial fixture, immutable file,
manifest or financial hash was modified.
