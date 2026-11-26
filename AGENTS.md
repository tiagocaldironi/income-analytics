# Repository working instructions

- Keep changes focused on the requested outcome. Preserve existing worktrees, local changes, data and credentials.
- Validate changed behavior with targeted checks. Use broader checks when required or justified by the risk. Report existing, unrelated failures separately from regressions introduced by the change.
- Group related, locally validated fixes before pushing. Open pull requests against `develop` unless the task specifies a different base.
- Inspect check summaries and bounded excerpts for failed steps. Avoid habitual polling, full log downloads and reruns without a material change or a diagnosed transient failure.
- If CI monitoring or completion is part of the requested task, follow the existing run to the requested outcome. Report meaningful changes rather than repeating unchanged status. If the task ends at PR creation, state which checks are still pending.
- Respect branch protection and required checks. Merge and deploy only when authorized. Verify the actual result before reporting integration or publication.
