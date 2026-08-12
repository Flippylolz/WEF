# Product Scope

## Product goal

Help a visitor explore Warsaw real-estate posts spatially, narrow them with practical filters, inspect photos and offer facts, and return to the original Telegram post when a verified source link is available.

The product is a discovery interface over dated source material. It is not a live availability guarantee or a transaction platform.

## Initial audience

- Buyers and investors browsing developments or apartments in Warsaw.
- Agency staff checking how imported channel posts appear geographically.
- Maintainers reviewing parsing and geocoding quality.

The public MVP does not require an account for browsing. In-house registration is optional and required only for restricted actions such as revealing masked contact details.

## Out-of-area and duplicate behavior

- Warsaw is the default geographic scope.
- Source messages/offers outside Warsaw remain imported. Their `Location` carries `out_of_scope=true` plus the appropriate geocoding review status, so they do not appear on the default public map.
- Reposts remain separate source messages but may resolve to the same canonical offer and location.
- The detail view may show source-history entries when multiple messages represent the same canonical offer.
- No record is silently discarded solely because parsing or geocoding failed.

## Explicit non-goals for the MVP

- Favorites, alerts, or saved searches.
- Payments, lead management, chat, or booking.
- Editing listings in the browser.
- Claiming real-time availability.
- Automated valuation or recommendation models.
- Full-text search beyond structured filters.
- Kubernetes, Redis, Elasticsearch, or multi-region deployment.
- Self-hosting a planet-scale map tile stack.

## Later product candidates

- Curated availability/status and an authenticated review queue.
- Saved searches and Telegram notifications.
- Polish, Russian, Ukrainian, and English interface localization.
- Draw-on-map and commute-time filters.
- Price-per-square-metre analytics.
- Lead workflows beyond the basic audited contact reveal.
- Public data freshness and ingestion-status indicators.
