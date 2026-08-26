# Repository and Change Rules

## Repository

- Canonical repository: `https://github.com/Flippylolz/WEF`.
- Intended visibility: private unless the owner explicitly changes it.
- Default branch: `main`.
- The current repository is empty and has no default branch.
- The local workspace is not yet a Git repository.
- Raw exports, media, databases, generated import reports containing source data, Telegram sessions, and secrets must never be committed.

As of 2026-08-12, the authenticated account has repository admin access, but GitHub returns `403` for private-repository rulesets with the current account plan. [ADR-017](../decisions/adr/ADR-017-no-enforced-branch-protection.md) makes paid-plan/protected-branch work completely out of scope. The rules below are procedural unless explicitly described as workflow-enforced.

## Branch policy

Every feature or independently reviewable change uses its own branch and pull request. Do not combine unrelated features in one branch.

Allowed branch patterns:

- `feature/<task-id>-<short-description>` for product features.
- `spike/<short-description>` for time-boxed architecture/dependency/research proofs with explicit exit criteria.
- `fix/<task-id>-<short-description>` for non-emergency defects.
- `hotfix/<short-description>` for production emergencies.
- `docs/<short-description>` for documentation-only changes.
- `chore/<short-description>` for tooling and maintenance.
- `dependabot/**` for GitHub-managed dependency updates.

Examples:

- `feature/E4-T1-map-geojson`
- `spike/backend-architecture-dependencies`
- `fix/E3-T3-geocode-bounds`
- `hotfix/api-startup`

Rules:

- Branch from the latest `main` when the task has no open dependency. Under [ADR-018](../decisions/adr/ADR-018-ordered-stacked-pull-requests.md), a dependent task branches from its immediate upstream task branch and targets that branch until the parent merges.
- Keep a branch scoped to one task/feature.
- Rebase or update from `main` before merge when required checks are strict.
- Merge through a pull request; do not push ordinary work directly to `main`.
- Use squash merge so one reviewed feature becomes one main-branch commit.
- Delete merged branches automatically.
- Never force-push `main`.

## Ordered stacked pull requests

Do not pause approved implementation merely because an upstream pull request awaits review:

1. Verify the dependent task's spike and implementation-plan approvals.
2. Record a `stacked` dependency gate with each upstream task, branch, pull request, and head commit.
3. Branch from the immediate upstream task branch.
4. Open the child pull request against that branch so the diff contains only the child task.
5. Continue the stack in dependency order; never combine two task scopes in one branch.
6. When a parent merges, retarget/rebase its direct child to the parent's new base and rerun required checks.
7. Merge from the bottom/base of the stack upward. A child cannot be completed or merged while any dependency is not `done`.

Reviews and CI remain required before merge. Stacking changes wait time, not acceptance or completion standards.

## `hotfix/` exception

`hotfix/*` is the emergency exception to the normal feature branch category and review timing, not an automatic way for any contributor to skip safety controls.

- Only the repository owner may authorize an emergency exception to the procedural policy.
- A hotfix still uses a `hotfix/*` branch and pull request whenever GitHub is operational.
- Run lint and relevant tests before merge whenever the production incident allows it.
- If the owner uses an administrator exception, record the incident/reason in the pull request, deploy the smallest possible change, and run the full pipeline immediately after merge.
- Any failed post-merge check requires an immediate follow-up fix or rollback.

`hotfix/**` is not excluded from CI with a workflow condition. The owner uses the separately audited manual deployment path when an emergency exception is genuinely required.

To keep administrator exceptions owner-only on a personal repository:

- Keep repository admin access limited to the owner.
- Give collaborators only the minimum read/triage/write/maintain role they need.
- Do not grant collaborators or GitHub Apps administrator/write authority unless a later decision names and justifies it.

## Procedural `main` policy and CI check names

GitHub does not enforce these controls under [ADR-017](../decisions/adr/ADR-017-no-enforced-branch-protection.md). Contributors and owner automation follow them procedurally:

