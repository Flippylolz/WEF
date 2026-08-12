---
schema: ai-workflow/proposed-task@1
id: E7-T6
epic: E7
title: "Transfer and import the historical dataset"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E3-T5, E7-T2, E7-T4]
requirement_ids: [P-001, P-002, P-005, P-007]
decision_ids: [ADR-005, ADR-006, ADR-007, ADR-010, ADR-015]
deferred_decision_ids: [D-002]
source: "legacy-roadmap:E7-T6"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T6: Transfer and import the historical dataset

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Transfer and import the historical dataset** to the epic outcome: every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Original roadmap definition

The following definition preserves the original E7-T6 roadmap entry:

- Priority/size: P1 / L
- Dependencies: E3-T5, E7-T2, E7-T4
- Work:
  - Follow [production server baseline](../../../operations/SERVER.md): calculate local archive SHA-256, resumably rsync only `est-test.tar.gz`, verify the server checksum, and extract beneath `/home/nuc/wef/imports/`.
  - Mount the source read-only and run production dry-run, canonical import, geocoding, media copy/derivatives, and reconciliation.
- Acceptance:
  - Local/server archive checksums match and transfer can resume after interruption.
  - No source data appears in Git, GHCR, Actions artifacts, or container image layers.
  - Production counts reconcile to the audited import report; missing/failed items remain reportable.
  - Existing Compose projects and user-visible services are healthy before, during, and after the bounded import.
  - Archive cleanup happens only after import integrity and media checks are verified.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E3-T5](../../E3-database-geocoding-media/proposed-tasks/E3-T5-import-and-review-the-complete-dataset.md), [E7-T2](E7-T2-provision-and-verify-supplied-server.md), [E7-T4](E7-T4-implement-health-verification-and-rollback.md)
- Deferred-decision gates: [D-002](../../../decisions/deferred/D-002-recurring-geocoding-provider.md).
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Security](../../../security/README.md), [Data](../../../data/README.md).

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
