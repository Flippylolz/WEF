---
schema: ai-workflow/implementation-plan@1
epic: E16
title: "Reliable numbered map-cluster expansion delivery"
status: awaiting_approval
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E16-T1
    revision: 1
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

# Implementation Plan: Reliable numbered map-cluster expansion delivery

## Approved spike baseline

- [E16 spike revision 1](SPIKE.md) was owner-approved on 2026-08-29.
- The binding recommendation is a guarded, non-interpolated public MapLibre
  camera update. The grouped-location contract, MapLibre/OpenFreeMap decision,
  source data, URL viewport ownership, and map instance remain unchanged.

## Scope and outcome

Deliver one frontend-only repair so numbered clusters expand without entering
MapLibre's failing combined center/zoom interpolation. Reject invalid or failed
expansion targets without changing camera state. Preserve unclustered selection,
map/list coordination, and viewport reporting.

## Ordered task sequence

1. [E16-T1](tasks/E16-T1-prevent-cluster-expansion-freeze.md), revision 1.
   This is independently reviewable and has no task dependencies. It changes
   only `warsaw-map.tsx` and its focused tests, then verifies the production-like
   map in a real browser. There is no migration, contract generation, dependency
   change, or configuration change.

## Cross-task architecture

There is one task. The frontend continues to consume backend-provided GeoJSON,
while MapLibre remains responsible for clustering. The handler queries the
public GeoJSON source for expansion zoom, validates a copied center/zoom target,
and invokes a public non-interpolated camera operation. Backend authority and
generated contracts are unaffected.

## Data and migrations

No schema, persisted data, source data, API contract, generated client, or
migration change.

## Security and privacy

No authentication, authorization, contact, audit, log, secret, or personal-data
flow changes. Tests use existing synthetic map fixtures and commit no user
screenshot or production response.

## Test and verification strategy

- Extend `warsaw-map.test.tsx` to prove a valid cluster uses the approved camera
  path and never selects a location.
- Add failure coverage for rejected expansion queries, non-finite zoom, and
  non-finite/copied coordinates; no invalid target may reach the camera.
- Preserve existing unclustered selection, viewport, reduced-motion, resize,
  failure, and map lifecycle assertions.
- Run frontend format check, lint, typecheck, unit tests, coverage floor, and
  production build; run repository-wide required checks before push/merge.
- In a real browser, activate multiple numbered clusters and then exercise pan,
  built-in zoom, and an unclustered pin while checking for console errors and
  correct URL bbox updates.

## Operations, rollout, and rollback

- Merge through the dedicated E16-T1 pull request only after all required CI
  checks are present and successful.
- Standard `main` release builds and deploys the web image. No backend or
  configuration ordering is required.
- Confirm the deployed release marker contains the merged SHA, then repeat the
  browser verification on production.
- Roll back to the previous complete release image if cluster expansion or
  another map interaction regresses.

## Risks and mitigations

- **Mock boundary misses render-loop failures:** mandatory real-browser checks
  before and after deployment.
- **Invalid worker result reaches camera:** finite-value guards and negative
  tests.
- **Jump transition is less visually smooth:** accepted P0 tradeoff for
  reliability and naturally compatible with reduced motion.
- **Scope expands to dependency work:** stop, invalidate, and reapprove before
  changing MapLibre or another dependency.

## Invalidation triggers

A MapLibre dependency change, map provider/style change, clustering-model
change, backend contract change, or failure of the guarded non-interpolated
camera path returns work to the spike. A module/test/rollout scope change with
the spike recommendation intact returns work to this plan.

## Approval checklist

- [x] The referenced spike revision has explicit owner approval and remains
      valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria
      and traceability.
- [x] Dependencies are complete, acyclic, and enforceable task by task.
- [x] Affected modules, contracts, tests, migrations, risks, rollout, and
      rollback are explicit.
- [x] Deferred decisions required for implementation are resolved (none).
- [x] No production or disposable proof code has been written.
- [x] `revision` represents the material plan being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval
authorizes implementation plan revision 1 after the E16-T1 task gate is updated
and its dedicated branch is created.

