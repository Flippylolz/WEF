---
schema: ai-workflow/implementation-plan@1
epic: E27
title: "Faster verified releases"
status: approved
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E27-T1
    revision: 1
  - id: E27-T2
    revision: 1
  - id: E27-T3
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: owner
  decided_at: "2026-09-05T10:22:10Z"
  approved_revision: 1
  evidence: OWNER_DECISIONS.md
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E27 implementation plan — revision 1

## Approved spike baseline and scope

[Spike revision 1](SPIKE.md) was approved by the owner on 2026-09-05; see
[the decision transcript](OWNER_DECISIONS.md). Its recommendation remains current:
measure outcomes, consolidate exact-SHA verification, parallelize independent
preparation, and serialize all production mutation without weakening health,
rollback, configuration, or associated-PR controls. The owner approved this plan on 2026-09-05. No executable changes preceded approval.

The promoted revision-1 tasks are:

- [E27-T1](tasks/E27-T1-measure-release-and-report-outcomes.md) — no dependency.
- [E27-T2](tasks/E27-T2-parallelize-verification-and-bound-deploy-lock.md) — depends on E27-T1.
- [E27-T3](tasks/E27-T3-prove-release-budget-and-unattended-recovery.md) — depends on E27-T2.

Each task is independently reviewable. A dependent task may start only after its
parent is done or recorded as an open ancestor PR with branch, URL and exact head
under ADR-018. A child cannot merge or complete until its parent is done. This
plan does not authorize merging; the owner must request that action separately.

## Findings from the current implementation

- Both [CI](../../../.github/workflows/ci.yml) and
  [release](../../../.github/workflows/deploy-production.yml) run on `main`
  pushes. They repeat verification of that commit using different definitions.
- Release verification installs backend and frontend dependencies on the host,
  provisions host PostGIS, then runs `make test` through Compose, which builds
  test images and uses another database. Independent suites execute sequentially.
- Backend and web images are built sequentially after verification. Existing
  Buildx cache scopes are `backend-production` and `web-production`.
- `wef-production` concurrency currently includes source resolution, verification,
  publishing, and deployment. The host also has a nonblocking `flock` inside
  [deploy.sh](../../../scripts/deploy/deploy.sh), but configuration transfer,
  directory activation, registry login/logout, and inventory collection occur
  outside that script. Narrowing the Actions lock must still cover those steps.
- The two frontend builds in CI have different environments: the Playwright
  build disables the map. They are not proven duplicates and must remain distinct.

The [audit](../../audits/2026-09-05-system-audit.md) supplies observed timings.
These source findings do not establish a measured speedup.

## Ordered task sequence

**E27-T1 — reporting first.** Add a sanitized, versioned release outcome document
and a matching Actions summary without changing execution order. Record source
SHA, run ID/attempt, event, eligibility reason, image digests, merged timestamp,
stage start/end timestamps, observed healthy SHA/time, and rollback result.
Represent absent timestamps as null with a reason. Separate gate rejection,
verification failure, queued activation, fresh deployment, already-current
no-op, superseded candidate, and failed candidate with restoration. Workflow
success alone must never imply production success.

Use job/step timestamps to separate service time from dependency/runner gaps.
Do not sum parallel durations as elapsed time. Treat healthy observation time as
an upper bound on first healthy service, and never substitute commit time for
merged time. Collect ordinary merged-PR observations separately from direct
pushes, emergency dispatches, and rehearsals. Reporting failure must be visible
without rerunning successful production mutation.

**E27-T2 — one verification definition and concurrent preparation.** Extract
repository-owned reusable verification jobs. PR CI invokes them without release
write privileges or production secrets. The main release invokes the same jobs
for the resolved exact merge SHA; remove the duplicate main-push CI invocation
only after its consumers and required-check names have been verified. Keep
`Backend`, `Frontend and contract`, `Repository safety`, `Runtime images`, and
`Coverage badge` stable on pull requests. PR-head results cannot certify a
squash-merge SHA.

