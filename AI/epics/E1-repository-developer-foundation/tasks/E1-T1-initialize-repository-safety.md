---
schema: ai-workflow/task@1
id: E1-T1
epic: E1
title: "Initialize repository safety"
status: in_progress
revision: 3
priority: P0
size: S
milestone: M1
dependencies: []
requirement_ids: []
decision_ids: [ADR-009, ADR-017, ADR-018]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E1-T1-initialize-repository-safety.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T21:14:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:14:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:14:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:14:00Z"
  evidence: []
branch:
  required: true
  name: chore/E1-T1-repository-safety
  task_id: E1-T1
  one_task_only: true
  created_at: "2026-08-12T21:21:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/2"
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

# E1-T1: Initialize repository safety

> Promoted after explicit owner approval of E1 spike revision 2 and implementation-plan revision 3. The repository-safety work is `in_progress` in its open stacked pull request and remains unmerged.

## Outcome

Create a safe Git/GitHub baseline in which pre-existing planning documentation has its own PR and repository-safety files have a stacked task PR, without admitting the raw export, media, sessions, secrets, or local state.

## Scope

- Initialize Git and configure `git@github.com:Flippylolz/WEF.git` as `origin`; use SSH for fetches and pushes.
- Create a minimal root-README commit on `main`, required because GitHub needs a base ref and empty commits are prohibited.
- Commit the pre-existing `AI/` documentation on `docs/ai-documentation-foundation` and open its PR to `main`.
- Create `chore/E1-T1-repository-safety` from the documentation branch.
- Commit root `.gitignore`, `.dockerignore`, `.env.example`, and the full root `README.md` on E1-T1 only.
- Push the task branch and open a stacked pull request to `docs/ai-documentation-foundation`.
- Verify ignore rules and Git/Docker candidate sets before commit.

## Out of scope

- Dockerfiles, Docker Compose, Makefile, application scaffolds, lockfiles, generated OpenAPI, CI workflows, Dependabot, production configuration, or source-data import.
- Any raw `est-test/` content or `est-test.tar.gz`.
- Enforced GitHub branch protection, which remains out of scope under ADR-017.
- Merging the pull request unless separately requested.

## Affected modules and contracts

- Root `.gitignore`, `.dockerignore`, `.env.example`, and `README.md`.
- Existing `AI/` planning/governance source of truth, carried by the prerequisite documentation PR rather than the E1-T1 commit.
- Local Git metadata and GitHub repository refs/PR metadata.

No application, public API, persisted data, or runtime contract changes.

## Implementation notes

- `.gitignore` excludes the export/archive, media, environment/secrets, Telegram sessions, local databases, caches, coverage, build outputs, generated sensitive reports, and editor/OS noise without excluding lockfiles or `contracts/openapi/v1.json`.
- `.dockerignore` protects any future root context from Git metadata, source data/media, secrets, local databases, caches, and unrelated generated output.
- `.env.example` contains safe names/comments only.
- The root README links `AI/README.md`, states the current planning-only status, lists safe prerequisites, and does not advertise Docker/Make/application commands that do not exist.
- The minimal root README on `main` is the one-time PR-base bootstrap. Existing docs use their own PR, and E1-T1 adds only its four root safety files in a stacked PR.

## Acceptance criteria

- [x] The canonical repository is `Flippylolz/WEF`, and Git pushes use SSH.
- [x] The only direct bootstrap content on `main` is the minimal root README.
- [x] Existing `AI/**` documentation is committed on `docs/ai-documentation-foundation` with [PR #1](https://github.com/Flippylolz/WEF/pull/1) to `main`.
- [x] The E1-T1 commit is on `chore/E1-T1-repository-safety`, branched from the docs branch.
- [x] Git status/add candidates contain no raw export, archive, media, Telegram session, environment secret, local database, or sensitive generated report.
- [x] Docker build-context rules exclude the export/archive and secrets.
- [x] Lockfiles and `contracts/openapi/v1.json` remain committable.
- [x] The root README links `AI/README.md` and does not claim unimplemented commands/services.
- [x] `.env.example` contains no production value or credential.
- [x] The task branch is pushed and [PR #2](https://github.com/Flippylolz/WEF/pull/2) targets `docs/ai-documentation-foundation`; its diff contains only E1-T1 changes.
- [x] Neither PR was merged.

## Test plan

- Git: inspect ignored/untracked/staged files and confirm remote/current branch.
- Safety: test representative export, archive, media, environment, session, database, cache, and report paths against ignore rules.
- Docker context: inspect future context candidates using `.dockerignore` semantics without building an application image.
- Documentation: validate Markdown links and lints.
- GitHub: verify both PRs' base/head and changed-file lists, including isolation of the stacked E1-T1 diff.

## Verification evidence

- Bootstrap commit: `a8eda7b` on `main`.
- Documentation commit: `87dec75` on `docs/ai-documentation-foundation`; [PR #1](https://github.com/Flippylolz/WEF/pull/1).
- E1-T1 safety commit: `c7f7410` on `chore/E1-T1-repository-safety`; [PR #2](https://github.com/Flippylolz/WEF/pull/2).
- `git check-ignore` matched representative export, archive, environment, session, database, report, and dependency-cache paths.
- IDE lints reported no errors for changed documentation.

## Rollout and rollback

Push the minimal README `main`, open the docs PR, then open the stacked E1-T1 PR. Before merge, rollback means close the PRs/delete their head branches. After merge, revert the relevant commit; do not rewrite shared history.

## Ready checklist

- [x] The file is authoritative under `tasks/`; its proposed definition is removed during promotion.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved spike revision 2 and is `satisfied`.
- [x] `implementation_gate` references owner-approved implementation-plan revision 3 and is `satisfied`.
- [x] The empty dependency set is verified and `dependency_gate` is `satisfied`.
- [x] Scope and acceptance criteria match the approved implementation plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] The dedicated branch is `chore/E1-T1-repository-safety`.
- [x] The branch is stacked from the documentation foundation and contains E1-T1 only.
- [x] `branch.name` and `branch.created_at` were recorded when setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
