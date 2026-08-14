---
schema: ai-workflow/spike@1
epic: E3
title: "Historical persistence, geocoding, media, and import research"
status: awaiting_approval
revision: 3
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-011, ADR-012, ADR-016, ADR-021]
domain_docs: [data, contracts, ingestion, security]
proposed_task_ids: [E3-T1, E3-T2, E3-T3, E3-T4, E3-T5]
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

# Spike: Historical persistence, geocoding, media, and import

> Revision 3 is research awaiting durable owner approval. It does not refine/promote E3-T2–T5, authorize implementation, approve [ADR-021](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md), or replace the approved revision 2 implementation plan, which authorized only completed E3-T1.

## Question

What architecture constraints should govern a later plan for converting the audited E2 stream into replay-safe canonical data, reviewed Warsaw coordinates, and safe media without exposing restricted source data or coupling the core to providers/storage?

## Current state and boundaries

- PostgreSQL/PostGIS remains canonical under ADR-005; E3-T1 already delivered the synthetic M1 `locations`/`offers` foundation.
- E2-T2/E2-T3 provide source-neutral extraction and media-association contracts. E2-T5 is `done` through merged [PR #42](https://github.com/Flippylolz/WEF/pull/42), so B-007 is satisfied.
- E3-T2 through E3-T5 remain unchanged revision 1 candidates under `proposed-tasks/`; none is actionable.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) remains the approved revision 2 plan for completed E3-T1 only. A material plan for later tasks may be authored only after this spike revision is approved.
- No real-world availability flag, contact product/reveal, public detail/media API, production import, live Telegram ingestion, or backup claim enters this spike.
- Research outputs contain no private export payload, contact value, source path, credential, provider response, or media bytes.

## Research method and dated official sources

Official behavior and policy pages were checked on **2026-08-13**:

