---
schema: ai-workflow/implementation-plan@1
epic: E3
title: "Historical persistence, geocoding, media, and staged import plan"
status: awaiting_approval
revision: 4
owner: owner
spike_revision: 4
task_sequence:
  - id: E3-T2
    revision: 2
  - id: E3-T3
    revision: 3
  - id: E3-T4
    revision: 2
  - id: E3-T5
    revision: 3
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

# Implementation Plan: Historical persistence, geocoding, media, and staged import

> Material revision 4 binds pending [spike revision 4](SPIKE.md), the owner's historical Geoapify decision in merged [PR #59](https://github.com/Flippylolz/WEF/pull/59), and revised E3-T3/E3-T5 task boundaries. It awaits revision-specific owner approval and authorizes no E3-T5 code yet. Historical plan revision 3 remains the authorization record for E3-T2 through E3-T4 work completed under it.

## Approved spike baseline

[E3 spike revision 4](SPIKE.md) is awaiting owner approval. If approved, its binding constraints for this plan are:

- Contact-safe persistence with no `ContactSpan` leakage into routine projections.
- Session-level/durable complete-run ownership with bounded transactions.
- Source-side canonical offer replay identity; fuzzy fingerprints are review suggestions only.
- Cache-miss ownership with healthy concurrency and ambiguous-retry reconciliation (not impossible at-most-once).
- Reviewed pin atomicity for selected result, coordinates, and review state.
- Independent media storage vs association outcomes; storage-class-scoped dedup; unread/rejected-before-read states; non-null E2 ordinals; observed content identity; derivative versioning by immutable input content.
- Same-message revision foreign keys; Python string offsets on preserved flattened text.
- Staged import failure domains; E3-T3 owns provider-neutral infrastructure/readiness, while E3-T5 owns Geoapify-only private-input quality and review evidence.
- ADR-021 is accepted for the historical import; D-002 stays deferred for recurring production use.

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

- Task: [E3-T3 revision 3](tasks/E3-T3-implement-geocoder-abstraction-and-cache.md).
- Dependencies: E2-T2, E3-T1, and E3-T2. After T2 merges, branch from then-current `main` and target `main`. Independent of E3-T4.
- Deferred gate: [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md) remains deferred for recurring production provider selection. ADR-021 selects Geoapify only for the historical import.
- Independent result: merged normalization, cache, miss ownership, review/selection lineage, no-network fixtures/adapters, and bounded Geoapify credential/readiness proof. Historical sample quality belongs to E3-T5.
- Affected modules: geocode/cache/review migrations and ports; provider adapters; composition secrets; operator geocode/review modes; tests.
- Verification: cache hits/versioning; process-level miss ownership with ambiguous-retry reconciliation; selected-result atomicity; bounds/precision/confidence; network-free fixtures; redacted bounded Geoapify readiness evidence from PR #59. No LocationIQ hosted comparison is required.

### 2b. E3-T4 — Media storage and derivatives

