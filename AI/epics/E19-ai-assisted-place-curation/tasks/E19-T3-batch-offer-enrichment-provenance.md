---
schema: ai-workflow/task@1
id: E19-T3
epic: E19
title: "Batch offer autofill and parser-gap provenance"
status: in_progress
revision: 2
priority: P0
size: L
milestone: M5
dependencies:
  - E19-T1
requirement_ids:
  - P-009
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-022
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E19-T3-batch-offer-enrichment-provenance.md
  promoted_by: "Cursor Agent (owner-directed E19 mission under AD-042/AD-043)"
  promoted_at: "2026-08-30T21:36:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "Cursor Agent (AD-042)"
  verified_at: "2026-08-30T21:36:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Cursor Agent (AD-043)"
  verified_at: "2026-08-30T21:36:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (owner-directed E19 mission under AD-042/AD-043)"
  verified_at: "2026-08-31T00:00:00Z"
  evidence:
    - "E19-T1 merged as 1120312 / PR #226"
branch:
  required: true
  name: feat/E19-T3-batch-offer-enrichment-provenance
  task_id: E19-T3
  one_task_only: true
  created_at: "2026-08-31T00:00:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/228"
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

# E19-T3: Batch offer autofill and parser-gap provenance

## Outcome

One owner-authorized, bounded batch can fill eligible missing offer details without
per-offer confirmation. Every proposal and applied value is traceable to the exact
source revision/evidence offsets and parser version that missed it, supports guarded
rollback, and can be compared with later deterministic parser replay.

## Scope

- Add durable batch/checkpoint and immutable item-scope state, append-only AI field
  events, and current per-field origin persistence with migrations and explicit
  enum constraints.
- Select an immutable offer cohort from owner filters and process one offer per
  Groq request and one offer per database transaction.
- Allow only missing/unknown market type, currency, apartment/parking/storage price
  bounds and included flags, area/room bounds, floor, and delivery fields.
- Require provider-returned source revision identity plus verbatim non-contact
  evidence; uniquely resolve exact offsets and apply deterministic field validators.
- Add idempotent start/process/pause/resume and guarded batch-revert interactors,
  daily pacing/checkpoints, outcome metrics, minimized audits, and failure recovery.
- Invalidate active AI origins on source edits and integrate with E17 parser replay
  to record parser-confirmed or parser-conflicting outcomes.
- Add per-field evaluation gates so only fields meeting an owner-approved quality
  threshold can auto-apply in production; other valid suggestions are recorded but
  do not mutate canonical data. Until those thresholds exist, production automatic
  apply stays disabled with the shared feature/ZDR gates.

## Out of scope

- Owner/public HTML, public API projections, badges, reports, or export UI (E19-T4).
- Overwriting existing canonical values, bulk place correction, automatic location/
  development reassignment, content-type or visibility changes, source/contact/
  media edits, merges, or deletes.
- Automatically modifying parser code, accepting model output as ground truth,
  fine-tuning, or producing unreviewed parser fixtures.
- Groq's provider-side batch endpoint or paid-plan activation.

## Affected modules and contracts

- Admin application batch interactors and the T1 provider port's offer schema
- Catalog/ingestion persistence models and E17 replay comparison hook
- Alembic revisions for batches, items, field events, and current origins
- Domain docs in `AI/contracts/DATA_MODEL.md` and `AI/ingestion/PIPELINE.md`

## Implementation notes

- Use the E19-T1 provider port with an offer-specific prompt/schema; no provider
  call occurs inside a database transaction.
- Store no raw source text, prompt, provider response, evidence quote, contact, or
  raw provider error. Typed canonical values and exact immutable-source offsets are
  allowed provenance.
- Keep `OfferSource.extraction_json` parser-owned. AI current origins and historical
  events use separate tables and cannot relabel parser output.
- Derive offer-level `data_origin` from active current field origins rather than
  trusting a provider-returned status.
- Never overwrite a non-missing parser value.

## Acceptance criteria

- [ ] Only an authenticated owner can create/control a bounded batch; a single
  start POST authorizes eligible item writes without further confirmation.
- [ ] Batch scope is immutable, defaults to 20 offers, is capped at 200 queued
  offers per owner, and shares the 20-provider-requests/day free-tier budget.
- [ ] Every item is idempotent, resumable, independently transactional, and safe
  across worker crash, duplicate delivery, pause/resume, and feature disable.
- [ ] No existing non-null/non-unknown offer value is overwritten; fields outside
  the allowlist cannot be proposed or applied.
- [ ] Every applied field passes strict schema parsing, exact unique evidence lookup,
  source/offer snapshot checks, type/range/domain validation, and the approved
  per-field automatic-apply evaluation gate.
- [ ] Ambiguous evidence, conflict, stale state, invalid values, provider failure,
  and below-threshold fields produce bounded outcomes and no canonical write.
- [ ] Current origins identify offer/field/value, source revision/offsets, parser
  version at the miss, batch/run, provider/model/prompt/schema, and timestamps;
  append-only events preserve every state transition.
- [ ] Source edits invalidate and clear a still-matching AI canonical value; a
  mismatched value becomes a review conflict. Neither path erases provenance or
  serves a stale AI value.
- [ ] Guarded revert clears only values still equal to the selected batch's applied
  value and never overwrites later parser/owner changes.
- [ ] E17 replay match records `parser_confirmed` and moves current origin to the
  parser; mismatch records `parser_conflicting` and requires owner review.
- [ ] Unit, migration, Postgres integration, masking, prompt-injection, evidence-
  offset, stale/concurrent, crash/resume, revert, and fake-provider tests pass
  without external network or raw data fixtures.

## Test plan

- Unit: allowlist, missing-only, evidence resolution, revert guards, replay
  comparison.
- Integration: Postgres batch checkpoint, crash/resume, source-edit invalidation.
- Contract/migration: new provenance tables.
- End-to-end: none in this task (E19-T4).
- Security/operations: no raw source/prompt leakage; feature-disable stops the
  worker without affecting readiness.

## Rollout and rollback

May stack on E19-T1 in parallel with E19-T2. Production automatic apply stays
behind evaluation/ZDR/flag gates. Rollback disables the flag and uses guarded
revert for still-matching values.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision and is `satisfied`.
- [x] `implementation_gate` references the owner-approved current implementation-plan revision, which contains this task ID/current revision, and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is an ancestor PR recorded by `dependency_gate: stacked`.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] One new branch contains this task ID.
- [x] The branch and pull request contain this task only.
- [x] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
