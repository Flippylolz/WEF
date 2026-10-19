# E26-T2 implementation and rollout evidence

Current status: implementation is complete; [production rollout evidence](PRODUCTION_ROLLOUT.md)
records the eleven verified canaries and automatic expansion. Exact coordinates
for the three reported cases remain unresolved and their pins are quarantined.
The sections below retain the historical implementation and pre-release checks;
the production evidence supersedes their then-pending rollout status.

## Historical implementation record


The implementation is on `feat/E26-T2-location-revalidation`, based on T1's
merged main commit `6722ecb79d47958a92eb3608aeade1a4a3cede9e`. T1's required CI and
[production release](https://github.com/Flippylolz/WEF/actions/runs/34016504593)
succeeded. T2 remains in progress: no existing production points have been
revalidated or changed by this task. The draft was rebased onto main `8ff50a9`
after all five approved E14 prerequisites merged.

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
   be deployed before application. E14-T1–T5 are now merged under the owner
   approval; T3 is deployed via PR #363 / release 34027321299. The explicit
   additive-schema rollback prerequisite is PR #364, carried by PR #365
   after its browser audit correction. That release must deploy before T2.
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

Do not close T2 or mark E26 done on synthetic tests alone. The operator
controls and rollback procedure are in
[OPERATOR_COMMANDS.md](../../operations/OPERATOR_COMMANDS.md#e26-location-revalidation).
Raw reports, provider payloads and source records stay outside Git.


## Release sequencing clarification

Approved plan revision 1 requires the normal CI/release path and starts T2 in
observation mode. The normal release path requires a merged implementation PR;
production canary evidence therefore follows that release. The earlier draft-only
wording would prevent deployment of the very worker needed to produce the evidence.
After local/current-head CI checks and T3 deployment, the implementation may merge
for observation-mode release while this task remains in progress. This does not
waive any application, canary, protected-state or completion gate. Only the already
approved bounded canary follows the observation report; automatic expansion still
requires its persisted verification evidence. The prior wording was implementation
status prose, not a change to the approved plan's deployment sequence.


The live read-only baseline contains over 2,200 locations, so a named regression
could otherwise wait behind the general observation queue. `observe --canary-id`
now enqueues at most 25 existing distinct locations through the identical snapshot
and protected-receipt path and prioritizes them within ordinary claims. It leaves
the durable scan cursor and the 25-item cycle/provider budget unchanged. A real
PostGIS test proves priority over older general work, idempotence, missing/duplicate/
oversize rejection and no selection application. The general scan remains automatic.


## Combined local verification

T2 was rebased onto the exact approved open T3 ancestor
`9f2c65d44ca06b0a4cc9eb953ee8e74f31b8c345` (PR #363) to validate the safe
release combination. T3 merge/deployment remains required before T2 application;
T2 will be rebased onto the equivalent main merge before publishing its final head.

`make verify` passed on code commit `d3065d8a7ef1ba857e5e6645c36abc37f54fa34e`:
1,279 backend tests, 91.14% backend coverage, 185 frontend tests, 95.99% frontend
lines / 90.05% branches, all existing critical coverage floors, 186 script tests,
format/lint/strict types, generated contract and compatibility/negative probes,
production topology/rollback/build proofs, architecture enforcement and links.
No production dependencies or budget increases were added. The dedicated priority
PostGIS suite passed 17 tests before this complete run.


`make test-e2e` then passed on the combined T2/T3 tree: 48 journeys across all five
profiles, 12 explicit non-Chromium WebGL skips, zero retries and zero failure
artifacts. The disposable database migrated through `20260906_0026`. This is
migration/UI integration evidence, not a claim of a production repair.


Final compatibility integration was verified on code commit
`5b055b0dae2801849ad8b01d9b35d87975da6e6a`, based on the exact open PR #364 head
`b7903ef2f08dfcf07cdddef6c3b7ff7e83909233`. `make verify` passed again: 1,280
backend tests, 185 frontend tests, 186 script tests and all required quality,
contract, runtime, build and architecture checks. The only rebase conflict was
the expected schema revision: T2 retains the allowlist but requires `0026`.

The built new reader was run against the separate actual `0025` database with no
validation tables: it correctly refused readiness. The predecessor image had
already passed readiness and a real map query against actual `0026` with all three
new tables. These tests establish both rollout and application-rollback direction.

Read-only production preparation selected ten canaries (the three tracked cases
plus protected/building/street/district/city strata), saved identity sets and
selection snapshots outside Git, and confirmed 1,928 requests remained in the
existing 2,700 daily allocation at that snapshot. There are 263 protected selections;
these are preserved, not silently classified as automatic repair candidates.
No existing production selection has yet been changed by T2.


The prior CI attempt `34028465912` failed the browser accessibility gate when
React replaced metadata during the asynchronous audit. Standalone PR #365
corrected the readiness assertion without disabling any rule or adding test
retries, passed all required CI, and merged as `cea47610ea88da7408d5633bd3670503e847a052`.
T2 is rebased onto that main commit. The replacement compatibility release is
`34029703306`; it must succeed before worker deployment.
