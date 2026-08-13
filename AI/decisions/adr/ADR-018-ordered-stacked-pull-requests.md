---
schema: ai-docs/adr@1
id: ADR-018
title: Allow ordered stacked pull request implementation
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-018: Allow ordered stacked pull request implementation

- Status: accepted
- Date: 2026-08-12
- Decision: do not wait for review or merge of an upstream task before preparing the next approved dependent task. A dependent task may enter `ready`/`in_progress` with `dependency_gate.status: stacked` when every incomplete dependency has an open pull request in the direct branch ancestry and merge order is explicit.
- Rationale: the owner wants continuous implementation through reviewable stacked pull requests while preserving small task boundaries and ordered integration.
- Consequence: a stacked task branches from the immediate upstream task branch and opens its pull request against that branch, so its review diff contains only the task. When an upstream pull request merges, each direct child is retargeted/rebased in order. No stacked task may be declared `done`, merged, or used for production until its dependency gate transitions from `stacked` to `satisfied` after all dependencies are `done`.
- Safety constraints:
  - Spike and implementation-plan approvals remain mandatory.
  - One task, branch, and pull request remain mandatory.
  - A `stacked` dependency gate records every upstream task ID, branch, pull request, and head commit.
  - Upstream material changes invalidate or require refreshing affected descendants.
  - Reviews and required CI remain merge gates even though implementation continues.
  - The stack merges from its base upward; no child merges before its parent.
- Scope: this changes task start/dependency timing only. It does not relax product, architecture, security, test, review, CI, completion, or deployment requirements.
