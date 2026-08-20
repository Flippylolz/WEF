---
schema: ai-workflow/epic@1
id: E12
title: "Database index audit"
status: done
milestones: [M3]
owner: owner
---

# E12: Database index audit

## Outcome

Catalog read paths used by the public map have reviewed, additive PostgreSQL indexes aligned with observed query patterns.

## Audit summary

See [INDEX_AUDIT.md](INDEX_AUDIT.md) for the full table-by-table review.

### Added in E12-T1

| Index | Table | Columns | Rationale |
|-------|-------|---------|-----------|
| `ix_offers_location_visible_published` | `offers` | `(location_id, visibility, published_at, id)` | Selected-location offer pages filter by location and visibility, then order by publication time with cursor pagination. |
| `ix_offers_visible_price_range` | `offers` | `(visibility, price_min_minor, price_max_minor)` partial `visibility = 'visible'` | Map price overlap filters always constrain visible offers; the partial index keeps the working set smaller. |

### Already sufficient

| Index | Rationale |
|-------|-----------|
| `ix_offers_publication` | Grouped map queries filter visible offers by publication time. |
| `ix_locations_point_gist` | Viewport queries use PostGIS intersection on location points. |
| `ix_locations_public_scope` | Accepted/public location scope and district filters. |
| Identity and ingestion indexes | Out of scope for the public map read path; retained as-is. |

## Promoted tasks

- [E12-T1: Add catalog query indexes from audit](tasks/E12-T1-add-catalog-query-indexes.md) — P1/M, M3
