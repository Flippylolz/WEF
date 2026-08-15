---
schema: ai-workflow/proposed-task@1
id: E7-T6
epic: E7
title: "Transfer the verified historical snapshot to production"
status: proposed
revision: 2
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E3-T5, E7-T2, E7-T4]
requirement_ids: [P-001, P-002, P-005, P-007]
decision_ids: [ADR-005, ADR-006, ADR-007, ADR-010, ADR-015]
deferred_decision_ids: []
source: "legacy-roadmap:E7-T6"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T6: Transfer the verified historical snapshot to production

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Move the verified E3-T5 terminal database state and application-owned media to production without re-running parsing, hosted geocoding, manual review, media copying, or derivative generation on the shared server.

## Historical roadmap definition

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

Revision 2 supersedes that execution approach: production consumes the already materialized, verified E3-T5 result rather than mounting the raw export and repeating the pipeline.

## Revision 2 scope

- Build an ignored, mode-0600 transfer bundle from the completed E3-T5 run containing a data-only PostgreSQL snapshot of the approved ingestion/catalog tables, application-owned restricted originals and public derivatives, and a non-sensitive manifest with migration head, release/pipeline versions, source checksum identity, terminal counts, object counts/bytes, and per-component SHA-256 values.
- Exclude raw export files, source-relative media, credentials, local paths, detailed reports, identity/session tables, and unrelated database schemas. The database component remains restricted because source rows may contain private text.
- Transfer only the versioned bundle over authenticated SSH with resumable `rsync`, verify the outer and component checksums before reading it, and keep it outside Git, GHCR, Actions artifacts, build contexts, and image layers.
- Pause WEF writers, clone the current production database into a new candidate database so current identity/session and unrelated state are preserved, migrate the candidate to the bundle's required schema head, and load the historical rows idempotently into that candidate. Any conflicting same-key/different-content row aborts; no existing production row is overwritten silently.
- Stage restricted/public media beneath new versioned application-owned roots, verify every manifest checksum/reference and derivative-only public boundary, then start a candidate release against the candidate database/media roots.
- Run complete reconciliation, API/media health, release-marker, and non-interference checks before atomically switching the WEF release pointers. The old database/media roots remain intact as the bounded rollback target until owner-approved cleanup.
- Never invoke a hosted geocoder, parse the raw export, recopy source media, or regenerate derivatives in production. D-002 is not a gate because this task transfers accepted materialized results and makes no provider call.

## Acceptance criteria

- [ ] Local bundle, server bundle, database component, and media manifest checksums match; interrupted transfer resumes without restarting completed bytes.
- [ ] The bundle identity exactly matches E3-T5's approved source checksum, pipeline/schema versions, terminal counts, selected-review lineage, media dispositions, and object manifest.
- [ ] Restore occurs only into a candidate clone of current production; identity/session and unrelated state match the maintenance-start snapshot, and conflicting historical rows fail closed.
- [ ] Candidate reconciliation equals E3-T5's aggregate/redacted audit, every visible pin/media reference resolves, restricted originals remain non-public, and no source/local path is exposed.
- [ ] Instrumentation proves zero hosted geocoder calls, zero raw parsing, zero source-media copies, and zero derivative transformations during production transfer/activation.
- [ ] Existing Compose projects and unrelated services remain healthy before, during, and after the bounded operation.
- [ ] Failed checksum, migration, load, media, integrity, or health gates leave the current production release/database/media pointers active; rollback restores them without deleting candidate or prior state.
- [ ] Transfer bundles and retained candidate/previous state stay mode-restricted and are removed only through a separate owner-authorized cleanup after acceptance; same-host retention is not described as backup/recovery.

## Scope and approval boundary

- Refine the revision 2 snapshot/clone/cutover design against a later owner-approved E7 spike/implementation-plan revision before promotion.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E3-T5](../../E3-database-geocoding-media/tasks/E3-T5-import-and-review-the-complete-dataset.md), [E7-T2](../tasks/E7-T2-provision-and-verify-supplied-server.md), [E7-T4](../tasks/E7-T4-implement-health-verification-and-rollback.md)
- Deferred-decision gates: none. [D-002](../../../decisions/deferred/D-002-recurring-geocoding-provider.md) remains relevant to recurring geocoding but this task performs no provider call.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Security](../../../security/README.md), [Data](../../../data/README.md).

## Risks and notes

- Revision 2 is a material planning change from production reprocessing to verified snapshot transfer; it remains proposed until a later E7 spike/plan explicitly approves it.
- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P1 / L`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
