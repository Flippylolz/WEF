---
schema: ai-workflow/spike@1
epic: E5
title: "Interactive map frontend research"
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-002, ADR-003, ADR-004, ADR-007, ADR-012]
domain_docs: [product, contracts, architecture, security]
proposed_task_ids: [E5-T1, E5-T2, E5-T3, E5-T4, E5-T5]
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

# Spike: Interactive map frontend

> This is a draft research scope. It authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

How should the Next.js client render the backend contract as a responsive, accessible MapLibre map/list/detail experience without reimplementing filters, permissions, masking, or other domain behavior?

## Context and constraints

- MapLibre/OpenFreeMap is the accepted renderer/basemap and required attribution remains visible.
- Generated OpenAPI types and the typed client are the normal API source; URL parameters own public filter state.
- The client manages layout, interaction, focus, localization, request lifecycle, and transient state only.
- The interface must preserve filters through loading/errors and provide keyboard, mobile, WebGL-degraded, missing-media, and low-confidence states.

Governing domains:

- [Product](../../product/README.md)
- [Contracts](../../contracts/README.md)
- [Architecture](../../architecture/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-002](../../decisions/adr/ADR-002-grouped-location-development-map.md)
- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-004](../../decisions/adr/ADR-004-maplibre-openfreemap.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)

## Research method

Map product interaction/quality criteria to component boundaries, generated API consumption, URL state, request cancellation, MapLibre lifecycle, responsive layout, accessibility/focus behavior, and media loading.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- P-001 through P-007 define grouped pins, details, filters, coordination, media, Telegram links, attribution, and confidence behavior.
- ADR-004 selects MapLibre/OpenFreeMap; ADR-012 forbids a second frontend domain/service layer.
- The roadmap requires 360 px behavior, WCAG 2.2 AA public flows, WebGL fallback, debounced viewport queries, and no full detail/media in initial map payloads.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Use feature-oriented map/offers components over generated query options, URL-backed filters, and local transient selection state.
- Introduce Redux/Zustand and client-side domain models initially, which adds duplicated state/rules without demonstrated need.
- Use a server-rendered static map, which cannot meet the accepted grouped-pin interaction.

## Draft recommendation

Refine shell/pins, URL filters, detail/gallery, responsive accessibility, and production UX/performance as separate tasks while keeping all business decisions in API responses.

This recommendation remains draft and may change after bounded research. It is not approved and does not authorize any proposed task.

## Proposed task boundaries

- [E5-T1: Build map shell and grouped pin interaction](proposed-tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md) — candidate boundary for spike refinement.
- [E5-T2: Add URL-backed filters and viewport querying](proposed-tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md) — candidate boundary for spike refinement.
- [E5-T3: Build offer detail and media gallery](proposed-tasks/E5-T3-build-offer-detail-and-media-gallery.md) — candidate boundary for spike refinement.
- [E5-T4: Complete responsive list/map accessibility](proposed-tasks/E5-T4-complete-responsive-list-map-accessibility.md) — candidate boundary for spike refinement.
- [E5-T5: Performance and production UX pass](proposed-tasks/E5-T5-performance-and-production-ux-pass.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- Map remounts and oversized payloads can harm the first useful render.
- Pointer-only interactions or unmanaged focus can fail accessibility.
- Frontend fallback logic can accidentally infer confidence, availability, or permissions.
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
