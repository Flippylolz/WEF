---
schema: ai-workflow/spike@1
epic: E7
title: "Docker/GitHub production delivery research"
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-005, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-011, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017]
domain_docs: [operations, governance, security, data]
proposed_task_ids: [E7-T1, E7-T2, E7-T3, E7-T4, E7-T5, E7-T6, E7-T7]
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Docker/GitHub production delivery

> This is a draft research scope. It authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

How should immutable GitHub-built releases be configured, transferred, deployed, verified, rolled back, and used for the historical import on the supplied shared NUC without disrupting existing services?

## Context and constraints

- GitHub Actions variables/secrets are the complete deploy-configuration source of truth; validated configuration is transferred atomically and never committed.
- The isolated wef-production Compose project uses /home/nuc/wef persistence and initially publishes only configurable port 3100.
- Existing AI Forecast, DuckDNS, and WireGuard workloads and ports 3000/TCP, 8080/TCP, and 51820/UDP must remain unchanged.
- Backups/restore drills are deferred under ADR-015; rollback covers compatible application releases, not guaranteed data restoration.

Governing domains:

- [Operations](../../operations/README.md)
- [Governance](../../governance/README.md)
- [Security](../../security/README.md)
- [Data](../../data/README.md)

Governing decisions and deferred gates:

- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-009](../../decisions/adr/ADR-009-feature-branch-development.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-014](../../decisions/adr/ADR-014-actions-owned-deploy-configuration.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [ADR-017](../../decisions/adr/ADR-017-no-enforced-branch-protection.md)
- [D-001](../../decisions/deferred/D-001-production-server-domain.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)

## Research method

Review the inspected server baseline, Compose/Caddy topology, GHCR/SSH trust, GitHub event and token boundaries, secret/config transfer, migration/rollback order, archive capacity/checksum/rsync flow, and HTTPS activation.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- D-001 records the supplied NUC, no-passwordless-sudo constraint, available capacity, existing bindings, and remaining HTTPS/resource-ceiling input.
- ADR-010 requires WEF isolation; ADR-014 assigns deploy configuration to Actions; ADR-017 keeps main/PR rules procedural.
- The roadmap requires merged-PR-origin verification, AUTO_DEPLOY_ENABLED, immutable SHA/digest images, locked deployment, health smoke tests, and resumable archive transfer.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Use one isolated Compose project with immutable images, Actions-owned complete configuration, verified SSH, health-gated activation, retained previous release, and explicit rollback.
- Build on the server or mutate a shared Compose project, which weakens reproducibility and non-interference.
- Claim backups from persistent volumes, which contradicts ADR-015.

## Draft recommendation

Refine production topology, server provisioning, image/deploy workflows, health rollback, deferred backup, historical transfer/import, and HTTPS auth activation as distinct gated tasks.

This recommendation remains draft and may change after bounded research. It is not approved and does not authorize any proposed task.

## Proposed task boundaries

- [E7-T1: Build production Compose topology](proposed-tasks/E7-T1-build-production-compose-topology.md) — candidate boundary for spike refinement.
- [E7-T2: Provision and verify supplied server](proposed-tasks/E7-T2-provision-and-verify-supplied-server.md) — candidate boundary for spike refinement.
- [E7-T3: Implement GitHub image and deployment workflows](proposed-tasks/E7-T3-implement-github-image-and-deployment-workflows.md) — candidate boundary for spike refinement.
- [E7-T4: Implement health verification and rollback](proposed-tasks/E7-T4-implement-health-verification-and-rollback.md) — candidate boundary for spike refinement.
- [E7-T5: Future backup and restore capability](proposed-tasks/E7-T5-future-backup-and-restore-capability.md) — deferred until its named trigger.
- [E7-T6: Transfer and import the historical dataset](proposed-tasks/E7-T6-transfer-and-import-the-historical-dataset.md) — candidate boundary for spike refinement.
- [E7-T7: Enable production registration and contact reveal](proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- A port/name/path collision can disrupt existing workloads.
- A partial/stale configuration transfer can activate an invalid release or leak secrets.
- Historical transfer/import can exhaust storage or create unrecoverable changes without reconciliation and forward-safe migrations.
- Confirm task-level traceability, cross-epic dependencies, test evidence, rollout, and rollback during spike refinement.
- Resolve every named deferred-decision gate before promoting affected work.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [ ] The bounded question is answered with evidence and uncertainty distinguished.
- [ ] Governing domain documents and decisions are reviewed and linked.
- [ ] Options, recommendation, risks, and open questions are complete.
- [ ] Proposed task scope, acceptance, dependencies, priority/size, and traceability are refined.
- [ ] No production or disposable proof code was created.
- [ ] `revision` represents the material content being submitted.
- [ ] Status is changed to `awaiting_approval` while approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of the current spike revision would permit task refinement/promotion and implementation planning only; it would not permit code.
