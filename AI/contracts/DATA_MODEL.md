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
- `current_revision_id`: required reference to the immutable snapshot matching the current row.
- `message_type`.
- `published_at`.
- `edited_at`: nullable.
- `deleted_at`: nullable.
- `text_original`: the exact flattened E2 `RawMessage.text` string, preserved without Unicode normalization, case folding, whitespace normalization, or any other mutation.
- `entities_json`.
- `raw_payload_json`.
- `raw_checksum`.
- `ingested_at`.

Constraints:

- Unique `(source_channel_id, external_message_id)`.
- Raw payload access is internal; public responses receive only explicitly selected fields.
- Initial ingestion creates `SourceMessageRevision` number 1 containing the exact initial representation and points `current_revision_id` to it.
- Initial source/revision insertion uses a deferred same-message foreign-key check within one transaction; no committed `SourceMessage` has a null or unresolved current revision.
- A changed checksum appends the complete new representation as the next immutable revision and updates the current row plus `current_revision_id` atomically. Unchanged replay creates no revision.
- Every current or historical source version therefore has a resolvable `SourceMessageRevision`; the current row is a convenience projection of the snapshot identified by `current_revision_id`.
- A live delete marks the source deleted and triggers visibility recalculation; it does not destroy lineage.

### SourceMessageRevision

Required fields:

- `id`: UUID.
- `source_message_id`.
- `revision_number`.
- `captured_at`.
- `message_type`.
- `published_at`.
- `edited_at`: nullable.
- `text_original`: exact unmodified flattened E2 `RawMessage.text` for this version.
- `entities_json`.
- `raw_payload_json`.
- `raw_checksum`.

Constraints:

- Unique `(source_message_id, revision_number)`.
- Revision 1 always exists for an ingested source message.
- `SourceMessage.current_revision_id` references a revision with the same `source_message_id`, and its current checksum/text/payload fields equal that immutable snapshot.

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
- `selected_geocode_result_id`: nullable reference to the currently selected audited result.
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
- `price_min_minor`, `price_max_minor`: nullable apartment price/range.
- `parking_price_min_minor`, `parking_price_max_minor`: nullable parking price/range.
- `parking_included_in_price`: true only when the source says parking is included.
- `storage_price_min_minor`, `storage_price_max_minor`: nullable storage price/range.
- `storage_included_in_price`: true only when the source says storage is included.
- `area_min_sqm`, `area_max_sqm`: nullable.
- `rooms_min`, `rooms_max`: nullable.
- `floor_label`: nullable source-compatible normalized text.
- `delivery_label`: nullable.
- `source_text_excerpt`: nullable contact-free excerpt; text covered by any `ContactSpan` is omitted rather than copied or merely labelled.
- `source_text_public_masked`: server-generated public rendering with contact spans masked/removed.
- `canonical_fingerprint`.
- `parser_version`.
- `created_at`, `updated_at`.

Rules:

- No `available`, `active`, or `sold` boolean exists in the MVP.
- A scalar parsed value is stored as equal min/max values.
- Unknown bounds remain null; they are not stored as zero.
- Parking and storage amounts remain distinct from the apartment price.
- An included add-on has null amount bounds and its explicit included flag set.
- `published_at` is always visible in the public offer representation.
- A fingerprint supports duplicate suggestions; it is not a unique constraint.
- Canonical offer replay/upsert identity is source-anchored through exact `OfferSource` relationships to immutable source message revisions. Fuzzy fingerprints never become uniqueness keys and must not silently merge offers.

### OfferSource

Relates canonical offers to one or more source messages.

Fields:

- `offer_id`.
- `source_message_id`.
- `source_message_revision_id`: immutable source snapshot against which every provenance offset was produced.
- `relationship`: `primary`, `repost`, `update`, or `possible_duplicate`.
- `confidence`.
- `extraction_json`: versioned field-level value, rule, non-contact source offsets, and confidence. It excludes plaintext `ContactSpan` values and the text of every contact-bearing span.
- `created_at`.

Constraint: unique `(offer_id, source_message_revision_id)`; a changed source revision appends revision-specific provenance rather than silently rebasing old offsets onto new text.

### StoredMediaObject

Represents one verified physical object in application-owned storage.

Fields:

- `id`: UUID.
- `storage_backend`.
- `storage_key`: opaque versioned key, never a source/host path.
- `storage_class`: `restricted_original` or `public_derivative`.
- `checksum_sha256`.
- `mime_type`.
- `byte_size`.
- `created_at`.

Constraints:

- Unique `(storage_backend, storage_key)`.
- Unique `(storage_backend, storage_class, checksum_sha256, byte_size)` permits physical deduplication only within one storage class. Identical restricted-original and public-derivative bytes remain distinct objects.
- Physical deletion is forbidden while any source asset or derivative references the object.
- `restricted_original` objects live outside the public derivative subtree and are never mounted into the API/edge.
- `public_derivative` objects may be served only from the dedicated derivative subtree; a broad parent containing originals is not a valid public mount.

