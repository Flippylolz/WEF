---
schema: ai-workflow/proposed-task@1
id: E25-T2
epic: E25
title: "Repair deterministic field extraction and money semantics"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies: [E25-T1]
requirement_ids: [P-002, P-003, P-006, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Version the parser and evaluate the benchmark plus an aggregate read-only production replay diff before enabling automatic historical application through T4.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Stop new replay scheduling on regression; restore prior parser for new work and use recorded field provenance to reverse only affected automatic writes.

## Risks and exclusions

A synonym-only regex patch can reveal an additional money-semantic bug. Validate the complete field pipeline, not just a successful regex match.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