- Task: [E3-T4 revision 2](tasks/E3-T4-implement-media-storage-and-derivatives.md).
- Dependencies: completed [E2-T3](../E2-historical-export-parser-audit/tasks/E2-T3-implement-media-grouping.md) ([PR #37](https://github.com/Flippylolz/WEF/pull/37)), E3-T1, and E3-T2. After T2 merges, branch from then-current `main` and target `main`. Deliberately independent of E3-T3; do not serialize T4 behind T3.
- Independent result: restricted originals, public derivatives, dispositions, and association preservation without geocoding.
- Affected modules: storage-class-scoped object/asset/disposition/derivative migrations; storage port/local adapter; operator media mode; edge mount contracts; tests.
- Verification: unread/rejected-before-read states; non-null E2 ordinals; observed content identity; class-scoped dedup; `explicit_group`; derivative versioning by immutable input content; adversarial path/no-open tests; mount exclusions.

### 3. E3-T5 — Complete import and review

- Task: [E3-T5 revision 3](tasks/E3-T5-import-and-review-the-complete-dataset.md).
- Dependencies: satisfied [E2-T5](../E2-historical-export-parser-audit/tasks/E2-T5-audit-the-complete-export.md) ([PR #42](https://github.com/Flippylolz/WEF/pull/42)) plus completed E3-T2, revised E3-T3 after revision-4 approvals, and completed E3-T4.
- Independent result: staged local complete import with aggregate/redacted reconciliation evidence.
- Affected modules: operator staged modes; durable complete-import lease/stage checkpoint and provider-budget reservation migration/ports; reconciliation reports; local ignored export/media wiring; tests/evidence docs.
- Batch/resume contract: claim a fenced durable run lease for the exact source/pipeline identity; process deterministic cache-first work in bounded batches; reserve each hosted attempt/retry atomically against a UTC-day 2,700-request safety budget before network I/O; enforce four requests/second; checkpoint stage/counts after every bounded unit; pause cleanly on operator limit, daily budget, `429`, cancellation, or lease loss; resume from durable unresolved version state rather than an offset alone.
- Verification: preflight identity/checksum; lease exclusion/expiry/fencing across multi-day pauses; atomic provider-budget reservations under concurrency/crash; batch limit/quota/`429`/cancellation resume; Geoapify-only aggregate quality and manual review; stage reconciliation; visible-pin acceptance; reportable unresolved categories; deterministic second run; leakage scans. Local completion does not authorize production mutation (E7-T6) or recurring geocoding (E8-T4/D-002).

## Cross-task architecture

- Ingestion domain owns immutable source/extraction/association/geocode/media/run values. Application owns normalization, review policy, orchestration, reconciliation, UoW/geocoder/storage/cache contracts, and stable reason codes. Infrastructure owns SQLAlchemy/Alembic, HTTP provider clients, Pillow/filesystem behavior, and report output. Composition alone loads settings/secrets.
- Catalog public queries continue through existing inward-owned read ports. Interface/public DTOs never import ORM rows, provider payloads, source descriptors, storage paths, or raw contacts.
- T2 establishes source/canonical transaction identity and complete-run ownership. T3 and T4 attach geocode/media state through their own bounded units; network and filesystem work never occurs while a database transaction is held.
- T5 coordinates stages, durable lease/checkpoint state, and provider-budget reservations but does not duplicate parser, normalization, geocoder, storage, or repository rules. Cache/result/selection/media state is the correctness source for resume; cursors are progress hints and cannot skip unresolved work.
- Import-linter extends the ingestion framework-independence contract to prohibit SQLAlchemy, GeoAlchemy, HTTP clients, Pillow, settings, and filesystem infrastructure from domain/application modules.
- Delivery shape remains **T2 → {T3, T4} → T5**. T2/T4 are done and T3 implementation is merged; revised T3 completion gates must be approved/revalidated before T5 starts. Ordering creates no undeclared T3→T4 dependency.

## Data and migrations

- Follow the refined [DATA_MODEL.md](../../contracts/DATA_MODEL.md) constraints for same-message revision FKs, contact-free provenance offsets, selected-pin atomicity, geocode miss claims, storage-class-scoped media, unread dispositions, and derivative attempts.
- T2 adds source/revision/development/offer-source/ingest-run tables and constraints, preserves current seed rows, and makes only the compatibility changes needed for unresolved real offers.
- T3 adds provider/version-complete geocode audit/cache rows, cross-process cache-miss claims, selected-result linkage, and append-only review history.
- T4 separates storage-class-scoped restricted original objects from public derivative objects, source-owned assets, disposition attempts, per-variant derivative attempts/failures, successful versioned derivatives, and ordered offer relationships.
- T5 adds `complete_import_runs`-equivalent durable lease/stage/checkpoint state plus provider budget/attempt state. The exact schema must enforce one active pipeline identity, owner/fencing/lease expiry, explicit running/paused/failed/succeeded state, stage/version identity, redacted pause reason/next-eligible time, and atomic checkpoint/count updates.
- Provider budget state is keyed by provider, UTC date, and a non-secret configuration/account identity. Row-locked reservation atomically increments the configured 2,700-attempt safety budget and allocates a globally spaced `not_before` slot at least 250 ms after the prior slot; HTTP occurs after commit. A non-sensitive attempt ledger links run/query hash/reservation/outcome without storing the query, key, headers, or payload. Retries reserve separately; ambiguous crash reservations remain spent.
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
- Provider tests use fake clocks/transports and recorded sanitized diagnostic subsets. PR #59 supplies bounded Geoapify readiness evidence for revised T3; T5's Geoapify-only private-input quality/review run remains outside CI and publishes only aggregate/redacted evidence.
- Complete-import tests use the sanitized E2 corpus in CI, including tiny daily budgets and forced multi-day clocks to prove pause/resume equivalence. T5 additionally runs the ignored export locally after exact E2 checksum/audit verification and commits only aggregate/redacted evidence.
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
- **Provider cost/terms/key failure:** free-plan limits, four-request/second throttle, durable 2,700-request UTC-day reservations with a safety margin, no paid activation, cache-first batches, clean quota/`429` pause, cross-process miss ownership with ambiguous-retry reconciliation, redacted configuration, Geoapify-only quality/review evidence during T5, and later E8-T4 revalidation.
- **Media escape/resource attack:** read-only source, restricted originals, derivative-only public mount, path confinement/no-follow checks, generated hostile fixtures, streamed bounds, Pillow limits, opaque atomic storage, and metadata-free derivatives (T4).
- **Dedup deletes ownership/bytes:** separate logical/physical tables, class-scoped dedup, reference constraints, idempotent keys, and orphan/reference integrity checks (T4/T5).
- **Private-data leakage:** no private samples/artifacts, redacted summaries, safety scans, restricted source tables, and contact-product deferral (all).
- **Incomplete E3 dependencies:** E3-T2 and E3-T4 are complete. E3-T3 completion awaits revised spike/plan approval; E3-T5 remains blocked by that gate. E2-T5 is already satisfied through PR #42.
- **No backup:** report/retain ADR-015 risk; E3 does not add destructive rollback or recovery claims.

## Invalidation triggers

Return to the spike for a changed source/canonical/media/geocode contract, provider/storage architecture, automatic fuzzy merge/acceptance, contact-product persistence, public API behavior, security boundary, source handling, or deployment topology.

Return to this plan for material changes to task sequence/dependencies, migration/table boundaries, transaction/checkpoint/cache/storage behavior, provider/codec dependencies, acceptance thresholds, complete-import stages, test strategy, rollout, or rollback.

## Approval checklist

- [ ] E3 spike revision 4 has durable owner approval and remains current.
- [x] E3-T2 revision 2, E3-T3 revision 3, E3-T4 revision 2, and E3-T5 revision 3 are authoritative under `tasks/` and locked into `task_sequence`.
- [x] The T2 → {T3, T4} → T5 order and cross-epic gates are explicit and acyclic; T4 is not serialized behind T3.
- [x] Architecture, migrations, transactions, cache/storage contracts, tests, security, operations, rollout, and rollback are explicit.
- [x] ADR-021 is accepted for historical use only; D-002 remains deferred; Geoapify-only quality/review evidence belongs to E3-T5.
- [x] E3-T2 through E3-T4 implementation history is preserved; no E3-T5 implementation code has been written.
- [x] `revision` is the material plan being submitted (4).
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

Pending. Only durable owner-authored approval of **SPIKE.md revision 4** and then **IMPLEMENTATION_PLAN.md revision 4** belongs next. Plan approval would permit E3-T3 completion reconciliation and E3-T5 implementation under their task/dependency/branch gates. It would not resolve D-002, authorize recurring geocoding or production import, or waive the dedicated E3-T5 branch.
