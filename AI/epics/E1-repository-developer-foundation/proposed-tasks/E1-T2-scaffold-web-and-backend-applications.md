---
schema: ai-workflow/proposed-task@1
id: E1-T2
epic: E1
title: "Scaffold web and backend applications"
status: proposed
revision: 2
actionable: false
priority: P0
size: M
milestone: M1
dependencies: [E0-T2]
requirement_ids: []
decision_ids: [ADR-001, ADR-012]
deferred_decision_ids: []
source: "legacy-roadmap:E1-T2"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E1-T2: Scaffold web and backend applications

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Scaffold web and backend applications** to the epic outcome: a reproducible monorepo that cannot accidentally commit or package the source archive/media.

## Original roadmap definition

The following definition preserves the original E1-T2 roadmap entry:

- Priority/size: P0 / M
- Dependencies: E0-T2
- Work:
  - Create `apps/web` with strict TypeScript/Next.js.
  - Create `apps/backend` as the approved package-by-feature modular monolith with composition root and enforced domain/application/infrastructure/interface boundaries.
  - Lock dependencies and pin supported runtime versions.
  - Add format, lint, type-check, and test commands.
- Acceptance:
  - Both applications start with placeholder health/page behavior.
  - A clean checkout installs/builds using only documented commands.
  - No application imports raw files through relative host paths.

## Revision 2 spike refinement

- Use the dedicated branch `feature/E1-T2-application-scaffold`.
- Consume the completed E0-T2 proof's exact runtime lines, manifests, lockfiles, package boundaries, health behavior, and measured commands; do not choose competing versions or architecture.
- Add named development/build/runtime Dockerfile targets for the real FastAPI and Next.js scaffold commands.
- Runtime stages use locked installs, non-root users, explicit entry commands, and exclude source data, media, development/documentation tooling, and build credentials.
- Introduce the root `Makefile` only with targets backed by commands implemented in this task: help, install, format, lint, type-check, test, contract generation/check, and image build.
- Additional acceptance:
  - Docker builds use the safe E1-T1 context controls and pass without copying the source export or secrets.
  - The Makefile is a thin command façade with no business logic, hidden environment selection, or no-op target.
  - Application health/page behavior runs both directly in its development container target and from its production runtime target.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above as refined by revision 2's Dockerfile, Makefile, branch, and accepted-E0 dependency boundaries.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E0-T2](../../E0-architecture-dependency-spike/tasks/E0-T2-execute-and-lock-the-architecture-proof.md)
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
