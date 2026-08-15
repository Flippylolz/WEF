---
schema: ai-docs/adr@1
id: ADR-021
title: Use cached provider-neutral geocoding with Geoapify first
status: proposed
date: 2026-08-13
supersedes: []
superseded_by: []
resolves: []
---

# ADR-021: Use cached provider-neutral geocoding with Geoapify first

- Status: **proposed** by [E3 spike revision 3](../../epics/E3-database-geocoding-media/SPIKE.md). Spike revision 3 is approved for planning/promotion only and does **not** accept this ADR. Still pending owner ADR approval and not implementation authority.
- Proposed decision: keep geocoding behind an inward-owned provider port and persistent versioned cache. Evaluate Geoapify first for the historical import, retain LocationIQ as a comparator, and select/activate neither until the reviewed Warsaw fixture and then-current terms pass.
- Architecture rationale: provider-specific request/response shapes must not become domain contracts; cached results and explicit review permit deterministic replay and prevent page-view geocoding.
- Quality gate: compare both hosted providers through the same interface on an owner-reviewed, redacted 30–50-address Warsaw fixture. Record building/street/district precision, correct-point rate, out-of-area false positives, latency, terms, and attribution. Missing credentials/fixture block the comparison and are not acceptance evidence.
- Review safety: provider success never implies acceptance. Out-of-scope, low-precision, ambiguous, or low-confidence results remain unresolved/reviewable; a selected public pin must retain auditable result/review lineage.
- Cache uncertainty: a unique cache key may not prevent concurrent duplicate misses. A later plan must choose and verify cross-process miss ownership with healthy concurrency and ambiguous-retry reconciliation, without holding a database transaction during provider I/O and without promising an impossible at-most-once network call.
- Operations: provider keys remain backend/operator secrets, CI remains network-free, quota exhaustion defers work, and paid-plan activation requires a separate owner decision.
- Recurring ingestion: D-002 remains deferred. E8-T4 must revalidate quota, terms, quality, and fallback behavior before recurring use even if this candidate is later accepted for the historical path.

## Official evidence checked 2026-08-13

- [Geoapify pricing](https://www.geoapify.com/pricing/) publishes 3,000 free credits/day, up to 5 requests/second, limited commercial use, and required free-plan attribution.
- [Geoapify Geocoding API](https://www.geoapify.com/geocoding-api/) permits stored results with source attribution; [Geoapify terms](https://www.geoapify.com/terms-and-conditions/) require OpenStreetMap attribution and Geoapify attribution for free subscriptions.
- [LocationIQ pricing](https://locationiq.com/pricing) publishes 5,000 free requests/day, 2 requests/second, 60 requests/minute, and limited commercial use with attribution.
- LocationIQ's official [caching policy](https://help.locationiq.com/support/solutions/articles/36000216111-can-i-save-addresses-from-api-output-) says response data may be stored indefinitely but free-account request/response caching is limited to 48 hours. The applicable account/terms therefore require verification before treating LocationIQ as compatible with durable replay.
- The [OSMF Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) sets an absolute maximum of one request/second, requires identifying headers/attribution, discourages recurring bulk use, and says smaller one-time bulk tasks **may be permissible** only with its additional single-thread/single-machine/caching controls.

Provider policies may change without notice. Recheck all linked sources when the hosted comparison runs and before activation.

## Consequences if accepted later

- Geoapify would be the first measured historical candidate, not an unconditional selection.
- Public Nominatim would remain, at most, a potential small one-time fallback that may be considered only if its policy permits the specific use and all conditions are met, never the recurring production provider.
- Acceptance would resolve only the provider-neutral historical selection direction. It would not supply credentials, approve the fixture, complete E3-T3, authorize implementation, or waive E8-T4 recurring-use revalidation.
