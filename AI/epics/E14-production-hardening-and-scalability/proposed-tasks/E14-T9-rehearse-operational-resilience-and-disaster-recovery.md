---
schema: ai-workflow/proposed-task@1
id: E14-T9
epic: E14
title: "Rehearse operational resilience and disaster recovery"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M5
dependencies: [E7-T5, E14-T6, E14-T7, E14-T8]
requirement_ids: [P-006, P-007, P-008]
decision_ids: [ADR-005, ADR-006, ADR-008, ADR-010, ADR-014, ADR-015]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E14-T9: Rehearse operational resilience and disaster recovery

## Outcome

Operators have measured, repeatable evidence that the service survives bounded runtime
failures and can restore PostgreSQL, media, required configuration, and worker state
from encrypted off-host backups into an isolated replacement environment within owner-approved RPO/RTO.

## Scope

- Consume—not duplicate—the approved/promoted E7-T5 backup capability and superseding ADR-015 decision.
- Define RPO/RTO, retention, encryption/key custody, off-host failure independence, restore authorization, and cost limits.
- Rehearse API/web/worker restart, database unavailability, disk pressure/full disk, read-only paths, network/provider outage, certificate/secret/session expiry, corrupt/missing release artifact, and telemetry outage.
- Restore database, public/restricted media, required configuration/secret references, and ingestion checkpoints into an isolated environment; reconcile counts/checksums/health/privacy.
- Measure data loss and recovery duration, exercise stale/failed backup alerts, and record operator decisions/runbooks.
- Preserve production and existing host workloads; never use destructive failure injection on live data.

## Out of scope

- Production destructive testing, an unapproved backup destination, unencrypted sensitive backups, high-availability claims, or treating rollback as data recovery.

## Acceptance criteria and checks

- [ ] ADR-015 is explicitly superseded or amended and E7-T5 is promoted/completed under valid approvals before this task becomes ready.
- [ ] Scheduled encrypted off-host backups cover database, media, and required recovery configuration with documented retention, key custody, freshness, and failure independence.
- [ ] A clean isolated host/environment restores from backup and passes migrations, readiness, public/restricted smoke, ingestion checkpoint reconciliation, counts/checksums, and leakage checks.
- [ ] Measured RPO and RTO meet owner-approved objectives; evidence identifies backup timestamp, release/schema, duration, loss, and verifier without sensitive payloads.
- [ ] Each bounded failure produces the expected degraded behavior, alert, runbook action, and recovery; application availability is not coupled to telemetry/provider failure.
- [ ] Restore is practiced at an approved cadence and stale/failed/invalid backups alert before retention eliminates the last good recovery point.
- [ ] Backup freshness/integrity, isolated restore, reconciliation, failure injection, alert fire/recover, security/redaction, and post-recovery full-stack checks pass.

## Dependencies and gates

Depends on existing E7-T5 plus E14-T6/T7/T8. It remains blocked while ADR-015 and E7-T5 are deferred.

## Risks and notes

Backup access is equivalent to production data access. Minimize principals, encrypt in
transit/at rest, test key recovery, and prevent restore artifacts from entering Git or logs.

## Promotion checklist

- [ ] E14 spike is explicitly owner-approved at its current revision.
- [ ] ADR-015/E7-T5 and every listed dependency gate are resolved.
- [ ] Scope, checks, dependencies, priority/size, and traceability match the approved spike.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.
