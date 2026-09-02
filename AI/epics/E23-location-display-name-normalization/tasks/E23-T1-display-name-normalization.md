---
schema: ai-workflow/task@1
id: E23-T1
epic: E23
title: "Add canonical location display-name normalization"
status: ready
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E17-T2]
requirement_ids: [P-002, P-003, P-007]
decision_ids: [ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E23-T1-display-name-normalization.md
  promoted_by: "Codex agent (owner-approved E23 spike revision 1)"
  promoted_at: "2026-09-02T17:34:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent"
  verified_at: "2026-09-02T17:34:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Codex agent"
  verified_at: "2026-09-02T20:32:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex agent"
  verified_at: "2026-09-02T17:34:00Z"
  evidence:
    - "E17-T2 done through https://github.com/Flippylolz/WEF/pull/208"
branch:
  required: true
  name: feat/E23-T1-display-name-normalization
  task_id: E23-T1
  one_task_only: true
  created_at: "2026-09-02T20:32:00Z"
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

# E23-T1: Add canonical location display-name normalization

## Outcome

New locations persist Polish-forward display names derived from source location
lines, without changing location identity (`normalized_address_hash`) or E18
verification state.

## Scope

- Extend location naming beyond whitespace collapse: strip bullets/emoji/
  decoration, map Cyrillic labels (`ул.` → `ul.`, drop `Улица:`, map `Район …`
  into district position), and prefer `street, district, Warszawa` ordering.
- Keep street tokens that are already Latin/Polish as written; do not invent
  transliterations.
- Preserve parser provenance for the source span used to build the display name.
- Cover the measured production name classes with unit fixtures.
- Apply only when creating a new location row (write-once for existing hashes).

## Out of scope

- Renaming existing locations (E23-T2).
- Near-suburb badge/filter product changes.
- Changing geocoding, review status, or public filter contracts.

## Acceptance criteria

- [x] Cyrillic-template fixtures normalize to Polish-forward display names.
- [x] Bullet/distance fragment fixtures do not become the whole display name when
      a usable street/district token remains.
- [x] `normalized_address_hash` is unchanged for identical parsed locations.
- [x] Existing hash hits still return the stored row without renaming.
- [x] Lint/tests for the touched ingestion path pass.

## Dependencies and gates

- Depends on completed E17-T2 raw-archive/replay lineage.
- Blocked on owner approval of [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) — satisfied at revision 1.
