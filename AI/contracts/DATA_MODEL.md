# Data Model

HTTP transport behavior is defined in [HTTP API](HTTP_API.md), and deterministic schema generation is defined in [OpenAPI](OPENAPI.md).

## Modeling principles

- Preserve source records before deriving product records.
- Keep source identity separate from canonical offer identity.
- Store ranges as ranges, not as invented point values.
- Represent publication/visibility separately from real-world availability.
- Preserve extraction provenance and confidence.
- Use opaque public UUIDs; never expose internal storage paths or sequential database IDs.
- Store timestamps in UTC and render them in the user's locale.
- Store money in integer minor units with an ISO currency code.
- Store area as `numeric` square metres, preserving decimal-comma input through parsing.

## Canonical entities

The names below are conceptual. Exact migration names may use plural snake case.

### SourceChannel

Represents one Telegram source.

Required fields:

- `id`: UUID.
- `platform`: initially `telegram`.
- `external_id`: Telegram numeric channel ID as a string-safe value.
- `display_name`.
- `username`: nullable.
- `verified_link_base`: nullable.
- `created_at`, `updated_at`.

Constraints:

- Unique `(platform, external_id)`.
- A source-link builder uses `verified_link_base` or verified username configuration; it never guesses from display name.

### SourceMessage

Stores the current source representation independently of parsing success.

Required fields:

- `id`: UUID.
- `source_channel_id`.
- `external_message_id`.
- `message_type`.
- `published_at`.
- `edited_at`: nullable.
- `deleted_at`: nullable.
- `text_original`.
- `entities_json`.
- `raw_payload_json`.
- `raw_checksum`.
- `ingested_at`.

Constraints:

- Unique `(source_channel_id, external_message_id)`.
- Raw payload access is internal; public responses receive only explicitly selected fields.
- A live edit updates the current row transactionally and stores the prior payload in `SourceMessageRevision`.
- A live delete marks the source deleted and triggers visibility recalculation; it does not destroy lineage.

### SourceMessageRevision

Required fields:

- `id`: UUID.
- `source_message_id`.
- `revision_number`.
- `captured_at`.
- `raw_payload_json`.
- `raw_checksum`.

Constraint: unique `(source_message_id, revision_number)`.

### Location

Represents the spatial group rendered as one map pin.

Required fields:

- `id`: UUID.
- `display_address`.
- `normalized_address`.
- `normalized_address_hash`.
- `district`: nullable canonical Warsaw district.
- `city`, `country_code`.
- `point`: PostGIS `geometry(Point, 4326)`, nullable until geocoded.
- `precision`: `building`, `street`, `district`, `city`, or `unknown`.
- `confidence`: decimal from 0 to 1.
- `review_status`: `accepted`, `needs_review`, `rejected`, or `ungeocoded`.
- `out_of_scope`: boolean.
- `created_at`, `updated_at`.

Rules:

- Coordinates are nullable; no fallback Warsaw-centre point is permitted.
- Similar normalized addresses may be candidates for merge, but only an explicit merge operation changes identity.
- Coordinate order at the API boundary is longitude, latitude.

### Development

Represents a named project when the source provides enough evidence.

Fields:

- `id`: UUID.
- `location_id`.
- `display_name`.
- `normalized_name`.
- `name_confidence`.
- `created_at`, `updated_at`.

Constraint: a location can have zero or more named developments. Offers without a reliable project name still relate directly to the location.

### Offer

Represents one canonical proposition shown to users.

Required fields:

- `id`: UUID.
- `location_id`: nullable until resolved.
- `development_id`: nullable.
- `content_type`: `development` or `unit`.
- `market_type`: `primary`, `secondary`, or `unknown`.
- `visibility`: `visible`, `needs_review`, or `hidden`.
- `published_at`: publication timestamp of the source message selected as the offer's primary public representation.
- `latest_source_at`: latest related source/revision timestamp, used for lineage/freshness diagnostics rather than the public publication-date filter.
- `currency`: nullable ISO 4217 code.
- `price_min_minor`, `price_max_minor`: nullable.
- `area_min_sqm`, `area_max_sqm`: nullable.
- `rooms_min`, `rooms_max`: nullable.
- `floor_label`: nullable source-compatible normalized text.
- `delivery_label`: nullable.
- `source_text_excerpt`.
- `source_text_public_masked`: server-generated public rendering with contact spans masked/removed.
- `canonical_fingerprint`.
- `parser_version`.
- `created_at`, `updated_at`.

Rules:

- No `available`, `active`, or `sold` boolean exists in the MVP.
- A scalar parsed value is stored as equal min/max values.
- Unknown bounds remain null; they are not stored as zero.
- `published_at` is always visible in the public offer representation.
- A fingerprint supports duplicate suggestions; it is not a unique constraint.

### OfferSource

Relates canonical offers to one or more source messages.

Fields:

- `offer_id`.
- `source_message_id`.
- `relationship`: `primary`, `repost`, `update`, or `possible_duplicate`.
- `confidence`.
- `extraction_json`: field-level value, rule, source span, and confidence.
- `created_at`.

Constraint: unique `(offer_id, source_message_id)`.

### MediaAsset

Represents a verified source file stored by the application.

Fields:

- `id`: UUID.
- `source_message_id`.
- `storage_backend`.
- `storage_key`.
- `checksum_sha256`.
- `media_type`: `image` or `video`.
- `mime_type`.
- `byte_size`.
- `width`, `height`, `duration_seconds`: nullable as applicable.
- `thumbnail_asset_id`: nullable self-reference.
- `created_at`.