- Require changes through pull requests.
- Require at least one approving review.
- Dismiss stale approvals when new commits are pushed.
- Require approval of the most recent reviewable push by someone other than its author.
- Require all review conversations to be resolved.
- Require strict status checks against the latest `main`.
- Block force pushes.
- Block branch deletion.
- Require linear history.
- Allow squash merge; disable merge commits and rebase merges unless a later decision changes history policy.
- Owner emergency exceptions require an audit trail and post-merge CI.

Expected CI check names must remain stable for scripts/manual review. Add them only after each workflow has run at least once:

- `docs`
- `backend-quality`
- `backend-tests`
- `frontend-quality`
- `frontend-tests`
- `contract`
- `compose-build`
- `e2e`

Checks may be introduced incrementally while the applications are scaffolded, but no implemented component may merge without its lint/type/test/build checks.

## Pull-request rules

Each pull request must:

- Reference one authoritative task in the [epic registry](../epics/README.md) or state why it is unplanned.
- Explain user impact and technical risk.
- Include a test plan and migration/deployment notes when relevant.
- Update affected documents under `AI/`.
- Contain no raw dataset, media, credentials, private session, or generated sensitive report.
- Pass every required check before ordinary merge.

Review should verify:

- Scope matches the branch/task.
- Tests cover behavior and failure cases.
- API/schema changes remain compatible or have a migration plan.
- Deployment changes preserve rollback and existing server workloads.
- Logs, fixtures, and public responses do not leak source contacts or secrets.

## CI and deployment event rules

CI runs for pull requests targeting `main`.

CI fails when backend coverage or frontend coverage is below 90%. The suites run in separate jobs and Makefile targets. The Backend job uses pytest `--cov-fail-under=90`. The Frontend job uses Vitest `coverage.thresholds` of 90% for lines and branches. The Coverage badge job applies the same per-suite floor and does not use a combined threshold.

Deployment does not run for:

- Feature, fix, docs, chore, hotfix, or Dependabot branch pushes.
- Pull-request events.
- Forks.
- Failed CI.

The release workflow triggers only on:

```yaml
on:
  push:
    branches:
      - main
```

Because branch protection is out of scope, the deployment job's associated-PR check is a permanent compensating control for this scope: an ordinary direct push to `main` is built/tested but does not auto-deploy. An owner-authorized hotfix uses the separately audited manual path.

The deploy job additionally:

- Depends on the release CI/build jobs.
- Reconstructs complete production configuration from GitHub Actions variables/secrets, transfers it to mode-0600 temporary files, validates it, and atomically activates it on every deploy; it does not depend on paid environment-review protection.
- Uses one concurrency group with `cancel-in-progress: false`.
- Builds/pulls images identified by commit SHA/digest.
- Receives no production secret in pull-request workflows.
- Verifies through the GitHub API that the pushed SHA is associated with a merged pull request targeting `main`; an unassociated direct push builds/tests but does not deploy automatically.

Until [E7-T4](../epics/E7-production-delivery/tasks/E7-T4-implement-health-verification-and-rollback.md) proves health-gated rollback on the supplied server, keep the repository variable `AUTO_DEPLOY_ENABLED=false` and deploy test releases by a manual `workflow_dispatch` for an explicit SHA. After that rehearsal, set it to `true`; successful, tested `main` merges then deploy automatically.

## Dependabot

Add `.github/dependabot.yml` for every committed dependency ecosystem:

- npm in `apps/web`.
- Python/pip-compatible metadata in `apps/backend`.
- Docker images in their actual Dockerfile directories.
- GitHub Actions in `/`.

Policy:

- Check weekly.
- Open security updates as soon as GitHub provides them.
- Group compatible patch/minor development updates by ecosystem.
- Keep a bounded open-pull-request limit.
- Do not group major runtime/framework upgrades with routine updates.
- Pin GitHub Actions to full commit SHAs; Dependabot updates those pins through reviewed pull requests.

Dependabot provides the update schedule and creates pull requests natively on GitHub Free. A custom scheduled merge controller replaces the unavailable protected-branch/native-auto-merge gate.

Create `.github/workflows/dependabot-merge.yml` with:

