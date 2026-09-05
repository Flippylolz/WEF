# E27 delivery proposal

Research supplement prepared on 2026-09-05 against `main` commit
`a2cdb16`. The owner selected E27 to reduce duplicate verification and queue
delays. This document makes the proposed change reviewable; it does not record
spike or implementation approval. The promoted task definitions are linked in [the task list](README.md#tasks).

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

## Proposed task sequence

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

## Planning handoff

The owner approved spike revision 1 on 2026-09-05. The candidates have been
promoted and this research proposal is now superseded for implementation detail
by [implementation plan revision 1](IMPLEMENTATION_PLAN.md), which the owner approved on 2026-09-05. See [the decision transcript](OWNER_DECISIONS.md).
