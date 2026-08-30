---
schema: ai-workflow/proposed-task@1
id: E19-T3
epic: E19
title: "Batch offer autofill and parser-gap provenance"
status: proposed
revision: 1
actionable: false
priority: P1
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
source: "Owner request on 2026-08-30 for batch AI autofill without per-offer confirmation and durable parser-improvement tracking"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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
  do not mutate canonical data.

## Out of scope

- Owner/public HTML, public API projections, badges, reports, or export UI (E19-T4).
- Overwriting existing canonical values, bulk place correction, automatic location/
  development reassignment, content-type or visibility changes, source/contact/
  media edits, merges, or deletes.
- Automatically modifying parser code, accepting model output as ground truth,
  fine-tuning, or producing unreviewed parser fixtures.
- Groq's provider-side batch endpoint or paid-plan activation.

## Work

- Use the E19-T1 provider port with an offer-specific prompt/schema; no provider
  call occurs inside a database transaction.
- Store no raw source text, prompt, provider response, evidence quote, contact, or
  raw provider error. Typed canonical values and exact immutable-source offsets are
  allowed provenance.
- Keep `OfferSource.extraction_json` parser-owned. AI current origins and historical
  events use separate tables and cannot relabel parser output.
- Derive offer-level `data_origin` from active current field origins rather than
  trusting a provider-returned status.

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

## Dependencies and gates

- E19-T1 supplies the configured provider client, common budget/error boundary,
  strict-schema transport, and fake provider.
- Requires explicit E19 spike approval, promotion, and an approved implementation
  plan before code/migration/config work.
- Production automatic apply additionally requires approved per-field evaluation
  thresholds, live Groq Zero Data Retention, and explicit batch feature activation.

## Risks and notes

The owner intentionally accepts no per-offer confirmation. Missing-only semantics,
exact evidence, per-field quality gates, immutable scope, one-offer transactions,
pause/revert, and append-only provenance are therefore mandatory rather than
optional hardening.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
