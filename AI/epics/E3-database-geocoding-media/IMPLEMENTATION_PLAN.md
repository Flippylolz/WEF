---
schema: ai-workflow/implementation-plan@1
epic: E3
title: "Historical persistence, geocoding, media, and staged import plan"
status: approved
revision: 3
owner: owner
spike_revision: 3
task_sequence:
  - id: E3-T2
    revision: 2
  - id: E3-T3
    revision: 2
  - id: E3-T4
    revision: 2
  - id: E3-T5
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-15T03:52:26Z"
  approved_revision: 3
  evidence: "Plan PR https://github.com/Flippylolz/WEF/pull/46 merged after green CI (squash 0fdb87f, conflicts reconciled) under the owner's standing 2026-08-14/15 session directives to proceed through stacked PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Historical persistence, geocoding, media, and staged import

> Material revision 3 binds approved [spike revision 3](SPIKE.md) and promoted E3-T2–T5. It is submitted for owner approval only. It does not authorize code, accept [ADR-021](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md), resolve [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md), or claim plan approval. Historical plan revision 2 remains the completed authorization record for done E3-T1 only.

## Approved spike baseline

[E3 spike revision 3](SPIKE.md) is owner-approved. Binding constraints for this plan:

- Contact-safe persistence with no `ContactSpan` leakage into routine projections.
- Session-level/durable complete-run ownership with bounded transactions.
- Source-side canonical offer replay identity; fuzzy fingerprints are review suggestions only.
- Cache-miss ownership with healthy concurrency and ambiguous-retry reconciliation (not impossible at-most-once).
- Reviewed pin atomicity for selected result, coordinates, and review state.
- Independent media storage vs association outcomes; storage-class-scoped dedup; unread/rejected-before-read states; non-null E2 ordinals; observed content identity; derivative versioning by immutable input content.
- Same-message revision foreign keys; Python string offsets on preserved flattened text.
- Staged import failure domains; T3 hosted comparison remains a hard completion gate; B-008 credentials/fixture remain unresolved.
- ADR-021 stays proposed; D-002 stays deferred.

## Scope and outcome

Deliver [E3-T2](tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md), then allow [E3-T3](tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) and [E3-T4](tasks/E3-T4-implement-media-storage-and-derivatives.md) to proceed independently after T2, then deliver [E3-T5](tasks/E3-T5-import-and-review-the-complete-dataset.md). Every implementation task uses its own branch/PR from then-current `main` targeting `main`.

The result preserves every source/revision, converges under replay, keeps checkpoint acknowledgment atomic, accepts only reviewed in-scope coordinates, stores source-owned media behind opaque keys, and reconciles the complete audited export. E3 does not implement contact encryption/reveal, live Telegram, public offer-detail/media APIs, production transfer/activation, backups, or inferred availability.

## Ordered task sequence

### 1. E3-T2 — Idempotent persistence and reprocessing

