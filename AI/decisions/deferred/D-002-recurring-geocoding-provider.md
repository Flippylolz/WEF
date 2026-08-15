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

- Status: deferred. [ADR-021](../adr/ADR-021-use-cached-provider-neutral-geocoding.md) remains proposed; approved E3 spike revision 3 and any later E3 plan approval do not resolve this decision. Recurring production provider selection still requires explicit later resolution plus E8-T4 revalidation.
- Detailed comparison: [Geocoding](../../ingestion/GEOCODING.md).
- Research recommendation: evaluate Geoapify first against LocationIQ through the same owner-reviewed Warsaw fixture, then record current terms and quality before selecting either.
- Self-hosted alternative: regional Nominatim with a Poland extract and daily replication, preferably on a separate host or only after a resource benchmark. Photon/OpenSearch and Pelias are too memory-heavy for the current shared 8 GB NUC as initial choices.
- Constraint: the public Nominatim instance may only be considered for a small, cached, one-time seed import under its [official usage policy](https://operations.osmfoundation.org/policies/nominatim/), checked 2026-08-13. It is not the production recurring-ingestion dependency.
- Evidence gate: provider credentials and the owner-reviewed redacted fixture remain unavailable. A later approved E3-T3 must record hosted terms/quality evidence before selection; E8-T4 still revalidates recurring-use quota, terms, quality, and fallback behavior.
