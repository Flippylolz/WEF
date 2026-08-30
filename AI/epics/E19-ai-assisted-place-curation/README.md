---
schema: ai-workflow/epic@1
id: E19
title: "AI-assisted owner catalog curation"
status: selected
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

## Workspace state

- [Spike](SPIKE.md): revision 3 is complete and awaits explicit owner approval.
- [E19-T1](proposed-tasks/E19-T1-ai-place-review-backend.md): proposed and
  non-actionable.
- [E19-T2](proposed-tasks/E19-T2-ai-place-review-console.md): proposed and
  non-actionable; depends on E19-T1.
- [E19-T3](proposed-tasks/E19-T3-batch-offer-enrichment-provenance.md): proposed
  and non-actionable; depends on E19-T1.
- [E19-T4](proposed-tasks/E19-T4-ai-enrichment-controls-and-reporting.md): proposed
  and non-actionable; depends on E19-T2 and E19-T3.
- `IMPLEMENTATION_PLAN.md` does not exist yet. The workflow permits it only after
  spike approval and task promotion.

## Approval boundary

This workspace is documentation and research only. ADR-022 records the owner's
requested provider/model direction; it does not bypass spike approval,
implementation-plan approval, the one-task-per-branch rule, CI, or the explicit
production data-control decision.
