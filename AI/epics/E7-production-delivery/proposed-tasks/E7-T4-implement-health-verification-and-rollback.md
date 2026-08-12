---
schema: ai-workflow/proposed-task@1
id: E7-T4
epic: E7
title: "Implement health verification and rollback"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M3
dependencies: [E7-T3]
requirement_ids: []
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015]
deferred_decision_ids: []
source: "legacy-roadmap:E7-T4"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T4: Implement health verification and rollback

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement health verification and rollback** to the epic outcome: every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Original roadmap definition

The following definition preserves the original E7-T4 roadmap entry:

- Priority/size: P1 / M
- Dependencies: E7-T3
- Work:
  - Add preflight, migration, post-deploy smoke tests, previous-release retention, and rollback command.
- Acceptance:
  - A deliberately unhealthy release fails deployment and restores the previous compatible app release.
  - Release SHA/digests and migration revision are auditable.
  - No automatic destructive schema downgrade occurs.
  - After rollback rehearsal succeeds, setting `AUTO_DEPLOY_ENABLED=true` makes future successful merged-PR pushes to `main` deploy automatically.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E7-T3](E7-T3-implement-github-image-and-deployment-workflows.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Decision registry](../../../decisions/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Security](../../../security/README.md), [Data](../../../data/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P1 / M`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
