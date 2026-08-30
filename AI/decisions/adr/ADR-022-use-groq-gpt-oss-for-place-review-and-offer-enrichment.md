---
schema: ai-docs/adr@1
id: ADR-022
title: Use Groq-hosted GPT-OSS 20B for place review and offer enrichment
status: accepted
date: 2026-08-30
supersedes: []
superseded_by: []
resolves: []
---

# ADR-022: Use Groq-hosted GPT-OSS 20B for place review and offer enrichment

## Decision

Start E19 on GroqCloud's free plan using the exact model ID
`openai/gpt-oss-20b` through Groq's OpenAI-compatible Chat Completions API. Keep
the provider behind an application-owned port so transport, prompting, and
response parsing do not become catalog or admin domain contracts. A later
provider or model change requires an ADR review but not a domain redesign.

E19 has two deliberately different application modes:

1. **Place review:** GPT-OSS 20B compares a place's current text fields with the
   selected current source descriptions and returns a structured proposal. A
   separate owner-confirmed interactor validates and applies selected place fields.
2. **Batch offer autofill:** one owner action selects a bounded offer cohort and
   authorizes processing. Each offer is sent in a separate provider request. Missing
   allowlisted offer fields that pass deterministic validation and exact source-
   evidence checks are applied automatically, without per-offer confirmation.

The model remains advisory in both modes. It may not call tools, write directly,
invent coordinates, change visibility/review status, merge records, or make data
public. Application interactors own every mutation and provenance write.

## Required API boundary

- Call `POST https://api.groq.com/openai/v1/chat/completions` from the backend
  only. `WEF_GROQ_API_KEY` never reaches HTML, JavaScript, a public endpoint,
  logs, fixtures, or committed configuration.
- Set `model="openai/gpt-oss-20b"`, `reasoning_effort="low"`, and an explicit
  bounded output limit initially. Do not use conversation state, streaming,
  tools, web search, file upload, or Groq's provider batch endpoint.
- Require strict JSON Schema Structured Outputs with `strict: true`. Reject
  refusals, incomplete responses, unknown fields, invalid enum values, and schema
  mismatches as failed reviews. Schema adherence does not make values factually
  or semantically correct. Backend validation is mandatory; place changes also
  require per-item owner confirmation, while batch offer fills must satisfy the
  narrower automatic boundary below.
- Treat every source description as untrusted quoted data. Source instructions
  cannot override the system message or output schema.
- Keep provider, model ID, and prompt/schema versions in each minimized operation
  record so later evaluation and rollback can distinguish behavior changes.

## Automatic batch boundary

Batch autofill may populate only currently missing or explicit-unknown offer fields:
`market_type`, `currency`, apartment/parking/storage price bounds and included
flags, area bounds, room bounds, `floor_label`, and `delivery_label`. It may not
change `content_type`, `visibility`, publication/source timestamps, source text,
contacts, location/development relationships, media, fingerprints, parser version,
or any non-missing canonical value.

For every proposed field, the provider returns a source revision identifier and a
verbatim non-contact evidence fragment. Before auto-apply, the backend must resolve
that fragment uniquely to exact offsets in the immutable source revision, validate
the typed value with existing domain rules, confirm the offer/source snapshot is
unchanged, and confirm the field is still missing. A model confidence score alone
never makes a field auto-applicable. Ambiguous evidence, conflicts, stale snapshots,
unsupported values, or existing values are skipped and recorded without mutation.

One owner submission is the batch authorization; there is no second confirmation
per offer. Processing is checkpointed, idempotent, paced under the shared provider
budget, and applies one offer per transaction. An owner can pause a batch and can
request a guarded rollback that clears only unchanged values written by that batch.

## Free-tier request budget

Groq currently publishes Free Plan limits for this model of 30 requests/minute,
1,000 requests/day, 8,000 tokens/minute, and 200,000 tokens/day. E19 deliberately
stays below those provider ceilings:

- Preflight every request and allow at most 5,500 input tokens plus 1,500 output
  and reasoning tokens, including prompts and schema. Do not send when the
  estimator cannot establish that the request fits.
- Select at most ten newest distinct current source revisions. Descriptions are
  included whole; omit the oldest whole descriptions until the token budget fits
  and show selected/omitted counts to the owner. Never cut a description in the
  middle.
- Limit generation to 20 provider requests per owner per day and one in-flight
  request per place/offer. Interactive and batch calls share this daily limit. A
  larger batch pauses at the limit and resumes on a later budget window. A rate-
  limit response pauses processing and is not retried automatically in the same
  window.
- Retry at most once only for a transient timeout or server failure when the
  request is safe to repeat. Never retry a refusal, validation failure, quota or
  rate-limit response, or other client error automatically.

Provider limits and free-plan availability are external, account-specific, and
may change. The live Groq console is authoritative before activation. Exhausting
the free allocation disables generation until capacity returns; it never changes
a place or applies the failed offer item, and it does not authorize paid usage.

## Data minimization

The input may contain the full text of selected current source-message revisions,
not the 280-character offer excerpt, because address evidence often appears later
in a message. Before transmission, reuse the server-side contact detector/masker
to replace phone numbers and Telegram handles. Do not send raw Telegram payload
JSON, entity metadata, media, contact values, account data, database credentials,
or unrelated offers.

