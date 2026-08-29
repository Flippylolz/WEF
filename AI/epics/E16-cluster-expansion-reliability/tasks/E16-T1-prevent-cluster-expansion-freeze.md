---
schema: ai-workflow/task@1
id: E16-T1
epic: E16
title: "Prevent cluster expansion from freezing the map"
status: done
revision: 1
priority: P0
size: S
milestone: M4
dependencies: []
requirement_ids: [P-004]
decision_ids: [ADR-002, ADR-004]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E16-T1-prevent-cluster-expansion-freeze.md
  promoted_by: "Codex agent under owner instruction"
  promoted_at: "2026-08-29T06:02:08Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent under owner instruction"
  verified_at: "2026-08-29T06:02:08Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Codex agent under owner instruction"
  verified_at: "2026-08-29T06:08:03Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex agent under owner instruction"
  verified_at: "2026-08-29T06:02:08Z"
  evidence: []
branch:
  required: true
  name: bugfix/E16-T1-cluster-expansion-freeze
  task_id: E16-T1
  one_task_only: true
  created_at: "2026-08-29T06:08:03Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/194
completion:
  completed_by: "Codex agent under owner instruction"
  completed_at: "2026-08-29T06:31:40Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/194"
  evidence:
    - "PR #194 merged as b09314d104045076e727e183d3f40819c6fcaa48 after Backend, Frontend and contract, Repository safety, Runtime images, and Coverage badge passed"
    - "Release and deploy production run 33238276936 passed candidate verification, immutable image publication, activation, and deployment verification"
    - "Production version b09314d: two numbered clusters expanded; later zoom, pan, and pin selection worked with no browser console errors"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E16-T1: Prevent cluster expansion from freezing the map

## Outcome

Selecting a numbered map cluster expands it without throwing a MapLibre camera
error, corrupting the canvas, or disabling subsequent map interaction.

## Scope

- Validate copied cluster center and expansion-zoom values before camera use.
- Replace the failing interpolated cluster camera path with a reliable
  non-interpolated public camera operation.
- Cover valid and rejected/invalid expansion targets in focused component
  tests.
- Verify representative cluster clicks and subsequent drag, built-in zoom, and
  unclustered-pin activation in a real browser.

## Out of scope

- Dependency upgrades/downgrades, MapLibre internals, map style/provider,
  clustering radius/counts, backend contracts, layout, and listing behavior.

## Affected modules and contracts

- `apps/web/src/components/warsaw-map.tsx` — cluster click camera behavior.
- `apps/web/src/components/warsaw-map.test.tsx` — success and failure-path
  component coverage.
- No backend, OpenAPI, generated-client, database, configuration, or dependency
  changes.

## Acceptance criteria

- [x] Clicking multiple numbered clusters expands each cluster and leaves the
      map responsive to pan, zoom, and later cluster/pin activation.
- [x] No singular-matrix/`_calcMatrices` error is emitted during cluster
      activation in the real-browser verification.
- [x] Missing, rejected, and non-finite expansion targets do not invoke a
      camera update or surface an unhandled rejection.
- [x] Unclustered pin selection, URL viewport reporting, reduced-motion
      behavior, and existing map/list coordination remain green.
- [x] Applicable format, lint, typecheck, frontend tests/coverage, production
      build, and real-browser checks pass.

## Test plan

- Vitest: valid expansion, copied finite coordinates, rejected source query,
  invalid zoom/coordinates, unclustered selection, and move-end reporting.
- Existing frontend lint/typecheck/unit/coverage/build checks.
- Real browser: activate at least two numbered clusters, then pan, use the
  built-in zoom control, and activate an unclustered pin; inspect console for
  camera/matrix failures.

## Rollout and rollback

- Standard frontend image release after merge to `main`; no migration or
  configuration sequencing.
- Roll back to the previous web image if production cluster interaction or
  unrelated map behavior regresses.

## Risks and notes

- Mocked component tests cannot prove render-loop stability, so browser
  verification is mandatory.
- If a dependency change becomes necessary, stop and revise/reapprove the spike
  and implementation plan.

## Ready checklist

- [x] Authoritative under `tasks/`; promoted after spike revision 1 approval.
- [x] Spike gate references approved revision 1.
- [x] Implementation gate references approved plan revision 1.
- [x] Dependency gate satisfied with no dependencies.
- [x] Dedicated `bugfix/E16-T1-cluster-expansion-freeze` branch is recorded.