### MediaAsset

Represents one source-owned logical media item independently of physical deduplication.

Fields:

- `id`: UUID.
- `source_message_id`.
- `source_ordinal`.
- `source_descriptor_json`: internal relative descriptor/provenance; never a public URL.
- `stored_object_id`.
- `media_type`: `image` or `video`.
- `mime_type`.
- `byte_size`.
- `width`, `height`, `duration_seconds`: nullable as applicable.
- `created_at`.

Constraints:

- Unique `(source_message_id, source_ordinal)`.
- `source_ordinal >= 0`.
- Multiple assets may reference one stored object without collapsing source ownership.
- `stored_object_id` must reference a `StoredMediaObject` whose `storage_class` is `restricted_original`; this is enforced by a storage-class-aware reference/constraint rather than application convention alone.

### MediaDispositionAttempt

Represents a versioned attempt to resolve, verify, associate, or store an expected source media item, including non-success outcomes.

Fields:

- `id`: UUID.
- `source_message_id`.
- `source_ordinal`: required non-negative E2 `MediaReference.media_index`/source ordinal, including when the disposition is `unassociated`.
- `source_message_revision_id`: required immutable source revision that produced the media reference.
- `source_descriptor_identity`: stable hash/identifier, never a public path.
- `observation_status`: `read_observed`, `unread_unavailable`, or `unread_rejected`.
- `observation_reason_code`: stable versioned reason. Required for unread states; examples include `missing`, `path_traversal`, `symlink`, `non_regular`, `oversized_metadata`, and `unsupported_descriptor`.
- `observed_checksum_sha256`: observed content checksum; required only for `read_observed` and null for every unread state.
- `observed_byte_size`: observed metadata/content size; may be null when unavailable/unsupported, may retain safe stat metadata for a pre-read oversized rejection, and does not imply bytes were opened.
- `attempt_number`.
- `verifier_version`.
- `association_version`.
- `disposition`: `stored`, `missing`, `rejected`, `unsupported`, or `unassociated`.
- `reason_code`: stable versioned reason.
- `media_asset_id`: nullable; present only when a logical asset was stored.
- `attempted_at`.

Constraints and replay identity:

- `source_ordinal >= 0`; unassociated media retains its original E2 ordinal rather than replacing it with null.
- The logical replay key is `(source_message_id, source_ordinal, source_message_revision_id, source_descriptor_identity, content-identity-component, verifier_version, association_version)`. The content-identity component is the checksum for `read_observed`, or a stable versioned `unread:<observation_reason_code>` sentinel for an unread state. `attempt_number` is unique within that key.
- Including `source_ordinal` prevents two identical descriptors in one message from collapsing into one attempt.
- Path confinement, symlink/no-follow, regular-file, supported-descriptor, and safe metadata/size checks run before content access. Traversal, symlink, non-regular, oversized, unsupported, missing, and similar failures are persisted as unread states without opening or hashing unsafe bytes.
- When bytes are safely readable, checksum is mandatory. Replacement under the same descriptor produces a different observed checksum and therefore a new attempt/review outcome; it cannot reuse the prior terminal attempt.
- An identical unread reason/sentinel plus immutable source revision may reuse the same terminal unread attempt. If the input later becomes safely readable, its checksum creates a new replay identity. A source revision, reason, or verifier/association version change likewise creates a new auditable attempt rather than overwriting history.

### MediaDerivative

Represents a reproducible public derivative of one logical source asset.

Fields:

- `id`: UUID.
- `media_asset_id`.
- `stored_object_id`.
- `variant`: versioned value such as `thumbnail_webp_v1` or `thumbnail_jpeg_v1`.
- `width`, `height`.
- `created_at`.

Constraints:

- Unique `(media_asset_id, variant)`.
- `stored_object_id` must reference a `StoredMediaObject` whose `storage_class` is `public_derivative`; a derivative can never reuse or expose a restricted-original object even when checksums match.

### MediaDerivativeAttempt

Represents each auditable attempt to generate one derivative variant, independently of original-file resolution/storage disposition.

Fields:

- `id`: UUID.
- `media_asset_id`.
- `variant`: the requested versioned derivative variant.
- `attempt_number`.
- `transform_version`.
- `status`: `pending`, `succeeded`, or `failed`.
- `reason_code`: nullable stable failure reason; required for `failed`.
- `source_object_checksum_sha256`: pins the restricted original used as input without copying its bytes/path.
- `media_derivative_id`: nullable; required only for `succeeded`.
- `started_at`, `finished_at`: `finished_at` nullable while pending.

Constraints:

- Unique `(media_asset_id, variant, attempt_number)`.
- A succeeded attempt references a `MediaDerivative` of the same asset/variant and therefore a `public_derivative` stored object.
- Replay under the same source checksum and transform version reuses the terminal attempt; a retry or changed transform appends an attempt rather than overwriting failure history.

### OfferMedia

