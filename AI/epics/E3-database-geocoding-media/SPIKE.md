---
schema: ai-workflow/spike@1
epic: E3
title: "Historical persistence, geocoding, media, and import research"
status: approved
revision: 3
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-011, ADR-012, ADR-016, ADR-021]
domain_docs: [data, contracts, ingestion, security]
proposed_task_ids: [E3-T1, E3-T2, E3-T3, E3-T4, E3-T5]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-14T00:42:00Z"
  approved_revision: 3
  evidence: "Owner merge of https://github.com/Flippylolz/WEF/pull/44 (f968adb) plus owner continue directive authorizing spike revision 3 for task refinement/promotion and implementation planning"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Historical persistence, geocoding, media, and import

> Revision 3 is owner-approved research. It authorizes task refinement/promotion and a later implementation-plan revision. It does not authorize code, accept [ADR-021](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md), resolve [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md), or approve any implementation plan.

## Question

What architecture constraints should govern a later plan for converting the audited E2 stream into replay-safe canonical data, reviewed Warsaw coordinates, and safe media without exposing restricted source data or coupling the core to providers/storage?

## Current state and boundaries

- PostgreSQL/PostGIS remains canonical under ADR-005; E3-T1 already delivered the synthetic M1 `locations`/`offers` foundation.
- E2-T2/E2-T3 provide source-neutral extraction and media-association contracts. E2-T5 is `done` through merged [PR #42](https://github.com/Flippylolz/WEF/pull/42), so B-007 is satisfied.
- E3-T2 through E3-T5 are refined and promoted under `tasks/` after this approval; they remain non-actionable until an owner-approved material implementation plan unlocks their implementation gates.
- Completed E3-T1 remains governed by the historical approved plan revision 2. A material plan for E3-T2–T5 is submitted separately and is not approved by this spike.
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
- **Cache ambiguity:** cache uniqueness alone may not prevent cross-process duplicate provider calls; later planning must choose and test miss ownership with a healthy-concurrency guarantee and ambiguous-retry reconciliation, not an impossible at-most-once network promise. Provider I/O must not hold a database transaction.
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
- **ADR-021 / D-002:** [ADR-021](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md) remains `proposed`. This spike approval does not accept ADR-021 or resolve [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md).

## Options evaluated

- **Recommend for owner review:** extend the existing catalog behind inward-owned persistence/geocoder/storage ports, durable replay evidence, explicit review, and restricted/public media separation.
- **Reject:** persist parser output directly as public projections; it couples uncertain/reprocessable evidence to API shape and risks contact leakage.
- **Reject:** expose provider SDK payloads or source-relative media paths through domain/public contracts.
- **Reject:** accept every provider hit, infer Warsaw-centre fallback coordinates, auto-merge fuzzy candidates, or combine database/network/filesystem work in one long transaction.

## Proposed task boundaries

- [E3-T1](tasks/E3-T1-create-schema-and-migrations.md) — completed under approved spike/plan revision 2.
- [E3-T2](tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md) — refined/promoted after this spike approval; implementation gate pending plan approval.
- [E3-T3](tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) — refined/promoted after this spike approval; implementation gate pending plan approval; hosted comparison remains a hard completion gate; B-008 unresolved.
- [E3-T4](tasks/E3-T4-implement-media-storage-and-derivatives.md) — refined/promoted after this spike approval; independent of E3-T3 after E3-T2; implementation gate pending plan approval.
- [E3-T5](tasks/E3-T5-import-and-review-the-complete-dataset.md) — refined/promoted after this spike approval; depends on E3-T2/T3/T4; implementation gate pending plan approval.

Delivery sequence after a later approved plan: T2 first, then T3 and T4 may proceed independently, then T5. Do not serialize T4 behind T3.

## Risks and open questions

- Source/contact leakage through provenance, excerpts, diagnostics, or committed fixtures.
- Replay divergence, overlapping runs, premature checkpoints, or canonical over-merge.
- Duplicate or ambiguous provider calls, changing terms/quotas, unavailable credentials/fixture, and misleading low-precision/out-of-scope pins.
- Traversal/symlink/non-regular/oversized/polyglot/decompression/metadata/partial-write media hazards.
- Original/derivative identity drift or physical deduplication that loses source association.
- Single-host database/media persistence remains data-loss exposure, not backup, under ADR-015.

## Exit checklist

- [x] The question is answered at architecture/research level.
- [x] Observed facts, recommendations, and unresolved evidence are distinguished.
- [x] Official external sources are dated and linked directly.
- [x] E2-T5/B-007 is recorded satisfied and B-008 remains unresolved.
- [x] Spike approval authorizes refinement/promotion and planning only; ADR-021 stays proposed and D-002 stays deferred.
- [x] No production/disposable proof code or private source data was created.
- [x] `status` is `approved` and approval metadata matches revision 3.

## Owner decision

Flippylolz approved spike revision 3 through the merge of [PR #44](https://github.com/Flippylolz/WEF/pull/44) (`f968adb`) and the owner continue directive that authorized recording that approval. This permits task refinement/promotion and a separate material implementation-plan revision. It does not authorize code, accept ADR-021, resolve D-002, or approve any implementation plan.