Run backend, frontend, and repository checks independently, using one disposable
PostGIS service for backend tests with locked host dependencies. Keep runtime
topology proofs that exercise containers. Prepare backend/web runtime images in
parallel; each candidate must pass runtime inspection before its digest enters
the release manifest. Assemble the artifact only after all verification and
image jobs succeed. Reuse caches as acceleration, never as verification evidence.

Move the shared `wef-production` Actions concurrency boundary to the entire
deployment job, including transfer, configuration, registry use, migration,
activation, health check, rollback, inventory, bootstrap, and cleanup. Keep
`cancel-in-progress: false` and host locking. Under the lock, read the current
healthy release and recheck source ancestry: an ancestor of the current healthy
SHA is superseded; unrelated or unverifiable ancestry fails closed. Do not order
releases by timestamps or assume queue order. A duplicate current SHA is a no-op
only after matching the verified manifest/digests and confirming healthy identity.

For emergency requests, look for a successful trusted same-repository release
run for the exact SHA and current verification definition before reusing an
artifact. Validate run conclusion, source identity, manifest/checksums and image
digests. Missing, expired, partial, mismatched, or cancelled evidence forces full
verification. A concurrent request must recheck current state inside the lock.
Explicit rehearsal flags cannot silently become no-ops. Configuration changes
for an already-deployed SHA require a clearly reported separate operational path;
they must not be hidden by an ordinary duplicate-release decision.

**E27-T3 — measure and prove.** Compare at least 20 eligible ordinary releases
before/after when available. Proposed targets remain p50 at most five minutes
and p95 at most seven minutes from merge to observed healthy version, including
queue time. Report sample counts, missing observations, cache state, runner
incidents, superseded releases, and manual interventions separately. Use nearest
rank percentiles and publish the definition. A superseded release has no healthy
latency; do not silently count it as a fast success or hide it from cohort counts.
Do not manufacture production releases to fill the sample. Insufficient data
keeps performance acceptance open.

## Verification parity required before consolidation

| Area | Required coverage in the shared verification path |
| --- | --- |
| Backend | Frozen dependencies; Ruff format/lint; mypy; architecture contracts and negative probe; PostGIS tests; 90% branch coverage; deterministic OpenAPI; dependency audit |
| Frontend | Frozen dependencies; format/lint/type; unit tests with existing coverage thresholds; generated contracts, lint and static docs; drift proof; compatibility and negative probe; production and map-disabled builds; Playwright; production dependency audit |
| Repository | Script format/lint/strict types and complete existing unittest list; Markdown links; source/secret exclusions; local Compose models |
| Delivery | Production topology, release-workflow, rollback, shared-edge and shell proofs; shellcheck; Caddy validation |
| Runtime | Both non-root runtime images; development-tool/source exclusion checks; production runtime/persistence proof |
| Artifacts | Per-suite coverage and badge floor; contract artifact; exact-SHA manifest, checksums and immutable digests |

Inventory the actual command lists when implementing; this matrix does not
authorize dropping checks added by concurrent work. Preserve coverage publishing
workflow consumers when changing artifact/run ownership.

## Failure proofs and operational limits

Extend existing release proofs for every dependency edge, missing/failed/cancelled
verification, wrong SHA/digest, absent artifact, direct push without a merged PR,
duplicate dispatch, out-of-order candidates, failed health checks, restored SHA,
unknown timestamps, and reporting after failure. Exercise concurrent deployment
attempts against a disposable host/state fixture to prove the protected boundary
covers transfer and cleanup as well as activation. Simulate interruption before
and after state activation and verify retry reconciliation does not double-apply
migration or overwrite a newer release.

Use bounded retries only for classified read/transfer failures before activation:
at most three attempts with 5/15-second delays. Never blindly retry migration or
activation after an ambiguous disconnect; first reconcile durable state and
health under the deployment lock. Retain existing rollback deadlines and shared
host non-interference controls. Exhausted access errors or ambiguous mutation
produce one actionable exception. No new provider, runner fleet, dependency,
database migration, secret ownership change, or production fault injection is
included.

Each task gets its own branch and PR in dependency order. Run applicable
format/type/contract checks and all delivery proofs, plus `make lint` and
`make test` before each push. Update deployment documentation, repository event
rules, and task evidence with the implementation. Roll out reporting first,
then shared verification and image preparation, then the narrower lock after
ordering proofs pass. A safety regression restores the previous workflow via a
reviewed change; do not cancel a running migration or rewind production data.

