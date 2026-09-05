---
schema: ai-workflow/proposed-task@1
id: E26-T1
epic: E26
title: "Validate address agreement and source-supported precision"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: []
requirement_ids: [P-001, P-003, P-004, P-007]
decision_ids: [ADR-003, ADR-005, ADR-012, ADR-021]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E26-T1: Validate address agreement and source-supported precision

## Outcome

A provider result on the wrong street cannot become an accepted exact-looking pin merely because it has a high score or falls inside the Warsaw bounding box.

## Scope and work

Version structured source/provider address evidence, normalize neighborhoods/districts/city separately, evaluate bounded candidate sets and ambiguity, validate geographic scope, and replace automatic blanket pending-pin acceptance with the accepted accuracy policy.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] The Jugosłowiańska-to-Grochowska-town-hall regression is rejected or retried despite provider confidence 1.00; amenity classification cannot supply unsupported building precision.
- [ ] Gocław is resolved as a neighborhood within the Warsaw context rather than displayed as a replacement city; both source variants preserve street tokens and source text provenance.
- [ ] Street/house-number/locality agreement is required at the claimed precision; missing numbers never become invented building-level matches, and a neighborhood centroid never claims to locate the requested street.
- [ ] Low-confidence and low-precision results receive bounded automatic normalization/candidate retries with versioned evidence; unresolved ambiguity is explicit and does not trigger endless provider requests.
- [ ] Actor/reason lineage distinguishes automatic decisions from genuine owner review; tests cover wrong street, duplicate street names, incompatible district, out-of-scope result, cache hit, quota limit, and manual verified override.

## Tests and verification

Extend test_geocoding.py, test_geocoding_integration.py, test_accept_pending_geocode_pins.py, and recurring-worker tests with sanitized provider payloads for the three audited cases and negative address matches.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

No task dependency. Current epic spike approval, task promotion, and implementation-plan approval are still required before implementation.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Version request/normalizer/review policy, supersede AD-034's recurring use explicitly, and evaluate old/new decisions in observation mode before selecting corrected points. Keep existing provider quotas.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Disable new selection writes and retain prior selection lineage; keep invalid results visibly uncertain rather than re-enabling blanket acceptance.

## Risks and exclusions

Owner visibility preferences behind AD-034 must be preserved through honest approximate/list discovery. No additional hosted provider or paid quota is authorized by this proposal.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
