---
schema: ai-workflow/spike@1
epic: E19
title: "AI-assisted owner catalog curation research"
status: awaiting_approval
revision: 4
owner: owner
research_only: true
code_allowed: false
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-021
  - ADR-022
domain_docs:
  - ../../product/EXPERIENCE.md
  - ../../architecture/SYSTEM.md
  - ../../security/AUTH_ADMIN_CONTACTS.md
  - ../../ingestion/GEOCODING.md
  - ../../ingestion/PIPELINE.md
  - ../../contracts/DATA_MODEL.md
  - ../../contracts/HTTP_API.md
  - ../../contracts/OPENAPI.md
  - ../../data/QUALITY_AND_READINESS.md
proposed_task_ids:
  - E19-T1
  - E19-T2
  - E19-T3
  - E19-T4
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: AI-assisted owner catalog curation research

## Question

How should the owner use Groq-hosted GPT-OSS 20B both to review canonical places
and to batch-fill missing offer details without per-offer confirmation, while
preserving exact AI provenance, exposing AI-assisted status, producing actionable
parser-gap evidence, and preventing unsafe model output from becoming writes?

## Context and constraints

- E18 already provides an owner-only `/admin/places` list and point editor behind
  `OwnerAuthProvider`, secure-cookie sessions, CSRF/origin checks, mutation rate
  limiting, application interactors, and minimized admin audit events.
- `locations` stores `display_name`, `display_address`, `normalized_address`, a
  unique `normalized_address_hash`, `district`, fixed Warsaw/PL identity, point,
  precision/confidence, review status, and scope state. Accepted rows must carry
  an in-scope point.
- The console currently shows only `offers.source_text_excerpt` (maximum 280
  characters). The complete current text is available from immutable
  `source_message_revisions.text_original`, joined to an offer through the exact
  revision anchor in `offer_sources`.
- Source text is untrusted and may contain phone numbers, Telegram handles, or
  prompt-like instructions. AI review/enrichment needs catalog evidence, not contact
  values, payload JSON, media, or source-platform metadata.
- ADR-022 selects Groq's Chat Completions API, exact model
  `openai/gpt-oss-20b`, strict Structured Outputs, no tools, and a backend-only
  provider port. Groq's published Free Plan limits the model to 8,000 tokens per
  minute and 200,000 tokens per day, so the application needs a substantially
  smaller request budget than the model's context window.
- Backend rules remain authoritative (ADR-012). AI output is a proposal, not
  verification, geocoding, or permission to publish.
- The owner additionally requires a batch option that applies eligible missing
  offer details after one batch-start action, without a second confirmation for
  each offer. This is a narrower automatic boundary than place correction: it
  cannot overwrite existing values or change location, visibility, or identity.
- No Groq or OpenAI SDK dependency may be added without owner approval. The
  existing `httpx` production dependency is sufficient for a narrow adapter, but
  the implementation plan must make the final dependency choice.

## Research method

Reviewed the current location, offer, source-message, source-revision,
offer-source, and geocode-lineage models; E18 admin application/store/view code;
owner authentication and mutation guards; deployment secret ownership; repository
workflow; official OpenAI GPT-OSS model documentation; and official Groq model,
API, Structured Outputs, rate-limit, and data-control pages. No provider call was
made, and no executable code or schema was created.

## Evidence

- Verified: `SourceMessageRevisionRow.text_original` is unbounded `Text` and
  immutable; `OfferSourceRow` identifies the exact revision supporting an offer.
  This is the correct evidence boundary for the requested raw description.
- Verified: E18's projection exposes only a 280-character excerpt, so the AI
  review reader needs a separate owner-only join. Public APIs must not gain this
  full text.
- Verified: the canonical district helper accepts a closed Warsaw district/alias
  set; the backend can reject a model-produced value outside that set.
- Verified: changing `normalized_address_hash` can collide with another canonical
  location. Automatic merge/reassignment would be a distinct, destructive
  workflow and must not be hidden inside Apply.
- Verified: an E18 unresolve transition can retain the old point while removing
  public eligibility. The same pattern safely preserves comparison evidence after
  an AI-assisted address correction.