## Cross-task contracts and data

T1 owns `scripts/deploy/evaluate_deploy_gate.py`, release-report helpers under
`scripts/deploy/`, reporting hooks in `.github/workflows/deploy-production.yml`,
and associated tests. Introduce a `wef-release-outcome/v1` JSON artifact with
UTC timestamps, nonnegative seconds or null with an unavailable reason, exact
SHA/run-attempt identity, explicit gate reason, verification result, deployment
result, image digests, and rollback identity. Human summaries derive from that
same document. Keep reports sanitized and retained for 90 days; keep deployable
release artifacts at the existing 14-day retention. Report artifacts cannot be
used as executable release evidence. Avoid new notification destinations.

T2 owns the shared workflows, CI/release callers, any Makefile extraction,
release-manifest assembly, duplicate/stale gate helpers, and deployment lock
integration. Coverage-badge publishing and required-check consumers must be
updated consistently. Workflow/check identity is part of artifact reuse
validation. Preserve repository-owned source and exact SHA checkout boundaries.
T3 owns aggregate measurement/reporting helpers, sanitized cohort evidence,
release/rollback proofs, and operational acceptance documentation.

No application API or database schema migration is planned. Additive release
metadata must remain readable alongside existing release state; missing legacy
fields are unknown, never implicit verification. Existing health-gated state
activation stays atomic. Deploy ordering must use verified ancestry and current
healthy state, with a fail-closed reconciliation path for interrupted activation.
No raw API exports, secrets, host inventories, contacts, or configuration enter
committed evidence or public artifacts. GitHub Actions continues to own complete
production configuration. Untrusted PR code never receives production secrets or
release write permissions. No production dependencies are introduced.

## Resource budgets and evidence

Use the existing hosted runner class and provider services. Run at most one
production mutation at a time. Three verification lanes and two image preparation
lanes may run concurrently; coverage aggregation, runtime proof, artifact
assembly and activation follow their required inputs. Preserve cache scopes and
locked tool versions. Measure runner minutes as well as elapsed latency; a
material cost increase or new runner infrastructure requires renewed review.
Read-only metadata/transfer retries are bounded as above. Do not add unlimited
polling or rerun full workflows simply to recover a missing summary.

T1 establishes a baseline using available historical ordinary release runs,
reporting missing health/cache timestamps explicitly. Twenty observations are
requested when available; unavailable historical fields cannot block delivery
of accurate reporting. T3's performance acceptance requires at least twenty
actual post-change ordinary observations with sufficient timing evidence;
otherwise T3 remains open. Neither small-sample results nor synthetic latency
stand in for production performance. Publish budget misses transparently.

Local synthetic failure/rollback tests are part of T2/T3. Production fault
injection, manual release dispatch, destructive repair, and credential changes
require separate authorization. Observe standard automatic releases after
owner-authorized merges. Existing deferred off-host backups remain deferred;
workflow rollback cannot restore data destroyed by a migration.

## Invalidation triggers

Return to spike review for altered release trust boundaries, deployment topology,
configuration ownership, production dependencies/providers, paid infrastructure,
or weakened checks. Return to plan review for material task/dependency, contract,
retry/budget, migration, rollout or rollback changes. Concurrent changes to
required checks must be reconciled in the parity inventory before consolidation.
No speed target authorizes a safety exception.

## Approval checklist

- [x] Current spike revision is owner-approved with decision evidence.
- [x] Every sequence entry is a promoted revision-1 task.
- [x] Dependencies are acyclic and enforceable through task gates.
- [x] Modules, contracts, verification, budgets, data, risks and rollout are explicit.
- [x] No unresolved deferred decision is required for this scope.
- [x] No production or disposable proof code has been written.
- [x] Revision 1 is owner-approved; the decision transcript is recorded.

## Owner decision

Approval of this exact plan revision will allow task implementation in the
recorded order, with one branch/PR per task and all task gates satisfied first.
Record that decision in the approval metadata and owner decision transcript.