Persist no raw prompt, raw provider response, or source text in the AI review
table or application logs. Persist only the bounded structured proposal, source
revision identifiers/checksums, input fingerprint, provider/model/prompt/schema
versions, token counts, latency/outcome, timestamps, owner/location IDs, and apply
state.

Groq states that inference inputs and outputs are not retained by default, while
usage metadata is retained and request content may be temporarily logged for
reliability or abuse investigation for up to 30 days. Production enablement
therefore requires the owner to enable and verify Zero Data Retention in the live
Groq project's Data Controls and confirm that sending contact-masked source
descriptions is permitted.

## Place change and safety boundary

AI-applicable fields are limited to `display_name`, `display_address`, and
`district`. The backend, not the model, canonicalizes the district, derives
`normalized_address` and its hash, fixes city/country to `Warszawa`/`PL`, checks
for an existing canonical-location collision, and enforces optimistic concurrency.

If an address or district changes, the location returns to `needs_review` through
the existing append-only geocode-selection lineage before it can be public again.
The existing point is retained only as owner evidence and is not treated as
verified for the corrected address. A display-name-only correction may preserve
the current geocode review state. Coordinate correction remains in E18's manual
picker or the existing provider-neutral geocoding flow.

Batch offer enrichment never invokes this place-correction path. It fills only the
missing offer fields listed above and never changes a location or geocode state.

## AI provenance and parser feedback

- Maintain a current field-origin record for every AI-applied offer field, linked
  to the offer, immutable source revision, exact evidence offsets, parser version
  that missed the value, batch/run, model, prompt/schema version, typed value,
  and apply timestamp.
- Maintain append-only events for proposed, applied, skipped, invalidated,
  rolled-back, parser-confirmed, and parser-conflicting outcomes. Do not replace
  the parser's existing `OfferSource.extraction_json` with model provenance.
- Project `data_origin="ai_assisted"` on an offer whenever at least one currently
  displayed field has an active AI origin. Admin and public offer presentations
  show an **AI-assisted data** label; admin views additionally identify each
  AI-filled field. Historical events remain after the label disappears.
- A source edit invalidates affected active AI origins and transactionally clears
  the canonical value only when it still equals the AI-applied value. A mismatch
  is marked conflicting for owner review. Stale AI values are never served.
- Parser-gap reports aggregate AI-applied/skipped fields by field, parser version,
  prompt/schema version, source revision, and outcome. Exact offsets let maintainers
  inspect retained source evidence and build reviewed parser fixtures without
  persisting prompt/response bodies or duplicate source text.
- Parser replay compares new deterministic output with active AI values. A match
  records `parser_confirmed` and transfers current origin to the parser; a conflict
  records `parser_conflicting` and requires review instead of silently overwriting.
  No model output automatically modifies parser code, rules, or training data.

## Operations and failure behavior

- The feature is disabled by default and fails closed when its flag, Groq API
  key, exact model configuration, or budget configuration is absent.
- CI and automated tests use a fake provider; they never call Groq.
- Batch workers are resumable and stop cleanly on feature disable, owner pause,
  daily budget exhaustion, or provider failure. Completed item transactions remain
  auditable; unprocessed items remain queued.
- Provider timeout, rate limit, refusal, malformed output, quota exhaustion, or
  network failure produces a visible owner outcome and changes neither a place nor
  the failed offer item.
- Log only minimized metadata. Never log prompt/output bodies or provider error
  bodies that could echo source text.
- Production rollback first disables the feature flag. AI availability never
  participates in application readiness and cannot block anonymous browsing.

## Official evidence checked 2026-08-30

- [OpenAI GPT-OSS 20B model documentation](https://developers.openai.com/api/docs/models/gpt-oss-20b)
  documents the open-weight model, Apache 2.0 license, configurable reasoning,
  Structured Outputs, and 131,072-token context window.
- [Groq GPT-OSS 20B model documentation](https://console.groq.com/docs/model/openai/gpt-oss-20b)
  identifies the hosted model ID and supported API behavior.
- [Groq Structured Outputs](https://console.groq.com/docs/structured-outputs)
  documents strict JSON Schema mode for `openai/gpt-oss-20b` and distinguishes
  structural guarantees from semantic correctness.
- [Groq rate limits](https://console.groq.com/docs/rate-limits) documents the
  published Free Plan request and token ceilings.
- [Groq data controls](https://console.groq.com/docs/your-data) documents default
  inference-content handling, retained usage metadata, temporary logging, and
  Zero Data Retention controls available to all customers.

Provider capabilities, limits, retention, and availability may change. Recheck
the linked official documentation and live account controls before production
activation and whenever the model, endpoint, data-control project, or plan changes.

## Consequences

The feature starts without an assumed paid provider budget and retains a small,
testable model boundary plus explicit owner-authorized mutation boundaries. The
free tier imposes a tighter per-request input budget and no availability guarantee.
The design still requires one external secret, review and enrichment provenance,
evaluation fixtures, and a privacy acceptance step. E19 spike revision 4 and
implementation-plan revision 1 are owner-approved under AD-042/AD-043. This ADR
still does not authorize paid usage or production enablement; those remain gated
on a supplied Groq secret and verified Zero Data Retention.
