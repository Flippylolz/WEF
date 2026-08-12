---
schema: ai-workflow/implementation-plan@1
epic: E0
title: Replace with implementation plan title
status: draft
revision: 1
owner: owner
spike_revision: null
task_sequence:
  - id: E0-T1
    revision: 1
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Replace with title

> Copy this file to an epic’s `IMPLEMENTATION_PLAN.md`. Replace every example identity/task value. Planning may begin only after the spike is approved; code remains prohibited until the owner approves this plan’s current revision.

## Approved spike baseline

- Link the epic `SPIKE.md`.
- Record why `spike_revision` is still current and list its binding decisions/constraints.

## Scope and outcome

State the approved epic outcome, included behavior, and explicit exclusions.

## Ordered task sequence

List every promoted task in the same order as YAML `task_sequence`. Each sequence object records the task’s `id` and current integer `revision`, locking the approved plan to that task definition. For each task:

1. link its file under `tasks/`;
2. state why it is independently reviewable;
3. list dependencies and the evidence that will satisfy them;
4. describe affected modules/contracts;
5. summarize tests, migrations, risks, rollout, and rollback.

Only promoted tasks are allowed. Proposed tasks are planning inputs and cannot appear as executable sequence entries.

## Cross-task architecture

Describe dependency direction, shared interfaces, transaction boundaries, generated contracts, and how tasks avoid duplicating domain/application rules.

## Data and migrations

Document schema/data changes, compatibility order, idempotency, validation, and rollback/recovery boundaries. State explicitly when rollback cannot restore data.

## Security and privacy

Document authentication/authorization, contact handling, audit minimization, secrets, threat controls, and negative tests as applicable.

## Test and verification strategy

Map task acceptance to unit, integration, contract, migration, end-to-end, accessibility, security, production-build, and operational checks.

## Operations, rollout, and rollback

Describe configuration ownership, release order, health checks, observability, rollback, host non-interference, and owner/manual steps. Do not describe persistent NUC data as backed up while backups remain deferred.

## Risks and mitigations

List concrete risks, likelihood/impact where useful, preventive controls, detection, response, and owning task.

## Invalidation triggers

List epic-specific conditions that return work to this plan or to the spike in addition to the global workflow rules.

## Approval checklist

- [ ] The referenced spike revision has explicit owner approval and remains valid.
- [ ] Every sequence entry is a promoted task with complete acceptance criteria and traceability.
- [ ] Dependencies are complete, acyclic, and enforceable task by task.
- [ ] Affected modules, contracts, tests, migrations, risks, rollout, and rollback are explicit.
- [ ] Deferred decisions required for implementation are resolved.
- [ ] No production or disposable proof code has been written.
- [ ] `revision` represents the material plan being submitted.
- [ ] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval authorizes the recorded plan revision, not blanket epic implementation: each task must still satisfy promotion, dependency, state, and one-branch-per-task gates.
