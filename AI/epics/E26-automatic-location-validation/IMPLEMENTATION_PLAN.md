---
schema: ai-workflow/implementation-plan@1
epic: E26
title: "Automatic location validation and repair"
status: approved
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E26-T1
    revision: 2
  - id: E26-T2
    revision: 2
  - id: E26-T3
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: "Owner (Flippylolz)"
  decided_at: "2026-09-06T05:33:04Z"
  approved_revision: 1
  evidence: "Owner: i approve, responding to approval request for E26 implementation plan revision 1; OWNER_DECISION.md"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation plan: Automatic location validation and repair

## Approved spike baseline

[Spike revision 1](SPIKE.md) supplies the address-agreement-first recommendation. The [owner decision](OWNER_DECISION.md) records the direction to start and its interpretation as permission for task refinement and planning. The owner approved this plan revision 1 on 2026-09-06; see OWNER_DECISION.md.

Read-only code inspection against main `4ba7e23` on 2026-09-06 confirms that `review_geocode_result` lacks source address input, Geoapify mapping selects `features[0]`, sanitized diagnostics retain result type without structured address agreement, and the recurring worker invokes blanket pending-pin acceptance. Changing normalizer/request versions alone does not schedule accepted locations. These are implementation findings, not a fresh production audit.

The two owner-reported locations and the additional town-hall mismatch remain unverified. No replacement coordinate is selected in this plan. Preserve ADR-003/005/012/021, current hosted provider and shared quotas, source evidence, offer/location identity, favorites, owner corrections, privacy and release controls. No production dependency, paid capacity, new provider or backup claim is introduced.

## Scope and task sequence

Each task gets a dedicated branch and PR after approval. Merge in dependency order with current-head CI and review gates, using standing owner merge authorization. A child may start only on a valid recorded ancestor stack; an unrelated unfinished dependency cannot be called stacked.

| Task | Dependencies and current evidence | Independently reviewable outcome |
| --- | --- | --- |
| [E26-T1 revision 2](tasks/E26-T1-validate-address-agreement-and-precision.md) | None | Source/provider agreement, bounded candidate selection and removal of automatic blanket acceptance |
| [E26-T2 revision 2](tasks/E26-T2-revalidate-and-repair-existing-points.md) | E26-T1; E24-T1 is done via PR #331, merge `64da1bd9dd00e64be4e5ddbfce32e53f19c8f2af`, present in inspected main | Durable version-aware revalidation and guarded correction of existing locations |
| [E26-T3 revision 2](tasks/E26-T3-show-honest-map-precision.md) | E26-T1; E14-T5 remains draft with implementation approval blocked | Backend precision/discovery contract and accessible map/list behavior proven through the shared real-stack harness |

Recheck dependency state before starting and merging. E14-T5 does not block T1/T2; it does block starting T3 without a valid ancestor stack and completing T3 without its full acceptance. This plan does not authorize implementing E14's separate epic. Do not mark E26 done while T3 is blocked.

## T1: Validate source agreement before selecting coordinates

Work in ingestion domain `geocoding.py`, application `geocoding.py`, provider adapters, geocode store/models, recurring worker and pending-pin application/adapter/command. Keep parsing and policy provider-neutral; transport adapters translate provider fields and expose sanitized evidence to the domain. Update GEOCODING.md, PIPELINE.md and operator guidance.

