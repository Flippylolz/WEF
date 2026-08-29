---
schema: ai-workflow/task@1
id: E14-T7
epic: E14
title: "Prove capacity and enforce performance budgets"
status: draft
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E14-T3, E14-T4, E14-T6]
requirement_ids: [P-001, P-002, P-003, P-004, P-005, P-006, P-007]
decision_ids: [ADR-004, ADR-005, ADR-008, ADR-010, ADR-012]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  source: ../proposed-tasks/E14-T7-prove-capacity-and-enforce-performance-budgets.md
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
  task_id: E14-T7
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

# E14-T7: Prove capacity and enforce performance budgets

## Outcome

A repeatable synthetic workload establishes how much traffic/data the current host and
architecture can serve within product targets, enforces regression budgets, and names
measured triggers for pooling, caching, queues, storage/CDN, replicas, or horizontal scale.

## Scope

- Define versioned representative dataset/workload profiles for anonymous browsing, auth/contact/favorites, ingestion bursts, media, and mixed traffic.
- Measure API p50/p95/p99, throughput/error rate, SQL query count/plans, connection-pool waits, CPU/memory/disk/network saturation, and payload sizes.
- Measure ingestion processing/catch-up rate, backlog, lock contention, provider-disabled behavior, and API isolation under worker load.
- Measure production frontend bundle/route sizes and lab Core Web Vitals at mobile/desktop profiles; correlate with T6 field metrics.
- Calibrate database pool/timeouts and existing container limits from evidence.
- Add stable regression budgets to CI and run heavier capacity tests on an approved scheduled/manual environment.
- Document explicit thresholds and lowest-cost response for each architecture scale trigger.

## Out of scope

- Unapproved production stress, premature infrastructure adoption, live personal data, provider quota consumption, or treating CI timing as production capacity.

## Acceptance criteria and checks

- [ ] Workload/data profiles are synthetic, versioned, reproducible, and document hardware/environment variance.
- [ ] Expected-load API map p95 remains under 500 ms and all additional approved latency/error/throughput budgets pass with headroom.
- [ ] SQL query/plan and connection-wait budgets catch N+1, scan, pool-exhaustion, and index regressions.
- [ ] Worker catch-up and mixed-load evidence proves the API remains within its SLO or documents a measured remediation trigger.
- [ ] Frontend first-use/LCP/INP/CLS and JS/CSS/image payload budgets are enforced; bundle regressions produce an inspectable diff.
- [ ] Rate-limit single-process limitations and any multi-process trigger are explicitly documented.
- [ ] Results include p50/p95/p99, errors, saturation, release/config/dataset identity, and at least three repeat runs or a justified statistical method.
- [ ] CI performance budgets, scheduled/manual capacity suite, query-plan, bundle, Lighthouse, and no-sensitive-fixture checks pass.

## Dependencies and gates

Depends on E14-T3/T4 stable seams and E14-T6 measurement definitions.

## Risks and notes

Use production-like topology without targeting the live service. Performance assertions
must separate deterministic regression budgets from noisy capacity observations.

## Ready checklist

- [x] E14 spike revision 1 is owner-approved under AD-041.
- [x] The task was moved to `tasks/` with complete promotion metadata.
- [ ] E14 implementation plan revision 1 is owner-approved and E14-T3/T4/T6 are done.
