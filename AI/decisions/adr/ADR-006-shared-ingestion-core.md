---
schema: ai-docs/adr@1
id: ADR-006
title: Keep one ingestion core with source adapters
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-006: Keep one ingestion core with source adapters

- Status: accepted
- Date: 2026-08-12
- Decision: the historical JSON importer and future Telegram listener feed the same normalization, parsing, deduplication, geocoding, and persistence services.
- Rationale: separate pipelines would drift and produce incompatible records.
- Consequence: source-specific code stops at a stable raw-message contract. Every stage after that must be replayable and idempotent.
