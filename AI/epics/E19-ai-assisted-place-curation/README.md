---
schema: ai-workflow/epic@1
id: E19
title: "AI-assisted owner catalog curation"
status: done
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E19: AI-assisted owner catalog curation

## Outcome

The owner gains two Groq-hosted GPT-OSS 20B workflows: a per-place **Review with
AI** action with explicit field-by-field confirmation, and an owner-started
**Batch fill offer details** action that automatically applies eligible missing
offer fields without per-offer confirmation. The application—not the model—owns
all validation and writes. Every AI-filled offer field retains exact source and
parser-gap provenance, and offers with active AI-filled data show an
**AI-assisted data** label.

## Product and safety contract

- Only the fixed `owner` role can generate/apply a place review or control a batch.
  Ordinary signed-in users and anonymous visitors receive no mutation route or
  batch control.
- Applicable fields are `display_name`, `display_address`, and `district`.
  Normalization, hash calculation, Warsaw district validation, uniqueness checks,
  review-state transitions, and audits remain backend-authoritative.
- GPT-OSS 20B never writes coordinates. An address/district correction returns the
  location to `needs_review`; E18's map picker or the geocoding workflow verifies
  the point afterward.
- Generation and application are separate POST actions. Stale proposals,
  conflicting source revisions, expired proposals, and canonical-location
  collisions are rejected without changing data.
- Provider failure degrades only the AI control. Existing location administration
  and anonymous browsing continue normally.
- Batch autofill accepts one owner authorization for a bounded cohort and then
  applies only missing/unknown offer fields with unique exact source evidence,
  deterministic validation, and unchanged snapshots. It never overwrites existing
  values or changes identity, visibility, location, development, dates, or media.
- Current AI field origins and append-only outcome events are separate from parser
  provenance. Public/admin projections expose `data_origin="ai_assisted"`; admin
  reports group parser gaps by field/parser version and support guarded batch
  pause/resume/revert.

## Governing documents

- [ADR-012: Backend-centric modular monolith](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-016: Pseudonymous accounts and owner console](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [ADR-021: Cached provider-neutral geocoding](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md)
- [ADR-022: Groq-hosted GPT-OSS 20B for place review and offer enrichment](../../decisions/adr/ADR-022-use-groq-gpt-oss-for-place-review-and-offer-enrichment.md)
- [P-009: AI-assisted owner catalog curation](../../product/EXPERIENCE.md#p-009-ai-assisted-owner-catalog-curation)
- [Authentication, administration, and contact reveal](../../security/AUTH_ADMIN_CONTACTS.md)
- [Canonical data model and AI provenance](../../contracts/DATA_MODEL.md)
- [Public HTTP API](../../contracts/HTTP_API.md)
- [OpenAPI contract](../../contracts/OPENAPI.md)
- [Ingestion and parser feedback](../../ingestion/PIPELINE.md)
- [Data quality and readiness](../../data/QUALITY_AND_READINESS.md)
- [Delivery workflow](../../workflow/README.md)
- [AD-042](../../workflow/AUTONOMOUS_DECISIONS.md#ad-042-approve-e19-spike-revision-4)
  and [AD-043](../../workflow/AUTONOMOUS_DECISIONS.md#ad-043-approve-e19-implementation-plan-revision-1-and-green-ci-merge-sequence)

## Workspace state

- **Delivery priority:** E19 is complete on `main`. Production AI activation
  remains gated on Groq secret and verified Zero Data Retention.
- [Spike](SPIKE.md): revision 4 owner-approved under AD-042.
- [Implementation plan](IMPLEMENTATION_PLAN.md): revision 1 owner-approved under
  AD-043.
- [E19-T1](tasks/E19-T1-ai-place-review-backend.md): done through
  https://github.com/Flippylolz/WEF/pull/226 (1120312).
- [E19-T2](tasks/E19-T2-ai-place-review-console.md): done through
  https://github.com/Flippylolz/WEF/pull/227 (d8673dc).
- [E19-T3](tasks/E19-T3-batch-offer-enrichment-provenance.md): done through
  https://github.com/Flippylolz/WEF/pull/228 (45094ba).
- [E19-T4](tasks/E19-T4-ai-enrichment-controls-and-reporting.md): done through
  https://github.com/Flippylolz/WEF/pull/230 (d7afef6).

## Approval boundary

Spike revision 4 and implementation-plan revision 1 are owner-approved. Individual
task branches, CI, privacy, and one-task-per-PR rules still apply. Production AI
enablement additionally requires a supplied Groq secret and verified Zero Data
Retention; paid usage is not authorized. Missing credentials must not block
deploying the disabled-by-default implementation.
