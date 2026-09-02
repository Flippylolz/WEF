---
schema: ai-workflow/task@1
id: E22-T1
epic: E22
title: "Add canonical property classification and safe backfill"
status: ready
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E17-T2]
requirement_ids: [P-002, P-003, P-007, P-010]
decision_ids: [ADR-005, ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E22-T1-property-classification-and-backfill.md
  promoted_by: "Codex agent (owner-approved E22 spike revision 1)"
  promoted_at: "2026-09-02T15:46:31Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent"
  verified_at: "2026-09-02T15:46:31Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Codex agent"
  verified_at: "2026-09-02T15:58:32Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex agent"
  verified_at: "2026-09-02T15:46:31Z"
  evidence:
    - "E17-T2 done through https://github.com/Flippylolz/WEF/pull/208"
branch:
  required: true
  name: null
  task_id: E22-T1
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

# E22-T1: Add canonical property classification and safe backfill

## Outcome

Offers persist an evidence-backed Apartment, House, Semi-detached house, or
Unknown classification, and operators can safely dry-run and idempotently backfill
historical records without changing unrelated catalog state.

## Scope

- Add the canonical `PropertyType` domain enum and non-null offer column/check
  constraint with a forward-compatible legacy default of `unknown`.
- Extend listing extraction, typed candidates, provenance JSON, fingerprints,
  persistence/upsert, seed/builders, raw replay, and operator reporting.
- Classify only explicit high-confidence multilingual source phrases. Prefer
  specific semi-detached evidence over generic house evidence and emit a stable
  conflict warning rather than choosing between categories.
- Add a bounded dry-run/apply backfill with aggregate classified/unknown/conflict/
  failure/change counts, parser version, idempotency evidence, and operational
  stop conditions.
- Update data model, ingestion pipeline, data-quality, and operator documentation.

## Out of scope

- API filters, facets, generated client changes, or public UI.
- External AI/provider calls, manual admin classification, or taxonomy expansion.
- Inferring from content type, numeric fields, address, development, photos, or
  other indirect signals.
- Changing visibility, availability, location, publication dates, media, contacts,
  or unrelated offer fields.

## Affected modules and contracts

- Catalog domain enums and `OfferRow` persistence constraints.
- Ingestion extraction domain/application, persistence adapter, provenance JSON,
  canonical fingerprint, replay command, and redacted operator report.
- The next Alembic migration after the current repository head.
- Sanitized parser/migration/persistence/replay fixtures and tests.
- Catalog data model, ingestion pipeline, quality/readiness, and operator docs.

## Implementation notes

- Store the value on each offer, never on location/development.
- Maintain a four-value stored/response enum and restrict filter input separately
  in E22-T2.
- Match specific semi-detached phrases before generic house phrases. Multiple
  category evidence fails to `unknown`; it never resolves by match order alone.
- The backfill must reuse source-anchored E17 replay and scope writes to property
  type plus its provenance.

## Work

- Define exact stable values and source-evidence rules with sanitized Polish,
  Russian, Ukrainian, and English positive, negative, and conflicting fixtures.
- Bump the deterministic parser version and maintain exact half-open source spans.
- Make old-application/new-schema and new-application/old-data transitions safe.
- Reuse E17 replay/source anchors; do not create a second historical import path.
- Review whether property type participates in existing AI field-origin machinery;
  deterministic parser provenance remains the required first implementation.

## Acceptance criteria

- [ ] Migration upgrades legacy offers to `unknown`, enforces the closed vocabulary,
  and rehearses downgrade locally without data truncation surprises.
- [ ] New and replayed offers persist one property type with exact parser evidence.
- [ ] Apartment, house, and semi-detached fixtures classify correctly across the
  supported source languages and case/punctuation variants.
- [ ] Ambiguous/conflicting/generic context produces `unknown` and a stable warning;
  no numeric or location heuristic assigns a type.
- [ ] Backfill supports dry-run and bounded apply, is idempotent, and emits only
  redacted aggregate evidence.
- [ ] Tests prove replay changes only property type/provenance and does not alter
  identity, visibility, location, dates, contacts, media, or unrelated fields.
- [ ] Coverage and conflict stop thresholds are documented for owner review before
  production apply.
- [ ] Data-model, ingestion, operator, and quality/readiness documents are current.

## Dependencies and gates

- E17-T2 is done and supplies source-anchored parser replay/re-import.
- Requires E22 spike approval, promotion, implementation-plan approval, satisfied
  dependency evidence, and a dedicated `feat/E22-T1-*` branch.
- Traces to P-002, P-003, P-007, P-010 and ADR-005/006/012.

## Risks and notes

The main risk is false confidence from generic “house/home/dom” text. Rules must
require property-bearing context and fail to `unknown`. Production coverage is an
acceptance input, not permission to guess. A low-coverage result may justify a new
owner-curation or AI-assisted proposal only through a later approved revision.

## Test plan

- Unit: multilingual positive/negative/conflict cases, exact source spans, enum
  validation, provenance serialization, fingerprint behavior.
- Integration: migration compatibility, new persistence, replay idempotency, and
  preservation of unrelated offer state.
- Contract/migration: upgrade existing rows to `unknown`, enforce the constraint,
  and rehearse downgrade locally.
- End-to-end: none; public contracts and UI belong to E22-T2/T3.
- Security/operations: redacted reports, bounded dry-run/apply, stop thresholds,
  and no source/contact leakage.

## Rollout and rollback

Deploy the additive migration and parser before running any historical write. Run
dry-run, review coverage/conflicts/failures, execute bounded apply, then rerun to
prove idempotency. A prior image is the code rollback; classifications persist.
Recovering incorrect production values requires an explicitly reviewed data
recovery operation rather than an automatic destructive downgrade.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under
  `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references approved E22 spike revision 1.
- [x] `implementation_gate` references an approved plan containing this task and
  revision.
- [x] E17-T2 is `done` with satisfied dependency evidence.
- [x] Scope and acceptance criteria match approved spike revision 1.
