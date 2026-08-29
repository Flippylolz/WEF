---
schema: ai-workflow/spike@1
epic: E16
title: "Prevent numbered map-cluster activation from freezing the map"
status: awaiting_approval
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-002, ADR-004]
domain_docs:
  - ../../product/EXPERIENCE.md
  - ../../product/QUALITY.md
  - ../E5-interactive-map-frontend/tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md
  - ../E13-dark-map-explorer/UX_DESIGN.md
proposed_task_ids: [E16-T1]
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Prevent numbered map-cluster activation from freezing the map

## Question

What is the smallest reliable change that restores numbered cluster activation
without changing the grouped-location contract, map provider, or ordinary
pin/list selection behavior?

## Context and constraints

- The owner reported on 2026-08-29 that selecting a numbered circle such as
  the attached six-location cluster freezes the map.
- E5-T1 requires cluster activation to zoom to members. E13 retained that
  behavior while changing the visual shell and listing rail.
- The backend GeoJSON response remains authoritative. Clustering and camera
  movement are frontend MapLibre concerns under ADR-002 and ADR-004.
- The fix must not remount the map, change URL-backed viewport ownership, add a
  production dependency, or weaken reduced-motion behavior.
- The raw user screenshot is diagnostic input only and must not be committed.

## Research method

1. Inspect the current cluster click handler and its component tests.
2. Reproduce the report in the deployed product at the public production URL.
3. Compare cluster activation with MapLibre's built-in zoom control.
4. Inspect the deployed stack trace, MapLibre 6.4.1 camera/source code, the
   locked dependency history, and the public map API coordinates.
5. Compare a guarded non-interpolated camera update with error handling and a
   dependency rollback.

Prohibited before implementation-plan approval:

- production or application code;
- scaffolds, migrations, infrastructure/configuration changes, or generated
  executable artifacts;
- throwaway scripts, prototypes, proof branches, or disposable proof code.

## Evidence

### Verified production behavior

- On 2026-08-29, clicking a numbered cluster reliably left the map canvas
  partially blank and unusable.
- The browser logged `TypeError: Cannot read properties of null (reading '0')`
  from MapLibre's vector-matrix transform during
  `_calcMatrices -> setZoom -> easeFunc -> _onEaseFrame`.
- The built-in `+` control completed its zoom, updated the URL bbox, refreshed
  the result count, and left the map usable. The defect is therefore not a
  general zoom, worker, tile, or canvas failure.
- Repeating cluster activation after a successful built-in zoom reproduced the
  same camera-animation exception.

### Verified data and code facts

- `warsaw-map.tsx` awaits `getClusterExpansionZoom(clusterId)` and then calls
  `easeTo` with the cluster center and returned zoom. There is no finite-value
  guard, alternative camera path, or test capable of exercising MapLibre's
  animation frames.
- The existing Vitest mock always returns zoom 13 and records the `easeTo`
  options; it cannot reproduce an internal animation-frame exception.
- All 776 backend features in the reproduced bbox had finite longitude and
  latitude values, ruling out malformed API point coordinates.
- The deployed matrix operation received a null inverse view/projection matrix
  while interpolating the combined cluster center/zoom camera move. Once that
  render-loop exception occurs, application-level `try/catch` around the
  earlier `easeTo` call cannot recover the already-corrupted animation.
- MapLibre's official cluster example uses the same expansion-zoom query and
  camera target shape, but it does not guarantee that this specific
  application/style/viewport combination is safe on the locked 6.4.1 runtime.

### Assumptions and uncertainty

- The exact upstream MapLibre condition producing the singular intermediate
  matrix is not proven. The app can avoid the failing interpolation without
  diagnosing or patching MapLibre internals.
- A non-interpolated camera update trades a short visual animation for a
  reliable cluster expansion. That is acceptable for a P0 interaction repair
  and is naturally compatible with reduced-motion preferences.

## Options considered

### Option A: Catch `getClusterExpansionZoom`/`easeTo` errors

- Benefit: smallest textual change.
- Cost: the observed exception is thrown later by MapLibre's animation frame,
  after `easeTo` returns, so a handler-level catch cannot protect the map.
- Decision: reject as insufficient.

### Option B: Guard the camera target and apply it without interpolation

- Validate the expansion zoom and copied center coordinates with
  `Number.isFinite`, then use a single non-interpolated public camera update.
- Add tests for a valid cluster, non-finite target rejection, source-query
  rejection, and reduced-motion-compatible behavior.
- Benefit: avoids the proven failing animation path, stays within public
  MapLibre APIs, changes no contract or dependency, and preserves one-click
  expansion.
- Cost: cluster expansion jumps rather than animates.
- Decision: recommend.

### Option C: Roll MapLibre back or upgrade it

- Benefit: may remove the upstream failure without an application workaround.
- Cost: broader regression surface, introduces dependency work, and current
  evidence does not identify a release whose notes guarantee this case.
- Decision: reject for this focused repair; revisit only if Option B fails the
  real-browser verification matrix.

## Recommendation

Implement Option B as one frontend-only bugfix task. Copy and validate the
cluster coordinates and expansion zoom, use a non-interpolated camera update,
and leave invalid/rejected expansion requests as harmless no-ops. Keep the map
instance, source, URL bbox reporting, unclustered selection, listing rail, and
backend contracts unchanged.

## Proposed task boundaries

- **E16-T1 — Prevent cluster expansion from freezing the map.** Add the guarded
  non-interpolated cluster camera transition, focused failure-path unit tests,
  and a real-browser cluster interaction verification. No dependency, API,
  style, or layout changes.

## Risks and open questions

- A real-browser check must prove that the chosen public camera method expands
  multiple representative clusters and that drag/zoom/pin selection still work
  afterward.
- If the non-interpolated public camera method reproduces the matrix failure,
  stop and return to this spike before changing the dependency version.
- The component test remains a mock boundary; browser verification is required
  because the failure occurs inside MapLibre's render loop.

## Invalidation triggers

- A required MapLibre version change, provider/style change, clustering-model
  change, backend contract change, or discovery that ordinary map movement is
  also affected invalidates this recommendation.

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Evidence and uncertainty are distinguishable.
- [x] Affected decisions and domain documents are linked.
- [x] Proposed task boundaries and dependencies are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of
this spike revision permits task refinement/promotion and implementation
planning; it does not permit code.

