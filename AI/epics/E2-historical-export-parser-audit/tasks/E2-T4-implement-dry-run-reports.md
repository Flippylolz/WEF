---
schema: ai-workflow/task@1
id: E2-T4
epic: E2
title: "Implement dry-run reports and operator wiring"
status: draft
revision: 2
priority: P0
size: M
milestone: M2
dependencies: [E2-T2, E2-T3]
requirement_ids: [P-007]
decision_ids: [ADR-006]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E2-T4-implement-dry-run-reports.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T18:58:46Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:58:46Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:58:46Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence:
    - "E2-T2 | ready | must merge before E2-T4 starts"
    - "E2-T3 | draft | must merge before E2-T4 starts"
branch:
  required: true
  name: null
  task_id: E2-T4
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

# E2-T4: Implement dry-run reports and operator wiring

> Promoted under revision 3, but blocked until E2-T2 and E2-T3 are merged and their dependency evidence is recorded.

## Outcome

Compose source scanning, extraction, and media grouping into a bounded read-only run that always emits a reconciled machine report and a concise human report with an unambiguous terminal state.

## Scope

- Add a streaming dry-run application orchestrator and immutable source/candidate/extraction/media stage counters.
- Define terminal states for success, empty, partial, cancelled, and failed runs.
- Reconcile every source record and downstream candidate/media disposition.
- Write deterministic JSON plus Markdown using atomic same-directory replacement.
- Report source checksum/file size/date range, parser/report versions, candidate/rule/extraction/media/reason buckets, stage timings, and terminal state.
- Exclude or mask full text, contacts, source payloads, internal paths, and private samples from logs/reports.
- Add bounded operator wiring configured with source path, expected identity, parser version, and ignored report destination.

## Out of scope

- Source/canonical/location/contact/geocode/media database writes, ingest-run row persistence, media copies, migrations, public API changes, or production data promotion.
- Complete private export acceptance and final audit publication (E2-T5).

## Acceptance criteria

- [ ] Primary source counts and every downstream stage reconcile exactly; no successful report can represent a partial scan.
- [ ] Successful, empty, malformed, partial, cancelled, source-I/O, and report-I/O terminal states have stable reason codes and exit behavior.
- [ ] JSON output is deterministic apart from explicit elapsed timing fields; Markdown is derived from the same immutable result.
- [ ] Both report outputs use atomic replacement and preserve existing outputs on pre-replacement failure.
- [ ] Reports/logs contain no source text, contact value, source payload, internal absolute path, or identifying sample.
- [ ] Dry runs perform no canonical/database/geocode/media write, media read/copy, or network request.
- [ ] Operator execution is bounded and returns stable exit codes.

## Test plan

- Orchestrator: success, empty, malformed, partial, cancelled, source failure, report failure, and stage reconciliation.
- Writers: deterministic JSON, Markdown parity, atomic replace, destination validation, and leak scanning.
- Operator: configuration validation, stable exits, redacted errors, and no canonical side-effect mocks invoked.
- Bounded processing: generated large source plus guarded active-state assertions.
- Repository: Ruff, strict mypy, import-linter/negative probes, branch coverage, dependency audit, contracts, safety, and runtime images.

## Rollout and rollback

Operator wiring is explicitly invoked and writes only configured ignored report artifacts. Revert the task PR to roll back; delete generated local reports if desired. No database/data/media rollback exists.

## Ready checklist

- [x] Promotion and current spike/implementation gates are recorded.
- [ ] E2-T2 and E2-T3 are `done`; dependency gate is satisfied.
- [ ] Status moves to `ready` only after all dependencies are complete.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated E2-T4 branch is created from latest `main`.
- [ ] Branch and PR contain E2-T4 only; metadata is recorded.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
