---
schema: ai-docs/adr@1
id: ADR-005
title: Use PostgreSQL with PostGIS
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-005: Use PostgreSQL with PostGIS

- Status: accepted
- Date: 2026-08-12
- Decision: store canonical records in PostgreSQL and coordinates in PostGIS geometry/geography columns.
- Rationale: bounding-box queries, distance checks, location deduplication, future spatial features, and concurrent API/Telegram-writer access are first-class requirements. The operational cost of one isolated PostgreSQL container is acceptable. SQLite/SpatiaLite would reduce one container but provides weaker concurrency and spatial operations; document databases add no benefit for the relational/source-lineage model.
- Consequence: local and production environments require PostgreSQL/PostGIS and versioned Alembic migrations. SQLite is not a supported runtime database.
