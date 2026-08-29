---
schema: ai-workflow/proposed-task@1
id: E17-T5
epic: E17
title: "Filter determinism and test coverage"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies:
  - E17-T4
requirement_ids: []
decision_ids:
  - ADR-012
deferred_decision_ids: []
source: ../../SPIKE.md#proposed-task-boundaries
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E17-T5: Filter determinism and test coverage

## Outcome

All filter behavior — facet derivation, value parsing, matching, ordering, and URL
round-trips — is covered by deterministic tests that fail closed, eliminating the
flaky behavior the owner observed instead of papering over it.

## Scope

- Backend contract/unit tests for every filter dimension (districts incl. rerouted
  aliases, rooms, market, content types, price/area ranges, publication dates,
  quick filters): boundary values, invalid inputs, duplicate/case-variant inputs,
  max-value limits, and empty-result behavior.
- Facet snapshot tests: canonical-only values, deterministic order, no dependence on
  insertion order or collation.
- Frontend tests exercising the generated contract only: option rendering, selection
  state, and URL state round-trips; removal of `localeCompare`-based ordering of
  backend-provided options in favor of the served order.
- Flake audit: identify and fix the actual sources of the observed instability
  (ordering, timing, fixture leakage), with each fix tied to a regression test.

## Out of scope

- New filter UX or new dimensions; performance benchmarking (E14 owns capacity).

## Work

- Tests must not sleep or depend on wall-clock ordering; shared fixtures are reset
  per case in line with existing integration-test conventions.

## Acceptance criteria

- [ ] Repeated local and CI runs of the filter suites are green with zero
      order-dependent variance (verified by shuffled/fixed-seed runs).
- [ ] Every documented filter failure mode (invalid value, over-limit repeats,
      conflicting ranges, unknown legacy district) has a failing-then-passing test.
- [ ] Facet ordering is asserted against the backend-defined order, not the client
      locale.
- [ ] Coverage of touched filter modules meets or exceeds the repository threshold.

## Dependencies and gates

- E17-T4 (canonical vocabulary defines the expected values under test).
- CI conventions from E1/E14 remain governing.

## Risks and notes

- If the flake audit finds a genuine production-data dependency (e.g. collation),
  escalate to the spike's open questions rather than normalizing in the client.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the
      approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
