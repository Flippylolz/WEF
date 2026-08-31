---
schema: ai-workflow/task@1
id: E19-T4
epic: E19
title: "AI enrichment controls, labels, and parser-gap reporting"
status: in_progress
revision: 2
priority: P0
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
promotion:
  source: ../proposed-tasks/E19-T4-ai-enrichment-controls-and-reporting.md
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
  verified_by: "Cursor Agent (E19-T4)"
  verified_at: "2026-08-31T05:45:00Z"
  evidence:
    - "E19-T2 done through PR #227"
    - "E19-T3 done through PR #228 (45094ba)"
branch:
  required: true
  name: feat/E19-T4-ai-enrichment-controls-and-reporting
  task_id: E19-T4
  one_task_only: true
  created_at: "2026-08-31T05:45:00Z"
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

## Affected modules and contracts

- Admin HTML batch/report views
- Catalog presenters, OpenAPI, generated frontend types, offer card/detail UI
- `AI/contracts/HTTP_API.md`, `AI/contracts/OPENAPI.md`,
  `AI/product/EXPERIENCE.md`, operations docs

## Implementation notes

- Reuse owner authentication, CSRF/origin guards, no-store admin responses, request
  IDs, idempotency, rate limiting, audit conventions, and accessible POST/303 flows.
- Public responses expose only the coarse current `data_origin`; detailed origins,
  batch state, source IDs/offsets, and parser-gap records remain owner-only.
- Make absence of the badge mean only “no currently displayed AI-origin field,” not
  “AI was never attempted”; historical outcome reporting remains independent.
- Candidate preview must warn that Start batch is the only confirmation before
  eligible fields are written automatically.

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

## Test plan

- Unit: `data_origin` derivation from active origins.
- Integration: public projection and admin report queries.
- Contract/migration: OpenAPI `data_origin` required enum.
- End-to-end: public badge on list/detail; owner batch preview/start/pause/revert
  with fake provider; accessibility of controls.
- Security: non-owner denial; redacted export contents.

## Rollout and rollback

Starts only after E19-T2 and E19-T3 are `done`. Production remains feature-disabled
until Groq secret and ZDR are verified. Rollback is the prior image; public badges
disappear when no active AI origin remains.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision and is `satisfied`.
- [x] `implementation_gate` references the owner-approved current implementation-plan revision, which contains this task ID/current revision, and is `satisfied`.
- [ ] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is an ancestor PR recorded by `dependency_gate: stacked`.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains this task ID.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
