---
schema: ai-workflow/proposed-implementation-plan@1
epic: E1
title: "Scheduled Dependabot merge controller"
status: proposed
revision: 6
owner: owner
spike_revision: 2
supersedes: 5
task_sequence:
  - id: E1-T7
    revision: 1
---

# Proposed Implementation Plan: Dependabot merge controller (revision 6)

> **Awaiting approval.** Follows completed E1-T6 Dependabot configuration.

## Context

- E1-T6 is `done`; Dependabot already opens grouped patch/minor PRs.
- Spike revision 2 and REPOSITORY_RULES require a 15-minute/manual controller that never checks out PR code.
- ADR-017 accepts this compensating control instead of native protected-branch auto-merge.

## Goal

Promote and execute **E1-T7 revision 1**: scheduled owner-label/check/bot-commit-gated squash merge for Dependabot-only patch/minor PRs.

## Owner decision request

1. Approve **this revision 6** under AD-009 continue authority after E1-T6.
2. Promote E1-T7 and implement on `chore/E1-T7-dependabot-merge-controller`.
