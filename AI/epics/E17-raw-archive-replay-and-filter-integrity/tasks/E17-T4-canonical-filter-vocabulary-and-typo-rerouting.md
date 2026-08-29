---
schema: ai-workflow/task@1
id: E17-T4
epic: E17
title: "Canonical filter vocabulary and typo rerouting"
status: done
revision: 1
priority: P1
size: M
milestone: M5
dependencies: []
requirement_ids: []
decision_ids: []
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E17-T4-canonical-filter-vocabulary-and-typo-rerouting.md
  promoted_by: "ZCode agent under owner instruction"
  promoted_at: "2026-08-29T17:10:10Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
dependency_gate:
  status: satisfied
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
  evidence: []
branch:
  required: true
  name: feat/E17-T4-canonical-filter-vocabulary-and-typo-rerouting
  task_id: E17-T4
  one_task_only: true
completion:
  completed_by: "ZCode agent under owner instruction"
  completed_at: "2026-08-30T00:00:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/201"
  evidence:
    - "Write-time canonical district vocabulary with reviewed typo rerouting, variant-expanding filter matching, canonical facet collapsing."
    - "PR #201 merged after Backend, Frontend and contract, Repository safety, Runtime images, and Coverage badge checks passed"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---


# E17-T4: Canonical filter vocabulary and typo rerouting

## Outcome

Filter facets are served exclusively from a backend-owned canonical Warsaw district
vocabulary with a reviewed typo/reroute table, so options like `BiałOłęCka`,
`BiałOłęKa`, and `Praga PołUdnie` can no longer appear as duplicates, and the
frontend applies no filter logic of its own beyond rendering backend options.

## Scope

- Write-time canonicalization: the labeled district path stores the canonical name
  (today only the `e2-v4` pin-line path does), preserving raw source text in the
  location's display/lineage fields — never as the filter value.
- Reviewed alias/reroute table for genuine variants that folding cannot fix, seeded
  from production evidence: `Praga Południe` → `Praga-Południe`,
  `Praga Północ` variants, `BiałOłęCka` → `Białołęka` (letter typo), plus
  space/hyphen normalization for hyphenated districts. The table is an in-repository
  reviewed list (auditable, versioned), not an admin-editable free-form mapping.
- Facet serving returns canonical values only, deterministically ordered by the
  backend; matching accepts canonical values (and reroutes legacy values from
  persisted URLs through the alias table rather than 404-ing shared links).
- Frontend changes are limited to rendering the backend contract verbatim: no
  client-side dedupe, case-folding, or option derivation; remove any residual
  locale-dependent ordering of backend-provided options.
- Generated API contract updated (`contract-generate`/`contract-check`).

## Out of scope

- New filter dimensions (rooms/market/content stay as-is), geocoding changes, and any
  vocabulary beyond Warsaw districts.

## Work

- Canonicalization and rerouting live in the ingestion/catalog domain layer
  (single source beside `canonical_warsaw_district`); persistence, facet queries,
  and filter matching consume the canonical form only.
- Existing mixed-case stored values are repaired by the E17-T2 replay/E17-T6 backup
  re-import rather than a one-off migration.

## Acceptance criteria

- [ ] Given source text containing `Praga PołUdnie`, `BiałOłęKa`, and `BiałOłęCka`,
      the served facet list contains exactly `Praga-Południe` and `Białołęka`.
- [ ] Selecting one canonical district matches every offer whose raw source used any
      rerouted variant of it.
- [ ] A previously shared URL carrying a legacy variant value still filters correctly
      via rerouting.
- [ ] The frontend contains no district-name transformation logic (verified by test
      and code review against the generated contract).

## Dependencies and gates

- None inside E17 (parallelizable with T1–T3); full data repair depends on T2/T6.
- ADR-012 backend-authoritative logic; E4 read-API filter contracts remain governing.

## Risks and notes

- Alias table must stay a reviewed closed list; fuzzy matching is explicitly rejected.
- Contract change requires regenerating frontend types — coordinate with
  `make contract-check` in CI.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the
      approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
