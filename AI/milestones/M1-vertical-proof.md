---
id: M1
title: "Vertical proof"
status: in_progress
---

# M1: Vertical proof

## Outcome

A deterministic synthetic fixture is migrated/seeded into canonical PostGIS locations/offers, backend endpoints emit filtered grouped GeoJSON/facets/dated location results, and the web app renders selectable grouped pins with URL-backed filters.

## Current constraints

- This turns the accepted architecture proof into the first browser-visible map MVP before full-data work.
- Historical parsing/import, the complete export, network geocoding, media, auth/contacts, and Telegram credentials are excluded from M1 completion and remain later gated work.
- E1-T5 is cancelled; procedural branch/PR/CI governance remains in force and does not block M1.
- No proposed or promoted task is actionable until its spike, promotion, implementation-plan, dependency, state, and branch gates pass.

## Included epic/task definitions

### [E0: Architecture and dependency spike](../epics/E0-architecture-dependency-spike/README.md)

- [E0-T1: Review architecture and dependency proposal](../epics/E0-architecture-dependency-spike/tasks/E0-T1-review-architecture-and-dependency-proposal.md) — `in_progress`, stacked on E1-T1
- [E0-T2: Execute and lock the architecture proof](../epics/E0-architecture-dependency-spike/tasks/E0-T2-execute-and-lock-the-architecture-proof.md) — `in_progress`, stacked on E0-T1
### [E1: Repository and developer foundation](../epics/E1-repository-developer-foundation/README.md)

- [E1-T1: Initialize repository safety](../epics/E1-repository-developer-foundation/tasks/E1-T1-initialize-repository-safety.md) — `in_progress`
- [E1-T2: Scaffold web and backend applications](../epics/E1-repository-developer-foundation/tasks/E1-T2-scaffold-web-and-backend-applications.md) — `in_progress`, stacked on E0-T2
- [E1-T4: Establish CI baseline](../epics/E1-repository-developer-foundation/tasks/E1-T4-establish-ci-baseline.md) — `in_progress`, stacked on E1-T2
- [E1-T3: Add local Docker Compose](../epics/E1-repository-developer-foundation/tasks/E1-T3-add-local-docker-compose.md) — `in_progress`, stacked through E1-T4 on E1-T2
- [E1-T5: Configure protected-main governance](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T5-configure-protected-main-governance.md) — `cancelled`
- [E1-T6: Configure Dependabot update pull requests](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T6-configure-dependabot-update-pull-requests.md) — `proposed`
- [E1-T7: Implement scheduled Dependabot merge controller](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md) — `proposed`
### [E3: Database, geocoding, and media pipeline](../epics/E3-database-geocoding-media/README.md)

- [E3-T1: Create M1 schema, migrations, and deterministic seed](../epics/E3-database-geocoding-media/tasks/E3-T1-create-schema-and-migrations.md) — `in_progress`, stacked on E1-T3
### [E4: Read API and filter contracts](../epics/E4-read-api-filter-contracts/README.md)

- [E4-T1: Implement map query service and GeoJSON endpoint](../epics/E4-read-api-filter-contracts/tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md) — `in_progress`, stacked on E3-T1
- [E4-T2: Implement facets and location offer collection](../epics/E4-read-api-filter-contracts/tasks/E4-T2-implement-facets-and-location-offer-collection.md) — `in_progress`, stacked on E4-T1
### [E5: Interactive map frontend](../epics/E5-interactive-map-frontend/README.md)

- [E5-T1: Build map shell and grouped pin interaction](../epics/E5-interactive-map-frontend/tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md) — `done`
- [E5-T2: Add URL-backed filters and viewport querying](../epics/E5-interactive-map-frontend/tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md) — promoted, `ready`, dependencies satisfied

Cancelled and deferred candidates remain linked for traceability but are not completion requirements unless an approved revision restores them to required scope.

## Exit evidence

- [ ] A deterministic synthetic fixture is migrated/seeded idempotently into canonical locations/offers.
- [ ] Accepted synthetic coordinates and visible dated offers appear in grouped GeoJSON/facets/location results with backend-owned filter semantics.
- [ ] The generated-contract frontend renders/selects grouped pins, dated results, and all URL-backed M1 filters with accessible degraded/list states.
- [ ] Architecture, migration, PostGIS, OpenAPI/client, browser, and production-build checks pass without real source data, media, network geocoding, or credentials.
- [ ] Every required task has been promoted, approved, dependency-gated, implemented on its dedicated branch, and completed with definition-of-done evidence.

## Status rule

`planned` records the current outcome checkpoint only; it grants no implementation permission. Change this milestone to `done` only when all required exit evidence and task completion records exist under the [workflow](../workflow/README.md).
