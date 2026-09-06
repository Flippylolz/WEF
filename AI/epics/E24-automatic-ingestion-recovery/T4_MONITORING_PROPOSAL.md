# E24-T4 progress monitoring — implementation-plan revision 4 proposal

Status: owner-approved on 2026-09-06T05:30:10.288298+00:00. This document is a concrete proposed extension to
approved implementation-plan revision 3, incorporated into approved implementation-plan revision 4. T4
is promoted; T3 remains in progress. Spike revision 2 already covers this
research and planning scope.

## Problem and current evidence

At 2026-09-06T05:26:02Z, media discovery reached its frozen upper bound 29,713.
No intentions or media work remained pending. The ledger held 22,266 completed,
3,480 quarantined for unproven source equivalence and 2,356 unsupported for missing
association evidence. Zero completed work items had generated variants after
ledger creation. The 28,117 assets and 56,078 derivatives were unchanged; public
associations increased from 23,947 to 25,535, with zero duplicate associations.
This is evidence of additional associations, not proof of missing-variant repair.

At 05:26:03Z the original archive cohort had 27,844 completions and 22 pending.
Receipt checksum mismatches and terminal originals without receipts were both
zero; prior terminal attempts and the original fingerprint remained intact.

Waiting for this drained historical media cohort to produce a repair is no longer
a useful acceptance strategy. T3 needs either naturally arriving eligible missing
variant work or an explicitly approved change to its acceptance method. Do not
delete production derivatives, override source equivalence, or mark T3 complete.

Current worker status reads durable traversal progress but still derives freshness
from reconciliation/run time. Runtime liveness publishes transport, consumer and
reconciliation state. Neither proves unique archive work has advanced. Keep the
lightweight file-only probe and public API readiness independent of DB aggregation.

## Proposed sequencing decision

Recommend allowing T4 implementation after T1/T2 completion and verification of
T3's deployed ledger/status contracts, while T3's production repair acceptance
remains open. This explicitly changes T4's existing completion dependency on T3;
it requires owner approval and must be recorded in plan revision 4 and the promoted
task before code starts. It does not waive T3 acceptance or close E24.

Without that sequencing approval, prepare the design only and keep T4 blocked
behind T3. Existing standing merge authorization is not scope approval.

## Implementation contract

1. Add one backend-authoritative ingestion progress projection, scoped by channel
   and stage (archive, traversal, media discovery, media execution). Read persisted
   work identities and outcomes, not log lines or maximum source ID alone.
2. Distinguish provider observations fetched, archived arrivals, attempts, unique
   canonical commits, terminal classifications, transient deferrals, quarantine,
   media completion, generated variants and association reconciliation. Fetched
   observations may repeat; they must never be summed with unique terminal work
   to claim completeness. Mark unavailable legacy counters as unavailable.
3. Define mutually exclusive snapshot populations. Archive totals reconcile with
   terminal, eligible, delayed and quarantined originals. Media totals reconcile
   with completed, superseded, unsupported, quarantined, eligible, delayed and
   leased work. Discovery coverage and undiscovered intentions remain separate.
4. Sample every 60 seconds using a repeatable snapshot and a five-second database
   statement timeout. Persist compact checkpoints and incident transitions per
   channel/stage; retain at most 48 hours of minute aggregates. Use existing due
   indexes and add only indexes justified by query plans. No source text, media
   paths, contacts, record IDs or provider exception strings enter diagnostics.
5. Maintain exact monotonic transition counters in the owning database transaction
   where existing durable records cannot reconstruct them. Deduplicate by existing
   event/work identity; failed commits cannot increment unique success. A restart
   or deployment cannot reset the comparison baseline or fabricate progress.
6. Evaluate eligible work against its earliest deadline. An empty stage is idle;
   delayed-only work is waiting until its persisted provider/retry deadline plus
   two sampling intervals. An active, renewed lease is in flight. A configured
   pause is paused. No-progress conditions require three consecutive samples and
   at least five minutes without a unique terminal transition despite eligible
   work. Queue age measures time since eligibility, not merely record creation.
