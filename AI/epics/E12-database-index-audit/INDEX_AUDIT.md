# E12 index audit

This document records the index review performed for public catalog read performance.

## Method

1. Trace SQL emitted by `SQLAlchemyMapQueryAdapter` and `SQLAlchemyCatalogBrowseAdapter`.
2. Compare predicate and ordering columns against existing Alembic and SQLAlchemy `Index` definitions.
3. Add only additive, forward migrations for missing high-value indexes.

## Catalog map query (`GET /api/v1/map/locations`)

- Joins `locations` to visible `offers`.
- Filters: review scope, PostGIS bbox, optional price/area/rooms/district/market/content groups, optional `published_at` lower bound.
- Existing coverage:
  - `ix_locations_point_gist` for bbox intersection.
  - `ix_locations_public_scope` for accepted/in-scope locations.
  - `ix_offers_publication (visibility, published_at, id)` for visible publication filtering.

## Selected-location offers (`GET /api/v1/locations/{id}/offers`)

- Filters offers for one `location_id`, usually with the same publication and range predicates.
- Orders by match rank, `published_at`, and offer id for cursor pagination.
- Gap: location-first access relied on `ix_offers_location` alone.
- Added: `ix_offers_location_visible_published`.

## Price overlap filters

- Map filters use overlap predicates on `price_min_minor` / `price_max_minor` for visible offers.
- Added partial index: `ix_offers_visible_price_range`.

## Non-goals

- No changes to ingestion, geocoding, or identity tables in this task.
- No destructive index drops or renames.
