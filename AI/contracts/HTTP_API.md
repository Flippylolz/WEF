# HTTP API

Persisted entity semantics are defined in the [data model](DATA_MODEL.md), and deterministic schema generation is defined in [OpenAPI](OPENAPI.md).

## API conventions

- Base path: `/api/v1`.
- JSON fields use snake case.
- Dates use ISO 8601 with timezone.
- Public IDs are UUID strings.
- Money uses minor units and explicit currency.
- Coordinates use GeoJSON order `[longitude, latitude]`.
- Errors use RFC 9457-style `application/problem+json` with a stable `type`/machine code, HTTP `status`, safe title, and request ID; the frontend maps machine codes to i18n keys.
- Unknown query parameters are rejected where practical.
- Range parameters are validated for order and safe bounds.
- Pagination uses opaque cursors for offer collections.
- OpenAPI is generated offline by FastAPI, committed at `contracts/openapi/v1.json`, and checked against generated frontend types in CI as defined in [OpenAPI](OPENAPI.md).
- Production serves no OpenAPI, Swagger UI, or ReDoc route.
- Backend query services/interactors own filtering, grouping, sorting, visibility, capabilities, masking, and authorization.
- Presenters map application DTOs to these versioned schemas without I/O or new business decisions.
- The frontend consumes generated `openapi-typescript`/`openapi-fetch` contracts and must not recompute API/domain semantics.

## Public endpoints

### `GET /api/v1/map/locations`

Returns a GeoJSON `FeatureCollection` of visible locations with at least one matching offer.

Query parameters:

- `bbox`: required `min_lng,min_lat,max_lng,max_lat`, constrained to a safe maximum area.
- `price_min`, `price_max`: PLN minor-unit integers in the MVP.
- `area_min`, `area_max`: decimal square metres.
- `rooms`: repeated integer values.
- `district`: repeated canonical district slugs.
- `market_type`: repeated enum values.
- `content_type`: repeated `development`/`unit`; defaults to both.
- `published_from`, `published_to`: dates/timestamps applied to `Offer.published_at`.
- `quick_filter`: one server-defined preset ID from `/api/v1/quick-filters`; preset constraints are merged with explicit filters by the backend.

Each feature contains:

- Location public ID and point.
- Development/display name when known.
- Normalized display address and district.
- Coordinate precision and coarse confidence indicator.
- Matching offer count and total related offer count.
- Latest matching publication date.
- Matching price/area summary where comparable.

It does not contain full source text or full media arrays.

Example shape:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "location-uuid",
      "geometry": {"type": "Point", "coordinates": [21.0122, 52.2297]},
      "properties": {
        "display_name": "Example development",
        "display_address": "Example address, Warszawa",
        "district": "srodmiescie",
        "coordinate_precision": "building",
        "confidence": "high",
        "matching_offer_count": 2,
        "total_offer_count": 3,
        "latest_published_at": "2026-08-01T10:00:00Z",
        "price_min_minor": 80000000,
        "price_max_minor": 125000000,
        "area_min_sqm": "35.00",
        "area_max_sqm": "71.50",
        "currency": "PLN"
      }
    }
  ],
  "meta": {
    "request_id": "request-uuid",
    "feature_count": 1,
    "matching_offer_count": 2
  }
}
```

The API sets an ETag based on normalized filters plus the latest relevant data version. Short public caching is allowed; the browser must revalidate.

### `GET /api/v1/filter-facets`

Returns canonical district, room, market, and content-type options plus visible-dataset min/max bounds. The implemented endpoint has no query parameters; it is a cacheable description of the current public filter domain.

### `GET /api/v1/quick-filters`

Returns the server-defined quick-filter preset identifiers, i18n label keys, and canonical filter constraints. Clients send the selected identifier back as `quick_filter`; they do not duplicate preset semantics.

### `GET /api/v1/locations/{location_id}/offers`

Returns cursor-paginated offer summaries.

It accepts the same offer filters as the map endpoint and an `include_non_matching=false` flag. The UI can request matching offers first, then deliberately request all related history. Pages use the stable order `matches_filters DESC, published_at DESC, id DESC` and an opaque versioned cursor.

Each summary contains only dated structured offer fields, a backend-owned display name and coarse completeness indicator, an explicit `matches_filters` value, and `data_origin: "parser" | "ai_assisted"`. Apartment, parking, and storage price ranges remain separate; parking and storage can instead be explicitly marked as included in the apartment price. The collection response also carries the selected location metadata plus matching and total visible counts; there is no separate `GET /api/v1/locations/{location_id}` endpoint. It excludes source text/links, media, contacts, raw payloads, and provider data. The coarse origin value drives a transparent **AI-assisted data** badge but exposes no model, prompt, batch, source-offset, or parser-gap details.

### `GET /api/v1/offers/{offer_id}`

Returns:

- Dated offer fields.
- Coarse `data_origin` (`parser` or `ai_assisted`), with no detailed
  AI/provider provenance in the public response.
- Server-side masked public source text.
- Field confidence indicators.
- Location/development summary.
- Ordered media metadata and public URLs.
- Source message ID and verified `https://t.me/elestate_warszawa/{message_id}` URL.
- Related source-history metadata when the offer was reposted or edited.