- Verified from official OpenAI and Groq documentation (checked 2026-08-30):
  GPT-OSS 20B supports configurable reasoning and Structured Outputs; Groq hosts
  it as `openai/gpt-oss-20b`, supports strict JSON Schema output, and publishes
  Free Plan ceilings of 30 RPM, 1,000 RPD, 8,000 TPM, and 200,000 TPD.
- Verified: current offer fields store only a whole-offer `parser_version`, while
  `OfferSource.extraction_json` holds deterministic field-level parser provenance
  anchored to immutable revision offsets. AI provenance must remain separate so
  parser output is never relabelled as model output or vice versa.
- Verified: E17 parser replay can re-derive offers from retained raw events. AI gap
  records can therefore be compared with a later parser version without copying
  raw descriptions into a new training or analytics store.
- Uncertainty: repository code does not expose a reusable full-text contact
  masker at the admin reader boundary. Implementation may need to extract a small
  inward-owned masking port from the existing ingestion/contact logic; it must not
  duplicate masking rules in the view or provider adapter.
- Uncertainty: the Groq project's actual limits and Data Controls cannot be
  established from repository state. Groq states inference content is not retained
  by default, while usage metadata is retained and request content may be logged
  temporarily for reliability or abuse investigation. Production enablement must
  record that Zero Data Retention is enabled in the live project.

## Options considered

1. **Dual workflow: confirmed place review plus missing-only batch offer autofill
   (selected).** Place corrections retain preview/selection/apply. A separately
   started batch automatically fills only missing allowlisted offer fields when
   exact source evidence and deterministic validators agree. It provides the
   requested low-friction mode without giving the model general write authority.
2. **Embedded conversational chat.** A free-form multi-turn chat is flexible but
   introduces conversation persistence, ambiguous action intent, prompt history,
   and a larger data-retention surface. It is unnecessary for one bounded place
   validation and is rejected for the first version.
3. **Unbounded automatic correction.** Allowing AI to overwrite parser values or
   change places, visibility, or relationships would let a model error silently
   alter grouping and public map behavior. It is rejected.
4. **Suggestion-only batch.** This preserves per-offer confirmation but does not
   meet the requested batch autofill behavior. It is retained only as the outcome
   for conflicts and fields that fail automatic-apply rules.

## Recommendation

Treat E19 as the next delivery epic, ahead of E14, and assign P0 priority to all
four proposed task slices. This sequencing decision does not bypass spike or
implementation-plan approval: implementation can begin only after both gates
are approved for their current revisions.

### Owner flow

1. Add **Review with AI** beside the existing place actions. It opens an
   owner-only review page showing current fields and source coverage.
2. `POST Generate review` loads the current location plus at most ten newest
   distinct linked current source revisions. Selected descriptions are complete,
   not excerpted or cut mid-message. Preflight to at most 5,500 input tokens,
   including system instructions and schema; omit the oldest whole descriptions
   until the request fits and report selected/omitted counts visibly.
3. Replace detected phone/Telegram contact spans before transmission. Send no raw
   payload JSON, media, public account data, or unrelated location records.
4. Call GPT-OSS 20B with no tools or conversation state and require a strict schema:
   overall verdict (`no_change`, `corrections_proposed`, `conflicting_evidence`,
   `insufficient_evidence`); per supported field, current/proposed value, action,
   confidence, and source-revision evidence references; plus bounded warnings.
   The schema contains no coordinate, status, SQL, HTML, or generic tool field.
5. Render a field-by-field diff. No checkbox is selected by default. The owner
   chooses fields and submits `POST Apply corrections`.
6. Apply only if the proposal is pending/unexpired and the location timestamp,
   current source-revision IDs/checksums, prompt/schema version, and current values
   still match. Otherwise expire it and require regeneration.

### Batch offer-autofill flow

1. Add an owner-only **Batch fill offer details** page. The owner filters by
   missing fields, parser version, source age/channel, and offer visibility, sees
   the exact candidate count and daily-cap estimate, then submits **Start batch**.
   That single POST authorizes eligible writes; there is no per-offer confirmation.
2. Store a bounded, immutable batch scope and process one offer per provider
   request. Default to 20 offers and cap one owner's queued batch scope at 200;
   process at most 20 provider calls per day under the shared free-tier budget and
   resume from a durable checkpoint in later budget windows.
3. Allow only missing/unknown offer fields: market type; currency and apartment,
   parking, and storage price ranges/included flags; area/room ranges; floor; and
   delivery. Never overwrite a non-missing value or change content type, visibility,
   dates, source text, contacts, location/development, media, or parser version.
