---
schema: ai-docs/adr@1
id: ADR-002
title: Use a grouped location/development map
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-002: Use a grouped location/development map

- Status: accepted
- Date: 2026-08-12
- Decision: one pin represents a normalized location or development. Selecting it opens every related dated offer.
- Rationale: the export contains both development posts and unit offers, often at the same address. Separate overlapping pins would be misleading and hard to use.
- Consequence: ingestion must normalize addresses, relate offers to locations, and expose compact grouped summaries.
