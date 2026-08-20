---
schema: ai-workflow/task@1
id: E4-T4
epic: E4
title: "Harden API behavior and performance"
status: done
revision: 1
priority: P1
size: M
milestone: M2
dependencies: [E4-T1, E4-T2, E4-T3, E3-T5]
requirement_ids: [P-001, P-002, P-003]
decision_ids: [ADR-012, ADR-013]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E4-T4-harden-api-behavior-and-performance.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-19T19:10:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T19:10:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T19:10:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T19:10:00Z"
  evidence:
    - "E4-T1 | done | merged on main"
    - "E4-T2 | done | merged on main"
    - "E4-T3 | done | merged PR #78"
    - "E3-T5 | done | merged on main"
branch:
  required: true
  name: cursor/feat-e4-t4-api-hardening-0c74
  task_id: E4-T4
  one_task_only: true
  created_at: "2026-08-19T19:10:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/83"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-19T19:34:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/83"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/83 with green CI"
    - "Performance evidence in E4-T4-PERFORMANCE.md"
    - "Public rate-limit middleware, request correlation, facet cache headers"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E4-T4: Harden API behavior and performance

> E4-T1 through E4-T3 and E3-T5 are done. This task completes cross-endpoint hardening on `cursor/feat-e4-t4-api-hardening-0c74`.

## Outcome

Stable, efficient public endpoints with predictable problems, request correlation, short-lived facet caching, representative performance evidence, and in-process public-read throttles.

## Acceptance criteria

- [x] Warsaw map query meets the 500 ms p95 target in a documented representative test.
- [x] Invalid/oversized requests fail predictably via bounded problem responses.
- [x] Public read throttling returns safe 429 problems without client identity reflection.
- [x] Error responses include matching `request_id` body fields and `X-Request-ID` headers.
- [x] Filter facets and quick filters advertise short public cache lifetimes.

## Evidence

- Performance: [E4-T4-PERFORMANCE.md](../E4-T4-PERFORMANCE.md)
- Tests: `test_api.py`, `test_map_query_integration.py`
