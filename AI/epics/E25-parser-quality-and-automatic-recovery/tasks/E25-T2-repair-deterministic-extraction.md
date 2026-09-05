---
schema: ai-workflow/task@1
id: E25-T2
epic: E25
title: "Repair deterministic field extraction and money semantics"
status: in_progress
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E25-T1]
requirement_ids: [P-002, P-003, P-006, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E25-T2-repair-deterministic-extraction.md
  promoted_by: Codex
  promoted_at: "2026-09-05T10:15:52Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T11:18:50Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T11:18:50Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E25-T2
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

# E25-T2: Repair deterministic field extraction and money semantics

## Outcome

Recognized listing templates preserve correct prices, units, inclusion flags, rooms, and classification while rejecting unsupported interpretations.

## Scope and work

Extend evidence-backed label variants and handle alternate currencies separately from same-currency ranges, price per area, and add-on values. Resolve the rooms warning and included-storage gap exposed by the Ostrzycka case; cover parser semantics with the benchmark.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A sanitized equivalent of the Ostrzycka source yields PLN 780,000 (78,000,000 minor units), area 37.50 m², and source-evidenced included storage; no exchange rate is inferred from its EUR alternative.
- [ ] The Jugosłowiańska regression preserves PLN 1,399,000 apartment price and PLN 39,000 parking price as separate values.
- [ ] Dual-currency alternatives, actual same-currency ranges, per-square-metre values, and included add-ons cannot be confused; contradictory amounts/units produce explicit non-applied evidence.
- [ ] The room-tag/room-label combination has the source-supported result and no spurious warning; real contradictions still warn.
- [ ] The T1 benchmark has no new false positives or regressions in previously correct fields, and the parser version/provenance changes consistently.

## Tests and verification

Extend the existing extraction fixture corpus and table-driven extractor tests with positive and negative cases. Include money-to-minor persistence and public-filter projection tests.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E25-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This promoted task remains `draft` under the [workflow](../../../workflow/README.md). [Implementation plan revision 1](../IMPLEMENTATION_PLAN.md) is approved; the task must satisfy its dependency and branch gates before implementation.

## Rollout and automatic operation

Version the parser and evaluate the benchmark plus an aggregate read-only production replay diff before enabling automatic historical application through T4.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Stop new replay scheduling on regression; restore prior parser for new work and use recorded field provenance to reverse only affected automatic writes.

## Risks and exclusions

A synonym-only regex patch can reveal an additional money-semantic bug. Validate the complete field pipeline, not just a successful regex match.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Readiness and completion

- [x] Spike revision 1 approval and task promotion are recorded; the authoritative file is under `tasks/`.
- [x] Implementation plan revision 1 is explicitly approved and the implementation gate is satisfied.
- [ ] Required dependencies are done, or valid ancestor PRs are recorded in a stacked gate.
- [ ] This task passes through `ready` and starts on its own dedicated branch/PR.
- [ ] Acceptance criteria, required checks, and the global definition of done pass; completion evidence is recorded.

The documentation branch is not this task's implementation branch. Follow the task-specific modules, migration ownership, numeric limits, and verification requirements in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Acceptance criteria above are preserved from proposed revision 1; promotion adds workflow metadata without changing their scope.

## Provider revision gate

Spike and implementation plan revision 2 are explicitly owner-approved following the
[Batch/ZDR incompatibility](../PROVIDER_PRIVACY_REVISION.md). Prior test evidence
is retained; approval gates are restored explicitly to revision 2.

The independently implemented T2 branch is `bugfix/E25-T2-deterministic-extraction`,
commit `20e9acd`, PR [330](https://github.com/Flippylolz/WEF/pull/330). Its completed
local validation remains evidence; the provider revision changes no T2 behavior.