Constraints:

- Unique `(storage_backend, storage_key)`.
- Unique checksum may be used for physical deduplication without collapsing source ownership.

### OfferMedia

Fields:

- `offer_id`.
- `media_asset_id`.
- `position`.
- `association_rule`: `same_message`, `reply`, `time_burst`, or `manual`.
- `association_confidence`.

Constraint: unique `(offer_id, media_asset_id)`.

### ContactPoint

Represents a contact extracted from an offer/source message but never returned by anonymous endpoints.

Fields:

- `id`: UUID.
- `offer_id`.
- `source_message_id`.
- `kind`: `phone` or `telegram`.
- `value_ciphertext`: application-encrypted value.
- `masked_value`: safe anonymous representation.
- `fingerprint_hmac`: keyed fingerprint for deduplication without plaintext indexing.
- `is_revealable`.
- `created_at`, `updated_at`.

The encryption/HMAC keys live in service secrets, not PostgreSQL. Logs, reports, cache keys, analytics, and database indexes never contain the plaintext value.

### User

Fields:

- `id`: UUID.
- `username_normalized`: unique and immutable.
- `username_display`.
- `hashed_password`.
- `role`: `user` or `owner`.
- `is_active`, `must_change_password`.
- `created_at`, `updated_at`, `last_login_at`.
- `disabled_at`, `deleted_at`: nullable.

Authentication behavior is defined in [Authentication and contact reveal](../security/AUTH_ADMIN_CONTACTS.md).

### UserSession

Fields:

- `id`: UUID.
- `user_id`.
- `token_hash`.
- `created_at`, `expires_at`, `last_used_at`.
- `revoked_at`: nullable.

Constraint: the raw opaque cookie token is returned once and never stored/logged.

### ContactReveal

Fields:

- `id`: UUID.
- `user_id`.
- `offer_id`.
- `source_message_id`: nullable.
- `contact_set_version`.
- `revealed_at`.
- `request_id`.
- `outcome`: `allowed`, `rate_limited`, `forbidden`, or `unavailable`.

The audit stores identity/action metadata but never the contact value.

### AdminAuditEvent

Fields:

- `id`: UUID.
- `owner_user_id`.
- `target_user_id`: nullable.
- `target_type`, `target_id`: nullable.
- `action`.
- `occurred_at`.
- `request_id`.
- `outcome`.

It records owner administration actions without passwords, hashes, session tokens, contact values, IP addresses, or user-agent data.

### GeocodeResult

Acts as an audit trail and cache.

Fields:

- `id`: UUID.
- `query_hash`.
- `query_original`.
- `query_normalized`.
- `provider`.
- `provider_result_id`: nullable.
- `point`: nullable PostGIS point.
- `display_name`: nullable.
- `precision`.
- `confidence`.
- `within_scope`: nullable.
- `response_json`: redacted provider response or diagnostic subset.
- `attempted_at`.
- `expires_at`: nullable.
- `error_code`: nullable.

Repeated normalized queries use a successful cache entry unless an explicit re-geocode/version change is requested.

### IngestRun

Fields:

- `id`: UUID.
- `source_channel_id`.
- `mode`: `dry_run`, `historical`, `reprocess`, `media_verify`, or `live`.
- `status`: `running`, `succeeded`, `failed`, or `cancelled`.
- `source_checksum`: nullable.
- `parser_version`.
- `checkpoint_json`.
- `counts_json`.
- `report_storage_key`: nullable.
- `started_at`, `finished_at`.
- `release_sha`.
- `error_summary`: nullable and redacted.

Dry-run mode may create/update only its isolated `IngestRun` and report artifact. It does not write source, location, offer, geocode, or media tables.

## Important indexes

- Unique B-tree on source channel/platform identity.
- Unique B-tree on `(source_channel_id, external_message_id)`.
- GiST on `Location.point`.
- B-tree on `Location.district`, `review_status`, and `out_of_scope`.
- B-tree on `Offer.visibility`, `published_at`, `latest_source_at`, `content_type`, and `market_type`.
- Partial indexes for visible offers with non-null price, area, and room ranges after query plans justify them.
- B-tree on `Offer.location_id` and `Offer.development_id`.
- B-tree on `OfferSource.source_message_id`.
- B-tree on `ContactPoint.offer_id`; keyed fingerprint uniqueness scoped to offer/type where appropriate.
- Unique B-tree on normalized `User.username_normalized`.
- Unique B-tree on `UserSession.token_hash` plus indexes on user/expiry/revocation.
- B-tree on `ContactReveal.user_id`, `offer_id`, and `revealed_at` for rate limiting/audit retention.
- B-tree on `AdminAuditEvent.owner_user_id`, `target_user_id`, and `occurred_at`.
- Unique B-tree on `GeocodeResult.query_hash` for the current cache-key version.

Index additions require an observed query and `EXPLAIN ANALYZE` evidence; avoid indexing every nullable parsed column up front.

## Field-level extraction provenance

`OfferSource.extraction_json` stores provenance in a stable shape:

```json
{
  "price": {
    "value": {"min_minor": 56000000, "max_minor": 56000000, "currency": "PLN"},
    "rule": "price_dash_v2",
    "confidence": 0.98,
    "source_span": "Цена квартиры — 560 000 zł"
  }
}
```

This structure is internal. Public responses may expose a coarse `verified`, `parsed`, or `uncertain` indicator but not parser internals by default.
