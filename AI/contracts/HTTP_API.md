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

Returns canonical district, room, market, and content-type options plus dataset min/max bounds. It accepts the non-facet filters needed for contextual counts but does not attempt complex search-engine-style aggregations in the first release.

### `GET /api/v1/locations/{location_id}`

Returns location/development metadata and aggregate counts. It does not automatically return every related source message.

### `GET /api/v1/locations/{location_id}/offers`

Returns cursor-paginated offer summaries.

It accepts the same offer filters as the map endpoint and an `include_non_matching=false` flag. The UI can request matching offers first, then deliberately request all related history.

### `GET /api/v1/offers/{offer_id}`

Returns:

- Dated offer fields.
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
- `POST /api/v1/auth/password/change`
- `GET /api/v1/users/me`
- `DELETE /api/v1/users/me`
- `DELETE /api/v1/users/me/sessions`

Auth endpoints use username/password, opaque database-backed HttpOnly cookies, generic login responses, CSRF/origin controls, rate limits, and no-store headers as applicable. There is no email verification or self-service forgotten-password endpoint.

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

Internal importer operations are CLI commands, not public HTTP endpoints:

- `import dry-run --source ...`
- `import historical --source ... --media-root ...`
- `import reprocess --channel ... --parser-version ...`
- `import verify-media --channel ...`
- `telegram listen --channel ...`

Exact syntax can change before implementation, but every command must support structured logs, an ingest-run record, a report destination, safe cancellation, and non-zero failure exit codes.

## Compatibility policy

- Additive response fields are allowed within `/v1`.
- Removing, renaming, or changing field meaning requires `/v2` or a coordinated deprecation.
- Database migrations are forward-only in production and must remain compatible with the previous application release during a rolling/restart window where feasible.
- Parser changes do not overwrite source history; reprocessing records the new parser version and import run.