4. Require each field proposal to name an immutable source revision and return a
   verbatim non-contact evidence fragment. Resolve it uniquely to exact source
   offsets, validate the typed value, snapshot, and missing-state, then auto-apply
   it transactionally. Self-reported confidence is recorded but is insufficient.
5. Skip ambiguous, conflicting, unsupported, stale, or already-filled fields. The
   batch report distinguishes applied, no evidence, conflict, invalid, stale,
   provider failed, paused-budget, and untouched outcomes without showing contacts
   or raw provider content.
6. Provide Pause/Resume and guarded **Revert batch**. Revert clears only values
   still equal to that batch's AI-applied value and appends provenance/audit events;
   later owner/parser edits are never overwritten.

### Status and parser-learning loop

- Store current per-field origin separately from append-only enrichment events.
  Current origin links field/value to offer, source revision and exact evidence
  offsets, parser version at the miss, batch/run, provider/model, prompt/schema,
  and timestamps. Never rewrite `OfferSource.extraction_json` as AI provenance.
- Project an offer-level `data_origin` of `parser` or `ai_assisted`. Show an
  **AI-assisted data** badge on public offer cards/details and admin pages whenever
  at least one displayed field currently comes from AI; admin pages also mark the
  individual fields. This label is provenance, not a quality guarantee.
- Source edits invalidate affected AI origins and clear the canonical field only
  when it still equals the AI-applied value; a mismatch becomes a review conflict.
  Stale AI values are never served, while history remains queryable.
- Add owner-only parser-gap reports grouped by field, parser version, source and
  outcome, with a redacted export of IDs, typed expected values, and exact offsets.
  Maintainers deliberately review these records before adding synthetic/redacted
  parser fixtures or rules; no automatic training or parser-code generation occurs.
- On E17 replay, a matching new parser value records `parser_confirmed` and makes
  the parser the current origin. A mismatch records `parser_conflicting` and keeps
  the offer in an owner-review state rather than silently choosing either value.

### Backend validation and mutation

- Allowed model proposals: `display_name`, `display_address`, `district` only.
  Require non-blank bounded Unicode text; canonicalize district with the existing
  Warsaw helper; keep city/country fixed; derive normalized address/hash in
  project code; reject unknown district or canonical hash collision.
- A display-name-only change may keep the geocode state. Any applied address or
  district change moves the location to `needs_review`, appends a selection-lineage
  row with a new stable `ai_assisted_correction` reason and owner actor, preserves
  the old point only as comparison evidence, and requires E18/provider verification
  before public eligibility returns.
- Record minimized admin audits for generate/apply allowed, denied, and failed
  outcomes. Store no prompt, source text, response body, evidence quote, contact,
  or provider error body in logs or audit rows.
- Persist a short-lived `place_ai_review_runs` row containing only owner/location,
  state, model/prompt/schema versions, input fingerprint, source revision IDs and
  checksums, location snapshot version, structured proposed field values,
  confidence/verdict/warning enums, token counts, provider latency/outcome,
  request IDs, timestamps, and expiry/application state. Default expiry: 24 hours.
- Persist durable `offer_ai_enrichment_batches` plus immutable-scope items,
  append-only `offer_ai_field_events`, and current `offer_field_origins`. These
  contain typed field values and revision offsets but no raw source, prompt,
  provider response, evidence quote, contact, or provider error body.

### Provider and operations

- Settings: disabled-by-default feature flag, backend-only `WEF_GROQ_API_KEY`,
  exact model allowlist containing only `openai/gpt-oss-20b`, timeout, token
  preflight, and bounded retry/rate limits. GitHub Actions remains the deploy
  configuration owner; no value is committed.
- Call Groq's OpenAI-compatible Chat Completions endpoint with explicit
  `reasoning_effort="low"`, strict JSON Schema, no streaming, no tools/state, and
  at most 1,500 output/reasoning tokens. Retry at most once for a transient timeout
  or 5xx; never retry a rate/quota, validation, refusal, or other 4xx failure.
- Add a stricter owner AI-generation limit (initially 20/day and one in flight per
  place/offer) shared by interactive and batch modes. The combined planned
  request ceiling remains below 7,000 tokens to leave headroom under Groq's
  current 8,000-TPM Free Plan limit.
