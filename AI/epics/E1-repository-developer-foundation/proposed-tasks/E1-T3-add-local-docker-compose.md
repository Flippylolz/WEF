---
schema: ai-workflow/proposed-task@1
id: E1-T3
epic: E1
title: "Add local Docker Compose"
status: proposed
revision: 2
actionable: false
priority: P0
size: M
milestone: M1
dependencies: [E1-T2]
requirement_ids: []
decision_ids: [ADR-005, ADR-008, ADR-010]
deferred_decision_ids: []
source: "legacy-roadmap:E1-T3"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E1-T3: Add local Docker Compose

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Add local Docker Compose** to the epic outcome: a reproducible monorepo that cannot accidentally commit or package the source archive/media.

## Original roadmap definition

The following definition preserves the original E1-T3 roadmap entry:

- Priority/size: P0 / M
- Dependencies: E1-T2
- Work:
  - Build web/backend development and production targets.
  - Add PostGIS, Caddy, API, web, and on-demand importer services.
  - Add health checks, named volumes, internal network, and read-only source mount.
- Acceptance:
  - `docker compose up --build` produces a same-origin web/API stack.
  - Only intended edge ports are published.
  - Database state survives service recreation.
  - The importer sees source data read-only and application images contain no media.

## Revision 2 spike refinement

- Use the dedicated branch `feature/E1-T3-local-compose`.
- Add `infra/compose.yaml` only after completed E1-T2 provides real image targets, application commands, and health behavior.
- Use a WEF-scoped project name, one internal network, named PostGIS/media volumes, no explicit `container_name`, and health-check dependency conditions.
- Mount the source export with long syntax and `read_only: true` only into explicit importer runs; it is unavailable to public application services.
- Keep Caddy optional for local same-origin routing and Telegram disabled until Epic 8; use profiles where they simplify the default path.
- Extend the existing Makefile only with real Compose build/up/down/logs and importer dry-run targets.
- Additional acceptance:
  - Web, API, and PostGIS do not publish host ports when accessed through the edge.
  - No host port conflicts with documented production/shared-host services.
  - `docker compose config` resolves from the safe example configuration without a secret.
  - A clean down/up cycle preserves database state and does not make the source mount writable.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above as refined by revision 2's project-isolation, mount, health, profile, Makefile, and branch boundaries.
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