- `schedule` every 15 minutes plus `workflow_dispatch`.
- One concurrency group and `cancel-in-progress: false`.
- Minimum `contents: write`, `pull-requests: write`, and read permissions needed for checks/actions.
- No checkout of the pull-request branch and no execution of pull-request code.
- A repository-owned script/config from the default branch that evaluates each candidate.

A pull request is eligible only when all conditions are true:

1. It is open, non-draft, targets `main`, and belongs to this repository.
2. Its author is `dependabot[bot]` or the GitHub GraphQL form `app/dependabot`, and its head branch starts with `dependabot/`.
3. It has the exact `automerge` label.
4. The current `automerge` label was applied by an allowlisted owner, initially `Flippylolz`; an automatically or collaborator-applied label is insufficient.
5. Dependabot metadata classifies it as a direct patch/minor update. Major updates never auto-merge.
6. Every commit's GitHub author is `dependabot[bot]`; committers may only be `dependabot[bot]` or a documented GitHub bot such as `web-flow`. Any human-authored commit makes the PR permanently ineligible until replaced by a clean Dependabot branch.
7. The head includes the current `main`; stale/diverged branches are deferred for Dependabot to rebase and must rerun CI.
8. Every explicitly configured required check name exists on the current head and completed successfully.
9. No check on the current head is pending, failing, cancelled, timed out, stale, or action-required.
10. GitHub reports the PR mergeable without conflicts.

Store the expected check-name allowlist in a reviewed default-branch file such as `.github/dependabot-required-checks.json`. The controller must not infer success from “no failing checks,” because missing CI would otherwise be treated as safe.

Immediately before merging, refetch labels, commits, head SHA, checks, and mergeability. Merge with:

```text
gh pr merge <number> --squash --delete-branch --match-head-commit <verified-sha>
```

`--match-head-commit` closes the race where a human pushes after validation. The controller records a step summary for every merged/deferred/rejected PR and never uses `--admin`.

The actual lint/test workflow remains unprivileged and runs on `pull_request`. The scheduled controller only reads its results and performs the final merge; it does not run dependency code with a write token.

This is a compensating control, not equivalent to protected branches: GitHub cannot atomically lock the base branch or label state together with the merge. The immediate refetch plus expected-head guard makes the window small; [ADR-017](../decisions/adr/ADR-017-no-enforced-branch-protection.md) accepts the remaining risk.

## Ownership and administrator-exception audit

- The GitHub repository owner is the only intended administrator-exception authority.
- Exceptions are for production emergencies and repository bootstrap only.
- Every exception must leave a GitHub audit trail and a linked explanation.
- An exception does not waive post-merge CI, deployment health checks, or rollback requirements.
- Routine dependency updates, documentation, and “small” fixes are not emergencies.

## Bootstrap order

Work allowed now:

1. Initialize the local repository with the existing `AI/` documentation and safety ignore files.
2. Add `origin` as `git@github.com:Flippylolz/WEF.git`; SSH is the preferred Git transport.
3. Create and push the initial `main`.
4. Add CI workflows and follow branch/pull-request rules manually.
5. Enable squash merge, auto-delete branches, vulnerability alerts, and Dependabot version/security updates.
6. Add the scheduled label/check/commit-gated Dependabot merge controller.
7. Build the main-only GHCR/SSH deployment workflow; keep automatic execution disabled with `AUTO_DEPLOY_ENABLED=false` until [E7-T4](../epics/E7-production-delivery/tasks/E7-T4-implement-health-verification-and-rollback.md).

Permanently out of current scope under [ADR-017](../decisions/adr/ADR-017-no-enforced-branch-protection.md):

1. Upgrading solely for private-repository branch protection.
2. Native protection-dependent auto-merge.
3. A protected-main ruleset and owner bypass list.
4. Claims/tests that direct pushes, force pushes, deletion, or failing-check merges are platform-blocked.

`main` protection is an accepted unenforced policy. The custom Dependabot controller and production auto-deploy provide their own explicit gates and do not claim to protect `main` from manual merges/pushes. The cancelled workflow candidate remains recorded as [E1-T5](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T5-configure-protected-main-governance.md).
