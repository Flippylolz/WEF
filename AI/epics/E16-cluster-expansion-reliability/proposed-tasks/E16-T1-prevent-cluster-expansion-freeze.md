---
schema: ai-workflow/proposed-task@1
id: E16-T1
epic: E16
title: "Prevent cluster expansion from freezing the map"
status: proposed
revision: 1
actionable: false
priority: P0
size: S
milestone: M4
dependencies: []
requirement_ids: [P-004]
decision_ids: [ADR-002, ADR-004]
deferred_decision_ids: []
source: "Owner defect report with screenshot, 2026-08-29"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E16-T1: Prevent cluster expansion from freezing the map

## Outcome

Selecting a numbered map cluster expands it without throwing a MapLibre camera
error, corrupting the canvas, or disabling subsequent map interaction.

## Scope

- Validate copied cluster center and expansion-zoom values before camera use.
- Replace the failing interpolated cluster camera path with the approved
  reliable public camera operation.
- Cover valid and rejected/invalid expansion targets in focused component
  tests.
- Verify representative cluster clicks and subsequent drag, built-in zoom, and
  unclustered-pin activation in a real browser.

## Out of scope

- Dependency upgrades/downgrades, MapLibre internals, map style/provider,
  clustering radius/counts, backend contracts, layout, and listing behavior.

## Work

- Keep cluster activation distinct from unclustered location selection.
- Treat missing source/coordinates, non-finite values, and rejected expansion
  queries as harmless no-ops that leave the map usable.
- Preserve the current move-end URL bbox flow and map instance lifecycle.

## Acceptance criteria

- [ ] Clicking multiple numbered clusters expands each cluster and leaves the
      map responsive to pan, zoom, and later cluster/pin activation.
- [ ] No singular-matrix/`_calcMatrices` error is emitted during cluster
      activation in the real-browser verification.
- [ ] Missing, rejected, and non-finite expansion targets do not invoke a
      camera update or surface an unhandled rejection.
- [ ] Unclustered pin selection, URL viewport reporting, reduced-motion
      behavior, and existing map/list coordination remain green.
- [ ] Applicable format, lint, typecheck, frontend tests/coverage, production
      build, and real-browser checks pass.

## Dependencies and gates

- No task dependency.
- P-004 and ADR-002 require grouped pins/clusters and coordinated map behavior.
- ADR-004 keeps MapLibre/OpenFreeMap; no provider or dependency decision is
  changed.
- The task remains non-actionable until the spike is approved, it is promoted,
  and implementation plan revision 1 is explicitly owner-approved.

## Risks and notes

- Mocked component tests cannot prove render-loop stability, so browser
  verification is mandatory.
- If a dependency change becomes necessary, stop and revise/reapprove the spike
  and implementation plan.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match
      the approved spike.
- [x] Required deferred decisions are resolved (none).
- [ ] The file will be moved—not copied—to the epic’s `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.

