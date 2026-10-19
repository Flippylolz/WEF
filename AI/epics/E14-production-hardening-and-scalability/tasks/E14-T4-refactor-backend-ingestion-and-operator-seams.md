---
schema: ai-workflow/task@1
id: E14-T4
epic: E14
title: "Refactor backend ingestion and operator seams"
status: done
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E14-T2]
requirement_ids: [P-001, P-002, P-005, P-006, P-007, P-008]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-021]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  source: ../proposed-tasks/E14-T4-refactor-backend-ingestion-and-operator-seams.md
  promoted_by: "Codex agent (owner-approved E14 planning under AD-041)"
  promoted_at: "2026-08-29T21:17:35Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent (AD-041)"
  verified_at: "2026-08-29T21:17:35Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-06T06:51:36.365914+00:00"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-06T07:49:46.660733+00:00"
  evidence: ["E14-T2 done via PR #359, merge 7367402ff76abe78c414c023d2f0c66254cedc2f; release 34019827017 succeeded"]
branch:
  required: true
  name: feat/E14-T4-backend-seams
  task_id: E14-T4
  one_task_only: true
  created_at: "2026-09-06T07:49:46.660733+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/361
completion:
  completed_by: Codex
  completed_at: "2026-09-06T08:40:32.182542+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/361
  evidence: ["Full make verify passed: 1232 backend, 172 frontend, 184 script tests", "PR #361 all required checks passed; merge a786d6b785253a3413ed5d338a443ba917fb5a70; release 34021148552 succeeded", "See ../T4_VERIFICATION.md"]
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E14-T4: Refactor backend ingestion and operator seams

## Outcome

Parsing, persistence, import orchestration, live-event handling, and operator commands
have cohesive boundaries with explicit transaction/cancellation/error semantics, while
replay identity, provenance, public projections, and CLI behavior remain compatible.

## Scope

- Characterize and incrementally decompose ingestion extraction/persistence, complete-import repositories, `import_command.py`, and the highest-risk proof/controller scripts.
- Separate parsing rules from extraction assembly, persistence sub-responsibilities from transaction orchestration, and CLI presentation from application services.
- Preserve inward-owned ports, import-linter contracts, advisory-lock/lease behavior, idempotent replay, revision provenance, and redacted errors.
- Replace broad lint suppressions only where decomposition makes the rule applicable; retain exact justified suppressions for trusted process-boundary code.
- Record transaction ownership, commit boundaries, retry/cancellation behavior, and operator exit-code contracts.

## Out of scope

- Parser behavior changes, schema redesign, service decomposition, new queue/cache, live data mutation, or rewriting every deployment script.

## Acceptance criteria and checks

- [x] Characterization tests show identical accepted/rejected extraction, persisted values, revision/provenance, live new/edit/delete convergence, checkpoints, and operator output/exit codes.
- [x] Transaction and lock ownership is documented and protected by rollback, cancellation, duplicate/replay, and concurrent-attempt tests.
- [x] Domain/application layers remain framework independent and all 17+ architecture contracts plus the violation probe pass.
- [x] Error paths remain bounded and redact source text, contacts, credentials, sessions, paths, and provider secrets.
- [x] Complexity/suppression counts improve in the selected hotspots without moving responsibilities into generic utility modules.
- [x] Ruff, strict mypy, architecture, unit, PostGIS integration, migration, replay/idempotency, cancellation, CLI, and coverage checks pass.

## Dependencies and gates

Depends on E14-T2 so persistence and orchestration behavior is falsifiable before refactor.

## Risks and notes

Transaction movement is a behavior change even when types stay equal. Any altered
atomicity, retry, or checkpoint rule requires spike/plan revalidation.

## Ready checklist

- [x] E14 spike revision 1 is owner-approved under AD-041.
- [x] The task was moved to `tasks/` with complete promotion metadata.
- [x] E14 implementation plan revision 1 is owner-approved and E14-T2 is done.

## Start evidence

Moved through ready before implementation under owner-approved T1–T5 scope.
Started from current main 7367402ff76abe78c414c023d2f0c66254cedc2f.
T2 full canonical verification provides the characterization baseline: 1218
backend tests, including parser, persistence, live convergence and CLI failures.
