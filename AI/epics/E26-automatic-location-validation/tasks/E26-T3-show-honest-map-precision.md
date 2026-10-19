---
schema: ai-workflow/task@1
id: E26-T3
epic: E26
title: "Show honest map precision and prove real pin behavior"
status: done
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
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-06T05:28:07Z"
  evidence: ["E26-T1 done via PR #355, merge 6722ecb79d47958a92eb3608aeade1a4a3cede9e", "E14-T5 done via PR #362, merge 8ff50a9a41b9fe4b1160e2afd1983d2ae9119c6d; full local checks and current-head CI passed"]
branch:
  required: true
  name: feat/E26-T3-honest-map-precision
  task_id: E26-T3
  one_task_only: true
  created_at: "2026-09-06T09:01:57.120807+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/363
completion:
  completed_by: Codex
  completed_at: "2026-09-06T10:35:17.087892+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/363
  evidence: ["T3_VERIFICATION.md; PR #363 merge 3fdcd7bb52b0e30d4160acaf8dab912ca51511c6; CI 34026980040 and release 34027321299 succeeded"]
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

- [x] A district/city centroid is never styled or described as an exact street/building position; street-only evidence explicitly says approximate street location.
- [x] Low-confidence location warnings appear in the selected-location flow, independent of missing structured-value notes; building/street/area semantics agree across map, detail, and list.
- [x] Unresolved offers remain discoverable under a documented backend filter/projection rule without fabricated coordinates; map/list counts remain reconcilable.
- [x] A WebGL-enabled regression loads real backend-persisted representative coordinates, selects each audited case, and verifies the displayed point/area, text, selection, and cluster interaction.
- [x] Keyboard/mobile flows retain access to precision information; generated API checks and existing offer IDs, favorites, URL state, and provider attribution remain compatible.

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
- [x] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [x] All referenced dependencies and required decisions resolved for the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [x] Dedicated branch and PR will cover this task only after implementation gates clear.

## Refined implementation boundary

Implement the corresponding T3 section of [implementation plan revision 1](../IMPLEMENTATION_PLAN.md), including its numeric budgets, migration/contract boundaries, protected-state guards and verification requirements. This refinement is task revision 2. No acceptance case is marked fixed by planning.

## Start evidence

Moved through ready before implementation on 2026-09-06T09:01:57.120807+00:00. The owner-approved E26
spike/plan revision 1 and task revision 2 remain authoritative. E14-T5 is the exact
open ancestor above; its CI and merge are required before E26-T3 completion.
Ostrzycka and Jugosłowiańska are not verified fixed by this start record.

The recorded ancestor merged after task start. Dependency gate is now satisfied;
the task branch is rebased onto that main merge before further implementation.
