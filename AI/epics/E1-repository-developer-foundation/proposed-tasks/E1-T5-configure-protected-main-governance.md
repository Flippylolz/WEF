---
schema: ai-workflow/proposed-task@1
id: E1-T5
epic: E1
title: "Configure protected-main governance"
status: cancelled
revision: 1
actionable: false
priority: P0
size: M
milestone: M1
dependencies: []
requirement_ids: []
decision_ids: [ADR-009, ADR-017]
deferred_decision_ids: [D-007]
source: "legacy-roadmap:E1-T5"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E1-T5: Configure protected-main governance

> This candidate is cancelled under ADR-017. It is retained for traceability and cannot be promoted unless approved scope explicitly restores it.

## Outcome

Contribute the independently reviewable result described by **Configure protected-main governance** to the epic outcome: a reproducible monorepo that cannot accidentally commit or package the source archive/media.

## Original roadmap definition

The following definition preserves the original E1-T5 roadmap entry:

- Priority/size: out of scope
- Status: cancelled under ADR-017.
- Dependencies: none
- Reopen only if the owner later adds an eligible GitHub plan or makes the repository public and explicitly restores enforced protection scope.

## Scope and approval boundary

- Preserve the cancellation and reopening conditions above if scope is ever restored.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: none.
- Deferred-decision gates: [D-007](../../../decisions/deferred/D-007-github-protection-eligibility.md).
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Decision registry](../../../decisions/README.md), [Architecture](../../../architecture/README.md), [Governance](../../../governance/README.md), [Operations](../../../operations/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `out of scope`. The YAML uses the required P0/M workflow classification while cancellation remains authoritative.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
