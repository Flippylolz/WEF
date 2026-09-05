---
schema: ai-workflow/spike@1
epic: E24
title: "Automatic ingestion recovery"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015]
domain_docs:
  - AI/ingestion/PIPELINE.md
  - AI/operations/DEPLOYMENT.md
proposed_task_ids: [E24-T1, E24-T2, E24-T3, E24-T4]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-09-05T10:19:12Z"
  approved_revision: 2
  evidence: "Codex task 01a0710e-adaa-76f2-8bcd-07784c03e9b2: owner message 'continue' directly responding to the request to approve E24 spike revision 2; recorded in AI/workflow/AUTONOMOUS_DECISIONS.md#AD-048"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Automatic ingestion recovery

## Question

How can ingestion terminate archived work, maintain a monotonic source cursor, and recover dependent media without an operator repeatedly running repair commands?

## Context and constraints

New, edited, and deleted source messages converge into the catalog with durable archive and media completion. Routine contention, restarts, and transient failures recover automatically, and health measures progress rather than repeated work.

The owner selected this audit and requested minimal manual operation on 2026-09-05. Routine human approvals/actions are not the product recovery mechanism. Existing [repository governance](../../governance/REPOSITORY_RULES.md) and [delivery workflow](../../workflow/README.md) still govern implementation revisions and releases. No new production dependency, provider spend increase, destructive data repair, or topology change is implicitly approved.

Affected domain documentation:
- [AI/ingestion/PIPELINE.md](../../../AI/ingestion/PIPELINE.md)
- [AI/operations/DEPLOYMENT.md](../../../AI/operations/DEPLOYMENT.md)

## Research method and evidence

Reviewed current `main` at `9fc612fc77dd752bc936bcc6cf8c6a13fe7d22b6`, existing tests, and repository workflow/architecture documentation. Ran locked validation suites and inspected bounded read-only production/GitHub evidence. The [audit](../../audits/2026-09-05-system-audit.md) records command results and separates confirmed behavior from hypotheses.

Audit I1 confirms a replay identity mismatch: 27,656 eligible pending rows, 25 pending rows with alternate-checksum terminal siblings, and sampled copies processed over 20,000 times. I2 records inconsistent durable/runtime cursors and lock-contention failures. I3 identifies a media retry gap after canonical commit. Production containers were healthy despite this evidence.

Primary implementation seams:
- [apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py](../../../apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py)
- [apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py](../../../apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/raw_event_archive.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/raw_event_archive.py)
- [apps/backend/src/wef_backend/features/ingestion/application/telegram_reconciliation.py](../../../apps/backend/src/wef_backend/features/ingestion/application/telegram_reconciliation.py)
- [apps/backend/src/wef_backend/features/ingestion/application/live_media.py](../../../apps/backend/src/wef_backend/features/ingestion/application/live_media.py)

## Options considered

Leaving the current drainer and adding more retries would repeat the same checksum mismatch. A new external message broker would not fix acknowledgement semantics and would add an unapproved dependency. Manual replay can be an emergency tool but cannot be the normal completion mechanism.

## Recommendation

Keep the current PostgreSQL-backed design. Acknowledge the original archived event, preserve its immutable payload identity, establish a channel cursor independent of individual run finish order, and track media completion separately. Defer contention automatically; measure queue age and unique completions. Repair existing rows only after the identity fix has regression coverage.

The task files define proposed acceptance and rollout boundaries, not approval to implement. Policy, contract, migration, retry, and budget choices must be locked in the implementation plan after this spike is approved.

## Proposed task boundaries

The owner selected ingestion recovery on 2026-09-05 with the direction to start
E24-T1, then cursor and retry reliability (E24-T2). This records priority and
sequence; it does not invent a revision-specific approval. Revision 2 adds the
source-level decisions below for review before promotion and implementation
planning. T3 and T4 remain separate candidates.

- [E24-T1: Terminate original archive work and repair starvation](tasks/E24-T1-terminate-original-archive-work.md) — P1/L; dependencies: none; promoted after approval.
- [E24-T2: Make source cursors monotonic and retries fair](tasks/E24-T2-monotonic-cursors-and-fair-retries.md) — P1/L; dependencies: E24-T1; promoted after approval.
- [E24-T3: Recover media independently after message commit](tasks/E24-T3-recover-media-after-message-commit.md) — P1/L; dependencies: E24-T1.
- [E24-T4: Verify ingestion progress and automate recovery escalation](proposed-tasks/E24-T4-verify-progress-and-automate-recovery.md) — P1/M; dependencies: E24-T1, E24-T2, E24-T3.

## Source inspection and recommended corrective contracts

Read-only inspection on 2026-09-05 against fetched `origin/main`
`a2cdb16` confirms the audit's control-flow findings. These are recommendations
for approval, not implemented behavior or new production measurements.

