# E26-T2 implementation and rollout evidence

The implementation is on `feat/E26-T2-location-revalidation`, based on T1's
merged main commit `6722ecb79d47958a92eb3608aeade1a4a3cede9e`. T1's required CI and
[production release](https://github.com/Flippylolz/WEF/actions/runs/34016504593)
succeeded. T2 remains in progress and its PR must remain draft: no existing
production points have been revalidated or changed by this task.

## Implemented boundaries

- Additive migration `20260906_0026`, application readiness revision, default
  observation mode, 100-row durable scan and unique source/version work keys.
- Shared foreground/repair request budget, bounded two-form cache path, renewable
  120-second leases, stale-source/selection/owner guards and retry/quota deferral.
- Atomic selection and immutable receipts; observation never marks application
  complete. Protected actors are discovered without spending provider quota.
- Explicit canary evidence gate before expansion, aggregate private reporting,
  pause/resume fencing and 25-receipt guarded rollback. Invalid or edited
  predecessors are never restored as precise points.
- No production dependency, public contract, identity-key, offer visibility,
  favorite, parser or source-content mutation.

## Verification scope

Real disposable PostGIS tests cover observation-to-apply, cache reuse, no-op
replay, wrong-street quarantine preserving offers/favorites, owner/source/selection
races, expired-lease takeover, renewal, protected discovery, quota pauses,
consecutive-failure limits, new policy generations, receipt rollback atomicity,
canary readiness, explicit pause/resume fencing, guarded predecessor rollback,
100-row checkpoint restart and concurrent independent claims. Orchestration tests
cover provider failures, cancellation, renewable leases, queue caps, foreground
capacity reservation and private command routing.

Final required command results are recorded in the PR. The coordinates in test
fixtures are invented and cannot establish either reported production fix.

## Remaining acceptance and release gates

1. T3 honest area/unresolved discovery and real map/list precision behavior must
   be deployed before application. E14-T5 remains draft with blocked
   implementation approval; this plan does not authorize implementing E14.
2. Produce the production observation report and named stratified canary (up to
   25). Check identities/favorites, source agreement, effective precision,
   request consumption and public behavior before `verify-canary` enables
   automatic expansion. Command flags are operator attestations, not independent
   proof of deployment or street geometry.
3. Verify Ostrzycka `373861ab-6214-4bf3-81c6-d9bd4c10c9ab` against dated authoritative
   street geometry with CRS/coverage and actual selected-point comparison.
4. Record persisted outcomes and public evidence for both Jugosłowiańska variants:
   `8df1fc76-a8d6-466a-93d2-c33b146026da` and
   `c09efdbc-5f58-4184-a5a0-86d8201f6cf6`. They remain unverified fixed.

Do not merge/close T2 or mark E26 done on synthetic tests alone. The operator
controls and rollback procedure are in
[OPERATOR_COMMANDS.md](../../operations/OPERATOR_COMMANDS.md#e26-location-revalidation).
Raw reports, provider payloads and source records stay outside Git.