1. Add immutable structured source/provider evidence: normalized street, house number, neighborhood, official district, city, country, provider result type and evidence version. Preserve source text and provenance; do not mutate identity hashes. Use reviewed exact aliases and Unicode folding, not fuzzy matching. Treat Gocław as a Warsaw neighborhood with its district context, never a replacement city. Keep unknown locality tokens explicit; do not assume every unrecognized segment is a city or street.
2. Advance normalizer/request/review versions to `warsaw-address-v3`, `forward-geocode-v3`, `warsaw-review-v2`. Retain existing scope bounds; the rectangle alone is insufficient address evidence. Cache keys include actual normalized request inputs and normalizer/request versions. Reapply current review policy on cache hits; old results without structured evidence cannot prove agreement.
3. Inspect at most five candidates per response, with at most two distinct source-supported query forms per source revision and policy version. Second form may remove noise or use structured constraints, but cannot discard a required street/number or invent either. Candidate ambiguity across distinct streets, numbers, districts or materially different same-name results produces an explicit unresolved outcome. Confidence breaks no address conflict.
4. Require compatible country/city/district where supplied and positive street agreement for a street claim; building additionally requires matching source and provider house numbers and an address/building result. Amenity classification alone cannot imply building precision. A street-only source with only building candidates remains unresolved unless an actual street-level candidate exists; do not reuse an arbitrary building point as proof of street geometry. An area centroid cannot satisfy a requested street. Confidence below the existing 0.80 floor remains uncertain after bounded attempts.
5. Persist bounded candidate evidence and the reason for the chosen or rejected result. Add a nullable versioned JSONB evidence envelope to cache rows if required to avoid changing the legacy response shape; old rows remain readable. Record effective source-supported precision separately from provider precision in selection evidence. Add stable reasons for address mismatch, unsupported precision and ambiguity; no secret/raw response logging.
6. Remove recurring AD-034 blanket promotion and make the operator command apply the same current validation rules. Explicitly supersede its automatic use in documentation; preserve historical lineage. Genuine manual accept/reject and owner/AI corrections remain protected. Only the exact legacy actor `ad-034-accept-pending-pins` is identifiable as the historical automatic acceptance; unknown operator provenance is not permission to overwrite. New automatic actions use `automatic_policy` and an accurate reason.

All candidate requests use the existing durable account budget and miss leases, including fallback forms. Do not multiply the cycle request cap by the number of candidates or retries. Quality failures exhaust the two-form limit and settle; timeout/quota failures defer through the durable T2 machinery rather than an unbounded quality retry. T1 must persist enough attempted-form information to avoid repeating a completed failed quality search on every recurring cycle.

T1 changes future decisions; existing accepted results are addressed by T2. Do not claim T1 repairs production examples. Until T3 ships, uncertain results may lose map eligibility under the existing projection; do not delete offers or change their visibility to disguise this transitional limitation. Stage broad T2 application only after honest discovery support is deployed.

Tests: wrong-street confidence 1.00, Jugosłowiańska/Grochowska amenity, both Gocław forms, duplicate street names, number conflicts, missing numbers, incompatible district/city/country, out-of-scope and invalid coordinates, incomplete evidence, candidate ordering, bounded forms, current/legacy cache, quota and genuine manual overrides. Use sanitized fixtures, real database selection boundaries and recurring/command regression tests.

## T2: Revalidate existing accepted results automatically

Add an inward-owned revalidation application service and SQLAlchemy queue adapter alongside the existing geocode store; integrate with the recurring geocode worker and settings. Reuse durable provider reservations and fencing. Do not route geocoding through the admin AI queue or change parser replay semantics. Update geocoding, pipeline, quality and operator documentation.

Add an indexed work table keyed uniquely by location ID, source fingerprint and target normalizer/request/review versions. Store pending/leased/deferred/terminal state, next-attempt time, bounded counters, observed selection revision, fencing token/lease expiry, outcome and timestamps. Store immutable before/after selection receipts linked to the work item. Retain query/cache/selection evidence; add schema before enabling the worker.

Discovery scans at most 100 locations per cycle with a durable keyset checkpoint and a version-specific scan generation. Include old accepted versions, missing evidence, weak precision, mismatches and historical automatic acceptances. For a new policy generation, cover all eligible existing locations, including high-confidence ones; never infer safety from confidence. New/edited locations enter through the ordinary pipeline or the next discovery pass. Completion receipts make repeat discovery and a second completed run a no-op. Changes to source/version create fresh work; unchanged terminal ambiguity does not reopen indefinitely.

Process at most 25 items and at most 25 combined foreground/revalidation provider requests per cycle, additionally bounded by the existing configured cap if lower. Reserve foreground capacity first; use at most half the configured cycle request cap for revalidation when both queues are nonempty (minimum one only when capacity permits). Within that share, allow at most two distinct query forms per item across restarts. Reuse current evidence without a provider call when sufficient; stale/missing evidence triggers the bounded fresh request path. Retain the existing account rate and daily ceiling; no independent repair quota.

