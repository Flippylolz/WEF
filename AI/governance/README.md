# Governance

This domain owns repository, branch, pull-request, CI, deployment-event, hotfix, dependency-update, and ownership rules.

## Canonical document

- [Repository and change rules](REPOSITORY_RULES.md) — repository safety, branch/PR policy, expected checks, deployment gates, Dependabot, and owner exceptions.

## Current enforcement model

- Every implementation task uses exactly one task-scoped branch and pull request; unrelated tasks do not share a branch.
- Ordinary work does not push directly to `main`, and `main` is never force-pushed.
- GitHub's active `Protect main` ruleset enforces pull requests, strict required checks, resolved conversations, linear history, and protection from force-pushes or deletion on `main` under ADR-023. Approving reviews are not required while the owner is the sole maintainer.
- Every PR has standing owner authorization to merge after all required CI checks pass on its current head and the repository's merge requirements are satisfied. Agents do not need another per-PR merge request or confirmation; use the verification and squash-merge procedure in the canonical rules.
- GitHub native auto-merge is available and enabled. Eligible PRs may opt in while CI runs, and GitHub merges them after its required checks and other merge gates pass.
- Repository administrators retain only the owner emergency/bootstrap bypass; every use requires an audit trail and post-merge CI.
- Raw exports, media, databases, Telegram sessions, credentials, secrets, and sensitive generated reports never enter Git.

Workflow approval makes work eligible to start; it does not waive repository governance or CI requirements.
