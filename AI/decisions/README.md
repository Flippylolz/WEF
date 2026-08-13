# Decisions

This registry is the highest-precedence documentation domain. Each linked architecture decision record (ADR) and deferred decision is authoritative for its own ID. IDs remain stable, and a later decision changes an accepted record only through an explicit linked supersession or resolution.

## Accepted/current

- [ADR-001 — Split Python API and TypeScript web application](adr/ADR-001-split-python-api-typescript-web.md)
- [ADR-002 — Use a grouped location/development map](adr/ADR-002-grouped-location-development-map.md)
- [ADR-003 — Do not infer current availability](adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-004 — Use MapLibre and OpenFreeMap initially](adr/ADR-004-maplibre-openfreemap.md)
- [ADR-005 — Use PostgreSQL with PostGIS](adr/ADR-005-postgresql-postgis.md)
- [ADR-006 — Keep one ingestion core with source adapters](adr/ADR-006-shared-ingestion-core.md)
- [ADR-007 — Use local mounted media first, behind a storage interface](adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-012 — Use a backend-centric modular monolith](adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013 — Commit OpenAPI and keep production docs offline](adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-014 — GitHub Actions owns deploy-time configuration](adr/ADR-014-actions-owned-deploy-configuration.md)
- [ADR-015 — Defer backups and accept single-host data-loss risk](adr/ADR-015-defer-backups.md)
- [ADR-016 — Username/password accounts and owner-only admin console](adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [ADR-017 — Operate without enforced GitHub branch protection](adr/ADR-017-no-enforced-branch-protection.md)
- [ADR-018 — Allow ordered stacked pull request implementation](adr/ADR-018-ordered-stacked-pull-requests.md)
- [ADR-019 — Separate the anonymous HTTP rehearsal from public launch](adr/ADR-019-anonymous-http-production-rehearsal.md)
- [ADR-020 — Use Nginx as the shared TLS ingress](adr/ADR-020-use-nginx-shared-tls-ingress.md)

## Partially superseded

- [ADR-008 — Deploy immutable images to one server](adr/ADR-008-single-server-immutable-deployments.md) — deployment model remains current; [ADR-015](adr/ADR-015-defer-backups.md) supersedes its backup requirement.
- [ADR-009 — Use protected-main feature-branch development](adr/ADR-009-feature-branch-development.md) — branch/PR workflow remains current; [ADR-017](adr/ADR-017-no-enforced-branch-protection.md) supersedes the platform-enforcement assumption.
- [ADR-010 — Isolate WEF on the shared NUC](adr/ADR-010-isolate-wef-shared-nuc.md) — application/data isolation remains current; [ADR-020](adr/ADR-020-use-nginx-shared-tls-ingress.md) permits only the reviewed shared Nginx ingress migration.
- [ADR-011 — In-house accounts gate contact reveal](adr/ADR-011-accounts-gate-contact-reveal.md) — anonymous browsing and the audited reveal boundary remain current; [ADR-016](adr/ADR-016-pseudonymous-accounts-owner-console.md) supersedes its email-based identity details.

## Resolved/out-of-scope

- [D-004 — Authentication and curation](deferred/D-004-authentication-curation.md) — resolved by [ADR-016](adr/ADR-016-pseudonymous-accounts-owner-console.md).
- [D-006 — UI languages](deferred/D-006-ui-languages.md) — resolved for the initial release by the canonical [Product Quality language section](../product/QUALITY.md#language) (`product/QUALITY`, a document key rather than an ADR/deferred-decision ID).
- [D-007 — GitHub protection eligibility](deferred/D-007-github-protection-eligibility.md) — resolved as out of scope by [ADR-017](adr/ADR-017-no-enforced-branch-protection.md); E1-T5 is cancelled.
- [D-008 — Transactional email provider](deferred/D-008-transactional-email-provider.md) — resolved as out of scope by [ADR-016](adr/ADR-016-pseudonymous-accounts-owner-console.md).

## Deferred/revalidation

- [D-001 — Production server and domain](deferred/D-001-production-server-domain.md) — resolved for the anonymous rehearsal by ADR-019.
- [D-002 — Recurring geocoding provider](deferred/D-002-recurring-geocoding-provider.md) — initial path resolved; evaluate at E3-T3/E7-T6 and revalidate before E8-T4.
- [D-003 — Telegram channel identity and access](deferred/D-003-telegram-channel-access.md) — public link format resolved; live access remains deferred until E8-T1.
- [D-005 — Object storage and CDN](deferred/D-005-object-storage-cdn.md) — revisit when its operational cost triggers occur.
- [D-009 — Shared TLS hostnames and forwarding](deferred/D-009-shared-tls-hostnames-and-forwarding.md) — resolve two public hostnames and 80/443 forwarding before E7-T8.

## Supersession and resolution graph

```text
ADR-008 -- backup requirement superseded by --> ADR-015
ADR-011 -- email identity details superseded by --> ADR-016
D-004   ---------------------- resolved by ----> ADR-016
D-008   ---------------- resolved/out-of-scope -> ADR-016
ADR-009 -- enforcement assumption superseded --> ADR-017
D-007   ---------------- resolved/out-of-scope -> ADR-017
ADR-010 -- public edge assumption superseded --> ADR-020
```

Direct graph links:

- [ADR-008](adr/ADR-008-single-server-immutable-deployments.md) → [ADR-015](adr/ADR-015-defer-backups.md)
- [ADR-011](adr/ADR-011-accounts-gate-contact-reveal.md) → [ADR-016](adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [D-004](deferred/D-004-authentication-curation.md) → [ADR-016](adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [D-008](deferred/D-008-transactional-email-provider.md) → [ADR-016](adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [ADR-009](adr/ADR-009-feature-branch-development.md) → [ADR-017](adr/ADR-017-no-enforced-branch-protection.md)
- [D-007](deferred/D-007-github-protection-eligibility.md) → [ADR-017](adr/ADR-017-no-enforced-branch-protection.md)
- [ADR-010](adr/ADR-010-isolate-wef-shared-nuc.md) → [ADR-020](adr/ADR-020-use-nginx-shared-tls-ingress.md)

## Status rules

- ADR states are `proposed`, `accepted`, `superseded`, or `rejected`; partial supersession keeps an ADR accepted and links the exact superseded scope.
- Deferred-decision states are `deferred`, `resolved`, or `cancelled`.
- Accepted records are append-only except for metadata, links, or an explicit supersession/resolution note.
- A superseding record links directly to every record it replaces and explains migration impact.
- A resolved deferred decision links to the ADR or other authoritative document that resolved it.

Changes to confirmed product behavior, public API contracts, persisted data, security, or deployment topology require a decision record before implementation approval.
