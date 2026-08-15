---
schema: ai-docs/adr@1
id: ADR-021
title: Use cached provider-neutral geocoding with Geoapify for the historical import
status: accepted
date: 2026-08-15
supersedes: []
superseded_by: []
resolves: []
---

# ADR-021: Use cached provider-neutral geocoding with Geoapify for the historical import

- Status: **accepted** for the historical import by the owner's provider decision in merged [PR #59](https://github.com/Flippylolz/WEF/pull/59). This decision does not by itself approve revised E3 spike/plan artifacts or recurring production use.
- Decision: keep geocoding behind an inward-owned provider port and persistent versioned cache, and use Geoapify for the historical import. LocationIQ is not a mandatory hosted comparator because its free-account cache terms were not selected for the durable replay model and the owner selected Geoapify after reviewing current pricing, rate, storage, attribution, and the successful bounded readiness call.
- Architecture rationale: provider-specific request/response shapes must not become domain contracts; cached results and explicit review permit deterministic replay and prevent page-view geocoding.
- Quality gate: E3-T5 runs Geoapify over the approved private historical inputs, records aggregate/redacted precision, acceptance, rejection, out-of-area, and unresolved counts, and requires manual review before any result becomes a visible pin. Private addresses and provider payloads remain outside Git and CI.
- Review safety: provider success never implies acceptance. Out-of-scope, low-precision, ambiguous, or low-confidence results remain unresolved/reviewable; a selected public pin must retain auditable result/review lineage.
- Cache uncertainty: a unique cache key may not prevent concurrent duplicate misses. A later plan must choose and verify cross-process miss ownership with healthy concurrency and ambiguous-retry reconciliation, without holding a database transaction during provider I/O and without promising an impossible at-most-once network call.
- Operations: provider keys remain backend/operator secrets, CI remains network-free, quota exhaustion defers work, and paid-plan activation requires a separate owner decision.
- Recurring ingestion: D-002 remains deferred. E8-T4 must revalidate quota, terms, measured quality, and fallback behavior before recurring use.

## Official evidence checked 2026-08-13

- [Geoapify pricing](https://www.geoapify.com/pricing/) publishes 3,000 free credits/day, up to 5 requests/second, limited commercial use, and required free-plan attribution.
- [Geoapify Geocoding API](https://www.geoapify.com/geocoding-api/) permits stored results with source attribution; [Geoapify terms](https://www.geoapify.com/terms-and-conditions/) require OpenStreetMap attribution and Geoapify attribution for free subscriptions.
- [LocationIQ pricing](https://locationiq.com/pricing) publishes 5,000 free requests/day, 2 requests/second, 60 requests/minute, and limited commercial use with attribution.
- LocationIQ's official [caching policy](https://help.locationiq.com/support/solutions/articles/36000216111-can-i-save-addresses-from-api-output-) says response data may be stored indefinitely but free-account request/response caching is limited to 48 hours. The applicable account/terms therefore require verification before treating LocationIQ as compatible with durable replay.
- The [OSMF Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) sets an absolute maximum of one request/second, requires identifying headers/attribution, discourages recurring bulk use, and says smaller one-time bulk tasks **may be permissible** only with its additional single-thread/single-machine/caching controls.

Provider policies may change without notice. Recheck all linked sources before the historical run and again before recurring activation.

## Consequences

- Geoapify is the selected historical provider, but provider success is never automatic pin acceptance.
- The complete import owns the Geoapify-only quality/review evidence; E3-T3 owns the provider-neutral cache, policy, adapter, and readiness boundary.
- Public Nominatim would remain, at most, a potential small one-time fallback that may be considered only if its policy permits the specific use and all conditions are met, never the recurring production provider.
- This resolves only the historical selection direction. It does not authorize paid activation, production import, or recurring use, and it does not waive E8-T4 revalidation.
