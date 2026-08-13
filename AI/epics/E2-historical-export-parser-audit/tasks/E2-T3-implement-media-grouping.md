---
schema: ai-workflow/task@1
id: E2-T3
epic: E2
title: "Implement deterministic media grouping"
status: done
revision: 2
priority: P0
size: M
milestone: M2
dependencies: [E2-T1, E2-T2]
requirement_ids: [P-005]
decision_ids: [ADR-006, ADR-007]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E2-T3-implement-media-grouping.md
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
  verified_at: "2026-08-13T19:18:11Z"
  evidence:
    - "E2-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/33 | merge 6e43d0a"
    - "E2-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/36 | merge 5a8552b"
branch:
  required: true
  name: feature/E2-T3-media-grouping
  task_id: E2-T3
  one_task_only: true
  created_at: "2026-08-13T19:18:11Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/37"
completion:
  completed_by: "Cursor Agent (owner-authorized)"
  completed_at: "2026-08-13T19:26:22Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/37"
  evidence:
    - "RawMessage and Telegram conversion expose a validated optional source-neutral media group ID while historical records remain null by default"
    - "Streaming e2-media-v1 grouping applies same-message, explicit-group, reply, and 120-second adjacency evidence in order with rule/confidence"
    - "Every descriptor retains source ownership and receives exactly one associated or stable unassociated disposition without opening media files"
    - "Sanitized golden cases cover photo/video/thumbnail runs, explicit groups, replies, services, empty/text boundaries, long gaps, unknown targets, and close consecutive listings"
    - "Local backend gates passed: Ruff, strict mypy, import-linter plus negative probes, 106 tests/4 PostGIS skips with 92.70% branch coverage, dependency audit, links and fixture safety"
    - "Initial task PR CI passed at 6da13cc: Backend, Frontend and contract, Repository safety, Runtime images | https://github.com/Flippylolz/WEF/actions/runs/31735556758"
    - "No media read/copy, database/API/geocode write, network call, or production activation; rollback is a PR revert"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E2-T3: Implement deterministic media grouping

> Promoted under revision 3, but blocked until E2-T2 is merged and its dependency evidence is recorded.

## Outcome

Associate every historical media descriptor with a listing candidate when supported by deterministic source evidence, or explicitly account for it as unassociated.

## Scope

- Extend `RawMessage` with an optional source-neutral media-group ID and populate it at adapter boundaries when available.
- Add immutable media association/group values with source identity, owner identity, association rule, and confidence.
- Implement chronological evidence order: same message, explicit group ID, reply, then historical adjacency/time burst.
- Use the versioned E2-T2 candidate decision to establish listing boundaries.
- Stop the 120-second historical burst at a new candidate, service record, reply boundary, or larger gap.
- Preserve source ownership and account for every media descriptor exactly once.

## Out of scope

- Reading/copying media bytes, thumbnails, or source media files.
- Dry-run report persistence/operator wiring (E2-T4), complete audit (E2-T5), database/API changes, or production promotion.

## Acceptance criteria

- [x] Every association emits an ordered stable rule and confidence.
- [x] Same-message, explicit-group, reply, and historical-burst cases are deterministic.
- [x] A new candidate, service event, reply boundary, or gap greater than 120 seconds ends an active historical burst.
- [x] Fixtures prove that two nearby consecutive listing galleries are not merged.
- [x] Every media descriptor is reconciled as associated or unassociated without changing its source owner.
- [x] Processing is bounded to active-run state plus the minimal message-ID index.
- [x] No media path is opened and no media file is copied or persisted.

## Test plan

- Unit/golden: same-message media, explicit groups, replies, photo/video runs, empty captions, unassociated media, long gaps, and close listings.
- Invariants: stable order, one disposition per descriptor, source ownership, confidence/rule validation, key-order/timezone independence.
- Boundaries: service records, candidate transitions, reply transitions, exact/over-120-second gaps, unknown reply targets.
- Repository: Ruff, strict mypy, import-linter/negative probes, branch coverage, dependency audit, contracts, safety, and runtime images.

## Rollout and rollback

This is inert in-memory association code and an additive internal raw-message field. Revert the task PR to roll back; no stored data or media cleanup is required.

## Ready checklist

- [x] Promotion and current spike/implementation gates are recorded.
- [x] E2-T1 completion is recorded.
- [x] E2-T2 is `done`; dependency gate is satisfied.
- [x] Status passed through `ready` after all dependencies completed.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated E2-T3 branch is created from latest `main`.
- [x] Branch contains E2-T3 only; branch metadata is recorded.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
