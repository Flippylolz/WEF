---
schema: ai-workflow/task@1
id: E1-T6
epic: E1
title: "Configure Dependabot update pull requests"
status: done
revision: 1
priority: P0
size: M
milestone: M1
dependencies: [E1-T1, E1-T4]
requirement_ids: []
decision_ids: [ADR-017]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E1-T6-configure-dependabot-update-pull-requests.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T17:53:13Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T17:53:13Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 5
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T17:53:13Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T17:53:13Z"
  evidence:
    - "E1-T1 | done | repository safety"
    - "E1-T4 | done | CI baseline"
branch:
  required: true
  name: chore/E1-T6-dependabot-updates
  task_id: E1-T6
  one_task_only: true
  created_at: "2026-08-20T17:53:13Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/140"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-20T17:58:29Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/140"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/140 (dependabot.yml + structural tests + plan rev 5 / AD-029)"
    - "CI all green on PR #140 (Backend, Frontend and contract, Repository safety, Runtime images, Coverage badge)"
    - "Repository vulnerability alerts and automated security fixes enabled via GitHub API after merge"
    - "E1-T7 merge controller remains proposed"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E1-T6: Configure Dependabot update pull requests

## Outcome

Dependabot opens weekly version and security update pull requests for every committed dependency ecosystem, each running the normal unprivileged CI pipeline, with patch/minor updates grouped and major upgrades left separate/manual.

## Scope

- Add `.github/dependabot.yml` for npm (workspace root), pip (`apps/backend`), Docker (`apps/backend`, `apps/web`), and GitHub Actions (`/`).
- Weekly schedule, bounded open-PR limit, patch/minor grouping for version updates.
- Document promotion under implementation-plan revision 5 / AD-029.

## Out of scope

- Scheduled merge controller (E1-T7), branch-protection enforcement, upgrading dependencies in this PR, production deploy changes.

## Work

- Commit Dependabot configuration matching [REPOSITORY_RULES](../../../governance/REPOSITORY_RULES.md).
- Unit-test the committed YAML covers required ecosystems and patch/minor groups without a merge workflow.
- Update E1 indexes/SPIKE notes for promotion status.

## Acceptance criteria

- [x] Dependabot configuration covers npm, Python, Docker (both app Dockerfiles), and GitHub Actions.
- [x] Patch/minor version updates are grouped; majors remain ungrouped.
- [x] Open pull-request limit is bounded per ecosystem.
- [x] No Dependabot merge-controller workflow is introduced.
- [x] Structural unit test for `.github/dependabot.yml` passes.

## Dependencies and gates

- Dependencies: E1-T1, E1-T4 (`done`).
- Implementation plan revision 5 authorizes this task.
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).

## Risks and notes

- npm uses the workspace root (`/`) so `pnpm-lock.yaml` and `apps/web` stay in one Dependabot surface.
- Security update PRs remain GitHub-native; auto-merge stays deferred to E1-T7.
- A write-capable merge workflow must not check out PR code (E1-T7 constraint).
