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
- Current state: `Flippylolz/WEF` is private and empty; the authenticated user has admin access, but GitHub returns `403` because private-repository rulesets/protected branches require an eligible paid plan.
- Constraint: do not claim `main` is protected or enable native protection-dependent auto-merge.
- Continue: GitHub Actions CI, GHCR publishing, Dependabot pull-request creation, GitHub Actions secrets/variables, the custom scheduled label/check/bot-commit merge controller, and merged-PR-verified deployment.