Fields:

- `offer_id`.
- `media_asset_id`.
- `position`.
- `association_rule`: `same_message`, `explicit_group`, `reply`, `time_burst`, or `manual`; E2's `explicit_group` value is preserved without remapping.
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
- `normalizer_version`.
- `scope_version`.
- `request_version`.
- `provider`.
- `provider_result_id`: nullable.
- `point`: nullable PostGIS point.
- `display_name`: nullable.
- `precision`.
- `confidence`.
- `within_scope`: nullable.
- `response_json`: redacted provider response or diagnostic subset.
- `attribution_text`.
- `attempted_at`.
- `expires_at`: nullable.
- `error_code`: nullable.

`query_hash` covers provider, normalizer/scope/request versions, and the normalized query. Repeated successful queries use that cache entry unless an explicit re-geocode/version change is requested.

### GeocodeMissClaim

Coordinates cross-process ownership of an identical cache miss before a provider call.

Fields:

- `query_hash`: unique.
- `owner_id`.
- `fencing_token`.
- `claimed_at`, `lease_expires_at`.
- `completed_geocode_result_id`: nullable.

The claim is acquired atomically in a short transaction. Provider I/O occurs after that transaction commits. Non-owners wait/recheck within a bound; only an expired claim can be taken over with a higher fencing token. Healthy concurrency plus bounded takeover is the guarantee: under timeout, crash, or lease expiry an ambiguous retry may still occur, and those outcomes must reconcile to one durable cache result rather than promising an impossible at-most-once network call.

### LocationGeocodeSelection

Records the selected result and append-only review lineage for a location.

Fields:

- `id`: UUID.
- `location_id`.
- `geocode_result_id`: nullable for a transition to unresolved.
- `from_state`, `to_state`.
- `reason_code`.
- `actor_type`, `actor_id`: actor ID nullable for a versioned automatic policy.
- `review_policy_version`.
- `selection_version`.
- `decided_at`.

The current `Location.selected_geocode_result_id`, `point`, `precision`, `confidence`, `review_status`, and `out_of_scope` change together with the latest selection event in one transaction. Acceptance cannot be inferred from provider success, and a new decision appends lineage rather than overwriting the prior event.

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
- B-tree on `OfferSource.source_message_id` and unique `(offer_id, source_message_revision_id)` for revision-anchored provenance.
- B-tree on `ContactPoint.offer_id`; keyed fingerprint uniqueness scoped to offer/type where appropriate.
- Unique B-tree on normalized `User.username_normalized`.
- Unique B-tree on `UserSession.token_hash` plus indexes on user/expiry/revocation.
- B-tree on `ContactReveal.user_id`, `offer_id`, and `revealed_at` for rate limiting/audit retention.
- B-tree on `AdminAuditEvent.owner_user_id`, `target_user_id`, and `occurred_at`.
- Unique B-tree on `GeocodeResult.query_hash`; the digest includes provider and all cache-key versions.
- Unique B-tree on `GeocodeMissClaim.query_hash` plus lease-expiry support for bounded takeover.
- B-tree on `LocationGeocodeSelection(location_id, selection_version)` with uniqueness per version and a reference index on `geocode_result_id`.
- Unique B-tree on `MediaAsset(source_message_id, source_ordinal)`, the normalized `MediaDispositionAttempt` replay key plus `attempt_number`, `MediaDerivative(media_asset_id, variant)`, and `MediaDerivativeAttempt(media_asset_id, variant, attempt_number)`.
- Unique B-tree on physical media `(storage_backend, storage_class, checksum_sha256, byte_size)` plus reference indexes on `stored_object_id`; storage-class-aware references enforce restricted originals for assets and public objects for derivatives.

Index additions require an observed query and `EXPLAIN ANALYZE` evidence; avoid indexing every nullable parsed column up front.

## Field-level extraction provenance

`OfferSource.extraction_json` stores provenance in a stable shape:

```json
{
  "price": {
    "value": {"min_minor": 56000000, "max_minor": 56000000, "currency": "PLN"},
    "rule": "price_dash_v2",
    "confidence": 0.98,
    "source_start": 17,
    "source_end": 26
  }
}
```

Every provenance `start`/`end` pair, including `source_start`/`source_end`, anchors through `OfferSource.source_message_revision_id` to the exact preserved flattened E2 `RawMessage.text` string stored by that immutable revision. No Unicode normalization, case folding, transliteration, whitespace cleanup, or other mutation may occur before slicing. Offsets are zero-based half-open Python `str` offsets—Unicode code-point indices with the invariant `preserved_text[start:end]`—never UTF-8 byte offsets or UTF-16 code-unit offsets. Multilingual tests must slice the preserved Polish/Cyrillic text and supplementary characters exactly as Python does; combining marks remain separate code points when present. The extracted source text itself is not copied into `extraction_json`. This structure is internal. Public responses may expose a coarse `verified`, `parsed`, or `uncertain` indicator but not parser internals by default.
