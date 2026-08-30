# Product Experience

## MVP experience

### P-001: Map and grouped pins

- Open centered on Warsaw with a sensible city-wide zoom.
- Show one pin per normalized location/development that has valid coordinates and at least one offer matching the current filters.
- Cluster pins at lower zoom levels.
- Selecting a cluster zooms to its members.
- Selecting a pin opens a side drawer on desktop and a bottom sheet on mobile.
- A selected location shows its development name when known, normalized address, geocoding confidence, matching offer count, and related dated offers.
- An ungeocoded offer remains accessible to maintainers through import reports but is not placed at an invented coordinate.

### P-002: Offer summaries and details

Each offer summary should show fields only when they were parsed with sufficient confidence:

- Source publication date and time.
- Offer type: development-level or individual unit.
- Primary or secondary market.
- Apartment price or price range in the source currency.
- Parking and storage prices when parsed, including an explicit included-in-price state.
- Area or area range in square metres.
- Room count.
- Floor.
- Delivery period.
- Source text excerpt.
- Photo thumbnail and media count.

Selecting an offer opens its full detail, public masked source text, complete media gallery, extraction caveats, and source action.

The date label must say `Published` or an equivalent localized phrase. The interface must not label imported records as `Available`, `For sale now`, or `Active` without a future authoritative status.

### P-003: Filters

The MVP supports:

- Minimum and maximum price.
- Minimum and maximum area.
- Room count, with multiple values selectable.
- Warsaw district, with multiple values selectable.
- Primary or secondary market.
- Publication date range.
- Content type: development posts, unit offers, or both.

Filter semantics:

- A location pin remains visible when at least one related offer satisfies every active filter.
- Ranges overlap inclusively. For example, a development with a parsed price range matches when its range intersects the requested range.
- Offers with an unknown value do not match a filter on that value, but remain visible when that filter is unset.
- The selected location drawer shows matching offers first and clearly states when additional non-matching related posts exist.
- `Clear filters` restores the default city view and both content types.
- Filter state is encoded in the URL so the view is reloadable and shareable.

### P-004: Map/list coordination

- Desktop shows a map and an accompanying results panel.
- Warsaw's 18 districts have clear labeled boundaries below the offer pins.
- Mobile prioritizes the map and opens results as a bottom sheet, with a control to switch to a full list.
- Hovering or focusing a result highlights its pin where pointer/keyboard behavior supports it.
- Changing the viewport refreshes results for that bounding box after a short debounce.
- The interface shows loading, empty, degraded-map, and API-error states without losing filter selections.

### P-005: Media

- Display optimized thumbnails first and load full images on demand.
- Preserve source aspect ratio.
- Provide keyboard-operable next/previous/close controls and useful alternative text based on known offer/location data.
- Video support may use the browser's native controls when a supported source is present.
- A missing file produces a placeholder and a logged diagnostic, not a broken layout.

### P-006: Telegram source links

- Store the source channel identity and message ID independently of the rendered URL.
- Show `Open in Telegram` only when the system can construct or store a verified link.
- Open external links in a new tab with safe external-link attributes.
- If no verified public link exists, show the source publication date and message ID without a dead link.
- Link behavior must work for both imported history and future live messages.

### P-007: Attribution and trust

- Display required OpenStreetMap/OpenFreeMap and selected geocoder attribution.
- Preserve the original source text internally for traceability and expose only its server-side masked public rendering.
- Mark fields that are inferred or low-confidence when they are shown.
- Do not expose internal file paths, credentials, ingestion errors, or Telegram session details to public clients.

### P-008: Registration and contact reveal

- All browsing remains anonymous.
- Provide in-house username/password registration, login/logout, password change, and session management as defined in [Authentication, administration, and contact reveal](../security/AUTH_ADMIN_CONTACTS.md); email and self-service recovery are out of scope.
- Public responses mask phone numbers and Telegram contact handles server-side.
- Clicking `Reveal contact` while anonymous opens sign-in/register and returns to the selected offer.
- Only an active logged-in user who is not awaiting a forced password change may reveal contacts through the separate backend endpoint.
- Every allowed/denied reveal is rate-limited and audited against the signed-in user without logging the contact value.
- An owner-only Starlette Admin console can disable/reactivate users, revoke sessions, force password reset, and inspect reveal audits through audited backend interactors.
- Contact reveal and owner administration are enabled only on the live HTTPS origin; the plain `:3100` rollback listener cannot establish production Secure-cookie sessions.

### P-009: AI-assisted owner catalog curation

- The owner-only Locations console can request a Groq-hosted GPT-OSS 20B review
  of one canonical place against its complete current source descriptions.
- The review reports whether the current display name, address, and Warsaw district
  are supported and may propose corrections with confidence, warnings, and source
  evidence references. Model output is advisory and never a verified fact by itself.
- Detected contacts are masked before source descriptions leave the application;
  raw Telegram payloads, media, contact values, account data, and unrelated places
  are never included.
- The owner sees a field-by-field current/proposed diff. No change is selected by
  default, and a separate explicit Apply action is required.
- The model cannot set coordinates, review state, visibility, city/country, hashes,
  or merge locations. Backend validators derive dependent fields and reject stale,
  expired, unsupported, invalid, or colliding proposals.
- Applying an address or district correction returns the place to `needs_review`;
  the existing manual picker or geocoder must verify its point before it is public.
- Every generate/apply outcome is rate-limited and audit-logged without prompt,
  response, raw source, contact, or secret content. Provider failure changes no
  place data or failed batch item and does not impair browsing or ordinary admin
  operations.
- The owner can preview a bounded offer cohort and submit **Start batch** once to
  fill eligible missing offer details automatically; no second confirmation is
  required per offer. Batch mode never overwrites an existing value and never
  changes content type, visibility, dates, identity, location/development, source
  text, contacts, or media.
- Automatic fill requires a unique exact evidence span in an immutable source
  revision, deterministic value validation, an unchanged offer/source snapshot,
  and an approved per-field quality gate. Ambiguous, conflicting, stale, invalid,
  or below-threshold proposals are skipped or retained for review without mutation.
- Every currently displayed AI-derived offer field has durable source/parser/run
  provenance. Offers containing one or more such fields expose
  `data_origin="ai_assisted"` and show an **AI-assisted data** badge; the badge is
  transparent provenance, not a verification claim.
- Owner-only parser-gap reports group AI outcomes by field and parser version and
  retain typed expected values plus exact source offsets. Parser replay can confirm
  or flag conflicts, but model output never changes parser code or fixtures without
  maintainer review.
