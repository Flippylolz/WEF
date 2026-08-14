---
schema: ai-workflow/task@1
id: E3-T5
epic: E3
title: "Import and review the complete dataset"
status: draft
revision: 2
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
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-14T00:42:00Z"
implementation_gate:
  status: blocked
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: null
  verified_by: null
  verified_at: null
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E3-T5
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E3-T5: Import and review the complete dataset

> Promoted after owner-approved spike revision 3. Status remains `draft` until implementation-plan revision 3 is owner-approved and remaining gates are satisfied. No code may start from this file yet.

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
- Add explicit operator modes for preflight, persistence, geocode/cache, review, media, and final verification.
- Wire E2 outputs to the E3-T2 persistence, E3-T3 geocoder/cache/review, and E3-T4 storage contracts without duplicating their rules.
- Acquire a session-level source/channel advisory lock for the complete run, including across stage and batch commits. An alternative durable lease must remain renewable/owned with fencing semantics for the complete run.
- Keep each database unit bounded and checkpoint source/canonical rows, counts, and stage state atomically without releasing run ownership between units.
- Require E3-T3 completion, including the hosted Geoapify/LocationIQ comparison; an unresolved provider-input blocker cannot substitute for that dependency.
- Reconcile raw/current/revision, canonical offer/location/development, contact-free provenance, selected geocode/review lineage, original media stored/missing/rejected/unsupported/unassociated dispositions, and per-variant derivative attempt/success/failure counts.
- Publish aggregate/redacted `IMPORT_AUDIT.md` evidence only; never commit source payloads, contact values/spans, paths, provider responses/secrets, media, databases, or detailed reports.

## Remaining dependency blockers

Only E3-T2, E3-T3, and E3-T4 remain incomplete. E2-T5 is done and is not an active blocker.

## Acceptance criteria

- [ ] E2-T5's exact approved source checksum/size/parser/report identity is verified before writes and all audited records reconcile through the staged pipeline.
- [ ] One run-level lock/lease is held across all bounded commits and stages; a second process cannot enter the same source run between commits, while resume/takeover obeys explicit owner/fencing rules.
- [ ] Replaying every stage against the same versions converges without duplicate source/revision/offer/location/geocode/media/relationship/disposition rows or repeated avoidable provider/storage work.
- [ ] Final counts reconcile to E2 reason/template/media buckets; every difference has a stable E3 status/reason.
- [ ] Every visible pin references an accepted selected geocode result, is in scope, and links to a dated visible offer; review changes retain auditable actor/reason/version lineage.
- [ ] Unparsed, conflicting, duplicate-suspect, ungeocoded, rejected/out-of-area, and stored/missing/rejected/unsupported/unassociated media categories remain queryable and appear in aggregate evidence.
- [ ] Stored originals remain restricted; public integrity checks cover only derivatives, and the API/edge cannot resolve an original key/path.
- [ ] A second complete run has identical non-timing terminal state and performs no avoidable hosted geocode or media copy.
- [ ] Leakage tests prove contacts/`ContactSpan` values, source text/paths, provider secrets/responses, and media bytes remain absent from committed evidence, routine logs, CI artifacts, and images.
- [ ] Local completion does not mutate production, enable inventory, delete seeds, or claim backup/recovery.

## Test plan

- CI: sanitized E2 corpus through all stages, deterministic rerun, injected database/provider/storage/cancellation failures, contact canary/redaction scans, and repository gates.
- Local full import: exact E2 preflight, complete-run lock verification, persistence replay, mandatory completed geocoder path, manual review, media dispositions/derivatives, final integrity/reconciliation, and deterministic second run.
- Database/storage: constraints/FKs/checkpoints, selected-result/review lineage, disposition attempts/reasons/versions, restricted-original/public-derivative separation, checksums/references/orphans, and disk usage.

## Dependencies and traceability

- Satisfied dependency: [E2-T5](../../E2-historical-export-parser-audit/tasks/E2-T5-audit-the-complete-export.md) — `done` through merged [PR #42](https://github.com/Flippylolz/WEF/pull/42).
- Remaining task dependencies: [E3-T2](E3-T2-implement-idempotent-persistence-and-reprocessing.md), [E3-T3](E3-T3-implement-geocoder-abstraction-and-cache.md), [E3-T4](E3-T4-implement-media-storage-and-derivatives.md)
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
- Traceability: [Source baseline](../../../data/SOURCE_BASELINE.md), [Data readiness](../../../data/QUALITY_AND_READINESS.md), [Pipeline](../../../ingestion/PIPELINE.md), [Data model](../../../contracts/DATA_MODEL.md).

## Approval and start boundary

- Spike gate is satisfied for revision 3. Implementation remains blocked until owner approval of implementation-plan revision 3 and remaining dependency/deferred gates required by the workflow.
- After authorization and completed dependencies, this task starts from then-current `main` on a dedicated E3-T5 branch and opens a PR targeting `main`.
- Production transfer/activation remains E7-T6. Code, private-data access, import runs, migrations, and destructive operations remain out of scope while status is `draft` and the implementation gate is blocked.

## Affected modules and contracts

- See the approved/awaiting [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 3 sequence entry for this task and [DATA_MODEL.md](../../../contracts/DATA_MODEL.md).

## Implementation notes

Material departures from the owner-approved plan revision invalidate the affected approval; editing this section alone does not authorize them.

## Rollout and rollback

Follow the task sequence entry in [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md): dedicated branch from then-current `main`, PR targeting `main`, forward-only migrations, schema-compatible rollback only, no destructive data recovery claims.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision 3 and is `satisfied`.
- [ ] `implementation_gate` references the owner-approved current implementation-plan revision containing this task ID/current revision, and is `satisfied`.
- [ ] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is a valid stacked ancestor; every deferred gate required for start is resolved per the approved plan.
- [ ] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains this task ID.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
