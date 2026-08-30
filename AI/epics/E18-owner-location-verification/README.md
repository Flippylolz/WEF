---
schema: ai-workflow/epic@1
id: E18
title: "Owner location management and verification"
status: done
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E18: Owner location management and verification

## Outcome

The owner console gains a "Locations" page over every canonical location — not
only pending ones — where the owner filters by review status and searches
addresses, inspects the retained offer evidence behind each address, and resolves
each map point by hand: placing a point on a map picker, accepting an in-scope
geocode candidate, rejecting a location, or sending a decided location back to
review. Every decision is appended to the existing geocode-selection lineage with
operator attribution and an owner-console audit event. No schema and no public
API contract change.

## Priority and selection

- The owner selected E18 on 2026-08-30 after reviewing uncertain geocode pins
  produced by the E17 replay and asking for manual map placement based on the
  offer data, covering all locations rather than a pending-only queue.
- Promoted tasks are `P1`: required for trustworthy public map data, not an
  active outage.
- Milestone M5 (production maturity); P-008 owner-administration surface.

## Governing documents

- [ADR-012: Backend-centric modular monolith](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-016: Pseudonymous accounts and owner console](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [ADR-021: Cached provider-neutral geocoding](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md)
- [Ingestion geocoding](../../ingestion/GEOCODING.md)
- [Auth, admin, and contacts](../../security/AUTH_ADMIN_CONTACTS.md)
- [System architecture](../../architecture/SYSTEM.md)
- [Delivery workflow](../../workflow/README.md)

## Workspace state

- [Spike](SPIKE.md): revision 1, owner-approved 2026-08-30.
- [Implementation plan](IMPLEMENTATION_PLAN.md): revision 1, owner-approved
  2026-08-30.
- [E18-T1](tasks/E18-T1-location-admin-backend.md): promoted 2026-08-30; `done` through [PR #217](https://github.com/Flippylolz/WEF/pull/217) after green required CI and a verified production deploy.
- [E18-T2](tasks/E18-T2-location-admin-console.md): promoted 2026-08-30; `draft`
  until E18-T1 is `done` and its dependency gate is satisfied.
- `tasks/` is the single authoritative location (no `proposed-tasks/` remains).

## Completion state (2026-08-30)

- E18-T1 done (PR #217), E18-T2 done (PR #218) — each merged after every
  required CI check passed, each followed by a verified production deploy
  (health live/ready 200 and `/admin` serving).
- The owner console now covers every location: status-filtered listing with
  address search, manual point placement on the map picker driven by the
  retained offer evidence, candidate acceptance, rejection, and unresolve —
  all lineage-tracked and audit-logged.

## Merge and deployment policy

Per the owner's 2026-08-30 instruction, task pull requests may be merged once
every required CI check is green; after each merge the production deployment must
be verified (deploy workflow green, health endpoint, `/admin` serving) before the
next task proceeds.
