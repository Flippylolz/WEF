---
schema: ai-workflow/spike@1
epic: E8
title: "Future Telegram live ingestion research"
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-010, ADR-015]
domain_docs: [ingestion, data, operations, security]
proposed_task_ids: [E8-T1, E8-T2, E8-T3, E8-T4, E8-T5]
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

# Spike: Future Telegram live ingestion

> This is a draft research scope. It authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

How should a single hardened Telethon worker reconcile the historical checkpoint and process new, edited, and deleted posts through the shared ingestion core without changing public contracts or leaking session credentials?

## Context and constraints

- Live ingestion starts only after M3 and D-003 channel/access confirmation.
- D-002 must be revalidated for recurring geocoding; public Nominatim cannot be the recurring production dependency.
- One worker replica owns the session/checkpoint lock and persists source state before advancing checkpoints.
- Telegram disconnects, flood waits, edits, deletes, and session rotation must not make the public API unavailable.

Governing domains:

- [Ingestion](../../ingestion/README.md)
- [Data](../../data/README.md)
- [Operations](../../operations/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)
- [D-003](../../decisions/deferred/D-003-telegram-channel-access.md)

## Research method

Review verified source-link identity, Telethon session/event/backfill behavior, source checkpoint overlap, grouped media IDs, idempotent persistence, delete visibility, geocoder quotas, worker locking, monitoring, and rotation runbooks.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- ADR-006 requires historical and live adapters to feed the same canonical ingestion core.
- D-003 verifies the public channel/link pattern but defers API credentials, authorized account/session, and edit/delete requirements.
- The roadmap requires restartable backfill, flood-wait handling, persisted-before-checkpoint ordering, revision lineage, overlap reconciliation, and stale/connectivity alerts.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Use one Telethon adapter/worker over existing ProcessSourceMessage and checkpoint contracts with bounded media and explicit locks.
- Create a second live-only parser/persistence path, which would duplicate canonicalization and public behavior.
- Run multiple unsynchronized workers, which risks checkpoint races and duplicate media/event processing.

## Draft recommendation

Confirm access first, revalidate recurring geocoding, then refine secure session/backfill, live event processing, and production reconciliation/alerting tasks over the existing ingestion ports.

This recommendation remains draft and may change after bounded research. It is not approved and does not authorize any proposed task.

## Proposed task boundaries

- [E8-T1: Confirm channel identity and access](proposed-tasks/E8-T1-confirm-channel-identity-and-access.md) — candidate boundary for spike refinement.
- [E8-T2: Implement secure Telethon session and backfill](proposed-tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — candidate boundary for spike refinement.
- [E8-T3: Implement live new/edit/delete processing](proposed-tasks/E8-T3-implement-live-new-edit-delete-processing.md) — candidate boundary for spike refinement.
- [E8-T4: Revalidate geocoder for recurring ingestion](proposed-tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — candidate boundary for spike refinement.
- [E8-T5: Production reconciliation and worker alerting](proposed-tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- Channel identity or account permissions may not support required edit/delete events.
- Session leakage or concurrent replicas can compromise the account or corrupt checkpoints.
- Provider quota/terms can make recurring geocoding unreliable unless cache/defer/alert behavior is explicit.
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
