---
schema: ai-workflow/proposed-implementation-plan@1
epic: E1
title: "Dependabot update pull requests"
status: proposed
revision: 5
owner: owner
spike_revision: 2
supersedes: 4
task_sequence:
  - id: E1-T6
    revision: 1
---

# Proposed Implementation Plan: Dependabot updates (revision 5)

> **Awaiting approval.** Follows completed E1-T1/T2/T3/T4 and remaining proposed Dependabot work from spike revision 2.

## Context

- E1-T1, E1-T2, E1-T4, and E1-T3 are `done`; E1-T5 remains cancelled.
- Spike revision 2 already bounded E1-T6 (Dependabot PRs) and E1-T7 (merge controller).
- REPOSITORY_RULES require weekly npm/Python/Docker/Actions updates with patch/minor grouping and bounded open PRs.
- E1-T7 stays proposed until this configuration exists.

## Goal

Promote and execute **E1-T6 revision 1**: add `.github/dependabot.yml` for every committed ecosystem so Dependabot opens version/security update PRs that run normal CI; keep majors ungrouped and leave auto-merge to E1-T7.

## Ordered sequence

### 1. E1-T6 (revision 1) — Configure Dependabot update pull requests

- Scope: weekly npm (workspace root), pip (`apps/backend`), Docker (`apps/backend`, `apps/web`), and GitHub Actions (`/`) with patch/minor grouping and open-PR limits.
- Out of scope: merge controller workflow (E1-T7), branch-protection changes, production deploy changes, dependency upgrades in this PR itself.

## Owner decision request

1. Approve **this revision 5** under AD-009 continue authority after M3 quality gates.
2. Promote E1-T6 and implement on `chore/E1-T6-dependabot-updates`.
