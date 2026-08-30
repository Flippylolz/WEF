---
schema: ai-workflow/implementation-plan@1
epic: E19
title: "AI-assisted owner catalog curation delivery"
status: approved
revision: 1
owner: owner
spike_revision: 4
task_sequence:
  - id: E19-T1
    revision: 4
  - id: E19-T2
    revision: 3
  - id: E19-T3
    revision: 2
  - id: E19-T4
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: "Flippylolz"
  decided_at: "2026-08-30T21:36:00Z"
  approved_revision: 1
  evidence: "AD-043; owner instruction in Cursor session on 2026-08-30 authorizing creation and approval of E19 IMPLEMENTATION_PLAN.md revision 1 under AD-009, strictly within spike revision 4, ADR-022, P-009, and the four existing E19 task boundaries"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: AI-assisted owner catalog curation delivery

## Approved spike baseline

- [E19 spike revision 4](SPIKE.md) is owner-approved under AD-042 and remains
  current. This plan implements that revision's selected dual workflow without
  changing product, privacy, mutation, or provider boundaries.
- Binding decisions: [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md),
  [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md),
  [ADR-021](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md),
  [ADR-022](../../decisions/adr/ADR-022-use-groq-gpt-oss-for-place-review-and-offer-enrichment.md),
  and [P-009](../../product/EXPERIENCE.md#p-009-ai-assisted-owner-catalog-curation).
- Binding provider/transport choice: Groq Chat Completions at
  `POST https://api.groq.com/openai/v1/chat/completions` with exact model
  `openai/gpt-oss-20b`, `reasoning_effort="low"`, strict JSON Schema, no
  streaming/tools/state, existing production `httpx` only. No Groq or OpenAI SDK
  dependency is added.
- Binding mutation boundaries: place corrections require preview, field
  selection, validation, and explicit apply; batch offer enrichment requires one
  batch-start confirmation, fills only missing/unknown allowlisted fields, and
  never overwrites existing parser values.

## Scope and outcome

Deliver four independently reviewable changes so the owner can (1) generate a
contact-masked Groq GPT-OSS 20B place review from complete current source
descriptions, (2) preview and apply selected display-name/address/district
corrections, (3) start a bounded missing-only offer-autofill batch without
per-offer confirmation, and (4) operate pause/resume/guarded rollback, see
**AI-assisted data** labels, inspect parser-gap reports, and read coarse
`data_origin` on public offer projections.

Explicit exclusions: conversational chat; overwriting existing offer values;
model-written coordinates, visibility, content type, relationships, merges, or
bulk place mutation; Groq/OpenAI SDK; paid-plan activation; recovering or using
the previously removed OpenAI key; production AI enablement without a supplied
Groq secret and verified Zero Data Retention; mutating real offers merely to
demonstrate the feature.

## Ordered task sequence

1. [E19-T1](tasks/E19-T1-ai-place-review-backend.md) revision 4 — Groq foundation
   and guarded place-review backend. Independently reviewable as
   settings/port/adapter/migration/interactor work with no HTML or public-contract
   change. Depends on done E18-T2 (PR #218). Tests: unit, Postgres/PostGIS
   integration, migration, authorization, masking, prompt-injection, stale apply,
   fake-provider, and deidentified eval harness. Rollback: prior image; unused
   `place_ai_review_runs` rows are inert. Owns the shared provider port, budget,
   fake provider, and fail-closed settings used by later tasks.
2. [E19-T2](tasks/E19-T2-ai-place-review-console.md) revision 3 — owner Review
   with AI console. Independently reviewable as Starlette Admin HTML/POST/303
   routes over T1 interactors. Depends on E19-T1. Tests: HTTP authorization,
   CSRF/origin, accessibility, browser, feature-disabled, stale/collision. No
   public OpenAPI change. Rollback: prior image; disable the feature flag.
3. [E19-T3](tasks/E19-T3-batch-offer-enrichment-provenance.md) revision 2 — batch
   offer autofill and parser-gap provenance. Independently reviewable as
   application/persistence/worker behavior with no HTML. Depends on E19-T1 and
   may proceed in parallel with E19-T2. Tests: missing-only overwrite refusal,
   exact-evidence offsets, pause/resume/crash, guarded revert, source-edit
   invalidation, parser-replay comparison, fake-provider. Rollback: feature
   disable plus guarded revert of still-matching AI values; history remains.
4. [E19-T4](tasks/E19-T4-ai-enrichment-controls-and-reporting.md) revision 2 —
   batch controls, public/admin AI labels, OpenAPI `data_origin`, and parser-gap
   reporting. Independently reviewable as the remaining owner/public surfaces.
   Depends on both E19-T2 and E19-T3 being `done`; it does not start while either
   parent is only stacked, because both parents cannot be ancestors of one
   branch. Tests: contract, browser, accessibility, stale-origin badge, pause/
   revert UX, authorization. Rollback: prior image; public badge disappears when
   no active AI origin remains.

Stacking: T2 and T3 may stack on the T1 branch while T1 awaits merge. T4 waits
until T2 and T3 are merged. Merge dependency-first after required CI is green.

## Cross-task architecture

- Inward dependency: `admin.interface` renders HTML; `admin.application` owns
  review/batch request/result types, interactors, and provider/budget ports;
  infrastructure owns SQLAlchemy models and the Groq `httpx` adapter. Catalog
  query presenters derive coarse `data_origin` from active `OfferFieldOrigin`
  rows; they do not call Groq.
- The provider port is operation-specific: place-review and offer-enrichment
  schemas are versioned separately and share only transport, token preflight,
  retry/budget, and fail-closed error mapping. Domain mutation logic never lives
  in the adapter.
- Contact masking is an inward-owned reuse of existing ingestion/contact
  detection; views and the Groq adapter never duplicate masking rules.
- Groq calls stay outside database transactions. Place apply is one transaction
  over the pending review row plus location/lineage/audit. Batch processing is
  one offer per provider request and one offer per database transaction.
- `OfferSource.extraction_json` remains parser-owned. AI current origins and
  append-only events use separate tables.
- Public OpenAPI is unchanged until T4, which adds only required
  `data_origin: "parser" | "ai_assisted"`. Admin HTML stays outside OpenAPI.

## Data and migrations

- T1: Alembic revision after `20260829_0014_view_history` for expiring
  `place_ai_review_runs` (owner/location, state, model/prompt/schema versions,
  input fingerprint, source revision IDs/checksums, location snapshot version,
  structured proposed field values, confidence/verdict/warning enums, token
  counts, provider latency/outcome, request IDs, timestamps, expiry/application
  state). No prompt, source text, provider body, evidence quote, contact, or raw
  error body.
- T3: `offer_ai_enrichment_batches`, immutable-scope items, append-only
  `offer_ai_field_events`, and current `offer_field_origins` as specified in
  [DATA_MODEL.md](../../contracts/DATA_MODEL.md). Typed values and exact
  offsets are allowed; raw source/prompt/response/evidence quotes are not.
- T4: no additional tables. Public projections read current origins.
- Rollback of code cannot rewind append-only events or restore overwritten
  parser-miss gaps; guarded revert clears only values still equal to that
  batch's AI-applied value. Backups remain deferred (ADR-015).

## Security and privacy

- Owner session, CSRF, origin, mutation rate limit, and no-store admin responses
  remain mandatory. Anonymous and non-owner callers receive no review, batch, or
  report route.
- Source descriptions are contact-masked before transmission. Tests include
  obfuscated phone/handle forms; insufficient masking confidence fails the
  operation rather than sending the source.
- `WEF_GROQ_API_KEY` is backend-only, optional in production release validation,
  never required for deploy or readiness, and never committed, logged, or sent to
  the browser. The previously removed OpenAI key is never recovered or used.
- Activation is fail-closed: the feature remains off unless the disabled-by-default
  flag is on, a Groq secret exists, the exact model allowlist is
  `openai/gpt-oss-20b`, and `WEF_GROQ_ZDR_VERIFIED` is true after the owner
  verifies Zero Data Retention in the live Groq project. Missing credentials are
  an activation requirement, not a merge or deploy blocker.
- Logs and audits store only minimized metadata. Parser-gap export is owner-only
  and redacted.

## Test and verification strategy

- T1: unit interactors with fakes; Postgres/PostGIS generate/apply; migration;
  authorization denied-without-provider-call; masking; prompt-injection;
  stale/expired/collision apply; fake-provider schema/timeout/4xx/5xx; eval
  corpus for Polish/Russian/Ukrainian deidentified cases without network.
- T2: HTTP/browser/accessibility for generate/apply, disabled controls, CSRF/
  origin, escaped provider-like HTML, no-change/conflict/stale/collision.
- T3: missing-only refusal, evidence-offset uniqueness, crash/resume, pause,
  guarded revert, source-edit stale/conflict, parser_confirmed/parser_conflicting,
  daily budget pause, feature-disable stop.
- T4: OpenAPI/generated-type contract; public list/detail badge derivation;
  stale history does not badge; owner batch/report authorization; pause/revert UX.
- Every push: `make lint`, `make test`, `make format-check`, `make typecheck`,
  `make contract-check`, `python3 scripts/check_markdown_links.py`, and
  `git diff --check` on the change. Maintain the 90% per-suite coverage floor.
- Production after merge: automatic deploy health, anonymous browsing, `/admin`
  serving, and feature-disabled smoke. Do not call Groq and do not mutate real
  offers.

## Operations, rollout, and rollback

- Settings added as optional/fail-closed: `WEF_AI_CURATION_ENABLED` default
  false, `WEF_GROQ_API_KEY` optional, `WEF_GROQ_MODEL` allowlist exactly
  `openai/gpt-oss-20b`, `WEF_GROQ_ZDR_VERIFIED` default false, timeout, daily
  owner request cap 20, one in-flight per place/offer, max 5,500 input and 1,500
  output/reasoning tokens. GitHub Actions remains configuration owner.
- Production release validation must accept absent Groq values so ordinary
  deploys continue. Do not invent live-provider evidence.
- Groq never participates in `/health/ready`. Feature-disabled and
  provider-unavailable states leave browsing, ingestion, location management,
  and readiness unchanged.
- Rollout: documentation PR, then T1, then T2 and T3, then T4; squash-merge each
  green PR and delete the branch. Rollback: disable flags and redeploy the prior
  immutable release. Guarded batch revert is the data-scoped undo; it is not a
  backup.

## Risks and mitigations

- Privacy leakage → pre-call masking, fail-closed masking confidence, no raw
  bodies in persistence/logs, ZDR verification gate (T1).
- Hallucinated writes → strict allowlist, exact evidence, deterministic
  validators, no default place selections, missing-only batch, stale snapshots
  (T1/T3).
- Canonical collision → apply stops; E19 does not merge locations (T1).
- Free-tier exhaustion → shared 20-request/day cap, token preflight, pause at
  rate/quota, no paid usage (T1/T3).
- Parser contamination → separate origin tables, maintainer-reviewed gap
  records, replay comparison rather than silent overwrite (T3/T4).
- Missing Groq secret → disabled-by-default implementation still merges and
  deploys; activation remains an owner operations step (all tasks).

## Invalidation triggers

Return to the spike if provider/model, Chat Completions transport, place
preview/apply, missing-only batch, contact-masking, or exact current-revision
evidence changes, or if Groq data-control/limit changes invalidate ADR-022.
Return to this plan for material changes to task order, modules, schemas,
migrations, tests, activation gates, rollout, or rollback.

## Approval checklist

- [x] The referenced spike revision has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria
  and traceability.
- [x] Dependencies are complete, acyclic, and enforceable task by task.
- [x] Affected modules, contracts, tests, migrations, risks, rollout, and rollback
  are explicit.
- [x] Deferred decisions required for implementation are resolved.
- [x] No production or disposable proof code has been written.
- [x] `revision` represents the material plan being submitted.
- [x] Owner AD-043 approved this revision 1 under AD-009 continue authority.

## Owner decision

The owner recorded the decision in the YAML `approval` object on 2026-08-30
(AD-043; this Cursor session). Approval authorizes this plan revision; each task
still satisfies promotion, dependency, state, and one-branch-per-task gates.
Production AI enablement, Groq spend, and ZDR verification remain separate
owner operations steps.
