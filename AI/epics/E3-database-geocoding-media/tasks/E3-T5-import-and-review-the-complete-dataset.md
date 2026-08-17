---
schema: ai-workflow/task@1
id: E3-T5
epic: E3
title: "Import and review the complete dataset"
status: done
revision: 3
priority: P0
size: L
milestone: M2
dependencies: [E2-T5, E3-T2, E3-T3, E3-T4]
requirement_ids: [P-001, P-002, P-005, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-021]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E3-T5-import-and-review-the-complete-dataset.md
  promoted_by: "Cursor Agent (owner-authorized after spike revision 3 approval)"
  promoted_at: "2026-08-14T00:42:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "Codex (owner-authorized)"
  verified_at: "2026-08-15T09:31:46Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 4
  verified_by: "Codex (owner-authorized)"
  verified_at: "2026-08-15T09:31:46Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex (owner-authorized)"
  verified_at: "2026-08-15T09:31:46Z"
  evidence:
    - "E2-T5 | done | merged PR https://github.com/Flippylolz/WEF/pull/42"
    - "E3-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/53"
    - "E3-T3 | done | merged PR https://github.com/Flippylolz/WEF/pull/59 | revision-4 gates revalidated 2026-08-15"
    - "E3-T4 | done | merged PR https://github.com/Flippylolz/WEF/pull/60"
branch:
  required: true
  name: feature/E3-T5-resumable-import
  task_id: E3-T5
  one_task_only: true
  created_at: "2026-08-15T09:31:46Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/65"
completion:
  completed_by: "ZCode agent (owner-directed)"
  completed_at: "2026-08-17T10:27:07Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/65"
  evidence:
    - "Implementation merged through PR https://github.com/Flippylolz/WEF/pull/65 (sanitized CLI proof, 260 backend + 33 frontend tests, contract/compose checks) with defect fix PR https://github.com/Flippylolz/WEF/pull/66 (migration 20260815_0008, pipeline identity e3-complete-v2)"
    - "Final local reconciliation recorded on merged PR #66: pipeline e3-complete-v2 terminal status succeeded; post-run dry run reports 27,170 unchanged with zero new/changed records, zero pending locations, and zero media work; 2,994 offers, 792 locations, 474 accepted locations, 9 no-result outcomes; media outcomes 23,173 stored / 3,952 unassociated / 55 missing / 55 unsupported; 24,532 restricted-original and 49,059 public-derivative files reconcile to logical assets/derivatives"
    - "Owner-verified 2026-08-16 snapshot identity recorded in E7 spike revision 4 (merged PR #68): source checksum 2399a88c70253c3f34b6ab73c423e094e7eb5f179ee9392b87ed715a74c6649d, schema 20260815_0008, 665 succeeded + 9 no-result provider attempts, 2,190,294,326 restricted-original bytes and 5,007,224,426 public-derivative bytes, final dry run unchanged"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E3-T5: Import and review the complete dataset

> Revision 3 completed the full local import/review on `feature/E3-T5-resumable-import` through PRs #65 and #66. The materialized snapshot is consumed by E7-T6; production was never mutated.

## Outcome

Once authorized, run the E2→E3 pipeline over the immutable complete export in resumable stages and publish non-sensitive evidence that canonical rows, reviewed pins, media dispositions, and storage/database integrity reconcile.

## Original roadmap definition

- Priority/size: P0 / L
- Dependencies: E2-T5, E3-T2, E3-T3, E3-T4
- Work:
  - Import raw/canonical records, geocode misses under policy, review ambiguous/out-of-area locations, and copy verified media.
  - Run integrity and storage checks.
- Acceptance:
  - Final import counts reconcile to the audited source.
  - Every visible pin has accepted coordinates and at least one dated offer.
  - Unparsed, ungeocoded, duplicate-suspect, out-of-area, and missing-media items remain reportable.

## Scope

