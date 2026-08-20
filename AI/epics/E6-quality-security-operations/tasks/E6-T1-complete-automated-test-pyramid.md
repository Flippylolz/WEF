---
schema: ai-workflow/task@1
id: E6-T1
epic: E6
title: "Complete automated test pyramid"
status: done
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
  pull_request: "https://github.com/Flippylolz/WEF/pull/136"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-20T17:28:16Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/136"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/136 (Playwright Chromium critical path + CI)"
    - "Local e2e: 3 passed (verified Telegram link, missing link fallback, map API error)"
    - "Synthetic fixtures only; NEXT_PUBLIC_WEF_DISABLE_MAP=1 for headless CI without WebGL"
    - "Existing vitest (67) + backend/contract layers retained as lower pyramid"
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

- Playwright config with standalone Next server for e2e.
- Synthetic fixture module + critical-path specs.
- CI: install Chromium browsers, build web with map canvas disabled, run e2e.

## Acceptance criteria

- [x] Tests cover filter-preserving error states, grouped pin/detail flow, verified/missing links.
- [x] Fixtures contain no unreviewed personal data.
- [x] Playwright Chromium job is required in CI alongside existing vitest/pytest/contract checks.

## Dependencies and gates

- Dependencies: E4-T3, E5-T3 (`done`).
- Implementation plan revision 8 authorizes this task.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).

## Risks and notes

- Headless Chromium lacks WebGL2; e2e builds set `NEXT_PUBLIC_WEF_DISABLE_MAP=1` so list/detail remains the critical path while MapLibre `onError` still fails closed in production builds.
- Keep browser installs Chromium-only to bound CI time/cost.

## Rollback

Remove the Playwright CI step and web e2e tooling; lower pyramid layers remain.
