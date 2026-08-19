---
schema: ai-workflow/task@1
id: E4-T3
epic: E4
title: "Implement offer detail"
status: in_progress
revision: 1
priority: P0
size: M
milestone: M2
dependencies: [E3-T4, E4-T2]
requirement_ids: [P-002, P-005, P-006, P-007, P-008]
decision_ids: [ADR-003, ADR-007, ADR-011, ADR-012, ADR-013, ADR-016]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E4-T3-implement-offer-detail.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-19T18:30:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T18:30:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T18:30:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T18:30:00Z"
  evidence:
    - "E3-T4 | done | merged PR https://github.com/Flippylolz/WEF/pull/60"
    - "E4-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/13"
branch:
  required: true
  name: feat/E4-T3-offer-detail
  task_id: E4-T3
  one_task_only: true
  created_at: "2026-08-19T18:30:00Z"
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

# E4-T3: Implement offer detail

> Promoted against approved [E4 spike revision 2](../SPIKE.md) and [implementation-plan revision 3](../IMPLEMENTATION_PLAN.md). Dependencies E3-T4 and E4-T2 are done.

## Outcome

Expose `GET /api/v1/offers/{offer_id}` with dated typed fields, server-masked public source text, field confidence indicators, location/development summary, ordered public media metadata/URLs, verified Telegram link metadata when available, and related source-history entries without leaking raw payload, contacts, paths, or unverified links.

## Scope

- Application query port/use case, SQL adapter joins across catalog and ingestion tables, presenter schemas, route wiring, OpenAPI export, generated frontend types, and focused unit/integration/HTTP tests.
- Reuse browse decoration for display name and coarse data confidence; serve persisted `source_text_public_masked` only.
- Build verified Telegram URLs only from configured `verified_link_base` or the verified `elestate_warszawa` username.
- Return same-origin opaque `/media/{storage_key}` URLs for succeeded public derivatives only.

## Out of scope

- Contact reveal, authentication changes, frontend detail UI (E5-T3), API hardening/performance (E4-T4), migrations, and production data transfer.

## Acceptance criteria

- [ ] `GET /api/v1/offers/{offer_id}` returns the public detail schema for visible offers on accepted in-scope locations and 404 otherwise.
- [ ] Responses include masked public source text, field confidence, location summary, optional development summary, ordered media metadata/URLs, source history, and verified source URL only when configured.
- [ ] No raw payload, local path, dedicated contact field, excerpt-only text, or unverified Telegram link is exposed.
- [ ] Missing media/link/source-lineage cases remain valid responses on synthetic M1 seed data.
- [ ] OpenAPI, generated TypeScript types, and catalog client helper are updated and checked in CI.

## Test plan

- Unit: confidence thresholds, verified-link policy, media URL builder, decoration.
- HTTP: 404 for missing/hidden offers, sensitive-field exclusion assertions.
- Integration: M1 seeded offer detail without source/media lineage.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] Spike and implementation-plan gates are satisfied for revision 3.
- [x] Dependencies E3-T4 and E4-T2 are done with a satisfied dependency gate.
- [x] Scope and acceptance criteria match the approved plan entry.

## Start checklist

- [x] Status passed through `ready` to `in_progress`.
- [x] Dedicated branch `feat/E4-T3-offer-detail` is created and recorded.
- [x] Branch contains E4-T3 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
