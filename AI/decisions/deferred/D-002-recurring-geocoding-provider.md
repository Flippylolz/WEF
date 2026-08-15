---
schema: ai-docs/deferred-decision@1
id: D-002
title: Recurring geocoding provider
status: deferred
task_gates:
  - E8-T4
resolved_by: []
---

# D-002: Recurring geocoding provider

- Status: deferred. [ADR-021](../adr/ADR-021-use-cached-provider-neutral-geocoding.md) accepts Geoapify only for the historical import through the owner's merged [PR #59](https://github.com/Flippylolz/WEF/pull/59). Recurring production selection still requires E8-T4 revalidation and an explicit later resolution.
- Detailed comparison: [Geocoding](../../ingestion/GEOCODING.md).
- Historical result: Geoapify was selected after the owner reviewed its current pricing, rate, storage, attribution, and successful bounded readiness call. Geoapify-only sample quality and manual review belong to E3-T5; LocationIQ is no longer a mandatory historical comparator.
- Self-hosted alternative: regional Nominatim with a Poland extract and daily replication, preferably on a separate host or only after a resource benchmark. Photon/OpenSearch and Pelias are too memory-heavy for the current shared 8 GB NUC as initial choices.
- Constraint: the public Nominatim instance may only be considered for a small, cached, one-time seed import under its [official usage policy](https://operations.osmfoundation.org/policies/nominatim/), checked 2026-08-13. It is not the production recurring-ingestion dependency.
- Evidence gate: E3-T5 must record aggregate/redacted Geoapify quality and review evidence for the private historical inputs. E8-T4 still revalidates recurring-use quota, current terms, measured quality, and fallback behavior.
