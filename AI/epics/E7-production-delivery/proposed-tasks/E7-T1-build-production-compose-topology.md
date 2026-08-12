---
schema: ai-workflow/proposed-task@1
id: E7-T1
epic: E7
title: "Build production Compose topology"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E1-T3, E6-T2, E6-T3]
requirement_ids: []
decision_ids: [ADR-005, ADR-008, ADR-010, ADR-014, ADR-015]
deferred_decision_ids: []
source: "legacy-roadmap:E7-T1"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T1: Build production Compose topology

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Build production Compose topology** to the epic outcome: every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Original roadmap definition

The following definition preserves the original E7-T1 roadmap entry:

- Priority/size: P1 / L
- Dependencies: E1-T3, E6-T2, E6-T3
- Work:
  - Add the isolated `wef-production` Compose project with immutable image references, Caddy same-origin routes/optional TLS, deploy-refreshed service-scoped secrets, project-owned persistent paths/networks, health checks, and resource limits.
- Acceptance:
  - A production-like Compose project starts from published images.
  - Only `WEF_PUBLIC_PORT` is published, initially 3100/TCP; 80/443 remain a later TLS decision.
  - Media/database/Caddy state survives release replacement.
  - PostgreSQL/PostGIS and Telegram checkpoints/media use `/home/nuc/wef` persistence rather than container layers or Git.
  - No container/network/volume name or host port collides with the existing AI Forecast, DuckDNS, or WireGuard projects.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T3](../../E1-repository-developer-foundation/proposed-tasks/E1-T3-add-local-docker-compose.md), [E6-T2](../../E6-quality-security-operations/proposed-tasks/E6-T2-perform-privacy-and-security-hardening.md), [E6-T3](../../E6-quality-security-operations/proposed-tasks/E6-T3-add-operational-diagnostics.md)
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