- Task: [E3-T2 revision 2](tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md).
- Dependencies: completed [E2-T2](../E2-historical-export-parser-audit/tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md) ([PR #36](https://github.com/Flippylolz/WEF/pull/36)) and completed [E3-T1](tasks/E3-T1-create-schema-and-migrations.md) ([PR #11](https://github.com/Flippylolz/WEF/pull/11)).
- Independent result: source/revision/offer-source/ingest-run persistence with replay-safe checkpoints, without geocoding or media copy.
- Affected modules: Alembic migrations/mappings; ingestion domain/application ports; SQLAlchemy UoW adapter; operator persistence mode; tests.
- Verification: clean/prior-head migration; initial/current snapshot resolvability; unchanged/changed replay; cross-process complete-run exclusion; batch rollback/resume; contact-free provenance and multilingual Python `str` offsets; leakage scans.

### 2a. E3-T3 — Geocoder abstraction and cache

- Task: [E3-T3 revision 2](tasks/E3-T3-implement-geocoder-abstraction-and-cache.md).
- Dependencies: E2-T2, E3-T1, and E3-T2. After T2 merges, branch from then-current `main` and target `main`. Independent of E3-T4.
- Deferred gate: [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md) remains deferred for recurring production provider selection. This plan does not accept ADR-021. E3-T3 may implement provider-neutral ports, durable cache, fixtures, and adapters under plan approval without resolving D-002 or accepting ADR-021.
- Independent result: normalization, cache, miss ownership, review/selection lineage, and no-network fixtures; hosted comparison is a hard completion gate.
- Affected modules: geocode/cache/review migrations and ports; provider adapters; composition secrets; operator geocode/review modes; tests.
- Verification: cache hits/versioning; process-level miss ownership with ambiguous-retry reconciliation; selected-result atomicity; bounds/precision/confidence; network-free fixtures; mandatory hosted Geoapify/LocationIQ comparison evidence. B-008 blocks that comparison until credentials/fixture exist and cannot substitute for it.

### 2b. E3-T4 — Media storage and derivatives

- Task: [E3-T4 revision 2](tasks/E3-T4-implement-media-storage-and-derivatives.md).
- Dependencies: completed [E2-T3](../E2-historical-export-parser-audit/tasks/E2-T3-implement-media-grouping.md) ([PR #37](https://github.com/Flippylolz/WEF/pull/37)), E3-T1, and E3-T2. After T2 merges, branch from then-current `main` and target `main`. Deliberately independent of E3-T3; do not serialize T4 behind T3.
- Independent result: restricted originals, public derivatives, dispositions, and association preservation without geocoding.
- Affected modules: storage-class-scoped object/asset/disposition/derivative migrations; storage port/local adapter; operator media mode; edge mount contracts; tests.
- Verification: unread/rejected-before-read states; non-null E2 ordinals; observed content identity; class-scoped dedup; `explicit_group`; derivative versioning by immutable input content; adversarial path/no-open tests; mount exclusions.

### 3. E3-T5 — Complete import and review

- Task: [E3-T5 revision 2](tasks/E3-T5-import-and-review-the-complete-dataset.md).
- Dependencies: satisfied [E2-T5](../E2-historical-export-parser-audit/tasks/E2-T5-audit-the-complete-export.md) ([PR #42](https://github.com/Flippylolz/WEF/pull/42)) plus completed E3-T2, E3-T3 (including hosted comparison), and E3-T4.
- Independent result: staged local complete import with aggregate/redacted reconciliation evidence.
- Affected modules: operator staged modes; reconciliation reports; local ignored export/media wiring; tests/evidence docs.
- Verification: preflight identity/checksum; run-level lock across stages; stage reconciliation; visible-pin acceptance; reportable unresolved categories; deterministic second run; leakage scans. Local completion does not authorize production mutation (E7-T6).

## Cross-task architecture

- Ingestion domain owns immutable source/extraction/association/geocode/media/run values. Application owns normalization, review policy, orchestration, reconciliation, UoW/geocoder/storage/cache contracts, and stable reason codes. Infrastructure owns SQLAlchemy/Alembic, HTTP provider clients, Pillow/filesystem behavior, and report output. Composition alone loads settings/secrets.
- Catalog public queries continue through existing inward-owned read ports. Interface/public DTOs never import ORM rows, provider payloads, source descriptors, storage paths, or raw contacts.
- T2 establishes source/canonical transaction identity and complete-run ownership. T3 and T4 attach geocode/media state through their own bounded units; network and filesystem work never occurs while a database transaction is held.
- T5 coordinates stages and checkpoints but does not duplicate parser, normalization, geocoder, storage, or repository rules.
- Import-linter extends the ingestion framework-independence contract to prohibit SQLAlchemy, GeoAlchemy, HTTP clients, Pillow, settings, and filesystem infrastructure from domain/application modules.
- Delivery shape is **T2 → {T3, T4} → T5**. After T2 merges green, T3 and T4 independently branch from then-current `main` and target `main`. Blocked T3 hosted evidence does not block T4 implementation or completion. T5 starts only after both are merged. Ordering creates no branch ancestry or undeclared T3→T4 dependency.

## Data and migrations

- Follow the refined [DATA_MODEL.md](../../contracts/DATA_MODEL.md) constraints for same-message revision FKs, contact-free provenance offsets, selected-pin atomicity, geocode miss claims, storage-class-scoped media, unread dispositions, and derivative attempts.
- T2 adds source/revision/development/offer-source/ingest-run tables and constraints, preserves current seed rows, and makes only the compatibility changes needed for unresolved real offers.
- T3 adds provider/version-complete geocode audit/cache rows, cross-process cache-miss claims, selected-result linkage, and append-only review history.
- T4 separates storage-class-scoped restricted original objects from public derivative objects, source-owned assets, disposition attempts, per-variant derivative attempts/failures, successful versioned derivatives, and ordered offer relationships.
- UUIDs are opaque. Exact source and cache/storage natural keys enforce replay; fuzzy address/offer fingerprints produce review suggestions and are never uniqueness constraints.
- Every migration upgrades both an empty database and the previous head, is repeatable to head, updates SQLAlchemy metadata/readiness expectations, and has constraint/index/forbidden-column integration tests.
- Migrations are forward-only for normal operations. Application rollback must remain schema compatible; downgrades, deleting imported rows, and removing stored objects are explicit destructive recovery operations outside automatic deployment.

## Security and privacy

- Source text/payload may contain contacts and remains restricted internal lineage. T2's `extraction_json`, excerpts, and all public/operational projections explicitly omit plaintext `ContactSpan` values and contact-bearing spans.
- Contact spans are not materialized as `ContactPoint`; E6-T5 owns encryption/HMAC/masking/reveal. E3 public masked text must fail closed until that boundary exists.
- Provider API keys come only from backend/operator secrets. Requests, logs, persisted diagnostics, fixtures, and exception messages exclude keys/authorization headers. CI never calls hosted providers.
- Geocode acceptance requires scope, precision, confidence, and review policy; provider success or a district/city result cannot silently become an exact public pin.
- Source media and restricted application-owned originals are mounted only into the operator. The API/edge mounts only the application-owned public derivative subtree read-only.
- The raw export/media, generated detailed reports, provider responses, database dumps, and imported storage remain ignored and excluded from Git, build contexts, CI artifacts, and runtime images.

## Test and verification strategy

- Unit/property-style invariants cover source/checksum/revision decisions, transaction commands, provenance serialization, normalizer/cache identity, Warsaw review policy, media path/key/type/derivative rules, staged reconciliation, and stable reason codes.
- Disposable PostGIS integration covers every migration path, exact uniqueness/check constraints/indexes, initial/current source snapshot references, complete-run lock ownership across commits, process-level cache miss ownership/ambiguous-retry reconciliation, rollback/resume, selected-result/review lineage, storage-class-scoped dedup/references, non-negative source ordinals, safe-read checksum versus unread-sentinel replay identity, no-open unsafe rejection tests, original dispositions, derivative attempts/failures, and repeat-to-head.
- Filesystem tests use generated safe/hostile fixtures only.
- Provider tests use fake clocks/transports and recorded sanitized diagnostic subsets. The hosted quality comparison is an explicit operator acceptance run outside CI and is mandatory before E3-T3 can be completed.
- Complete-import tests use the sanitized E2 corpus in CI. T5 additionally runs the ignored export locally after exact E2 checksum/audit verification and commits only aggregate/redacted evidence.
- Every PR keeps CI green, including backend coverage `fail_under=90`, Ruff, mypy, import-linter, Markdown links, and existing Compose/production proofs applicable to docs-free task PRs later. This planning PR is documentation only.

## Operations, rollout, and rollback

- Deliver T2 first from then-current `main`. After T2 merges green, T3 and T4 may proceed independently on separate branches/PRs from then-current `main`; T3's hosted acceptance blocker does not hold T4. Start T5 from then-current `main` only after both T3 and T4 merge green.
- T2–T4 add inert migrations/libraries/operator paths before T5 invokes the private full dataset. Existing synthetic browsing remains available and no production import is automatic.
- T5 preflights free disk, read-only source identity/checksum, migration head, provider/cache configuration, and destination ownership. It runs persistence, geocoding, review, media, and verification as separate resumable modes.
- Database commits precede checkpoint acknowledgment; stored bytes are published before their referencing transaction, and unreferenced temp/orphan objects are reported for bounded cleanup rather than hidden.
- Production transfer/import remains E7-T6 under the deploy/host lock and explicit source/provider secrets. E3-T5 local evidence does not authorize production mutation or public activation.
- Roll back code only to schema-compatible images. Never auto-downgrade migrations, delete source lineage, purge media, or claim data recovery. ADR-015 means the accepted single-host loss risk remains until E7-T5.

## Risks and mitigations

- **Replay divergence/checkpoint loss:** database uniqueness, checksum revisions, complete-run session locks or durable leases, same-transaction checkpoints, injected-failure integration tests, and deterministic second-run comparisons (T2/T5).
- **Canonical over-merge:** exact source relationships converge; fingerprints/fuzzy addresses only suggest review and never delete or auto-merge (T2/T3/T5).
- **Misleading coordinates:** provider-neutral mappings, versioned cache, explicit bounds/precision/confidence, accepted-state constraints, and unresolved reports (T3/T5).
- **Provider cost/terms/key failure / B-008:** free-plan limits, no paid activation, durable cache, cross-process miss ownership with ambiguous-retry reconciliation, redacted configuration, mandatory fixture quality/terms gate, unresolved credentials/fixture blocker, and later E8-T4 revalidation (T3).
- **Media escape/resource attack:** read-only source, restricted originals, derivative-only public mount, path confinement/no-follow checks, generated hostile fixtures, streamed bounds, Pillow limits, opaque atomic storage, and metadata-free derivatives (T4).
- **Dedup deletes ownership/bytes:** separate logical/physical tables, class-scoped dedup, reference constraints, idempotent keys, and orphan/reference integrity checks (T4/T5).
- **Private-data leakage:** no private samples/artifacts, redacted summaries, safety scans, restricted source tables, and contact-product deferral (all).
- **Incomplete E3 dependencies:** E3-T5 remains blocked only by E3-T2, E3-T3, and E3-T4. E2-T5 is already satisfied through PR #42.
- **No backup:** report/retain ADR-015 risk; E3 does not add destructive rollback or recovery claims.

## Invalidation triggers

Return to the spike for a changed source/canonical/media/geocode contract, provider/storage architecture, automatic fuzzy merge/acceptance, contact-product persistence, public API behavior, security boundary, source handling, or deployment topology.

Return to this plan for material changes to task sequence/dependencies, migration/table boundaries, transaction/checkpoint/cache/storage behavior, provider/codec dependencies, acceptance thresholds, complete-import stages, test strategy, rollout, or rollback.

## Approval checklist

- [x] E3 spike revision 3 has durable owner approval and remains current.
- [x] E3-T2 through E3-T5 revision 2 are promoted under `tasks/` and locked into `task_sequence`.
- [x] The T2 → {T3, T4} → T5 order and cross-epic gates are explicit and acyclic; T4 is not serialized behind T3.
- [x] Architecture, migrations, transactions, cache/storage contracts, tests, security, operations, rollout, and rollback are explicit.
- [x] ADR-021 remains proposed; D-002 remains deferred; hosted comparison remains a hard E3-T3 completion gate; B-008 remains unresolved.
- [x] No E3-T2 through E3-T5 implementation code has been written.
- [x] `revision` is the material plan being submitted (3).
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

Pending. Only a durable owner-authored approval reference for **IMPLEMENTATION_PLAN.md revision 3** belongs next. Approval would authorize implementation under each task’s dependency/start gates. It would not accept ADR-021, resolve D-002, waive the E3-T3 hosted comparison, or start code without dedicated task branches.
