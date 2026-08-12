---
schema: ai-workflow/proposed-task@1
id: E0-T1
epic: E0
title: Replace with proposed task title
status: proposed
revision: 1
actionable: false
priority: P0
size: S
milestone: M1
dependencies: []
requirement_ids: []
decision_ids: []
deferred_decision_ids: []
source: null
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E0-T1: Replace with proposed task title

> Copy this file into an epic’s `proposed-tasks/`. Replace all example identity values. `actionable` remains `false`; no branch or implementation work may start from this file.

## Outcome

State the single independently reviewable result.

## Scope

- List included work.

## Out of scope

- List explicit exclusions and likely follow-up work.

## Work

- Describe intended behavior and constraints without prescribing unapproved implementation details.

## Acceptance criteria

- [ ] Add objective, testable criteria.

## Dependencies and gates

- Explain each task dependency and deferred-decision gate.
- Link affected product requirements, decisions, and domain documents.

## Risks and notes

Record uncertainty, data/security/operational concerns, and questions to resolve during refinement.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic’s `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.

Valid proposed-task states are only `proposed`, `cancelled`, and `deferred`. Promotion uses the [task template](TASK.md) and does not itself make the task `ready`.
