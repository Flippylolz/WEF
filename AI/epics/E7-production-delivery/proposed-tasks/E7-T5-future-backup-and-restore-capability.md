---
schema: ai-workflow/proposed-task@1
id: E7-T5
epic: E7
title: "Future backup and restore capability"
status: deferred
revision: 1
actionable: false
priority: P2
size: L
milestone: M3
dependencies: []
requirement_ids: []
decision_ids: [ADR-015]
deferred_decision_ids: []
source: "legacy-roadmap:E7-T5"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T5: Future backup and restore capability

> This candidate is deferred under ADR-015. It is retained for traceability and cannot be promoted until its named trigger is approved.

## Outcome

Contribute the independently reviewable result described by **Future backup and restore capability** to the epic outcome: every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Original roadmap definition

The following definition preserves the original E7-T5 roadmap entry:

- Priority/size: P2 / L
- Status: deferred; out of initial scope under ADR-015.
- Dependencies: none
- Future work:
  - Add encrypted off-server database/media/config backups, retention, restore drills, recovery measurements, and failed/stale backup alerts.

## Scope and approval boundary

- Preserve and refine the future-work scope above, and define acceptance only if the deferred task is reactivated.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: none.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Decision registry](../../../decisions/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Security](../../../security/README.md), [Data](../../../data/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P2 / L`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
