# AGENTS.md — repository-wide Codex policy

## Primary objective
Deliver the requested product change with the smallest safe diff. CI/CD is a validation mechanism, not a separate ongoing assignment. Follow more specific instructions in nested AGENTS.md files.

## Token-efficient CI workflow
1. Identify acceptance criteria and affected files before editing.
2. Run focused local checks for changed behavior; run broader checks when risk warrants them.
3. Open a PR against `develop` and report its URL, commit and checks status.
4. Do not continuously poll GitHub Actions. Avoid `gh run watch`, `gh pr checks --watch`, repeated `gh run view` or sleep/retry loops unless the user explicitly requests monitoring.
5. Do not fetch entire CI logs by default. If investigating a failure, inspect failed jobs/steps and only relevant log excerpts.
6. After opening a PR, stop the session with CI marked pending when appropriate. Never claim pending checks passed.
7. A failed check can be diagnosed in a separate focused task. Limit attempts to two materially different fixes; then report the blocker and next action.
8. Do not auto-merge or deploy. Required checks and protections must pass before integration.

## Scope and quality
- Fix regressions introduced by the change; record unrelated pre-existing failures separately.
- Do not silently bypass required tests, security gates, or branch protection.
- Avoid unrelated global refactors, mypy cleanups, dependency upgrades or pipeline rewrites.
- Preserve data, credentials, existing worktrees and uncommitted changes; do not run destructive cleanup.
- Report implementation, files changed, targeted tests, known risks, outstanding checks and blockers.

## Completion states
- **Implemented / CI pending:** code and targeted tests ready; PR checks not yet complete.
- **Blocked:** required check, regression, security or data-integrity concern unresolved.
- **Integrated:** only after verified merge and required checks.
