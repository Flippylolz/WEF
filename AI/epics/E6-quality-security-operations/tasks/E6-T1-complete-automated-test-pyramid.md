---
schema: ai-workflow/task@1
id: E6-T1
epic: E6
title: "Complete automated test pyramid"
status: in_progress
revision: 1
priority: P1
size: L
milestone: M3
dependencies: [E4-T3, E5-T3]
requirement_ids: [P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008]
decision_ids: [ADR-012, ADR-013, ADR-016]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E6-T1-complete-automated-test-pyramid.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T17:16:12Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T17:16:12Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 8
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T17:16:12Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T17:16:12Z"
  evidence:
    - "E4-T3 | done | offer detail API"
    - "E5-T3 | done | offer detail/media gallery UX"
branch:
  required: true
  name: feat/E6-T1-automated-test-pyramid
  task_id: E6-T1
  one_task_only: true
  created_at: "2026-08-20T17:16:12Z"
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E6-T1: Complete automated test pyramid

## Outcome

Close the spike-confirmed browser/e2e gap with Chromium Playwright critical-path coverage for grouped location selection, offer list/detail (verified and missing links), and API error states — on synthetic fixtures with no unreviewed personal data — while retaining existing unit/integration/contract/a11y layers.

## Scope

- Add `@playwright/test` as a web **devDependency** with Chromium-only CI.
- Route-mock `/api/v1/*` using invented M1 synthetic payloads.
- Cover pin/list → offer detail, missing verified source link, and map API error states.
- Wire `pnpm --filter web test:e2e` into Makefile and CI.

## Out of scope

- Firefox/WebKit matrix, load/performance suites, Dependabot (E1-T6/T7), Prometheus/OTel, live historical content assertions, product feature work.

## Work

- Playwright config with `webServer` against `next start` (or `next dev` locally with reuse).
- Synthetic fixture module + critical-path specs.
- CI: install Chromium browsers, build web, run e2e.

## Acceptance criteria

- [ ] Tests cover filter-preserving error states, grouped pin/detail flow, verified/missing links.
- [ ] Fixtures contain no unreviewed personal data.
- [ ] Playwright Chromium job is required in CI alongside existing vitest/pytest/contract checks.

## Dependencies and gates

- Dependencies: E4-T3, E5-T3 (`done`).
- Implementation plan revision 8 authorizes this task.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).

## Risks and notes

- MapLibre may fall back when tiles/style are slow; list-driven selection remains the authoritative critical path.
- Keep browser installs Chromium-only to bound CI time/cost.

## Rollback

Remove the Playwright CI step and web e2e tooling; lower pyramid layers remain.
