# Governance

This domain owns repository, branch, pull-request, CI, deployment-event, hotfix, dependency-update, and ownership rules.

## Canonical document

- [Repository and change rules](REPOSITORY_RULES.md) — repository safety, branch/PR policy, expected checks, deployment gates, Dependabot, and owner exceptions.

## Current enforcement model

- Every implementation task uses exactly one task-scoped branch and pull request; unrelated tasks do not share a branch.
- Ordinary work does not push directly to `main`, and `main` is never force-pushed.
- GitHub branch protection enforces pull requests, review, strict required checks, resolved conversations, linear history, and protection from force-pushes or deletion on `main` under ADR-023.
- Repository administrators retain only the owner emergency/bootstrap bypass; every use requires an audit trail and post-merge CI.
- Raw exports, media, databases, Telegram sessions, credentials, secrets, and sensitive generated reports never enter Git.

Workflow approval makes work eligible to start; it does not waive repository governance or CI requirements.