It never returns raw/unmasked source text, raw payload JSON, original file paths, plaintext contact fields, parser stack traces, or geocoder credentials/responses.

### Authentication endpoints

Expose versioned in-house account flows defined in [Authentication and contact reveal](../security/AUTH_ADMIN_CONTACTS.md):

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/password`
- `POST /api/v1/auth/sessions/revoke-all`
- `POST /api/v1/auth/account/disable`
- `POST /api/v1/auth/account/delete`

Auth endpoints use username/password, opaque database-backed HttpOnly cookies, generic login responses, CSRF/origin controls, rate limits, and no-store headers as applicable. There is no email verification or self-service forgotten-password endpoint.

### Favorites endpoints

Authenticated accounts can persist public catalog locations:

- `GET /api/v1/favorites` lists the account's favorites newest-first.
- `PUT /api/v1/favorites/{location_id}` adds one accepted public location idempotently.
- `DELETE /api/v1/favorites/{location_id}` removes one favorite idempotently.

Favorites contain only public location labels and never create access to hidden locations or offers.

### View-history endpoints

Authenticated accounts can carry a “New since last visit” baseline across
browsers and retain a bounded record of opened public offers:

- `PUT /api/v1/view-history/visits/{visit_id}` starts one idempotent browser
  visit and returns its stable `current_visit_at` and nullable
  `previous_visit_at`. Replaying the same account/visit UUID does not advance
  the baseline.
- `PUT /api/v1/view-history/offers/{offer_id}` records a successful public
  offer-detail view, preserving the first timestamp while advancing the last
  timestamp and count. Absent or non-public offers return `404`.
- `GET /api/v1/view-history/offers` lists the account's still-public viewed
  offers, most-recent first.

All three endpoints are self-only, require an active authenticated session,
apply the identity origin/CSRF policy, and use no-store response handling.
Anonymous “New since last visit” remains browser-local and does not write
backend history.

### Owner administration console

Starlette Admin is mounted at `/admin` after HTTPS and is not included in public OpenAPI. Owner-only custom views/actions invoke application interactors for user disable/reactivate, session revocation, forced temporary-password reset, and reveal/admin audit queries. Generic model CRUD cannot access password hashes, sessions, contact ciphertext/plaintext, or secrets.

### `POST /api/v1/offers/{offer_id}/contacts/reveal`

Requires an active authenticated user whose `must_change_password` is false.

Response:

- Only revealable contacts associated with the visible offer.
- Contact type and plaintext value for this response only.
- No-store/private cache headers.

The endpoint decrypts values only after authorization/rate-limit checks and records a `ContactReveal` linked to user/offer/request without storing/logging plaintext, IP, or user-agent. Anonymous, disabled, forced-password-change, rate-limited, or invalid-ID requests do not reveal whether hidden data exists beyond the public masked representation.

### `GET /api/v1/health/live`

Returns process liveness without testing downstream systems.

### `GET /api/v1/health/ready`

Returns readiness only when the database is reachable and the migration revision is compatible.

### Deprecated compatibility endpoint

`GET /api/v1/estates` remains as the deprecated E0 compatibility shape and returns an inert empty projection. Catalog consumers use the grouped map/location/offer endpoints.

## Filter semantics

- Different filter groups combine with AND.
- Repeated values inside rooms, districts, market types, and content types combine with OR.
- A stored range matches a requested range when the ranges intersect inclusively.
- A null field does not match an active filter for that field.
- Date filtering uses the same `Offer.published_at` shown in the offer summary. Repost/edit timestamps remain source-history metadata and do not silently move an offer into a newer publication-date range.
- Only `Offer.visibility=visible`, accepted in-scope locations, and non-null coordinates appear on the public map.
- A map feature exists when at least one related offer matches.

These semantics must be implemented once in a query service shared by map, facet, and location-offer endpoints.

## Internal command contracts

Implemented operator operations are CLI entry points, not public HTTP endpoints:

- `wef-import {dry-run,persist,geocode,media,verify,run}` for the resumable historical pipeline.
- `wef-importer-dry-run` for the aggregate read-only parser audit.
- `wef-geocoder-check` and `wef-revalidate-recurring-geocoder` for bounded provider readiness/policy checks.
- `wef-promote-public-catalog` and `wef-accept-pending-geocode-pins` for explicit reviewed catalog transitions.
- `wef-verify-telegram-channel`, `wef-telegram-backfill`, `wef-telegram-worker`, and `wef-telegram-worker-status` for live ingestion and operations.
- `wef-migrate`, `wef-seed-m1`, and `wef-bootstrap-owner` for migration/rehearsal/owner bootstrap operations.

These commands fail non-zero when their safety or completion conditions are not satisfied and emit only bounded/redacted operator output.

## Compatibility policy

- Additive response fields are allowed within `/v1`.
- Removing, renaming, or changing field meaning requires `/v2` or a coordinated deprecation.
- Database migrations are forward-only in production and must remain compatible with the previous application release during a rolling/restart window where feasible.
- Parser changes do not overwrite source history; reprocessing records the new parser version and import run.
