---
schema: ai-workflow/proposed-task@1
id: E1-T4
epic: E1
title: "Establish CI baseline"
status: proposed
revision: 1
actionable: false
priority: P0
size: M
milestone: M1
dependencies: [E1-T2]
requirement_ids: []
decision_ids: [ADR-009, ADR-012, ADR-013, ADR-017]
deferred_decision_ids: []
source: "legacy-roadmap:E1-T4"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E1-T4: Establish CI baseline

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Establish CI baseline** to the epic outcome: a reproducible monorepo that cannot accidentally commit or package the source archive/media.

## Original roadmap definition

The following definition preserves the original E1-T4 roadmap entry:

- Priority/size: P0 / M
- Dependencies: E1-T2
- Work:
  - Add backend/frontend quality jobs, test database, image build checks, documentation-link validation, and `import-linter` architecture contracts.
  - Generate/compare committed `contracts/openapi/v1.json`, lint it, detect breaking changes, generate/type-check the frontend client, and upload static HTML/contract artifacts per [OpenAPI contract](../../../contracts/OPENAPI.md).
- Acceptance:
  - A representative failing lint, test, migration, contract, or build check blocks CI.
  - A stale/breaking OpenAPI change or frontend contract mismatch blocks CI.
  - JSON, generated TypeScript declaration, and static HTML are available as a commit-addressed CI artifact.
  - CI uses synthetic fixtures and no production/source credentials.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T2](E1-T2-scaffold-web-and-backend-applications.md)
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Decision registry](../../../decisions/README.md), [Architecture](../../../architecture/README.md), [Governance](../../../governance/README.md), [Operations](../../../operations/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P0 / M`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
