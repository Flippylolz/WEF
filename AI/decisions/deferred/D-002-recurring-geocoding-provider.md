---
schema: ai-docs/deferred-decision@1
id: D-002
title: Recurring geocoding provider
status: deferred
task_gates:
  - E3-T3
  - E7-T6
  - E8-T4
resolved_by: []
---

# D-002: Recurring geocoding provider

- Status: initial provider path resolved; revalidate before live ingestion task E8-T4.
- Detailed comparison: [Geocoding](../../ingestion/GEOCODING.md).
- Recommended MVP option: Geoapify's free hosted plan, currently 3,000 credits/day and up to 5 requests/second, with server-side API key, required attribution, persistent caching, and quota monitoring.
- Free hosted alternative: LocationIQ, currently 5,000 requests/day with lower per-second/minute limits and required attribution.
- Self-hosted alternative: regional Nominatim with a Poland extract and daily replication, preferably on a separate host or only after a resource benchmark. Photon/OpenSearch and Pelias are too memory-heavy for the current shared 8 GB NUC as initial choices.
- Constraint: the public Nominatim instance may only be used for the small, cached, one-time seed import under its usage policy. It is not the production recurring-ingestion dependency.
- OpenCage's free allowance is a testing trial, not a production-free tier.
- Implementation gate: E3-T3 compares Geoapify and LocationIQ on the verified Warsaw fixture; Geoapify becomes the historical/initial production provider if it passes. E7-T6 uses that selected/cached provider. E8-T4 revalidates quota/terms/quality for recurring use rather than selecting from scratch.