### T1: preserve original archive identity through canonical persistence

- `record_to_live_event` drops media, entity, reply, and original text structure;
  `live_message_payload` adds `from_live`. Re-landing that representation is not
  an idempotent operation against the original checksum. Pass the original
  `RawEventRecord` through an explicit archive-processing boundary instead of
  making the drainer impersonate a newly received live event. Acknowledge its
  exact UUID; validate channel, message ID, event kind, and payload identity
  before persistence. A malformed record must never be applied to the worker's
  different configured channel.
- Decode archived payloads through the existing historical normalization rules
  into `RawMessage`; keep the stored payload/checksum unchanged. Preserve mixed
  text, entities, media descriptors, reply IDs, and source timestamps. Do not
  normalize archive evidence in place. `seed_from_history` currently flattens
  text while keeping the source checksum: new seeds must retain verbatim JSON,
  and existing seed mismatches need explicit provenance reconciliation, not
  silent checksum replacement.
- Keep the shared extraction/persistence path, with an archive-aware ordering
  guard inside the same channel lock and canonical transaction. The current
  `_persist_message` creates a revision for any changed checksum, with no source
  age comparison. Reject older source versions before they can overwrite a
  newer revision. Treat equal-time, differing semantic content as an unresolved
  conflict unless retained source evidence proves equivalence. Archive receipt
  time alone cannot prove which source revision is newer.
- Preserve deletion authority. `mark_source_deleted` currently returns `missing`
  without retaining a canonical tombstone when the message is absent. A retained
  archived delete must prevent later replay of an older message from creating an
  offer. Existing source tombstones must also prevent offer refresh from making
  deleted content visible. Include delete-before-create and delete-after-edit
  cases in the ordering contract, not only a stale update to an existing row.
- Return an explicit per-record result: applied, already canonical, intentional
  non-candidate, superseded/deleted, or unresolved conflict. Persist terminal
  outcome and correlated canonical revision/deletion evidence only after the
  canonical transaction commits. A sibling's channel/message/event kind alone
  is insufficient proof. Keep any additive outcome/evidence schema compatible
  with old readers and document its migration in the implementation plan.
- Make archive acknowledgement conditional on `processed_at IS NULL`. Today
  `mark_attempt` can increment a terminal sibling indefinitely or reopen it on a
  later failure. A terminal row must stay terminal, including a delayed failed
  attempt and a repeated successful acknowledgement. Retrying after a canonical
  commit but before acknowledgement must detect the already-applied revision
  and avoid creating another offer/revision. Cancellation must propagate; durable
  pending work is the restart mechanism, not a fabricated success or data error.
- Report attempted and uniquely completed work separately. The worker currently
  updates `last_event_committed_at` when `drain_once` returns any selected rows,
  including all-failure batches. T1 must remove this false completion signal;
  T4 owns broader progress health and escalation.

### T1: bounded reconciliation, before any broad backfill

Use the corrected archived-input path to reconcile originals. Do not run an
unconditional update that completes pending rows because terminal siblings exist.
Preflight is read-only and reports eligible/exhausted counts, oldest pending age,
candidate sibling correlations, unprovable conflicts, and proposed transitions.
Every applied transition must retain original UUID/checksum, previous state,
reason, and exact canonical evidence in restricted durable storage.

Recommended initial limits are one worker, 25 records per batch, a first canary
of 100 records, and no new external-provider calls for acknowledgement-only
reconciliation. Verify the canary, then continue through bounded batches with a
durable pause switch. A restart resumes pending work; repeated reconciliation
of the same completed cohort makes zero transitions. Separate unrelated new
arrivals when comparing cohorts. Stop automatic expansion on evidence mismatch,
canonical regression, or protected-value conflict. Do not delete originals,
siblings, revisions, contacts, or media to improve queue counts.

Before declaring T1 complete, use a 15-minute production observation window after
authorized release: report original pending IDs completed, remaining cohort size,
new arrivals, quarantined/exhausted exclusions, and terminal attempt-counter
stability. Read-only counts alone do not establish that 27,656 missing offers
exist. No production mutation, merge, or deployment is authorized by this spike.

### T2: a durable channel cursor and separate retry budgets

- `RawEventDrainer` reads its checkpoint before `processing_lock`; move the read
  under serialization. That local lock alone cannot protect another worker
  process. The channel advisory lock and database transaction must serialize
  authoritative cursor changes as well.
- Replace latest-finished-run authority with a durable channel progress record.
  Update monotonically in the canonical commit transaction; late completion of
  an older run must not change it. Runtime and operator status must read the same
  committed record. Retain run checkpoints as diagnostic history.
- Distinguish highest observed/applied message ID from the polling completeness
  boundary. A passive event above an unprocessed interval cannot certify that
  interval as traversed. Poll forward from a durable traversal boundary and
  advance it only after the fetched batch's outcomes commit. Gaps in Telegram
  numeric IDs are not themselves evidence of missing offers. Bootstrap from
  verified run/traversal evidence with a conservative fallback, never merely
  `MAX(source_messages.external_message_id)`.
