# Verified Dependabot merge evidence

Coverage work exposed four conflicts between the merge controller and the existing
repository merge rules: skipped/neutral required checks could authorize a merge,
completed checks without results were promoted to success, an empty commit list
could pass authorship checks, and missing GitHub identities were filled from commit
display names. Synthetic regressions reproduced five failing assertions before
the fix; no GitHub operation was performed by those probes.

## Corrected eligibility

A required check must have an explicit `SUCCESS` result. A completed check without
a result remains unverified. Existing optional-check handling and the required
check-name allowlist are preserved. Commit authorship evidence must be nonempty,
and every author/committer must match the existing verified GitHub bot allowlists.
Commit display names provide no identity authorization.

The controller still requires the owner-applied label, direct patch/minor update,
current main, all healthy checks, known mergeability and an immediate second
snapshot. Head changes, label/check changes and merge-command refusal remain
recorded as reject/defer outcomes. The merge command retains squash, branch
cleanup and the exact expected-head argument.

## Regression and coverage evidence

Ten new cases plus the existing 21 controller tests pass. All 290 statements and
128 branch paths measure exactly 100%, with zero exclusions or coverage pragmas.
The file joins the completed operational floors, and a deliberate policy fault
rejects dropping that floor.

Tests assert required-check refusal, missing commit evidence and unavailable
conclusions/identities; malformed check configuration, unknown versions/states,
label actor history and mergeability; API projection and process diagnostics;
second-snapshot races, simulated merge errors, dry-run/owner options, summary output
and a real invalid-repository CLI entrypoint. Every GitHub command is injected or
mocked. The real entrypoint rejects its invalid repository before any GitHub call.
No real pull request is listed, changed or merged by the tests.

This corrects the existing [E1-T7 successful-check and bot-only acceptance
conditions](../epics/E1-repository-developer-foundation/tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md)
and [ADR-023's successful-CI requirements](../decisions/adr/ADR-023-enforce-main-branch-protection.md),
under the owner's coverage request. Required CI, owner allowlists, labels, update classes, branch protection,
application contracts and production dependencies retain their existing boundaries.
Remaining operational Python, shell and substantive embedded Python still require
coverage before the overall goal can be completed.

## Validation

The full locked `make format-check lint typecheck test contract-check quality-gates
compose-config` passes: 2,266 backend and 355 frontend tests retain 100%, and all 288
operational tests pass with 34 independent 100% file floors. The focused 31 tests,
strict Ruff/mypy, Markdown links and Git whitespace checks also pass.

The comparable native operational audit, including the same existing release,
topology and rollback proof drivers, rises from 81.89% to 83.86%. It measures all
4,661 statements and 1,440 branch paths after removing the unsafe inference paths;
717 lines and 268 branch paths remain uncovered. Its reports stay ignored, and
remaining operational Python, shell and substantive embedded code stay in scope.
