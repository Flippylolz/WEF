# Ingestion

This domain owns historical and live source adapters, the canonical parsing/normalization pipeline, media grouping, geocoding, idempotency, reconciliation, and failure policy.

## Canonical documents

- [Ingestion pipeline](PIPELINE.md) — historical import, shared canonical pipeline, reporting, review, and future Telethon adapter.
- [Geocoding](GEOCODING.md) — provider options, Warsaw/Poland constraints, caching, review, and provider-selection gates.

## Invariants

- Historical export and live Telegram events use the same canonical persistence core through source adapters.
- Source lineage is preserved and reprocessing is idempotent.
- Heuristic fields retain confidence/provenance and are never presented as verified facts.
- A public Telegram link is formed only from a verified channel identity.
- Recurring geocoding retains Geoapify under the resolved D-002 decision. The live worker implementation is deployed, while verified live entity/event, gap-reconciliation, and outage-recovery acceptance remain tracked under D-003/B-003.

Import runs must reconcile accepted, skipped, failed, and quarantined records without leaking private source data into Git, images, logs, or CI artifacts.