7. Detect attempted work without unique completion as a distinct signal, including
   repeated terminal sibling processing. Quarantine growth is visible but does not
   count as successful canonical ingestion. Repeated deferral is not a data failure.
   A stalled stage makes ingestion progress unhealthy even if transport is healthy;
   report that independently from process liveness to avoid restart storms.
8. Reuse existing bounded retry, lease expiry and supervised-loop recovery first.
   Do not reset budgets, rewind cursors, replay terminal work or restart a healthy
   whole worker as generic remediation. A terminated stage may be restarted once
   under existing supervision; a running but stuck stage receives one deduplicated
   incident after its existing lease/deadline bounds expire. Systemic source-access
   failures preserve the existing stage-specific pause behavior.
9. Persist one incident per channel/stage/reason episode. Notify only when an
   actionable episode opens or changes materially; recovery closes it automatically
   after two healthy samples. Repeated unchanged samples create no notifications.
   Expose the signal through E14's existing privacy-safe observability integration;
   adding a new delivery provider or sending a test message needs separate scope.

## Files and boundaries

Extend `application/telegram_worker_status.py`,
`infrastructure/telegram_worker_status_store.py`,
`application/telegram_worker_liveness.py`, `telegram_worker_status_command.py`,
and `telegram_worker_command.py`. Keep state classification in an inward domain
module with an injected clock; place snapshot/counter persistence in ingestion
infrastructure. Use the existing archive retry/recovery and media ledger seams.
The file-only Compose health probe must retain its ORM-free import boundary.

An additive migration creates progress checkpoints, bounded samples and incident
state. Choose its revision/parent from current main at implementation time; do
not reserve a migration number while other work is landing. No production
package, broker, provider, CPU/memory increase or public API contract is proposed.
Update ingestion, operations and E14 observability documentation together.

## Verification and acceptance

- Fake-clock tests: idle versus stalled, delayed-only provider waits, renewable and
  expired leases, repeated sibling attempts, late samples, restart continuity,
  clock regression and automatic incident closure.
- Real PostGIS tests: exact identity counters, transaction rollback, competing
  monitors, population reconciliation, bounded history retention and query timeout.
- Outage/contention tests: text landing continues, retries recover automatically,
  incident state clears and no repeated owner notifications occur.
- Media tests distinguish completed reuse, new variants and association changes;
  a drained queue with zero new variants must preserve the open T3 repair gate.
- Run lint, full tests, formatting, typing, contracts, links and the existing real
  0.5-CPU/file-probe and 64-MiB staging proofs. Inspect aggregate query plans on
  representative data without publishing source records.

Deploy observation-only classification first. Require a healthy 15-minute window
with bounded query latency and no liveness regressions before enabling incident
classification. No production fault injection is assumed. Then collect a full
24-hour acceptance window: no repeated terminal work, non-growing eligible
backlog at ordinary load, deduplicated incidents and zero routine interventions.
Pre-existing quarantine is reported separately from the eligible backlog.
Source silence is not failure; gaps or missing samples invalidate the window.
T4 cannot be marked done before this evidence exists. T3's separate repair gate
and E24 completion remain explicitly open if still unresolved.

Rollback disables the monitor's recovery/incident trigger while retaining read-only
status, source data, counters, queue state and incident history. No destructive
schema downgrade, asset deletion, budget reset or source override is permitted.

## Approval requested

Approve implementation-plan revision 4 with the contract above, including the
explicit sequencing change allowing T4 to proceed against deployed T3 contracts
while T3 production repair acceptance remains open. On approval, promote T4,
record the new revision and dependency evidence, publish the planning PR, and
implement on its own branch under the existing green-CI merge policy.

## Approval record

The owner replied **I approve** directly to the revision-specific approval request
in Codex task `01a0710e-adaa-76f2-8bcd-07784c03e9b2` on 2026-09-06. This approves
the contract and explicit sequencing change above. Earlier conditional proposal
wording records the decision reviewed; the canonical plan now records approval.
