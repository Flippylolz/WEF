---
schema: ai-workflow/proposed-task@1
id: E7-T3
epic: E7
title: "Implement GitHub image and deployment workflows"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E1-T4, E7-T1, E7-T2]
requirement_ids: []
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017]
deferred_decision_ids: []
source: "legacy-roadmap:E7-T3"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T3: Implement GitHub image and deployment workflows

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement GitHub image and deployment workflows** to the epic outcome: every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Original roadmap definition

The following definition preserves the original E7-T3 roadmap entry:

- Priority/size: P1 / L
- Dependencies: E1-T4, E7-T1, E7-T2
- Work:
  - Build/push SHA/digest-tagged images to GHCR.
  - Reconstruct complete production configuration from GitHub Actions variables/secrets, transfer it plus release metadata to mode-0600 temporary paths, validate, and atomically activate it during the locked remote deployment.
  - Use pinned Actions, main-SHA pull-request-origin verification, and `AUTO_DEPLOY_ENABLED`.
- Acceptance:
  - A successful `main` push reruns/depends on CI and publishes the exact tested images.
  - Feature, hotfix, Dependabot, and pull-request events cannot run the production deploy job.
  - Automatic deployment requires `AUTO_DEPLOY_ENABLED=true` and a pushed SHA associated with a merged pull request targeting `main`; an unassociated direct push is tested/built but not deployed.
  - Manual `workflow_dispatch` can deploy an explicit tested SHA for the E7-T4 rehearsal.
  - Concurrent deployments cannot overlap.
  - The server uses read-only package credentials and verified SSH host identity.
  - Every deploy refreshes complete config without logging secrets; invalid config never becomes active and transfer temporaries are removed.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T4](../../E1-repository-developer-foundation/tasks/E1-T4-establish-ci-baseline.md), [E7-T1](E7-T1-build-production-compose-topology.md), [E7-T2](E7-T2-provision-and-verify-supplied-server.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Decision registry](../../../decisions/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Security](../../../security/README.md), [Data](../../../data/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P1 / L`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
