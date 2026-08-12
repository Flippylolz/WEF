---
schema: ai-workflow/spike@1
epic: E6
title: "Quality, security, and operations research"
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-007, ADR-008, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014, ADR-015, ADR-016]
domain_docs: [product, security, operations, governance, contracts]
proposed_task_ids: [E6-T1, E6-T2, E6-T3, E6-T4, E6-T5, E6-T6, E6-T7]
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

# Spike: Quality, security, and operations

> This is a draft research scope. It authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

What cross-cutting test, privacy, security, identity, contact-reveal, administration, localization, and operational controls are required for a safe public launch?

## Context and constraints

- Anonymous browsing remains available; pseudonymous username/password accounts gate only restricted actions.
- Contacts are extracted and encrypted at rest, masked server-side, explicitly revealed through a no-store audited endpoint, and never logged in reveal audits.
- The fixed owner role alone administers users/sessions/resets/audits through owner-authorized interactors; generic admin forms cannot expose sensitive fields.
- Authentication/admin/reveal remain disabled on plain HTTP and require production HTTPS/secrets.

Governing domains:

- [Product](../../product/README.md)
- [Security](../../security/README.md)
- [Operations](../../operations/README.md)
- [Governance](../../governance/README.md)
- [Contracts](../../contracts/README.md)

Governing decisions and deferred gates:

- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-014](../../decisions/adr/ADR-014-actions-owned-deploy-configuration.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)

## Research method

Review product quality, AUTH, public/persisted contracts, architecture boundaries, production threat surfaces, test pyramid, observability requirements, i18n, and owner-console controls.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- ADR-016 defines username/password accounts and the owner console; ADR-011 retains anonymous browsing and audited reveal boundaries.
- The roadmap requires Argon2, opaque database sessions, CSRF/origin controls, rate limits, forced-password-change state, minimized audits, and accessibility/security tests.
- Production docs routes and runtime documentation assets must be absent under ADR-013.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Use focused project-owned identity code unless approved E0 evidence shows FastAPI Users adaptation is smaller/safer; keep authorization in interactors.
- Use email-first hosted identity, which conflicts with accepted pseudonymous no-email scope.
- Expose contacts in general detail responses, which defeats explicit authorization, no-store delivery, and audit minimization.

## Draft recommendation

Refine quality, security, diagnostics, identity, contact reveal, restricted-action UX, and owner administration tasks with explicit negative, integration, accessibility, and production-configuration tests.

This recommendation remains draft and may change after bounded research. It is not approved and does not authorize any proposed task.

## Proposed task boundaries

- [E6-T1: Complete automated test pyramid](proposed-tasks/E6-T1-complete-automated-test-pyramid.md) — candidate boundary for spike refinement.
- [E6-T2: Perform privacy and security hardening](proposed-tasks/E6-T2-perform-privacy-and-security-hardening.md) — candidate boundary for spike refinement.
- [E6-T3: Add operational diagnostics](proposed-tasks/E6-T3-add-operational-diagnostics.md) — candidate boundary for spike refinement.
- [E6-T4: Implement in-house registration and sessions](proposed-tasks/E6-T4-implement-in-house-registration-and-sessions.md) — candidate boundary for spike refinement.
- [E6-T5: Implement contact masking, encryption, reveal, and audit](proposed-tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md) — candidate boundary for spike refinement.
- [E6-T6: Implement English i18n and restricted-action UX](proposed-tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md) — candidate boundary for spike refinement.
- [E6-T7: Implement owner administration console](proposed-tasks/E6-T7-implement-owner-administration-console.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- Cookie authentication without HTTPS/CSRF/origin controls enables session abuse.
- Admin integration can bypass application interactors or expose hashes/tokens/contacts.
- Observability and fixtures can leak private source data unless redaction is verified.
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
