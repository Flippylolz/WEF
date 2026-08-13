---
schema: ai-workflow/task@1
id: E2-T2
epic: E2
title: "Implement candidate detection and typed extractors"
status: done
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
  name: feature/E2-T2-candidate-extraction
  task_id: E2-T2
  one_task_only: true
  created_at: "2026-08-13T19:06:01Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/36"
completion:
  completed_by: "Cursor Agent (owner-authorized)"
  completed_at: "2026-08-13T19:15:07Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/36"
  evidence:
    - "Versioned e2-v1 candidate decisions expose stable weighted reasons, exact spans, thresholds, and canonical content types"
    - "Typed multilingual extraction covers market/content, location/district/development, apartment/parking/storage values, included flags, area, rooms, floor, delivery, Google Maps links, and internal contact spans"
    - "Sanitized extraction corpus plus runtime-only contact tests cover Unicode, decimal comma/point, ranges, explicit/unknown/non-PLN currency, conflicts, and negative non-listings"
    - "Local backend gates passed: Ruff, strict mypy, import-linter plus negative probes, 97 tests/4 PostGIS skips with 92.22% branch coverage, dependency audit, link and fixture safety"
    - "Initial task PR CI passed at 2822e6f: Backend, Frontend and contract, Repository safety, Runtime images | https://github.com/Flippylolz/WEF/actions/runs/31734663247"
    - "No source mutation, availability inference, database/API/geocode/media write, media copy, network call, or production activation; rollback is a PR revert"
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

- [x] Golden fixtures produce expected candidate decisions, typed ranges, exact spans, rule/version provenance, confidence, and warnings.
- [x] Development and unit templates classify canonical market/content types without duplicating catalog enums.
- [x] Unknown, missing, ambiguous, and conflicting values remain null/reviewable and are never invented.
- [x] Negative non-listings with overlapping price/location tokens do not become candidates.
- [x] Unicode/whitespace, decimal comma/point, ranges, unknown/non-PLN currencies, links, and delivery variants are deterministic.
- [x] Source text/entities/payload and checksums remain unchanged by detection/extraction.
- [x] Committed Telegram fixtures remain sanitized and contact-free; contact spans are covered by synthetic runtime values.
- [x] Domain/application architecture and full repository CI pass.

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

- [x] Status passed through `ready`.
- [x] Dedicated E2-T2 branch is created from the latest `main`.
- [x] Branch contains E2-T2 only; branch metadata is recorded.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
