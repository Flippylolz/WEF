---
schema: ai-workflow/proposed-task@1
id: E19-T1
epic: E19
title: "Groq AI foundation and guarded place-review backend"
status: proposed
revision: 4
actionable: false
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
source: "Owner request on 2026-08-30 for a Groq GPT-OSS place update/validation button based on raw descriptions"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E19-T1: Groq AI foundation and guarded place-review backend

## Outcome

The admin application can generate a minimized, structured Groq GPT-OSS 20B review
for one place and can apply owner-selected supported corrections atomically after
deterministic validation and stale-snapshot checks. The provider port/client also
supports separate versioned strict schemas for the dependent offer-enrichment task
without sharing domain mutation logic.

## Scope

- Add the provider-neutral application port, exact Groq Chat Completions adapter,
  operation-specific strict output schemas, prompt/schema versioning, and
  fail-closed error mapping.
- Add an owner-only reader for complete current source revisions linked through
  offer sources; mask contacts and enforce source/input bounds before transmission.
- Add the minimized, expiring `place_ai_review_runs` persistence model/migration.
- Add generate/apply interactors, field allowlist, deterministic normalization,
  Warsaw district validation, collision detection, optimistic concurrency,
  address/district-to-`needs_review` lineage, and minimized admin audits.
- Add disabled-by-default settings, secret/config validation, per-owner/per-place
  limits, token/latency outcome metrics, and fake-provider tests/evaluation corpus.

## Out of scope

- HTML, routes, buttons, or browser behavior (E19-T2).
- Batch selection, offer-field mutation, AI field provenance, or parser-gap
  reporting (E19-T3/E19-T4).
- Model-written coordinates, automatic application, location merge, offer edits,
  bulk review, chat/conversation state, tools, web search, or public APIs.
- Enabling production, paid usage, or approving Groq project data controls.

## Work

- Preserve dependency direction: admin application owns the request/result types;
  infrastructure owns SQLAlchemy and Groq HTTP details.
- Use complete selected descriptions but transmit only contact-masked text. Never
  persist or log prompt/output bodies.
- Ensure Apply locks/validates the proposal and location snapshot in one
  transaction and is idempotent for repeated form submission.
- Keep all Groq calls outside database transactions.

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
  token usage; production activation remains blocked on its approved threshold.

## Dependencies and gates

- E18-T2 is done and supplies the existing place console, point correction, auth,
  guards, lineage, and audit foundation.
- Requires explicit E19 spike approval, task promotion, and approved implementation
  plan before any code/migration/config work.
- Production activation additionally requires verified Zero Data Retention in the
  live Groq project plus the owner's free-tier-limit decision; that operational
  gate does not authorize code or paid usage.

## Risks and notes

The largest risks are privacy leakage, unsupported model corrections, stale writes,
and canonical-location collisions. The design contains them with pre-call masking,
strict schemas and validators, explicit owner apply, snapshot fingerprints, and a
fail-closed collision outcome.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
