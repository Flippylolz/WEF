---
id: M1
title: "Vertical proof"
status: planned
---

# M1: Vertical proof

## Outcome

A synthetic/redacted fixture enters through the historical adapter, known records resolve through a geocode cache, one API endpoint emits grouped GeoJSON, and the web app renders grouped pins with filters plus a source-date panel.

## Current constraints

- This proves the architecture before full-data work.
- The complete export, network geocoding, full media copy, production deployment, and Telegram credentials are excluded.
- E1-T5 is cancelled; procedural branch/PR/CI governance remains in force and does not block M1.
- No proposed or promoted task is actionable until its spike, promotion, implementation-plan, dependency, state, and branch gates pass.

## Included epic/task definitions

### [E0: Architecture and dependency spike](../epics/E0-architecture-dependency-spike/README.md)

- [E0-T1: Review architecture and dependency proposal](../epics/E0-architecture-dependency-spike/tasks/E0-T1-review-architecture-and-dependency-proposal.md) — `in_progress`, stacked on E1-T1
- [E0-T2: Execute and lock the architecture proof](../epics/E0-architecture-dependency-spike/tasks/E0-T2-execute-and-lock-the-architecture-proof.md) — `in_progress`, stacked on E0-T1
### [E1: Repository and developer foundation](../epics/E1-repository-developer-foundation/README.md)

- [E1-T1: Initialize repository safety](../epics/E1-repository-developer-foundation/tasks/E1-T1-initialize-repository-safety.md) — `in_progress`
- [E1-T2: Scaffold web and backend applications](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T2-scaffold-web-and-backend-applications.md) — `proposed`
- [E1-T3: Add local Docker Compose](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T3-add-local-docker-compose.md) — `proposed`
- [E1-T4: Establish CI baseline](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T4-establish-ci-baseline.md) — `proposed`
- [E1-T5: Configure protected-main governance](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T5-configure-protected-main-governance.md) — `cancelled`
- [E1-T6: Configure Dependabot update pull requests](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T6-configure-dependabot-update-pull-requests.md) — `proposed`
- [E1-T7: Implement scheduled Dependabot merge controller](../epics/E1-repository-developer-foundation/proposed-tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md) — `proposed`
### [E2: Historical export parser and audit](../epics/E2-historical-export-parser-audit/README.md)

- [E2-T1: Implement source adapter and fixture corpus](../epics/E2-historical-export-parser-audit/proposed-tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md) — `proposed`
- [E2-T2: Implement candidate detection and typed extractors](../epics/E2-historical-export-parser-audit/proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md) — `proposed`
### [E3: Database, geocoding, and media pipeline](../epics/E3-database-geocoding-media/README.md)

- [E3-T1: Create schema and migrations](../epics/E3-database-geocoding-media/proposed-tasks/E3-T1-create-schema-and-migrations.md) — `proposed`
- [E3-T2: Implement idempotent persistence and reprocessing](../epics/E3-database-geocoding-media/proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md) — `proposed`
- [E3-T3: Implement geocoder abstraction and cache](../epics/E3-database-geocoding-media/proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) — `proposed`
### [E4: Read API and filter contracts](../epics/E4-read-api-filter-contracts/README.md)

- [E4-T1: Implement map query service and GeoJSON endpoint](../epics/E4-read-api-filter-contracts/proposed-tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md) — `proposed`
### [E5: Interactive map frontend](../epics/E5-interactive-map-frontend/README.md)

- [E5-T1: Build map shell and grouped pin interaction](../epics/E5-interactive-map-frontend/proposed-tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md) — `proposed`
- [E5-T2: Add URL-backed filters and viewport querying](../epics/E5-interactive-map-frontend/proposed-tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md) — `proposed`

Cancelled and deferred candidates remain linked for traceability but are not completion requirements unless an approved revision restores them to required scope.

## Exit evidence

- [ ] A synthetic/redacted fixture is reconciled through the historical adapter and persisted idempotently.
- [ ] Known fixture locations resolve through the no-network cache and appear in grouped GeoJSON.
- [ ] The generated-contract frontend renders grouped pins, publication date, and the M1 filters.
- [ ] Architecture/import and OpenAPI/client checks pass without real source data, media, network geocoding, or credentials.
- [ ] Every required task has been promoted, approved, dependency-gated, implemented on its dedicated branch, and completed with definition-of-done evidence.

## Status rule

`planned` records the current outcome checkpoint only; it grants no implementation permission. Change this milestone to `done` only when all required exit evidence and task completion records exist under the [workflow](../workflow/README.md).
