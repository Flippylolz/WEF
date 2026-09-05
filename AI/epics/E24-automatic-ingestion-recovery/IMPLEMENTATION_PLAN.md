---
schema: ai-workflow/implementation-plan@1
epic: E24
title: "Automatic ingestion recovery"
status: approved
revision: 1
owner: owner
spike_revision: 2
task_sequence:
  - id: E24-T1
    revision: 2
  - id: E24-T2
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-09-05T10:33:19Z"
  approved_revision: 1
  evidence: "Codex task 01a0710e-adaa-76f2-8bcd-07784c03e9b2: owner message 'continue I approve' directly responding to implementation plan revision 1 approval request; AD-049"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation plan: Automatic ingestion recovery

## Approved baseline and scope

[Spike revision 2](SPIKE.md) was approved by the owner under
[AD-048](../../workflow/AUTONOMOUS_DECISIONS.md#ad-048-approve-e24-spike-revision-2-and-prepare-the-first-implementation-plan).
This first plan implements the requested order: stop archive starvation in T1,
then make cursors and retries reliable in T2. It locks both promoted task
definitions at revision 2. No implementation has begun.

Retain PostgreSQL, the backend-authoritative ingestion architecture, source
evidence, protected offer fields, contact encryption, and existing provider
budgets. No production dependency is added. T3 media recovery and T4 broad
progress health/24-hour acceptance remain proposed and require a later plan
revision. Fixing the drainer's false completion count belongs to T1 because it
is necessary to verify this repair; it does not complete T4.

## Ordered task sequence and delivery

| Order | Task and revision | Dependency | Independently reviewable result |
| --- | --- | --- | --- |
| 1 | [E24-T1 revision 2](tasks/E24-T1-terminate-original-archive-work.md) | None | Original archive work terminates using retained source evidence; safe bounded reconciliation resumes the queue. |
| 2 | [E24-T2 revision 2](tasks/E24-T2-monotonic-cursors-and-fair-retries.md) | E24-T1 | Durable channel progress, fair retry scheduling, and bounded old-message reconciliation survive concurrency and restarts. |

Land planning metadata through its own documentation PR. Use
`bugfix/E24-T1-original-archive` and `bugfix/E24-T2-cursors-and-retries` as separate
implementation branches/PRs. Start T1 from current `main` after planning lands;
if that documentation PR remains open, use its branch as the documented planning
parent, consistent with AD-045. Record the exact branch, open PR, and head before
starting. T2 may stack on T1 under ADR-018; its dependency gate must name the
current T1 head/PR and show ancestry. Retarget/revalidate after a parent merges.
Do not mark either task done merely because its code is ready.

Plan approval permits implementation and review preparation, not merge. Any
subsequent owner-authorized merge must wait for required green CI and proceed
base-first. Production acceptance below is a release gate to execute after that
authorization, not a claim that the production backlog has been repaired.

## T1: archived input and terminal outcome

### Modules and interfaces

Change `application/raw_archive.py`, `application/telegram_events.py`, and the
inward-owned persistence contracts in `application/persistence.py`. Inject an
archived-payload decoder port implemented with the existing
`infrastructure/telegram_record.py::convert_record`; application code must not
import infrastructure. Wire it in `telegram_worker_command.py` and any existing
archive-replay composition root. Keep `application/raw_replay.py` compatible with
the shared decoder so parser replay cannot retain the lossy conversion path;
do not add parser/backfill policy under T1.

Extend `RawEventRecord` with the stored checksum and define an archive-processing
result containing the original UUID, disposition, canonical evidence, and whether
this invocation made a new terminal transition. Live arrival still lands before
processing; replay consumes the already-landed row and never calls `land` on a
reconstructed event. Both converge on shared extraction/persistence behavior.

`infrastructure/raw_event_archive.py` owns immutable landing, channel-scoped
selection, outcome projection, and reconciliation queries.
`infrastructure/persistence_adapter.py` owns ordering and canonical outcomes
inside its transaction. Additive ORM/Alembic changes belong to
`infrastructure/models.py` and `apps/backend/migrations/versions/`.

### Identity and reconstruction rules

1. Check configured channel against the archived channel and require a positive,
   non-boolean integer message ID matching the payload. Reject invalid event
   kinds and malformed timestamps with safe categories. Never apply an item to
   another channel because it happened to be in a global pending batch.
2. Decode the retained raw JSON, preserving original mixed text, entities,
   reply IDs, media/album descriptors, timestamps, and checksum. Descriptors are
   evidence, not permission to read an arbitrary archived filesystem path.
3. New historical seeds copy retained raw JSON verbatim. For old seeds whose
   checksum no longer hashes their flattened JSON, require a retained source
   revision with that checksum and an exact match of the known legacy flattening
   transform to the stored archive payload. Decode that proven original revision
   while retaining both references. Missing or ambiguous proof is quarantined;
   never rewrite the archive checksum/payload to manufacture agreement.
4. Terminal siblings are candidates for investigation only. Correlate exact
   source version and canonical revision/deletion evidence. An exact known lossy
   projection plus matching retained source history can establish the old replay
   bug; same channel/message ID or same timestamp alone cannot.

### Ordering and deletion rules

Apply the same guard before canonical source/offer mutations in live/archive
upsert paths. Under the channel advisory lock and canonical transaction, first
resolve any durable prior receipt for the original event, then check deletion
evidence, then compare source versions (`edited_at` or `published_at`).

- A newer source version may advance canonical state. An older one resolves as
  superseded against retained evidence without changing the current revision or
  offer. A known prior canonical revision is an idempotency anchor, not a reason
  to replace the newer current revision.
- Equal source version with equal evidence is already canonical. If historical
  and live shapes differ, accept only proven equivalent representations. A repair
  that restores fields lost by the known legacy replay projection requires its
  exact projection checksum, retained original revision, and absence of a newer
  semantic edit. It may produce one corrective source revision. Otherwise retain
  a conflict without changing canonical state. Arbitrary receipt time is not an
  ordering tie-breaker.
- A retained source deletion blocks stale recreation/refresh even when no source
  message existed when the delete arrived. Record that negative source evidence
  durably, keyed by channel/message ID. Canonical deletion hides linked offers
  without removing lineage. Automatic archive replay never clears a tombstone.
  Guard parser replay through the same canonical boundary as well.
- Preserve existing owner/AI field protections and contact behavior on every
  allowed upsert. A superseded/deleted result must not run offer refresh hooks.

### Transaction and acknowledgement contract

Add `telegram_archive_resolutions`, with original event UUID as its unique/primary
key, an allowlisted disposition, recorded source checksum, nullable canonical
message/revision or deletion-evidence reference, policy version, and commit time.
Applied, already-canonical, non-candidate, superseded, and deleted are terminal
resolutions. Require the reference appropriate to each disposition; an intentional
non-candidate can instead carry its explicit classification. Ambiguity or failure
does not create a success receipt.

Commit the resolution in the same transaction as its canonical effect or verified
no-op. For deletion-before-create, persist the tombstone and receipt atomically.
After commit, project the receipt onto the original archive row. Projection uses
`processed_at IS NULL` and returns whether it changed a row; a delayed failed
attempt cannot reopen or increment a terminal record. Keep the legacy archive
`outcome` vocabulary (`processed`, `skipped_non_candidate`, `failed`) compatible;
the resolution table carries the more precise terminal reason.

On restart after canonical commit but before acknowledgement, project the durable
receipt without repeating extraction, offer mutation, or media work. On rollback
before commit there is no receipt, so the original remains retryable. Propagate
cancellation and close a started run as cancelled where possible; cancellation
must not consume a malformed-record retry or be swallowed by the drain loop.
An acknowledgement/database outage must surface as a failed worker stage if even
the error ledger cannot be written. Avoid a second error masking the primary
safe failure category.

Return separate selected, attempted, newly terminal, failed, and unchanged-terminal
counts. Update `last_event_committed_at` only for newly verified terminal work,
using committed evidence; do not refresh it on an all-failure or repeated-terminal
batch. Media completion is not implied by canonical/archive completion. Retain
descriptors for T3 and do not expand provider/media processing during repair.

## T1: bounded reconciliation and migration

Add a durable per-channel recovery state with phase (`canary`, `running`,
`paused`), policy version, bounded canary cohort, baseline counts, progress, and
safe pause reason. Reuse the receipt as the transition ledger: store the old
archive outcome/attempt values needed to reconcile each changed row. Retain all
originals and siblings. No unbounded data backfill belongs inside Alembic.

Expose a backend/operator preflight and bounded apply use case, with a read-only
default. Output aggregate eligible and exhausted populations, oldest pending age,
candidate terminal siblings, provable transitions, and exclusions. Detailed UUID,
checksum, and revision evidence stays in the restricted database, not public logs
or Git. Automatic operation invokes the same use case, not a separate repair SQL.

Use one archive worker, at most 25 records per batch and one batch per 5-second
interval. Start with a durable 100-record canary of the oldest eligible cohort
(or all eligible records if fewer). After verified successful transitions and
receipt/source consistency checks, expand automatically. A canary evidence
mismatch, protected-field conflict, or canonical regression pauses expansion
with one reason. In normal running, isolate a malformed item so later work can
continue; systematic identity/evidence faults pause the affected channel.

The durable pause setting is authoritative across restarts and exposed through
the same restricted operator command; there is no per-record approval step.
Acknowledgement-only reconciliation performs zero provider calls. Any existing
downstream work created by a genuine missing canonical offer remains under its
existing provider quotas and is not part of the repair's throughput claim.

Migration order: pause the old archive drainer at authorized release, add the
receipt/tombstone/recovery tables and indexes, deploy the corrected worker, run
preflight, then enable its bounded canary. A table keyed by source channel must
also support deletion evidence before a `SourceMessageRow` exists. Index pending
selection by channel, receipt time, and UUID; preserve the existing unique archive
identity constraint. Use synthetic pre-migration fixtures to verify upgrade and
repeated application. Do not purge or downgrade the evidence tables in rollback.

## T2: durable channel progress

Extend `application/telegram_reconciliation.py`, the persistence port/adapter,
`infrastructure/telegram_worker_status_store.py`, `telegram_worker_command.py`,
and the operator/runtime status models in `application/telegram_worker_status.py`,
`application/telegram_worker_liveness.py`, and `domain/telegram_worker_ops.py`.

Add a channel progress row, uniquely keyed by source channel, with these distinct
values and timestamps:

| Value | Meaning and permitted writer |
| --- | --- |
| `applied_high_water_id` | Greatest positively verified applied/terminal message ID; upsert atomically with canonical outcomes using a monotonic maximum. It is not completeness evidence. |
| `polled_through_id` | Upper boundary of a forward range whose fetched items have durable classified outcomes; only the polling coordinator advances it. Deferred/quarantined outcomes stay visible as unresolved work. |
| `sweep_after_id`, `sweep_upper_id` | Continuation and fixed upper bound for the current older-known-ID sweep; reset only on starting a new sweep, never confused with the monotonic forward cursor. |
| coverage state/times | Bootstrap state, last completed sweep, and source access/history limitations. Unresolved archive work prevents a false claim of complete canonical coverage. |

Use atomic conditional/upsert writes and the existing per-channel PostgreSQL
advisory lock. Acquire the local processing lock before reading progress, then
re-read authoritative state under the advisory lock before writing; run finish
order is never authoritative. Do not hold canonical DB transactions or the local
processing lock across provider backoff/network waits. Landing remains available
while another process owns canonical processing.

Forward traversal and canonical progress are independently recoverable: land
every fetched record before applying it; advance a polled batch boundary only
after all its records have committed canonical or explicit durable deferred/
quarantined outcomes. Pending retry work still makes coverage incomplete. A crash
before that boundary re-fetches idempotently. A passive high ID cannot advance
the polling boundary. A verified exhausted page may close the observed numeric
range, but a partial page, transport error, or access loss may not. Repeated
terminal records do not generate revisions or fresh completion timestamps.

Bootstrap `applied_high_water_id` from verified committed source/receipt evidence.
Legacy run checkpoints cannot prove polling coverage because they mix live and
archive processing. Unless trustworthy persisted traversal evidence exists,
initialize `polled_through_id` at zero and catch up in bounded ascending batches;
expose bootstrap/incomplete coverage throughout. Do not copy `MAX(message_id)`
or the last finished run into the traversal boundary. This costs bounded extra
reads but cannot silently skip an unobserved interval.

Publish named fields for both values in operator and runtime status, and update
the existing compatibility checkpoint field to mean `polled_through_id`. State
that meaning in the runbook. Keep runtime health JSON schema version 1 with
additive optional diagnostic fields and tolerant reads for old documents; core
liveness/readiness behavior stays unchanged. Use the progress row's commit/
traversal times rather than a late-finished run as freshness evidence. Existing
run rows remain diagnostic history.

## T2: fair retries and old-message coverage

Add `next_attempt_at`, `data_failure_count`, `deferral_count`, and retry-policy
version to raw work. Keep `attempts` as historical accounting; do not zero its
old values. Select eligible, non-terminal records for the configured channel by
`next_attempt_at`, then `received_at`, then UUID. Re-read under the channel lock
to reject stale selections; receipt uniqueness and terminal compare-and-set
protect concurrent selections without holding row locks across network calls.

| Condition | Durable action |
| --- | --- |
| Channel lock held, transport timeout/disconnection, rate deferral | Increment deferrals; do not consume data failures. Persist next eligibility. |
| Invalid source structure/checksum proof or ordering conflict | Increment data failures with a safe category; after five failures, quarantine and create/update one exception for that original UUID. |
| Authentication/channel identity/systemic storage failure | Pause or supervise/restart the affected channel with backoff; one channel incident, not a failure recorded against every row. |
| Cancellation | Propagate; leave receipt/pending state resumable without an artificial data failure. |

Transient delay is `min(300s, 5s * 2**(consecutive_deferrals-1))` plus uniformly
bounded positive jitter up to 20%, capped at 300 seconds before applying the
provider's retry-after as a minimum. Persist the resulting UTC due time once,
inject clock/randomness in tests, and cap exponent arithmetic. Data failures use
the same delay envelope but a distinct counter. Inspect wrapped persistence
causes at the adapter boundary so a DB connection failure is not misclassified
as malformed source data. Reset a consecutive transient streak only on real
successful progress, not on each worker restart.

Store one exception per original UUID with safe reason, evidence references,
policy/code version, first/last occurrence, state, and re-evaluation version.
Automatically re-evaluate after a relevant decoder/retry policy version change;
unchanged releases or timestamps do not reset five data failures forever. Proven
old `RunLockHeldError` exhaustion is rescheduled once by policy version with its
original attempts retained. Other legacy exhausted errors remain excluded unless
their causes can be safely classified. A channel-wide outage deduplicates to one
condition; successful recovery clears it without owner acknowledgement.

Use the existing reconciliation interval and at most 500 source IDs per cycle:
reserve up to 400 for forward catch-up and up to 100 for the older-known-ID sweep.
Each request batch is at most 100. A sweep snapshots its upper bound and resumes
from its persisted continuation; new records join the next sweep rather than
extending the current one forever. Persist a separate due time for source rate
deferral and honor it without sleeping under processing locks.

Extend the inward-owned Telegram client port and fake/Telethon adapters with a
bounded explicit-ID observation result: present message, confirmed deletion, or
unavailable/unknown. Validate actual adapter responses with deterministic tests;
omitted results, exceptions, and inaccessible history are unknown, never deletes.
Only an authoritative per-ID deleted/empty result from a successfully verified
channel can create a tombstone. If the provider cannot distinguish deletion from
inaccessibility in a case, report unknown and retain a coverage limitation.
Metadata rechecks do not download media. Lower-ID edits use T1 ordering and do
not lower either forward value. This covers retained known IDs over repeated
bounded sweeps; inaccessible history and never-observed deleted records remain
explicitly outside provable coverage. E8 passive callback evidence remains open
under its own task.

## Verification and acceptance evidence

| Scope | Required proof |
| --- | --- |
| T1 archive identity | Real PostGIS historical photo/entity/mixed-text record plus differently shaped terminal live sibling; two drains advance to the next oldest batch without re-landing, changing sibling attempts, or losing evidence. |
| T1 commit boundaries | Inject before commit, after commit/before acknowledgement, acknowledgement outage, and cancellation; restart produces one offer/revision effect and one original terminal transition. |
| T1 ordering/privacy | Old/new/edit/delete sequences, delete-before-create, exact known legacy projection, unprovable checksum mismatch, cross-channel/ID mismatch, equal-time conflict, protected offer fields, and no contact/path leakage. |
| T1 repair | Preflight matches the synthetic cohort; bounded apply balances receipts and source effects; applying again makes zero additional changes. An all-failure drain does not refresh completion health. |
| T2 concurrency | Deterministic delayed archive vs newer polling race and two database sessions; late run finish cannot reduce progress. A high passive ID cannot skip a polling interval. |
| T2 scheduling | More than five lock deferrals followed by success; poison beside healthy records; wrapped transient DB error; persisted due times across restart; one exhausted exception and one version-triggered re-evaluation. |
| T2 coverage | Crash during bootstrap/batch/sweep, old edits/deletes beyond the overlap, truncated page, and inaccessible source; no false traversal or deletion claim. Operator/runtime fields agree with committed state. |
| Migration/compatibility | Upgrade from the previous schema, old terminal rows, legacy lock failures, large synthetic pending population, no payload mutation, preserved constraints, and tolerant diagnostic readers. |

Extend `test_telegram_live_events.py`, `test_raw_event_archive_integration.py`,
`test_telegram_reconciliation.py`, `test_telegram_worker_ops.py`, existing
persistence/Telethon adapter suites, and focused integration cases as needed.
Use synthetic data, actual PostGIS constraints and transaction boundaries, fake
providers, fake clocks, and event barriers; do not rely on timing sleeps or a fake
archive that lacks unique keys. Verify architecture imports and both public
readiness and contact-redaction invariants. No public HTTP or frontend UI change
is planned; contract checks must confirm that assumption.

Install locked dependencies with `make install`. Before each push run `make lint`
and `make test`; also run `make format-check`, `make typecheck`, and
`make contract-check` for these backend/contract-affecting changes. Full tests use
disposable PostGIS; use an isolated Compose project/ports if other agents have a
stack running, and never reset a shared development or production database.
Required CI coverage floors and runtime-image/repository-safety checks still apply.
Record exact commands, results, exclusions, migration head, and reviewed SHA in
each PR. This plan does not claim those implementation tests have run.

## Release observation, rollback, and limits

Update `AI/ingestion/PIPELINE.md` with receipts, ordering, progress meanings, and
coverage limits, and `AI/operations/DEPLOYMENT.md` with preflight, pause/resume,
bounded activation, compatible migration order, and evidence queries. Runtime
configuration must use the repository's deployment-owned settings path; do not
depend on a hand-edited production environment file.

After authorized T1 release, observe a fixed 15-minute window with redacted
baseline/end counts: original cohort completions, remaining eligible cohort,
arrivals, deferrals/quarantine/exhaustion, oldest age, and stable terminal attempt
counters. Receipt transitions must reconcile with changed rows; source checksums
must remain intact. The old 27,656 count is an audit baseline, not a live count or
a claim of missing offers. Do not expand broad parser/geocoder recovery ahead of
T1 acceptance. T2 activation then verifies monotonic cursor/scheduling behavior
and bounded bootstrap/sweep progress. T3/T4 completion is not implied.

On identity mismatch, canonical regression, or systemic failure, persist pause and
stop the affected recovery worker. Retain live landing when safe and preserve
every receipt, cursor, retry, source, and media record. Roll back executable code
only to a release that respects the pause and cannot resume the known lossy loop;
if none exists, keep draining stopped and roll forward a fix. Do not downgrade
or delete the new evidence tables or rewind durable cursors to accommodate old
code. Additive schema rollback cannot undo canonical mutations; investigate a
bad effect through its retained receipt before any separately approved repair.
Off-host backup remains deferred under ADR-015; this plan makes no backup claim.

## Risks and invalidation

The chief risks are false sibling equivalence (T1 proof/quarantine), resurrection
after a missed delete (T1 durable tombstone), falsely certified ID gaps (T2 separate
traversal/coverage), retry storms (T2 persisted delay/limits), and expensive catch-up
(bounded batches, single worker, no repair provider calls). Evidence must make
each risk observable without storing source content in reports.

Return to spike approval if implementation needs broader automatic write
authority, relaxed evidence/privacy rules, a new dependency/provider, increased
provider spend, or altered source/deletion semantics. Return to plan approval for
material task/dependency, schema contract, retry budget, verification, rollout,
or rollback changes. File/symbol naming and non-semantic refactoring may follow
repository conventions without inventing new behavior. No unresolved deferred
decision is required for this two-task sequence.

## Approval checklist

- [x] Spike revision 2 has attributable owner approval and remains current.
- [x] Both sequence entries are promoted tasks at revision 2 with traceability.
- [x] T1 has no task dependency; T2 depends only on T1 with an enforceable stack.
- [x] Modules, persisted contracts, transaction boundaries, tests, limits, migrations, risks, rollout, and rollback are specified.
- [x] Provider/dependency, privacy, production-release, and follow-up scope boundaries are explicit.
- [x] No production code, tests, migrations, or disposable proof artifacts have been written.
- [x] Owner approved implementation plan revision 1 on 2026-09-05 under AD-049; exact approval metadata is recorded.

## Owner decision

The owner replied `continue I approve` directly to the request to approve this
plan revision 1 in Codex task `01a0710e-adaa-76f2-8bcd-07784c03e9b2`.
[AD-049](../../workflow/AUTONOMOUS_DECISIONS.md#ad-049-approve-e24-implementation-plan-revision-1)
records implementation authorization for T1 revision 2 followed by T2 revision 2.
Merge and production release authorization remain separate.

## Planning verification and changed files

On 2026-09-05, `python3 scripts/check_markdown_links.py` and `git diff --check`
passed. A read-only PyYAML validation using the existing backend environment
passed for all seven E24 workflow files: unique YAML keys, exact approval/plan
revisions, promotion uniqueness, blocked implementation gates, and the acyclic
four-task dependency closure. A wider inventory found an existing duplicate
E23-T2 definition in both proposed/promoted locations, confirmed present at HEAD;
the E24 validation does not claim that unrelated repository metadata is clean.
No application tests were run for this documentation-only preparation, and no
commit, push, PR, merge, or production operation has been performed.

The scoped documentation changes are:

- [E24 spike](SPIKE.md): revision 2 research and owner approval.
- [This implementation plan](IMPLEMENTATION_PLAN.md): revision 1 for T1/T2.
- [E24 workspace](README.md): planning state and promoted/follow-up task split.
- [E24-T1](tasks/E24-T1-terminate-original-archive-work.md): moved from its identically named `proposed-tasks/` file and refined to revision 2.
- [E24-T2](tasks/E24-T2-monotonic-cursors-and-fair-retries.md): moved from its identically named `proposed-tasks/` file and refined to revision 2.
- [Epic registry](../README.md): current E24 gates and audit-candidate counts.
- [M5 milestone](../../milestones/M5-production-maturity.md): current E24 planning status.
- [Audit file index](../../audits/2026-09-05-files.md): links follow the two promoted task files.
- [Autonomous decision log](../../workflow/AUTONOMOUS_DECISIONS.md): AD-048 records the owner-authored spike approval reply and its scope.
