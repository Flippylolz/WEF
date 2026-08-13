---
schema: ai-workflow/spike@1
epic: E3
title: "Database, geocoding, and media pipeline research"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-011, ADR-012, ADR-016]
domain_docs: [data, contracts, ingestion, security]
proposed_task_ids: [E3-T1, E3-T2, E3-T3, E3-T4, E3-T5]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T22:34:40Z"
  approved_revision: 2
  evidence: "Owner directive to prepare the MVP/autodeploy, choose safe defaults, log decisions/blockers, and continue stacking PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Database, geocoding, and media pipeline

> Revision 2 is approved research. The spike itself remains non-executable; implementation is authorized only through a separately approved plan and promoted task.

## Question

What persisted model and bounded geocoding/media workflows make historical reprocessing idempotent, map coordinates reviewable, and public media paths safe on the single-host deployment?

## Context and constraints

- PostgreSQL/PostGIS is canonical; source identity, revisions, provenance, checkpoints, and ingest runs must survive reprocessing.
- No real-world availability boolean may be introduced.
- External geocoding uses a provider-neutral port, persistent cache, Warsaw bounds, confidence/precision, and review states; D-002 gates provider use.
- Media is copied atomically to opaque keys, served read-only, and stripped of unnecessary metadata; source paths never become public URLs.

Governing domains:

- [Data](../../data/README.md)
- [Contracts](../../contracts/README.md)
- [Ingestion](../../ingestion/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)

## Research method

Review persisted contracts, ingestion/geocoding rules, source/media constraints, PostGIS indexing needs, provider policy, and single-host storage boundaries. Compare transaction and reprocessing boundaries in documentation only.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Evidence

- ADR-005 selects PostgreSQL/PostGIS, ADR-007 selects mounted media behind a storage interface, and ADR-006 requires one ingestion core.
- The roadmap requires advisory locking, bounded transactions, resumable checkpoints, checksum deduplication, and migration tests.
- D-002 identifies Geoapify as the initial candidate, LocationIQ as an alternative, and public Nominatim as one-time cached seed use only.
- The accepted E0 proof verifies async SQLAlchemy/PostGIS mapping, inward-owned query ports, and non-root backend images.
- E1-T3 verifies persistent PostGIS/media volumes and isolated Compose health without production credentials.
- The first browser-visible MVP needs canonical `Location`/`Offer` rows and accepted synthetic coordinates, but not real-source parsing, provider calls, contact data, or media.

No private export payload was inspected for this revision. The documented source baseline is sufficient to keep future ingestion constraints explicit.

## Options to evaluate

- Use canonical source/revision entities, idempotent upserts, narrow repository/UoW ports, cached provider-neutral geocoding, and local opaque media storage.
- Persist parser output directly into public projections, which would couple uncertainty and reprocessing to API shape.
- Expose source media paths or provider-specific fields, which would violate storage and contract boundaries.

## Approved recommendation

Promote only E3-T1 for the first map MVP. Implement the M1 subset of the canonical schema (`Location` and `Offer` plus required enums/indexes), Alembic clean-install migrations, and an explicit deterministic synthetic seed command. Synthetic coordinates are fixture facts marked accepted; they are not inferred or provider results.

Keep E3-T2 through E3-T5 proposed. Real-source idempotent persistence, geocoding/provider/cache behavior, media, and full import remain required before historical data replaces the seed. The seed command is idempotent, verification-only, and cannot run implicitly in production.

## Proposed task boundaries

- [E3-T1: Create schema and migrations](tasks/E3-T1-create-schema-and-migrations.md) — promote for the deterministic M1 schema/seed boundary.
- [E3-T2: Implement idempotent persistence and reprocessing](proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md) — keep proposed for historical ingestion.
- [E3-T3: Implement geocoder abstraction and cache](proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) — keep proposed; no provider is needed for synthetic fixtures.
- [E3-T4: Implement media storage and derivatives](proposed-tasks/E3-T4-implement-media-storage-and-derivatives.md) — keep proposed.
- [E3-T5: Import and review the complete dataset](proposed-tasks/E3-T5-import-and-review-the-complete-dataset.md) — keep proposed.

Only promoted E3-T1 may appear in implementation-plan revision 2.

## Risks and open questions

- A uniqueness or transaction mistake can duplicate canonical offers or advance checkpoints before commit.
- Low-precision/out-of-bounds coordinates can become misleading public pins.
- Single-host media/database persistence is not backup; E7-T5 remains deferred.
- Migration/schema drift can leave a competing disposable proof model; E3-T1 replaces proof persistence rather than maintaining two models.
- Synthetic fixtures can be mistaken for inventory; label them clearly and require an explicit seed command.
- D-002 does not gate accepted synthetic coordinates. It continues to gate real provider implementation/use in E3-T3/E8-T4.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] E3-T1 scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created during the spike.
- [x] Revision 2 represents the approved material content.
- [x] Status and approval metadata record the delegated owner decision.

## Owner decision

Flippylolz approved revision 2 through the explicit overnight MVP/autodeploy delegation. This permits E3-T1 promotion and implementation planning only; code still requires approved plan revision 2 and an in-progress task branch.
