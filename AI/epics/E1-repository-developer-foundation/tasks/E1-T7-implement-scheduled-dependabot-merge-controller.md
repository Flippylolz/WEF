---
schema: ai-workflow/task@1
id: E1-T7
epic: E1
title: "Implement scheduled Dependabot merge controller"
status: done
revision: 1
priority: P0
size: M
milestone: M1
dependencies: [E1-T4, E1-T6]
requirement_ids: []
decision_ids: [ADR-017]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T18:01:53Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T18:01:53Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 6
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T18:01:53Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T18:01:53Z"
  evidence:
    - "E1-T4 | done | CI baseline"
    - "E1-T6 | done | Dependabot update PRs"
branch:
  required: true
  name: chore/E1-T7-dependabot-merge-controller
  task_id: E1-T7
  one_task_only: true
  created_at: "2026-08-20T18:01:53Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/148"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-20T18:08:55Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/148"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/148 (workflow + controller + required-checks allowlist + tests)"
    - "CI all green on PR #148"
    - "Dependabot already opened grouped patch/minor and separate major PRs after E1-T6"
    - "Controller merges only after owner applies automerge; majors remain manual"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E1-T7: Implement scheduled Dependabot merge controller

## Outcome

Owner-labeled Dependabot-only direct patch/minor pull requests with successful required checks are squash-merged by a scheduled controller that never checks out or executes pull-request code.

## Scope

- `.github/workflows/dependabot-merge.yml` (15-minute schedule + `workflow_dispatch`).
- Default-branch script `scripts/dependabot_merge_controller.py` and `.github/dependabot-required-checks.json`.
- Unit tests for every allow/deny gate including the head-change race.

## Out of scope

- Branch-protection rulesets, native GitHub auto-merge, dependency upgrades in this PR.

## Acceptance criteria

- [x] Workflow uses pinned Actions, minimum permissions, one concurrency group, default-branch checkout only.
- [x] Eligibility requires Dependabot authorship, `dependabot/` head, owner-applied `automerge`, direct patch/minor metadata, bot-only commits, current main, required checks, no bad checks, and mergeability.
- [x] Refetch + `--match-head-commit` closes the head-change race; `--admin` is never used.
- [x] Tests cover allow and deny paths including missing/failed checks, stale base, wrong label actor, human commits, majors/indirect, and head SHA change.

## Dependencies and gates

- Dependencies: E1-T4, E1-T6 (`done`).
- Implementation plan revision 6 authorizes this task.
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).

## Risks and notes

- Compensating control under ADR-017; not equivalent to enforced branch protection.
- Controller must keep writing tokens away from untrusted PR code.
