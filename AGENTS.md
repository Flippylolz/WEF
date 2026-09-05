# Repository Instructions

These instructions apply to every agent working in this repository. Follow the
more detailed policies in `AI/governance/REPOSITORY_RULES.md` and the workflow
documentation under `AI/workflow/` when they are relevant to a change.

## Setup

- Install locked backend and frontend dependencies with `make install`.
- Start the complete local stack with `make up` when integration behavior is
  needed; use `pnpm --filter web dev` for frontend-only development.
- Use the tool versions recorded in `.tool-versions` and the package manager
  versions recorded in the lockfiles and package manifests.

## Validation

- Run `make lint` and `make test` before every push.
- Run `make format-check`, `make typecheck`, and `make contract-check` when the
  affected scope can exercise those checks.
- Add or update tests when behavior changes, including relevant failure cases.
- Report the commands run and their results in the pull request.

## Branches and pull requests

- Start each independently reviewable change from an up-to-date `main` on its
  own dedicated branch. Do not implement ordinary work directly on `main` and
  do not reuse a previous change's branch.
- Use a descriptive category prefix: `feat/` for features, `doc/` for
  documentation, `bugfix/` for defects, `hotfix/` for production emergencies,
  `chore/` for tooling or maintenance, and `spike/` for time-boxed research.
- Keep each branch and pull request limited to one coherent change.
- Open pull requests against `main` unless an approved stacked change must
  target its immediate parent branch.
- Use the GitHub CLI (`gh`) to create and manage pull requests.
- Run `gh` commands with escalated access outside the sandbox so the GitHub CLI
  can read credentials from the system keychain.
- Do not merge while any required CI check is pending, failing, cancelled, or
  missing. Merge only after every required check has completed successfully.
- Every pull request has standing owner authorization to merge once all required
  CI checks pass on its current head and the repository's merge requirements are
  satisfied. Do not ask for a separate per-PR merge request or confirmation.
- GitHub native auto-merge is available and enabled. An eligible PR may be queued
  while CI runs using `gh pr merge` with `--auto --squash --delete-branch` and
  `--match-head-commit <head-sha>`; GitHub merges only after its required checks
  and other merge gates pass.
- Before merging, verify the current head, required checks, resolved review
  conversations, mergeability, and any task dependencies. Squash-merge with
  `--match-head-commit <verified-sha>` and never use `--admin` for an ordinary merge.

## Multi-agent coordination

- Assume other agents may be changing the repository at the same time. Check
  `git status` before editing, before staging, and after completing work.
- Preserve unrelated changes. Never discard, overwrite, stage, commit, or
  revert work outside the assigned scope.
- Do not switch branches in a shared checkout that contains another agent's
  work. Use an isolated worktree or coordinate ownership first.
- Keep edits scoped to the files required for the task, and report every file
  changed when handing work off.
- If another agent changes a file you are editing, reconcile both changes
  deliberately instead of replacing either version wholesale.

## Code and repository conventions

- Follow existing architecture and implementation patterns before introducing
  new abstractions.
- Keep the backend authoritative for business behavior; the frontend should
  render generated API contracts and backend-provided projections.
- Do not add production dependencies without user approval.
- Update affected documentation under `AI/` when behavior, contracts,
  architecture, operations, security, or delivery assumptions change.
- Never commit raw exports, source media, databases, generated sensitive
  reports, environment files, credentials, private keys, or Telegram sessions.
