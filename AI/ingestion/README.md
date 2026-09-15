# Ingestion

This domain owns historical and live source adapters, the canonical parsing/normalization pipeline, media grouping, geocoding, idempotency, reconciliation, and failure policy.

## Canonical documents

- [Ingestion pipeline](PIPELINE.md) — historical import, shared canonical pipeline, reporting, review, and deployed Telethon adapter.
- [Geocoding](GEOCODING.md) — provider options, Warsaw/Poland constraints, caching, review, and provider-selection gates.
- [Ungeocoded backlog and AI-assisted recovery](UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md) — Groq enablement, place-review vs offer-enrichment, and clearing remaining ungeocoded pins.

## Invariants

- Historical export and live Telegram events use the same canonical persistence core through source adapters.
- Source lineage is preserved and reprocessing is idempotent.
- Heuristic fields retain confidence/provenance and are never presented as verified facts.
- A public Telegram link is formed only from a verified channel identity.
- Recurring geocoding retains Geoapify under the resolved D-002 decision. The live worker, verified entity resolution, gap reconciliation and outage recovery are deployed and verified. D-003/B-003 retain the separate passive new/edit/delete acceptance requirement. E28 completed its fixed-cohort map/gallery checks and continuous 24-hour delivery window; see [production acceptance](../epics/E28-live-offer-map-delivery/PRODUCTION_ACCEPTANCE.md).

Import runs must reconcile accepted, skipped, failed, and quarantined records without leaking private source data into Git, images, logs, or CI artifacts.
