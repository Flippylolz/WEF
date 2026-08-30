---
schema: ai-workflow/task@1
id: E19-T1
epic: E19
title: "Groq AI foundation and guarded place-review backend"
status: draft
revision: 4
priority: P0
size: L
milestone: M5
dependencies:
  - E18-T2
requirement_ids:
  - P-009
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-021
  - ADR-022
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E19-T1-ai-place-review-backend.md
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
  verified_by: "Cursor Agent (AD-043)"
  verified_at: "2026-08-30T21:36:00Z"
  evidence:
    - "E18-T2 done through https://github.com/Flippylolz/WEF/pull/218"
branch:
  required: true
  name: null
  task_id: E19-T1
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

# E19-T1: Groq AI foundation and guarded place-review backend

## Outcome

The admin application can generate a minimized, structured Groq GPT-OSS 20B review
for one place and can apply owner-selected supported corrections atomically after
deterministic validation and stale-snapshot checks. The provider port/client also
supports separate versioned strict schemas for the dependent offer-enrichment task
without sharing domain mutation logic.

## Scope

- Add the provider-neutral application port, exact Groq Chat Completions adapter
  over existing `httpx`, operation-specific strict output schemas, prompt/schema
  versioning, and fail-closed error mapping. Do not add a Groq or OpenAI SDK.
- Add an owner-only reader for complete current source revisions linked through
  offer sources; mask contacts and enforce source/input bounds before transmission.
- Add the minimized, expiring `place_ai_review_runs` persistence model/migration.
- Add generate/apply interactors, field allowlist, deterministic normalization,
  Warsaw district validation, collision detection, optimistic concurrency,
  address/district-to-`needs_review` lineage, and minimized admin audits.
- Add disabled-by-default settings, optional secret/config validation, per-owner/
  per-place limits, token/latency outcome metrics, fake-provider tests, and a
  deidentified evaluation corpus. Activation requires the flag, Groq secret, exact
  model allowlist, and `WEF_GROQ_ZDR_VERIFIED`; absence must not break deploy or
  readiness.

## Out of scope

- HTML, routes, buttons, or browser behavior (E19-T2).
- Batch selection, offer-field mutation, AI field provenance, or parser-gap
  reporting (E19-T3/E19-T4).
- Model-written coordinates, automatic application, location merge, offer edits,
  bulk review, chat/conversation state, tools, web search, or public APIs.
- Enabling production, paid usage, or verifying Groq project data controls.

## Affected modules and contracts

- `apps/backend/src/wef_backend/settings.py`
- `apps/backend/src/wef_backend/features/admin/application/`
- `apps/backend/src/wef_backend/features/admin/infrastructure/`
- `apps/backend/migrations/versions/` after `20260829_0014_view_history`
- `apps/backend/tests/` for unit, integration, migration, authorization, and
  fake-provider coverage
- Optional fail-closed keys in `.env.example` and deploy config builders, never
  required for production validation
- Domain docs already describing the planned T1 persistence boundary

## Implementation notes

- Preserve dependency direction: admin application owns the request/result types;
  infrastructure owns SQLAlchemy and Groq HTTP details.
- Call `POST https://api.groq.com/openai/v1/chat/completions` with
  `model="openai/gpt-oss-20b"`, `reasoning_effort="low"`, strict JSON Schema, no
  streaming/tools/state, at most 5,500 input plus 1,500 output/reasoning tokens.
- Use complete selected descriptions but transmit only contact-masked text. Never
  persist or log prompt/output bodies.
- Ensure Apply locks/validates the proposal and location snapshot in one
  transaction and is idempotent for repeated form submission.
- Keep all Groq calls outside database transactions.
- CI never calls Groq; tests inject a fake provider.

## Acceptance criteria

- [ ] Only an authenticated owner application call can generate/apply; denied
  attempts create minimized denied audit events and no provider request/write.
- [ ] The provider request uses exact `openai/gpt-oss-20b`, Groq's Chat
  Completions API, low reasoning effort, no streaming/tools/state, at most 5,500
  input plus 1,500 output/reasoning tokens, and strict JSON Schema output.
- [ ] At most ten newest distinct current source descriptions are selected whole;
  the oldest whole descriptions are omitted until preflight fits, and generation
  is limited to 20 reviews per owner per day and one in flight per place.
- [ ] Full selected source descriptions are contact-masked before the call; raw
  payloads, media, contacts, account data, and unrelated places are absent.
- [ ] Provider timeout/refusal/quota/network/schema failures return a bounded error,
  record safe metadata, and make no location change.
- [ ] Only display name/address/district may be proposed or applied; the backend
  derives/canonicalizes all dependent fields and rejects unsupported fields,
  unknown districts, invalid text, and location collisions.
- [ ] Stale, expired, already-applied, or source-mismatched proposals cannot apply.
- [ ] Address/district application appends owner-attributed geocode lineage and
  returns the place to `needs_review`; no coordinate is changed or invented.
- [ ] Review persistence/logging contains no prompt, provider body, source text,
  evidence quote, contact, API key, or raw provider error.
- [ ] Unit, migration, Postgres/PostGIS integration, prompt-injection, masking,
  stale/concurrent apply, and fake-provider tests pass without external network.
- [ ] A deidentified multilingual evaluation report records schema success,
  supported-field precision, contact leakage, unsupported changes, latency, and
  token usage; production activation remains blocked on its approved threshold
  plus Groq secret and verified ZDR.
- [ ] Existing browsing, ingestion, location management, and readiness continue
  when Groq configuration is absent.

## Test plan

- Unit: generate/apply interactors, budget, token preflight, masking, collision,
  stale/expired apply, denied authorization.
- Integration: PostGIS generate/apply lineage, uniqueness collision, audit rows.
- Contract/migration: Alembic upgrade/downgrade of `place_ai_review_runs`.
- End-to-end: none in this task (E19-T2).
- Security/accessibility/operations: no key/source/prompt leakage; readiness
  independent of Groq; fake provider only.

## Rollout and rollback

Ship disabled-by-default. Optional Groq settings must not be required by
`validate_release`. Rollback uses the prior immutable image; unused review rows
are inert history.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision and is `satisfied`.
- [x] `implementation_gate` references the owner-approved current implementation-plan revision, which contains this task ID/current revision, and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`.
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
