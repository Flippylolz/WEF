---
schema: ai-workflow/task@1
id: E2-T4
epic: E2
title: "Implement dry-run reports and operator wiring"
status: done
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
  status: satisfied
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:29:40Z"
  evidence:
    - "E2-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/36 | merge 5a8552b"
    - "E2-T3 | done | merged PR https://github.com/Flippylolz/WEF/pull/37 | merge 4a2e8c5"
branch:
  required: true
  name: feature/E2-T4-dry-run-reports
  task_id: E2-T4
  one_task_only: true
  created_at: "2026-08-13T19:29:40Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/40"
completion:
  completed_by: "Cursor Agent (owner-authorized)"
  completed_at: "2026-08-13T19:41:31Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/40"
  evidence:
    - "Streaming orchestrator composes source scan, e2-v1 extraction, and e2-media-v1 grouping with reconciled source/candidate/media counters"
    - "Terminal reports distinguish succeeded, empty, partial, cancelled, and failed runs with stable redacted error and process codes"
    - "e2-report-v1 JSON and Markdown include source checksum/size/date range, explicit versions, reason/rule/field/media buckets, and stage timings"
    - "Atomic same-directory writers render both formats before replacement; tests preserve existing targets on pre-replacement failure"
    - "Runtime-only contact/source values, source payload/text, media paths, and internal paths are absent from reports and operator output"
    - "Local backend gates passed: Ruff, strict mypy, import-linter plus negative probes, 118 tests/4 PostGIS skips with 91.80% branch coverage, dependency audit, deterministic OpenAPI, links and Compose config"
    - "Initial task PR CI passed at 72aa006: Backend, Frontend and contract, Repository safety, Runtime images | https://github.com/Flippylolz/WEF/actions/runs/31736834109"
    - "No database/canonical/geocode/media write, media copy, or network request; output is limited to configured ignored report artifacts"
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

- [x] Primary source counts and every downstream stage reconcile exactly; no successful report can represent a partial scan.
- [x] Successful, empty, malformed, partial, cancelled, source-I/O, and report-I/O terminal states have stable reason codes and exit behavior.
- [x] JSON output is deterministic apart from explicit elapsed timing fields; Markdown is derived from the same immutable result.
- [x] Both report outputs use atomic replacement and preserve existing outputs on pre-replacement failure.
- [x] Reports/logs contain no source text, contact value, source payload, internal absolute path, or identifying sample.
- [x] Dry runs perform no canonical/database/geocode/media write, media read/copy, or network request.
- [x] Operator execution is bounded and returns stable exit codes.

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
- [x] E2-T2 and E2-T3 are `done`; dependency gate is satisfied.
- [x] Status passed through `ready` after all dependencies completed.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated E2-T4 branch is created from latest `main`.
- [x] Branch contains E2-T4 only; branch metadata is recorded.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
