---
schema: ai-docs/deferred-decision@1
id: D-007
title: GitHub protection eligibility
status: resolved
resolution: out_of_scope
task_gates:
  - E1-T5
resolved_by: [ADR-017]
---

# D-007: GitHub protection eligibility

- Status: resolved as out of scope by [ADR-017](../adr/ADR-017-no-enforced-branch-protection.md); E1-T5 is cancelled.
- State at resolution: `Flippylolz/WEF` was private and empty; the authenticated user had admin access, but GitHub returned `403` because private-repository rulesets/protected branches required an eligible paid plan.
- Later change: the repository became public and branch protection was enabled under [ADR-023](../adr/ADR-023-enforce-main-branch-protection.md). Native auto-merge remains out of scope.
- Continue: GitHub Actions CI, GHCR publishing, Dependabot pull-request creation, GitHub Actions secrets/variables, the custom scheduled label/check/bot-commit merge controller, and merged-PR-verified deployment.