- Apply lower-ID edits and deletes through the same canonical ordering rules
  without lowering either progress value. The existing forward overlap of 20
  IDs cannot prove recovery of arbitrary edits/deletes after an outage. Add a
  bounded older-message sweep using a durable continuation (recommended 100
  known IDs per cycle, at most 500 per cycle across forward/sweep work); do not
  infer deletion from an access failure or an incomplete page. Expose unsupported
  history or unresolved intervals as incomplete coverage. Preserve E8's separate
  passive-event acceptance requirement.
- Add durable per-record `next_attempt_at` and separate deferral and data-failure
  accounting. `RunLockHeldError`, transport failure, and provider rate deferral
  must not consume the five-attempt malformed-record budget. Recommended
  transient backoff is exponential from 5 seconds, capped at 5 minutes, with
  bounded jitter and provider retry-after respected as a minimum. Due work is
  selected by next eligibility then receipt time/UUID within the channel so a
  poisoned oldest record cannot monopolize every batch.
- Five data failures create one deduplicated exception tied to the original row,
  containing safe reason and evidence references. Re-evaluate on relevant code
  or policy version change; repeated unchanged data is not an infinite retry
  trigger. Existing `RunLockHeldError` exhaustion can be rescheduled through a
  bounded, audited transition; preserve its historical attempts. Repeated
  systemic/access failure pauses or slows the affected worker and produces one
  actionable condition, not thousands of per-record requests.

### Verification that must survive task promotion

T1 tests must use real PostGIS unique constraints and real canonical persistence,
not only `_FakeArchive`, which does not prove acknowledgement identity. Land a
historical payload containing photo/entity/mixed-text fields and a differently
shaped terminal live sibling. Drain a small batch twice: the original must
complete, the sibling must stay unchanged, and the next oldest records must be
selected. Check exact source evidence, source/offer/revision counts, terminal
attempts, and no archive row creation by replay.

Inject failures before canonical commit, after commit/before acknowledgement,
during acknowledgement, and cancellation at those boundaries. Verify restart
convergence, non-candidate outcomes, channel/ID mismatch rejection, old/new/edit/
delete ordering, delete of a not-yet-canonical message, and equal-time conflicts.
Validate preflight/apply/second-apply counts against the same seeded cohort.

T2 tests must control the race deterministically: suspend old archive work,
commit a newer polled batch, then resume the archive worker and finish its run.
Verify both durable cursor meanings and operator/runtime agreement. Include two
database sessions, lock deferrals beyond five cycles, poison beside healthy work,
retry eligibility across restart, deduplicated exhaustion, and outage recovery
with old edits/deletes outside the forward overlap.

Implementation must run the repository's lint, format, type, contract, migration,
and database-backed tests; `make lint` and `make test` are required before any
push. These tests have been specified here, not executed or claimed passing.

## Risks and open questions

Reconstructed historical payloads must not replace richer or newer source revisions. Completion must not skip genuine edits, deleted-source visibility rules, or media work. A connection failure can occur between canonical commit and acknowledgement; retries must converge. Historical pending counts include records that are already canonical and must not be treated as missing offers.

The implementer must resolve concrete schema/contract and accepted numeric budgets in the promoted task/plan revisions. Irreducible ambiguity, access loss, protected-field conflict, and destructive recovery are exceptional manual cases; transient errors and routine backlog work must resume automatically. Existing ADR-015 backup deferral remains unchanged.

## Invalidation triggers

Material changes to source semantics, geospatial confidence/precision claims, automatic write authority, schema/contracts, provider choice or cost, release trust boundaries, or the evidence supporting this recommendation return the spike to review. Task sequencing, test, rollout, or rollback changes follow implementation-plan revision rules after approval.

## Exit checklist

- [x] Bounded question answered with one recommendation.
- [x] Evidence and uncertainty distinguishable in the linked audit.
- [x] Affected modules/domain documents and decisions identified.
- [x] Proposed task scope, acceptance, dependencies, and exception handling recorded.
- [x] Outputs are documentation only; no production or disposable proof artifacts created.
- [x] Revision 2 approved by the owner on 2026-09-05; decision metadata and session evidence recorded.

## Owner decision

The owner replied `continue` directly to the request to approve spike revision 2
in Codex task `01a0710e-adaa-76f2-8bcd-07784c03e9b2`. This approves the presented
revision and permits task refinement/promotion and implementation planning.
[AD-048](../../workflow/AUTONOMOUS_DECISIONS.md#ad-048-approve-e24-spike-revision-2-and-prepare-the-first-implementation-plan)
records the decision and scope. Implementation-plan approval remains separate.