Use a 120-second fenced work lease, renewable for active work. Expired leases resume automatically. Retry transient transport/system failures at 1, 5, 15, 60 and 240 minutes; after five consecutive failures emit an actionable systemic exception and stop that item's retry storm. A successful attempt resets its consecutive-failure counter. Quota/429 follows provider Retry-After or the existing durable daily reset and does not consume the quality-query allowance or become a false no-result. Never hold a database row lock during network I/O.

Before applying, lock the location and compare the observed source fingerprint, latest selection revision and protection state. A stale worker cannot publish. Requeue a changed source under its new key; mark protected conflicts without overwriting. Automatic predecessor selection, projection update and terminal receipt commit together. Preserve location/offer IDs, source links, favorites, owner fields and AI lineage. Unknown actor provenance is protected; absence of an owner flag is insufficient to override a known manual decision.

Apply unambiguous corrections automatically only in apply mode. Explicitly invalidate a proven mismatch and clear its precise public point; do not retain a known wrong point while asking the provider again. Mere transient failure must not erase a previously validated current point. Source-limited/ambiguous results end with uncertainty and a reason, not an invented replacement or a recurring owner campaign.

Expose bounded status/observation/apply controls and aggregate reports: eligible/completed/deferred/exception counts, street agreement, precision transitions, unique affected locations/offers, preserved IDs/favorites and human interventions. Populations overlap; report transitions rather than adding incompatible counts. Separate observation receipts from applied completion so observing a version never prevents subsequent application.

Tests use real PostGIS transactions: accepted old-version rows, high-confidence wrong streets, known AD-034 actor versus genuine owner, source/owner/AI edits during I/O, lease takeover, concurrent workers, atomic receipt failure, no result, quota/reset, restart after reservation, observation-to-apply and second-run no-op. Run concurrent parser replay fixtures to demonstrate stale-source protection.

## T3: Honest precision, uncertainty and discovery

Work in catalog domain/application projections, `map_query_adapter.py`, `browse_adapter.py`, API response schemas, generated OpenAPI/TypeScript and map/selected-location/list/detail components. The backend owns effective precision and eligibility; the browser renders it without reparsing addresses. Update HTTP_API.md and catalog/map documentation.

Add compatible optional fields for effective location precision (`building`, `street`, `area`, `unresolved`), validation status and uncertainty reason. Derive labels consistently: building location, approximate street location, approximate area and location unresolved. Provider confidence is not a probability of accuracy. Keep attribution and old fields for compatible readers.

Map features include only accepted source-supported points. Street features use an explicitly approximate treatment distinct from buildings. City/district-only evidence is area precision and does not receive a precise pin; without verified area geometry, use the list's area label rather than inventing an uncertainty circle or polygon. Quarantined/unresolved results never acquire a manufactured point.

Add a separately paginated list-only discovery mode for visible offers with unresolved or area-only locations. Apply ordinary non-spatial filters and trusted canonical district filters, but do not pretend to spatially filter point-less results by viewport. Expose this distinction to the user as “Location uncertain — outside map results”; selection opens details without flying to a fabricated point. Direct offer/detail access continues to honor visibility/auth rules. Existing viewport totals remain viewport-only; return separate mapped and list-only totals under their documented filter scopes. Keep stable IDs, favorites, URL state, selection and pagination behavior.

Low-confidence/uncertainty messages must appear in selected location and details independently of missing-value notes, with equivalent keyboard/mobile access. Unknown/legacy contract values fall back to explicit uncertainty.

Use focused projection/component tests plus E14-T5's real persisted backend/PostGIS/WebGL harness. Load sanitized Ostrzycka, Jugosłowiańska and town-hall regression records. Prove actual point/area/list behavior, cluster selection, labels, focus and mobile access. Mock-only tests and map-disabled journeys do not satisfy this acceptance. E14-T5 remains mandatory and separately owned.

## Data, security and compatibility

