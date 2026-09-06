---
schema: ai-workflow/task@1
id: E26-T3
epic: E26
title: "Show honest map precision and prove real pin behavior"
status: draft
revision: 2
priority: P1
size: M
milestone: M5
dependencies: [E26-T1, E14-T5]
requirement_ids: [P-001, P-003, P-004, P-007]
decision_ids: [ADR-003, ADR-005, ADR-012, ADR-021]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  source: ../proposed-tasks/E26-T3-show-honest-map-precision.md
  promoted_by: Codex
  promoted_at: "2026-09-06T05:28:07Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-06T05:28:07Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-06T05:33:04Z"
dependency_gate:
  status: blocked
  verified_by: Codex
  verified_at: "2026-09-06T05:28:07Z"
  evidence: ["See implementation plan revision 1; incomplete dependencies remain blocked"]
branch:
  required: true
  name: null
  task_id: E26-T3
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

# E26-T3: Show honest map precision and prove real pin behavior

## Outcome

Users can distinguish building, street, area, and unresolved locations in map, selection, and listing views without interpreting a generic data-completeness note as location accuracy.

## Scope and work

Define backend-owned precision/uncertainty projection and compatible generated contracts, then render clear point/area/list behavior and precise accessible labels. Supply regression fixtures to the real-stack browser infrastructure owned by E14-T5.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A district/city centroid is never styled or described as an exact street/building position; street-only evidence explicitly says approximate street location.
- [ ] Low-confidence location warnings appear in the selected-location flow, independent of missing structured-value notes; building/street/area semantics agree across map, detail, and list.
- [ ] Unresolved offers remain discoverable under a documented backend filter/projection rule without fabricated coordinates; map/list counts remain reconcilable.
- [ ] A WebGL-enabled regression loads real backend-persisted representative coordinates, selects each audited case, and verifies the displayed point/area, text, selection, and cluster interaction.
- [ ] Keyboard/mobile flows retain access to precision information; generated API checks and existing offer IDs, favorites, URL state, and provider attribution remain compatible.

## Tests and verification

Add focused projection/component tests and real browser/API/PostGIS map regressions using E14-T5's shared harness. If that harness is not yet available, its completion is required acceptance evidence before closing this task.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E26-T1, E14-T5. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This task is promoted under spike revision 1. Implementation plan revision 1 is approved; the dependency gate must be satisfied or validly stacked before implementation.

## Rollout and automatic operation

Ship additive contract support before frontend use. Enable the display after old clients can safely handle the new fields; coordinate with T2 remediation without requiring all records to be re-geocoded first.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Retain compatible fields and fallback precision labels; rolling back visual treatment must not silently restore a claim of exactness for coarse data.

## Risks and exclusions

This task supplies geospatial acceptance cases; E14-T5 remains the sole owner of general full-stack/cross-browser harness work and is an explicit dependency.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Spike revision 1 approval interpretation recorded in the owner decision.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.

## Refined implementation boundary

Implement the corresponding T3 section of [implementation plan revision 1](../IMPLEMENTATION_PLAN.md), including its numeric budgets, migration/contract boundaries, protected-state guards and verification requirements. This refinement is task revision 2. No acceptance case is marked fixed by planning.
