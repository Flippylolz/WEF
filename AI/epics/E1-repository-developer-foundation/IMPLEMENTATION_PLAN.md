---
schema: ai-workflow/implementation-plan@1
epic: E1
title: "Repository and developer foundation implementation plan"
status: approved
revision: 3
owner: owner
spike_revision: 2
task_sequence:
  - id: E1-T1
    revision: 3
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T21:14:00Z"
  approved_revision: 3
  evidence: "Explicit owner approval in the current Cursor conversation: minimal README main bootstrap, documentation PR, then stacked E1-T1 PR"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Repository and developer foundation

## Approved spike baseline

[E1 spike revision 2](SPIKE.md) was explicitly approved by Flippylolz on 2026-08-12. It separates repository safety, application/Dockerfile scaffolding, CI, and Compose into independent tasks and branches.

This implementation-plan revision intentionally authorizes only the repository-safety bootstrap requested now. E1-T2 through E1-T7 remain proposed/cancelled and are not executable sequence entries.

## Scope and outcome

Create a reproducible Git/GitHub baseline that cannot accidentally commit or package the source archive/media:

- initialize the empty repository and canonical remote;
- create a minimal root-README commit on `main`, because empty commits are not allowed and GitHub needs a base ref;
- put all existing `AI/**` documentation on `docs/ai-documentation-foundation` and open a PR to `main`;
- stack `chore/E1-T1-repository-safety` on the documentation branch;
- add `.gitignore`, `.dockerignore`, `.env.example`, and a concise root `README.md`;
- commit and push the task branch and open its PR against the documentation branch; and
- leave both PRs unmerged unless the owner separately requests merge.

Dockerfiles, Compose, Makefile, applications, lockfiles, CI, Dependabot, and deployment are explicitly excluded from this plan revision.

## Ordered task sequence

### 1. E1-T1 — Initialize repository safety

- Task: [E1-T1 revision 3](tasks/E1-T1-initialize-repository-safety.md).
- Dependencies: none.
- Branch: `chore/E1-T1-repository-safety`.
- Independent result: root ignore/environment/README safety baseline committed on one task branch and proposed through one stacked PR after the pre-existing documentation gets its own PR.
- GitHub bootstrap: because the remote is empty, create/push a minimal root-README commit on `main`. Put the existing AI documentation on `docs/ai-documentation-foundation` with a PR to `main`, then branch E1-T1 from it and target the stacked PR back to the documentation branch.
- Verification: Git ignore/staging inspection, Docker-context candidate inspection, Markdown/link/lint checks, remote/branch checks, and PR base/head/file review.

## Affected files and systems

- Existing `AI/**` documents, committed independently on `docs/ai-documentation-foundation`.
- New root `.gitignore`, `.dockerignore`, `.env.example`, and `README.md`.
- Local `.git` metadata.
- GitHub `Flippylolz/WEF` main/head refs and two unmerged pull requests.

No application module, runtime, public API, database, migration, production host, or source dataset is changed.

## Safety and privacy

- Ignore the raw `est-test/` tree, `est-test.tar.gz`, archives, media, environment/secrets, Telegram sessions, local databases, caches, coverage, build outputs, and sensitive generated reports.
- Keep dependency lockfiles and the future committed OpenAPI contract eligible for version control.
- `.env.example` contains safe names/comments only.
- Verify candidates before staging and staged content before commit.
- Do not build or copy an application image in this task.

## Commit and pull-request plan

1. Confirm the GitHub repository is empty and the authenticated owner has access.
2. Initialize Git with the canonical remote.
3. Commit and push a minimal root `README.md` on `main`, solely to create the PR base.
4. Create `docs/ai-documentation-foundation`, stage only `AI/**`, review the full staged diff, commit, push, and open a documentation PR to `main`.
5. Create `chore/E1-T1-repository-safety` from the documentation branch.
6. Add and validate `.gitignore`, `.dockerignore`, `.env.example`, and the full root README.
7. Stage only those E1-T1 files; review the full staged diff and secret/data exclusions.
8. Commit and push the task branch.
9. Open a stacked PR from E1-T1 to `docs/ai-documentation-foundation`, so its diff contains only E1-T1.
10. Do not merge either PR without a separate owner instruction.

## Test and verification strategy

- `git check-ignore`/status/staged diff for representative sensitive paths and intended files.
- `.dockerignore` candidate inspection without an application build.
- Markdown relative-link validation and IDE lints.
- Git remote/current branch/log checks.
- GitHub PR base/head/changed-file verification for both the documentation PR and stacked E1-T1 PR.

## Rollout and rollback

The only external rollout is creating refs and two PRs. Before merge, rollback is closing the PRs and deleting their head branches. After merge, rollback is a normal revert; do not force-push or rewrite shared history. The minimal README base remains harmless repository history.

## Risks and mitigations

- **Source/secret leak:** strict ignore files plus pre-stage and staged-diff inspection.
- **No PR base in an empty repository:** one minimal README bootstrap commit on `main`; pre-existing docs and E1-T1 then use separate/stacked PRs.
- **Stacked diff contamination:** branch E1-T1 from the documentation branch and target its PR to that branch, then verify changed files.
- **Scope creep into Docker/Compose/Make:** explicitly excluded and left in later proposed tasks.
- **False branch-protection claim:** ADR-017 remains authoritative; use procedural review/checks only.
- **Accidental merge:** PR creation is in scope, merge is not.

## Invalidation triggers

Return to the E1 spike if repository ownership, branch/PR policy, source-data boundaries, or the task split changes materially. Return to this plan if the approved spike remains valid but commit contents, base/bootstrap sequence, branch, verification, or rollback changes.

## Approval checklist

- [x] E1 spike revision 2 has explicit owner approval and remains valid.
- [x] E1-T1 revision 3 is promoted with complete acceptance and traceability.
- [x] Its empty dependency set is verified.
- [x] Files, Git/GitHub effects, safety checks, risks, rollout, and rollback are explicit.
- [x] No deferred decision blocks repository initialization or procedural PR use.
- [x] No proposed task appears as an executable sequence.
- [x] No production or disposable proof code is authorized by this draft.
- [x] Revision 3 received explicit owner approval and approval metadata matches this revision.

## Owner decision

Flippylolz explicitly approved implementation-plan revision 3 on 2026-08-12 by selecting the minimal README bootstrap, separate documentation PR, and stacked E1-T1 PR. This authorizes the specified files, Git initialization, commits, pushes, and two PRs. It does not authorize merge, Dockerfiles, Compose, Makefile, applications, CI, or any other proposed task.
