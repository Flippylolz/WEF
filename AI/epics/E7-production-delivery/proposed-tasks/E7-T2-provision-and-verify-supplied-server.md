---
schema: ai-workflow/proposed-task@1
id: E7-T2
epic: E7
title: "Provision and verify supplied server"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M3
dependencies: [E7-T1]
requirement_ids: []
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015]
deferred_decision_ids: [D-001]
source: "legacy-roadmap:E7-T2"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T2: Provision and verify supplied server

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Provision and verify supplied server** to the epic outcome: every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Original roadmap definition

The following definition preserves the original E7-T2 roadmap entry:

- Priority/size: P1 / M
- Dependencies: D-001, E7-T1
- Work:
  - Complete the server handoff in [deployment documentation](../../../operations/DEPLOYMENT.md) and use the inspected baseline in [production server baseline](../../../operations/SERVER.md).
  - Configure `/home/nuc/wef`, selected public port, router/firewall, DNS/HTTP(S), secret files, and resource ceilings within the provided `nuc` user's permissions.
- Acceptance:
  - Host checks, known-host SSH, DNS/HTTP(S), chosen-port reachability, disk headroom, and restricted access are documented and pass.
  - No source export is copied before storage capacity is verified.
  - Before/after inventories prove existing projects, containers, health, and bindings on 3000/TCP, 8080/TCP, and 51820/UDP are unchanged.
  - The owner-reported 3100 router rule reaches Caddy after a same-run host-port conflict check.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E7-T1](E7-T1-build-production-compose-topology.md)
- Deferred-decision gates: [D-001](../../../decisions/deferred/D-001-production-server-domain.md).
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