- [SQLAlchemy 2.0 asyncio documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.async_sessionmaker.begin) documents `async_sessionmaker.begin()` as a session/transaction context manager that commits on successful exit; [the PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert) exposes `INSERT ... ON CONFLICT`.
- [PostgreSQL advisory-lock documentation](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS) distinguishes session locks, held until release/session end, from transaction locks, released at transaction end.
- [Pillow `Image.verify()`](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.verify) checks file integrity without decoding pixels and requires reopening before later loading; [`ImageOps.exif_transpose()`](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose) applies EXIF orientation; [Pillow security guidance](https://pillow.readthedocs.io/en/stable/handbook/security.html#denial-of-service) retains decompression-bomb safeguards.
- [Geoapify pricing](https://www.geoapify.com/pricing/) lists 3,000 daily free credits and up to 5 requests/second; its [Geocoding API page](https://www.geoapify.com/geocoding-api/) says results may be stored with required source attribution, and its [terms](https://www.geoapify.com/terms-and-conditions/) require OpenStreetMap attribution plus Geoapify attribution on the free plan.
- [LocationIQ pricing](https://locationiq.com/pricing) lists 5,000 free requests/day, 2 requests/second, 60 requests/minute, and limited commercial use with attribution. Its official [caching policy](https://help.locationiq.com/support/solutions/articles/36000216111-can-i-save-addresses-from-api-output-) distinguishes indefinite response-data storage from a 48-hour free-account request/response cache.
- The [OSMF public Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/) caps use at one request/second, requires identifying headers and attribution, discourages recurring/bulk use, and says smaller one-time bulk tasks **may be permissible** only under its additional single-thread/single-machine/caching conditions.

Library behavior above was cross-checked against current SQLAlchemy and Pillow documentation through Context7. Provider terms can change and must be rechecked at implementation/activation time.

## Observed repository facts

- E2 extraction offsets refer to the unchanged flattened Python source string; contact spans and media references remain source-owned.
- The complete E2 audit publishes reconciled aggregate evidence while keeping private source/media outside Git.
- The current runtime topology has a read-only application-media path, but source originals and public derivatives are not yet specified by an approved E3 implementation contract.
- Existing synthetic catalog behavior must remain compatible while unresolved historical candidates wait for later review/geocoding.

## Recommended architecture constraints

These are spike-level constraints for later planning, not approved tables, fields, task acceptance criteria, or implementation instructions:

- **Contact-safe persistence:** retain restricted lineage while excluding plaintext contact values/spans from routine projections, excerpts, logs, reports, indexes, and errors until the later encrypted contact boundary.
- **Complete-run ownership with bounded commits:** prevent overlapping writers for one source across the whole run while keeping row/checkpoint transactions bounded; session advisory locking is one candidate, not a selected implementation.
- **Canonical replay identity:** preserve exact source/version ownership and same-message provenance; fuzzy fingerprints may suggest review but must not become canonical uniqueness or silently merge records.
- **Cache ambiguity:** cache uniqueness alone may not prevent cross-process duplicate provider calls; later planning must choose and test miss ownership without holding a database transaction across HTTP.
- **Reviewed pin atomicity:** provider success is not pin acceptance; selected coordinates, review state, and auditable selection lineage must change coherently.
- **Independent media ownership:** physical deduplication must not collapse source/media associations, including E2 `explicit_group`; restricted originals and public derivatives require separate serving boundaries.
- **Immutable derivative input identity:** a derivative must remain attributable to the exact verified original/version used, and unsafe/unread inputs must be rejectable without reading bytes merely to derive identity.
- **Staged import:** persistence, geocoding/review, media, and reconciliation must remain resumable failure domains rather than one long database/network/filesystem transaction.

## Provider recommendation and unresolved evidence

- **Recommendation, not decision:** retain a provider-neutral, persistent cache and evaluate Geoapify first because its currently published free quota/rate/storage/attribution terms fit the historical workload.
- Compare Geoapify and LocationIQ through the same interface against an owner-reviewed, redacted Warsaw fixture; record quality, precision, false positives, latency, current terms, and attribution before selecting or activating either provider.
- LocationIQ remains a comparator only after its then-current account/cache terms are confirmed compatible with the required durable result model.
- Public Nominatim remains, at most, a potential small one-time fallback that may be considered only if the linked OSMF policy permits the specific use and all conditions are met; it is not a recurring production dependency.
- **Unresolved:** no provider credentials or owner-reviewed redacted fixture are in the repository. B-008 remains active; absent evidence cannot be treated as provider approval or task completion.

## Options evaluated

- **Recommend for owner review:** extend the existing catalog behind inward-owned persistence/geocoder/storage ports, durable replay evidence, explicit review, and restricted/public media separation.
- **Reject:** persist parser output directly as public projections; it couples uncertain/reprocessable evidence to API shape and risks contact leakage.
- **Reject:** expose provider SDK payloads or source-relative media paths through domain/public contracts.
- **Reject:** accept every provider hit, infer Warsaw-centre fallback coordinates, auto-merge fuzzy candidates, or combine database/network/filesystem work in one long transaction.

## Proposed task boundaries

The existing task definitions remain unchanged planning inputs:

- [E3-T1](tasks/E3-T1-create-schema-and-migrations.md) — completed under approved spike/plan revision 2.
- [E3-T2](proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md) — unchanged revision 1 candidate.
- [E3-T3](proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) — unchanged revision 1 candidate.
- [E3-T4](proposed-tasks/E3-T4-implement-media-storage-and-derivatives.md) — unchanged revision 1 candidate.
- [E3-T5](proposed-tasks/E3-T5-import-and-review-the-complete-dataset.md) — unchanged revision 1 candidate; E2-T5 is satisfied, while later E3 dependencies remain unapproved/incomplete.

No task sequence, branch order, detailed model, acceptance criteria, migration, or rollout is approved by this spike draft. Those belong to a separate post-approval planning PR.

## Risks and open questions

- Source/contact leakage through provenance, excerpts, diagnostics, or committed fixtures.
- Replay divergence, overlapping runs, premature checkpoints, or canonical over-merge.
- Duplicate provider calls, changing terms/quotas, unavailable credentials/fixture, and misleading low-precision/out-of-scope pins.
- Traversal/symlink/non-regular/oversized/polyglot/decompression/metadata/partial-write media hazards.
- Original/derivative identity drift or physical deduplication that loses source association.
- Single-host database/media persistence remains data-loss exposure, not backup, under ADR-015.

## Exit checklist

- [x] The question is answered at architecture/research level.
- [x] Observed facts, recommendations, and unresolved evidence are distinguished.
- [x] Official external sources are dated and linked directly.
- [x] E2-T5/B-007 is recorded satisfied and B-008 remains unresolved.
- [x] Existing proposed tasks and the approved revision 2 implementation plan remain unchanged.
- [x] No production/disposable proof code or private source data was created.
- [x] `status` is `awaiting_approval` and approval metadata is `pending`.

## Owner decision

Pending. Only a durable owner-authored approval reference for **SPIKE.md revision 3** belongs on this branch. Approval would permit later task refinement/promotion and implementation planning; it would not authorize code, accept ADR-021, resolve D-002, or approve a later implementation plan.
