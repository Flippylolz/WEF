# E24-T2 rollout correction plan

Revision: 1. Status: approved. The owner replied `continue` directly to the
request to approve this bounded staging correction and publication of its
aggregate evidence to public `Flippylolz/WEF` in task
`01a0710e-adaa-76f2-8bcd-07784c03e9b2` on 2026-09-05.

## Problem and scope boundary

T2's historical bootstrap exposes unbounded downloaded-file retention in the
worker's 64 MiB temporary filesystem. Repeated heartbeat OSError failures prevent
stable activation. [Production evidence](PRODUCTION_EVIDENCE.md#acceptance-failure-and-containment)
records the observations and the safe pause. T1 remains done; T2 remains in
progress. This proposal corrects staging lifetime and capacity within T2's bounded
polling path. It does not approve T3's durable media-recovery ledger, source-version
conflict resolution, data resets, or broader T4 health policy.

This changes media acquisition/lifetime assumptions beyond implementation plan
revision 1. The owner approved this correction under that plan's risks and invalidation
rule; its requirements now supplement implementation plan revision 1.

## Proposed implementation contract

1. Establish a bounded worker-owned staging lifecycle. Account for in-progress and
   completed temporary files under a total byte budget with reserved heartbeat
   capacity. Failed, oversized, timed-out, and cancelled downloads release partial
   files and reservations. Enforce limits during writes, not after a large download
   has already exhausted the filesystem.
2. Stream bounded forward work instead of eagerly retaining downloads for all
   400 source messages before processing. Preserve the existing 400-forward plus
   100-old-ID cycle bound and no-more-than-100 source IDs per request.
3. Tie successful temporary-file release to consumer/media-pipeline ownership.
   Keep files still referenced by queued callbacks or pending album associations;
   release only worker-owned staging files whose consumers have finished. Do not
   delete restricted originals, public derivatives, source evidence, or arbitrary
   filesystem paths. Avoid filename collisions between overlapping observations.
4. Treat temporary staging pressure as a transient deferral with persisted delay,
   not a malformed-record failure or silent successful empty-media result. A
   partially acquired forward batch cannot certify an unobserved polling interval.
   Retain unknown/incomplete history and existing retry/receipt semantics.
5. Preserve network waits outside canonical locks and maintain live callback
   acceptance. Use existing dependencies and storage boundaries. If a durable media
   ledger is necessary for correctness, stop and revise the plan to promote T3;
   do not smuggle that independent feature into this correction.

## Validation and rollout

- Reproduce bootstrap under a constrained staging filesystem. Prove the aggregate
  byte bound, heartbeat headroom, and progress beyond multiple old failure windows.
- Exercise overlapping callback/polling downloads, shared message IDs, pending
  album references, processing failure, cancellation, and oversized source output.
- Verify staging deferral preserves polling boundaries and data-failure budgets;
  restart preserves applied/polled/sweep positions and original receipts.
- Run make lint, make test, applicable format/type/contract checks, and link checks.
  Use one dedicated bugfix PR against current main; require all current-head CI.
- Keep production paused until the reviewed correction is deployed. Resume through
  the existing durable canary control, then observe at least 15 minutes, spanning
  several previous 3–4-minute failure intervals. Require no health-stage restarts,
  bounded staging usage, continued archive and cursor progress, unchanged receipt
  invariants, and HTTP 200 public readiness. Pause again on systemic failure.

## Approved publication

Publish this plan and the aggregate-only rollout evidence to the canonical public
repository https://github.com/Flippylolz/WEF. The evidence includes record counts,
source cursor boundaries, release/run identifiers, health failure categories, and
restart times. It excludes payloads, per-record identifiers, contacts, credentials,
raw logs, source media, and checksum exports. The owner explicitly authorized publication of these production operational
details when approving this correction.

## Implementation and local proof

The correction uses exclusive stable-path leases, reserves each download's full
maximum against a 56 MiB aggregate budget, and checks an 8 MiB free-space reserve
before allocation and writes. Leases are absent from serialized evidence. Streaming
commits each classified observation before acquiring the next download; an interrupted
source response therefore retains its committed prefix. Polling and callbacks
share storage processing but keep separate association state. The existing grouper
retains only IDs and emits each message's dispositions synchronously, so lease
release after its consumer completes cannot remove pending album media.

A real Docker 64 MiB tmpfs proof processed 500 synthetic one-MiB downloads and
500 heartbeat writes. Peak temporary use was 1,052,672 bytes with zero media files
remaining. Regression tests also exercise capacity reservations, overlap, stable
checksums, partial/oversized/cancelled downloads, consumer failures, source backoff,
and a database failure after the committed streamed prefix.

Final local validation: make lint, format-check, typecheck, contract-check, link
checks and diff checks passed. The full make test run passed 842 backend tests
with 90.38% coverage and 169 frontend tests. Production acceptance remains open.
