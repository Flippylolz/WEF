---
schema: ai-workflow/proposed-task@1
id: E19-T4
epic: E19
title: "AI enrichment controls, labels, and parser-gap reporting"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies:
  - E19-T2
  - E19-T3
requirement_ids:
  - P-009
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-022
deferred_decision_ids: []
source: "Owner request on 2026-08-30 for a batch autofill control, AI-filled offer label, and parser-improvement tracking"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E19-T4: AI enrichment controls, labels, and parser-gap reporting

## Outcome

The owner can start and operate bounded offer-autofill batches, inspect item/field
outcomes, and report parser gaps. Public and admin offer presentations clearly
label active AI-derived data without exposing prompts, source text, or internals.

## Scope

- Add owner-only batch candidate preview, start, progress, pause, resume, guarded
  revert, item-outcome, and parser-gap report/export pages.
- Show candidate count, immutable filters, estimated free-tier windows, processed/
  applied/skipped/failed/paused counts, and per-field origin/outcome details.
- Add `data_origin: "parser" | "ai_assisted"` to affected public offer projections,
  generated OpenAPI/frontend types, and list/detail UI.
- Show an **AI-assisted data** badge whenever any currently displayed field has an
  active AI origin; admin views additionally mark each field and its safe provenance
  metadata. The badge never implies verification.
- Add a redacted parser-gap report/export containing identifiers, typed expected
  values, source revision/offsets, parser/model/prompt/schema versions, and outcome,
  but no raw source text, contacts, prompt, provider response, or evidence quote.
- Add activation, monitoring, pause/disable, rollback, and provenance-retention docs.

## Out of scope

- Provider calls, selection/mutation rules, persistence, replay comparison, or
  rollback semantics owned by E19-T3.
- Public batch controls or public parser/provider internals.
- Automatic parser changes, model training, raw-source exports, or declaring
  AI-assisted data verified.

## Work

- Reuse owner authentication, CSRF/origin guards, no-store admin responses, request
  IDs, idempotency, rate limiting, audit conventions, and accessible POST/303 flows.
- Public responses expose only the coarse current `data_origin`; detailed origins,
  batch state, source IDs/offsets, and parser-gap records remain owner-only.
- Make absence of the badge mean only “no currently displayed AI-origin field,” not
  “AI was never attempted”; historical outcome reporting remains independent.

## Acceptance criteria

- [ ] Anonymous/non-owner users cannot reach batch/report routes or mutations;
  CSRF/origin and duplicate-submit protections cover every batch action.
- [ ] Candidate preview shows exact scope/count and warns that Start batch is the
  only confirmation before eligible fields are written automatically.
- [ ] Progress and terminal reports distinguish every E19-T3 outcome without
  exposing source bodies, contacts, prompts, responses, or provider error bodies.
- [ ] Pause/resume/revert are idempotent, accessible, clearly scoped, and show
  partial-completion and guarded-skip results accurately.
- [ ] Public offer list/detail responses and UI show `ai_assisted`/the badge exactly
  when a displayed active field is AI-origin; stale/invalidated-only history does
  not trigger the badge or leak stale values.
- [ ] Admin offer details identify individual AI-filled fields and safe origin
  metadata while parser-only fields retain their existing confidence presentation.
- [ ] Parser-gap reports group by field, parser version, source, outcome, and model/
  prompt/schema versions; the redacted export is bounded, audited, and owner-only.
- [ ] HTTP, browser, accessibility, OpenAPI, generated-type, status derivation,
  stale-origin, partial-batch, pause/revert, and authorization tests pass.
- [ ] Operations docs cover free-tier pacing, ZDR verification, worker health,
  feature-disable semantics, batch rollback, and provenance retention.
- [ ] `make lint`, `make format-check`, `make typecheck`, `make test`, and
  `make contract-check` pass.

## Dependencies and gates

- E19-T2 supplies the owner AI console patterns; E19-T3 supplies authoritative
  batch, origin, status, reporting, and mutation behavior.
- Requires explicit E19 spike approval, task promotion, and an approved
  implementation plan before public-contract or UI work.
- Production activation follows E19-T3's per-field evaluation and Groq ZDR gates.

## Risks and notes

A single offer may mix parser- and AI-derived fields. The coarse public badge is
therefore intentionally transparent but not a quality score; detailed field-level
origin stays owner-only to avoid presenting implementation internals as facts.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