- Groq failure never affects readiness. Controls are disabled with a clear reason
  when configuration is absent; a failed request changes neither place data nor
  the failed offer item.
- Before production enablement, run a deidentified multilingual evaluation set
  (Polish/Russian/Ukrainian), including correct/no-change, correction, conflict,
  insufficient evidence, prompt injection, contact masking, duplicate-location,
  and stale-apply cases. CI uses a fake provider and no external network.
- Production batch enablement requires the evaluation to establish per-field
  automatic-apply eligibility. Fields below the approved precision threshold stay
  suggestion-only even when another field on the same offer is auto-applied.

## Proposed task boundaries

- **E19-T1 — AI place-review backend:** migration/review-run model, full-source
  owner reader with contact masking, Groq GPT-OSS provider port/adapter,
  structured schema, generate/apply interactors, lineage/audit/concurrency rules,
  settings, unit/integration/contract-free provider tests, and deidentified eval
  harness.
- **E19-T2 — AI place-review console:** owner-only routes and views, Review with
  AI action, source-coverage and diff UI, explicit field selection/apply,
  loading/error/stale/collision/accessibility states, HTTP/browser tests, and
  production activation/rollback documentation. Depends on E19-T1.
- **E19-T3 — Batch offer enrichment and provenance:** batch/run/current-origin
  migrations, missing-only allowlist, exact-evidence validation, checkpointed
  worker, auto-apply/rollback, source-edit invalidation, parser-replay comparison,
  audits, metrics, and fake-provider/evaluation tests. Depends on E19-T1.
- **E19-T4 — Batch controls, AI labels, and parser-gap reporting:** owner batch
  start/pause/resume/revert/report pages, public/admin AI-assisted labels, OpenAPI
  provenance projection, parser-gap report/export, browser/contract tests, and
  activation/rollback docs. Depends on E19-T2 and E19-T3.

## Risks and open questions

- **Provider data controls:** owner must enable and verify Zero Data Retention in
  the live Groq project before production enablement. Until then, the feature
  flag remains off.
- **Masking completeness:** detected contacts must be replaced before the provider
  call; tests include obfuscated phone/handle forms. If masking confidence is
  insufficient, fail the review rather than send the source.
- **Model hallucination:** strict field allowlist, evidence references, deterministic
  validators, no default selections, owner confirmation, and stale checks contain
  the risk; evals determine whether the feature is useful enough to enable.
- **Automatic batch writes:** one batch-start action intentionally replaces
  per-offer confirmation. Missing-only writes, exact evidence, per-field evaluation
  gates, one-offer transactions, pause/revert, immutable scope, and append-only
  provenance bound the blast radius.
- **Parser feedback contamination:** model output is a candidate expected value,
  not ground truth. Gap records remain separate from parser provenance and require
  maintainer review before becoming fixtures or rules.
- **Canonical collision:** Apply stops and tells the owner that a separate merge
  workflow is required. E19 does not move offers between locations.
- **Free-tier capacity/latency:** bounded source count/input/output, owner rate
  limit, and token/latency metrics keep requests below the published Groq Free
  Plan ceilings. Free availability is not an SLA; the feature fails closed when
  capacity is unavailable, and this spike does not authorize paid usage.
- **SDK choice:** use direct `httpx` unless implementation-plan review establishes
  that the official SDK materially reduces schema/error-handling risk and the
  owner approves the new production dependency.

## Invalidation triggers

- Changing from Groq-hosted `openai/gpt-oss-20b`, Chat Completions, the explicit
  place-preview/apply boundary, or the missing-only automatic batch boundary.
- Allowing batch overwrite of existing offer values or AI changes to coordinates,
  visibility/review status, content type, relationships, merges, or bulk place data.
- Sending unmasked contact values, raw payload JSON, media, or conversation state.
- A source-lineage/schema change that removes exact current revision evidence.
- Groq model/limit/data-control changes that invalidate ADR-022's capability or
  privacy assumptions.

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Evidence and uncertainty are distinguishable.
- [x] Affected decisions and domain documents are linked.
- [x] Proposed task boundaries and dependencies are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of
this spike revision permits task refinement/promotion and implementation planning;
it does not permit code, API spend, secret changes, or production activation.
