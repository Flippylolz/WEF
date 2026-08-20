---
schema: ai-workflow/implementation-plan@1
epic: E1
title: "Scheduled Dependabot merge controller"
status: approved
revision: 6
owner: owner
spike_revision: 2
task_sequence:
  - id: E1-T7
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T18:01:53Z"
  approved_revision: 6
  evidence: "Owner continue after E1-T6; AD-009 bounded plan revision; E1 spike revision 2; REPOSITORY_RULES Dependabot controller; ADR-017"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Dependabot merge controller (revision 6)

> Revision 6 authorizes only E1-T7 revision 1 after E1-T6.

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved.
- Binding docs: [REPOSITORY_RULES Dependabot](../../governance/REPOSITORY_RULES.md), ADR-017.
- E1-T6 is `done`.

## Scope and outcome

Add a scheduled/manual Dependabot merge controller that squash-merges only owner-labeled, bot-only, direct patch/minor PRs whose required CI checks succeeded — without checking out or executing pull-request code.

## Ordered task sequence

### 1. E1-T7 (revision 1) — Implement scheduled Dependabot merge controller

- Task: [E1-T7](tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md).
- Independently reviewable: workflow + default-branch script/config + unit tests for every allow/deny gate including head-change race.
- Dependencies: E1-T4, E1-T6 — both `done`.
- Out of scope: branch-protection rulesets, native auto-merge, upgrading dependencies in this PR.

## Safety and privacy

- Checkout default branch only; write token never executes PR code.
- Never use `gh pr merge --admin`.
- Refetch and `--match-head-commit` immediately before merge.

## Approval checklist

- [x] Spike revision 2 remains current.
- [x] E1-T6 is `done`.
- [x] AD-009 continue authority recorded as AD-030.
