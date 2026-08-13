---
schema: ai-workflow/task@1
id: E2-T2
epic: E2
title: "Implement candidate detection and typed extractors"
status: ready
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E2-T1]
requirement_ids: [P-002, P-003, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T18:58:46Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:58:46Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:58:46Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:58:46Z"
  evidence:
    - "E2-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/33 | merge 6e43d0a"
branch:
  required: true
  name: null
  task_id: E2-T2
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

# E2-T2: Implement candidate detection and typed extractors

> Ready under owner-approved spike and implementation-plan revision 3. Start only from the merged documentation gate on a dedicated task branch.

## Outcome

Convert accepted raw messages into deterministic, versioned listing-candidate decisions and complete typed extraction results while preserving exact provenance and unknown/conflicting evidence.

## Scope

- Add immutable candidate reason/score, source span, rule/version provenance, confidence, warning, typed range, contact, link, and listing-candidate domain values.
- Implement deterministic `e2-v1` development and unit candidate rules.
- Extract canonical market/content type, location/district, development name, apartment/parking/storage price ranges and currency, included-price flags, area, rooms, floor, delivery, Google Maps URLs, and contact spans.
- Reuse canonical catalog enums for market/content semantics.
- Preserve `RawMessage.text`, original text entities, and raw payload unchanged.
- Expand sanitized fixture/golden coverage and synthetic runtime-only contact cases.

## Out of scope

- Media grouping, reply association, or gallery ownership (E2-T3).
- Dry-run report persistence/operator wiring (E2-T4).
- Complete-export audit publication (E2-T5).
- Database/API/geocoding/media writes, media copies, live Telegram access, or production promotion.

## Implementation notes

- Rules are pure, ordered, locale-independent, and identified by parser/rule version.
- Candidate decisions expose every matched reason and score component, not only a boolean.
- Exact source spans use Python string offsets into preserved flattened text.
- Numeric values use `Decimal`; ranges preserve lower/upper bounds and never infer a midpoint or zero.
- Currency remains unknown unless explicit. Included-price flags are explicit facts rather than inferred availability.
- Multiple equal-confidence incompatible values produce a warning/reviewable null.
- Contact extraction preserves typed values internally; routine logs and committed fixtures do not expose real contact data.

## Acceptance criteria

- [ ] Golden fixtures produce expected candidate decisions, typed ranges, exact spans, rule/version provenance, confidence, and warnings.
- [ ] Development and unit templates classify canonical market/content types without duplicating catalog enums.
- [ ] Unknown, missing, ambiguous, and conflicting values remain null/reviewable and are never invented.
- [ ] Negative non-listings with overlapping price/location tokens do not become candidates.
- [ ] Unicode/whitespace, decimal comma/point, ranges, unknown/non-PLN currencies, links, and delivery variants are deterministic.
- [ ] Source text/entities/payload and checksums remain unchanged by detection/extraction.
- [ ] Committed Telegram fixtures remain sanitized and contact-free; contact spans are covered by synthetic runtime values.
- [ ] Domain/application architecture and full repository CI pass.

## Test plan

- Unit: domain invariants, spans, Decimal ranges, confidence, warnings, deterministic reason scores, parser/rule versions.
- Golden: development/unit variants, multilingual Unicode, whitespace, ranges/currencies, parking/storage, delivery, maps links, and null/conflict cases.
- Negative: announcements, service/empty records, token-overlap non-listings, malformed accepted boundaries, and availability-inference traps.
- Stability: JSON key order, locale/process timezone independence, repeated execution, and source immutability.
- Repository: Ruff, strict mypy, import-linter/negative probes, branch coverage, dependency audit, contracts, safety, and runtime images.

## Rollout and rollback

This is inert parser library code with no persistence or network side effect. Revert the task PR to roll back; no schema, data, or media cleanup is required.

## Ready checklist

- [x] Authoritative promoted task exists under `tasks/` and proposed source is removed.
- [x] Promotion metadata and owner-approved spike/implementation gates are recorded.
- [x] E2-T1 is `done`; dependency evidence is recorded.
- [x] Scope, acceptance, tests, dependencies, and rollback match approved revision 3.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated E2-T2 branch is created from the latest `main`.
- [ ] Branch and PR contain E2-T2 only; metadata is recorded.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