- E2-T5 is satisfied through merged [PR #42](https://github.com/Flippylolz/WEF/pull/42). Consume and verify its recorded exact source size/SHA-256/parser/report identity before any E3 write.
- Add explicit operator modes for preflight, persistence, geocode/cache, review, media, and final verification. Geocode mode exposes bounded `batch_size` and `max_provider_requests` controls with safe defaults.
- Wire E2 outputs to the E3-T2 persistence, E3-T3 geocoder/cache/review, and E3-T4 storage contracts without duplicating their rules.
- Use one durable complete-import run/lease per exact source and pipeline-version identity. Each invocation claims or renews owner/fencing state, holds the source advisory lock while active, atomically checkpoints batches, and may resume or explicitly take over only after lease expiry.
- Keep each database unit bounded and checkpoint source/canonical rows, counts, and stage state atomically without releasing run ownership between units.
- Require revised E3-T3 completion after spike/plan revision 4 approval. Geoapify is the historical provider; LocationIQ is not a mandatory comparator.
- Reserve Geoapify daily budget durably before every hosted attempt, including retries, using provider, UTC date, and a non-secret configuration/account identity with the configured 2,700-request safety cap. A crash may conservatively consume a reservation but must never cause the cap to be exceeded.
- Allocate a globally spaced `not_before` call slot in the same reservation transaction, at least 250 ms after the prior slot, then perform HTTP after commit. This enforces the configured four requests/second across processes without holding a database transaction during the wait or call.
- Process a deterministic cache-first worklist in bounded batches. Cache hits and already-selected current-version results consume no provider budget or batch retry work.
- Treat local batch limits, the daily safety cap, provider `429`/quota responses, and operator cancellation as resumable paused states with a redacted reason and next eligible time. Resume recomputes unresolved work from durable cache/selection/version state rather than trusting an offset that could skip failures.
- Reconcile raw/current/revision, canonical offer/location/development, contact-free provenance, geocode cache hits/provider reservations/results/paused batches, selected geocode/review lineage, original media stored/missing/rejected/unsupported/unassociated dispositions, and per-variant derivative attempt/success/failure counts.
- Publish aggregate/redacted `IMPORT_AUDIT.md` evidence only; never commit source payloads, contact values/spans, paths, provider responses/secrets, media, databases, or detailed reports.

## Remaining dependency blockers

E3-T2 and E3-T4 are done. Revised E3-T3 completion plus spike/plan revision 4 approval are the remaining blockers. E2-T5 is done and is not an active blocker.

## Acceptance criteria

- [x] E2-T5's exact approved source checksum/size/parser/report identity is verified before writes and all audited records reconcile through the staged pipeline.
- [x] One durable run lease plus active source lock owns all bounded commits and stages; a second process cannot enter the same source run, while pause/resume/takeover obey explicit owner, expiry, and fencing rules.
- [x] Geoapify work runs cache-first in deterministic bounded batches, never exceeds four requests/second globally or the durable 2,700-request UTC-day safety budget, and reserves every attempt/retry before network I/O without holding a transaction during wait/HTTP.
- [x] Batch limit, daily quota, `429`, cancellation, crash, and expired-owner takeover tests resume from durable unresolved state without skipping work, duplicating accepted selections, or repeating avoidable hosted calls; conservative crash reservations may reduce that day's remaining budget but never exceed it.
- [x] Replaying every stage against the same versions converges without duplicate source/revision/offer/location/geocode/media/relationship/disposition rows or repeated avoidable provider/storage work.
- [x] Final counts reconcile to E2 reason/template/media buckets; every difference has a stable E3 status/reason.
- [x] Every visible pin references an accepted selected geocode result, is in scope, and links to a dated visible offer; review changes retain auditable actor/reason/version lineage.
- [x] Unparsed, conflicting, duplicate-suspect, ungeocoded, rejected/out-of-area, and stored/missing/rejected/unsupported/unassociated media categories remain queryable and appear in aggregate evidence.
- [x] Stored originals remain restricted; public integrity checks cover only derivatives, and the API/edge cannot resolve an original key/path.
- [x] A second complete run has identical non-timing terminal state and performs no avoidable hosted geocode or media copy; a multi-day continuation reaches the same state as one uninterrupted run.
- [x] Leakage tests prove contacts/`ContactSpan` values, source text/paths, provider secrets/responses, and media bytes remain absent from committed evidence, routine logs, CI artifacts, and images.
- [x] Local completion does not mutate production, enable inventory, delete seeds, or claim backup/recovery. Promoted-draft [E7-T6 revision 3](../../E7-production-delivery/tasks/E7-T6-transfer-and-import-the-historical-dataset.md) later transfers the verified materialized database/media snapshot without rerunning this pipeline.

## Test plan

- CI: sanitized E2 corpus through all stages, deterministic rerun, injected database/provider/storage/quota/`429`/cancellation/crash/takeover failures, contact canary/redaction scans, and repository gates.
- Local full import: exact E2 preflight, durable complete-run lease verification, persistence replay, quota-aware multi-batch Geoapify continuation, manual review, media dispositions/derivatives, final integrity/reconciliation, and deterministic second run.
- Database/storage: constraints/FKs/checkpoints, selected-result/review lineage, disposition attempts/reasons/versions, restricted-original/public-derivative separation, checksums/references/orphans, and disk usage.

## Dependencies and traceability

- Satisfied dependency: [E2-T5](../../E2-historical-export-parser-audit/tasks/E2-T5-audit-the-complete-export.md) — `done` through merged [PR #42](https://github.com/Flippylolz/WEF/pull/42).
- Satisfied dependencies: [E3-T2](E3-T2-implement-idempotent-persistence-and-reprocessing.md), [E3-T3 revision 3](E3-T3-implement-geocoder-abstraction-and-cache.md), and [E3-T4](E3-T4-implement-media-storage-and-derivatives.md) are done.
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
- Traceability: [Source baseline](../../../data/SOURCE_BASELINE.md), [Data readiness](../../../data/QUALITY_AND_READINESS.md), [Pipeline](../../../ingestion/PIPELINE.md), [Data model](../../../contracts/DATA_MODEL.md).

## Approval and start boundary

- Spike and implementation gates are satisfied by explicit owner approval of revision 4 artifacts and revised E3-T3 completion reconciliation.
- This task started from then-current `main` on dedicated branch `feature/E3-T5-resumable-import`; draft PR #65 targets `main` while the private import/review remains pending.
- Production transfer remains promoted-draft [E7-T6 revision 3](../../E7-production-delivery/tasks/E7-T6-transfer-and-import-the-historical-dataset.md), and public activation remains proposed E7-T11 behind the ADR-019 gates. Both consume the materialized local snapshot and must not rerun hosted geocoding or media transformations. E3-T5 authorizes only the approved local staged import and aggregate/redacted evidence.

## Affected modules and contracts

- See approved [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 4 and [DATA_MODEL.md](../../../contracts/DATA_MODEL.md).

## Implementation notes

Material departures from the owner-approved plan revision invalidate the affected approval; editing this section alone does not authorize them.

## Rollout and rollback

Follow the task sequence entry in [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md): dedicated branch from then-current `main`, PR targeting `main`, forward-only migrations, schema-compatible rollback only, no destructive data recovery claims. Production snapshot transfer remains promoted-draft E7-T6 revision 3.

## Completion evidence

- Implementation merged through [PR #65](https://github.com/Flippylolz/WEF/pull/65) with sanitized CLI proofs and full repository validation; defect fix [PR #66](https://github.com/Flippylolz/WEF/pull/66) widened source-derived location columns, released stale geocode claims on pause, inferred safe Telegram photo MIME candidates, and bounded media concurrency.
- Final local reconciliation (recorded on merged PR #66): pipeline `e3-complete-v2` terminal status `succeeded`; post-run dry run reports 27,170 unchanged records with zero new/changed records, zero pending locations, and zero media work; 2,994 offers, 792 locations (474 accepted), 9 no-result outcomes; media outcomes 23,173 stored / 3,952 unassociated / 55 missing / 55 unsupported; logical assets/derivatives reconcile exactly to 24,532 restricted-original and 49,059 public-derivative files.
- Owner-verified snapshot identity recorded in [E7 spike revision 4](../../E7-production-delivery/SPIKE.md) (merged PR #68): source checksum `2399a88c70253c3f34b6ab73c423e094e7eb5f179ee9392b87ed715a74c6649d`, schema `20260815_0008`, 665 succeeded + 9 no-result provider attempts, 2,190,294,326 restricted-original bytes, 5,007,224,426 public-derivative bytes.
- Aggregate/redacted evidence only: no source payloads, contact values, paths, provider responses/secrets, media bytes, or databases were committed.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved current spike revision 4 and is `satisfied`.
- [x] `implementation_gate` references owner-approved implementation-plan revision 4 containing E3-T5 revision 3 and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] One new branch contains this task ID.
- [x] The branch contains this task only; the pull request will be recorded after creation.
- [x] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
