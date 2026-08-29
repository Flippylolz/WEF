---
schema: ai-workflow/task@1
id: E14-T2
epic: E14
title: "Strengthen critical-path test confidence"
status: draft
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E14-T1]
requirement_ids: [P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-011, ADR-012, ADR-013, ADR-016, ADR-021]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  source: ../proposed-tasks/E14-T2-strengthen-critical-path-test-confidence.md
  promoted_by: "Codex agent (owner-approved E14 planning under AD-041)"
  promoted_at: "2026-08-29T21:17:35Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent (AD-041)"
  verified_at: "2026-08-29T21:17:35Z"
implementation_gate:
  status: blocked
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: null
  verified_by: null
  verified_at: null
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E14-T2
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

# E14-T2: Strengthen critical-path test confidence

## Outcome

Tests measure risk rather than only aggregate line execution: critical authorization,
contact, catalog, persistence, ingestion, migration, and operator behavior has explicit
failure-case coverage and independently enforced confidence floors.

## Scope

- Inventory behavior/risk by module and classify unit, integration, contract, browser, and operational ownership.
- Add critical-module/package coverage floors without demanding uniform 100% coverage.
- Close high-risk gaps identified in the spike, especially persistence/offer-detail/import/command paths.
- Add adversarial negative cases for auth/contact leakage, idempotent replay, concurrency, cancellation, partial failure, migration, pagination/filter boundaries, and operator exit codes.
- Introduce reusable synthetic builders/fixtures where they reduce test duplication and preserve clarity.
- Run a bounded mutation or deliberate-fault sample over selected pure critical logic; choose tooling only in the approved plan.
- Detect flaky/order-dependent tests through repeat/seed evidence and prohibit silent retries below browser level.

## Out of scope

- Full-stack browser matrix (T5), module refactors (T3/T4), production load tests (T7), or chasing coverage on trivial glue.

## Acceptance criteria and checks

- [ ] A reviewed risk matrix maps critical behaviors to the test layer that owns them.
- [ ] Global 90% floors remain, and approved critical modules/packages have stricter independently enforced floors or explicit branch/behavior assertions.
- [ ] Known low-coverage critical adapters/commands either gain failure-path coverage or receive a documented, reviewed exclusion rationale.
- [ ] Representative deliberate mutations/faults in auth, contacts, catalog filters, ingestion replay, and release gates make the suite fail.
- [ ] Tests are deterministic across documented repeat/seed runs and emit no unapproved warnings.
- [ ] Fixtures remain synthetic/redacted and leakage scans pass.
- [ ] Unit, PostGIS integration, migration, contract, architecture, coverage, repeat/seed, and negative-probe checks pass.

## Dependencies and gates

Depends on E14-T1 so new confidence gates use the canonical truthful pipeline.

## Risks and notes

Coverage is a diagnostic, not the goal. Acceptance is based on important behavior and
failure modes being falsifiable, not on maximizing one percentage.

## Ready checklist

- [x] E14 spike revision 1 is owner-approved under AD-041.
- [x] The task was moved to `tasks/` with complete promotion metadata.
- [ ] E14 implementation plan revision 1 is owner-approved and E14-T1 is done.