Migrations are additive: nullable sanitized evidence plus selection evidence in T1; work/checkpoint/receipt storage in T2; additive API fields and discovery mode in T3. Do not rewrite historical evidence or canonical identity keys. Legacy missing evidence reads as unvalidated. Schema must support the prior release while application rollback is needed; no destructive downgrade or queue reset.

Only bounded address components already needed for geocoding reach the existing provider. No full message, contact, session, credential or raw response is added to diagnostics, reports or Git. Authenticated operator controls retain existing authorization; public contracts expose neither audit actors nor raw candidate payloads. Test redaction and visibility failures. No new runtime package is approved.

## Operations, rollout and rollback

After implementation approval, deploy through the repository's normal CI/release path. T1 runs old/new policy observation against a fixed sanitized/current-cache sample before enabling future selection writes. T2 begins in observation mode; deployments and restarts resume durable work, but never silently switch observation into application.

Before applying to the existing production catalog, require T1 green, T3 discovery deployed, current schema/release health and a bounded observation report. Canary the three tracked cases plus up to 22 stratified locations (high-confidence, coarse, current-valid and protected). Verify no protected/identity changes, bounded requests, accurate lineage and map/list behavior, then expand automatically in 25-item batches within the same budget. Failed acceptance pauses application, retaining the queue and receipts. No per-location owner approval is the routine recovery mechanism.

For Ostrzycka, acquire dated authoritative street geometry and record its source, CRS, coverage and spatial comparison against the actual selected point before claiming correctness. Do not treat a provider self-reported street label or a new synthetic point as that proof. If geometry is unavailable, keep that acceptance open; do not invent an exact replacement. For both Jugosłowiańska variants, record source/provider street agreement, supported precision, persisted outcome and public selection evidence. Redact evidence; keep raw exports outside Git.

Rollback stops selection application/scheduling and retains observation and lineage. Restore only an unchanged automatic selection with matching receipt/revision, and never reinstate a known invalid point as precise. Protected or subsequently edited values are not reversible by a bulk rollback. Roll back UI with compatible uncertainty labels; do not restore blanket acceptance. Same-host retained data is rollback material, not a verified backup; ADR-015 backup deferral remains unchanged.

## Verification and completion

Install locked dependencies with `make install` using recorded tool versions. For each implementation PR run `make format-check`, `make lint`, `make typecheck`, `make test` and `make contract-check` where affected; always run lint/test before a push. Use an isolated Compose project and disposable test database to avoid other agents' services. Run migration compatibility and targeted regression tests, frontend production build, then the required real-stack browser journeys for T3. Record commands/results, CI head, release and applicable production evidence in each task.

Planning validation checks front matter, links, unique task authority, revision references and `git diff --check`. No application tests are authored during planning. Planning alone cannot close any regression, task or production acceptance item.

## Risks and invalidation

Failing closed can reduce map coverage: T3 list-only discovery must precede broad T2 application. Ambiguous or incomplete source evidence can make a precise repair impossible: keep a terminal reason and honest discovery. Legacy manual lineage may be indistinguishable from owner intent: exact-actor handling and protection guards take precedence over queue clearance. Concurrent parser changes can invalidate work: fingerprint/revision checks and new generation receipts prevent stale writes. Budget contention defers work durably rather than starving ingestion.

New provider/cost, changed source or protected-write authority, broader geometry infrastructure, weaker privacy or architecture changes return to the spike. Material numeric-budget, schema/contract, task/dependency, rollout or acceptance changes return to this plan for revision approval. E14-T5 cannot be silently removed or replaced with mocks.

## Approval checklist

- [x] Spike direction and approval interpretation are recorded with exact owner evidence.
- [x] Each sequence entry is promoted at revision 2 with preserved acceptance criteria.
- [x] Dependency status and the E14-T5 blocker are explicit.
- [x] Modules, contracts, migrations, budgets, guards, tests and recovery are specified.
- [x] No new provider, dependency or paid allocation is required.
- [x] No application code, test, migration or production mutation has been performed.
- [x] Owner approved revision 1; attributable decision metadata is recorded.

## Owner decision

Approval of revision 1 authorizes its bounded implementation sequence. It does not mark incomplete dependencies done or waive CI, review, protected state, canary or real-case verification gates.
