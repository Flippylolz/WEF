---
schema: ai-workflow/spike@1
epic: E18
title: "Owner location management and verification research"
status: approved
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-021
domain_docs:
  - ../../ingestion/GEOCODING.md
  - ../../security/AUTH_ADMIN_CONTACTS.md
  - ../../architecture/SYSTEM.md
proposed_task_ids:
  - E18-T1
  - E18-T2
approval:
  required_role: owner
  status: approved
  decided_by: owner
  decided_at: "2026-08-30T11:03:58Z"
  approved_revision: 1
  evidence: "ZCode session owner instruction on 2026-08-30: implement this epic; PR merges are allowed after the CI is green; deployment health must be verified after merges"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Owner location management and verification research

## Question

How should the owner admin console expose every canonical location's review state so
the owner can browse all locations (not only pending ones), inspect the offer data
behind each address, and manually set, accept, reject, or re-open each map point —
without changing the public API contract or the database schema?

## Context and constraints

- Locations carry the uncertainty surface already: `locations.review_status`
  (`accepted`/`needs_review`/`rejected`/`ungeocoded`), nullable PostGIS `point`,
  `precision`, `confidence`, `out_of_scope`, with
  `ck_locations_accepted_public_point` requiring accepted rows to have an in-scope
  point (`apps/backend/src/wef_backend/features/catalog/infrastructure/models.py`).
- `location_geocode_selections` is the append-only decision lineage
  (`from_state`/`to_state`, nullable `geocode_result_id`, `reason_code`,
  `actor_type`/`actor_id`, monotonic `selection_version`); `SelectionReason`
  already defines `manual_accept`, `manual_reject`, and `manual_unresolve`
  (`features/ingestion/domain/geocoding.py`), and
  `SQLAlchemyAcceptPendingGeocodePinsAdapter` is the canonical transition recipe
  (latest-selection row-number subquery, lineage append, location update).
- The review policy `review_geocode_result` fails closed (provider error →
  `ungeocoded`; outside the Warsaw bbox → `needs_review` + `out_of_scope`;
  non-building/street precision → `needs_review`; confidence < 0.80 →
  `needs_review`; else `accepted`); `within_warsaw` is the versioned scope check.
- The owner console is the server-rendered Starlette Admin mount at `/admin`
  (ADR-016), deliberately outside OpenAPI (`AI/contracts/OPENAPI.md`); views are
  `CustomView`s (`UsersAdminView`, audit views) guarded by `OwnerAuthProvider`
  (owner session) and `AdminMutationGuardMiddleware` (same-origin + rate limit on
  mutations), with CSRF via `csrf_input` and audit events through `AdminService`.
- Offers hold the verification evidence: `offers.source_text_excerpt` (≤280 chars),
  price/area/rooms ranges, visibility, `published_at`, keyed by `location_id`
  (`features/catalog/infrastructure/models.py`).
- `starlette_admin.BaseAdmin` accepts `static_dir` (mounted at `/admin/static`,
  checked before built-in assets), and `CustomView` routes may return any Starlette
  `Response`, including a complete standalone HTML document.
- Governance: backend authoritative, frontend renders generated contracts
  (ADR-012); no production dependencies without owner approval (`AGENTS.md`);
  admin mutations are owner-only and audited (ADR-016); geocoding stays cached and
  provider-neutral (ADR-021).

## Research method

Read the catalog/ingestion domain and infrastructure models, the geocoding review
policy, the admin feature (mount, auth, guards, views, application interactors,
SQLAlchemy audit store), the batch-accept adapter, composition wiring, admin HTTP
tests, and the installed `starlette-admin` package (route/static machinery).
Verified `geocode_result_id` nullability and the accepted-point check constraint in
the models. No code, scripts, or prototypes were executed; outputs are Markdown only.

## Evidence

- Verified: `LocationRow` fields and constraints as above; `LocationGeocodeSelectionRow.geocode_result_id`
  is nullable (`ondelete="RESTRICT"`), so a manual pin without a provider result
  needs no migration.
- Verified: `AdminService` is a frozen dataclass of interactors assembled in
  `composition.py`; the admin audit store pattern (protocol in application,
  SQLAlchemy adapter in admin infrastructure importing cross-feature infrastructure
  models) already imports `contacts.infrastructure.models`, so importing catalog and
  ingestion models from admin infrastructure follows an existing precedent.
- Verified: `UsersAdminView` renders HTML tables with per-row POST forms carrying
  `csrf_input`, redirecting 303 back to the page; tests drive the real app with fake
  services and scrape CSRF tokens (`tests/test_admin_api.py`).
- Verified: `starlette_admin` mounts `static_dir` at `/admin/static` and
  `CustomView` routes support GET/POST returning arbitrary responses.
- Verified: offers reference locations by `location_id` with the raw source text
  excerpt retained, so the console can show the operator "why this address exists".
- Uncertainty (accepted constraint): tile rendering depends on outbound access to
  the OSM raster tile CDN at owner-browser runtime; the console already presumes
  owner-network access and geocoding providers are called server-side today. No
  tile/CDN dependency enters the backend process.

## Options considered

1. **Starlette Admin `CustomView` page with a dependency-free map picker**
   (selected). Reuses the existing owner-only console: auth, CSRF, mutation guard,
   audit, and HTML-table conventions already exist; a full-page GET route returns a
   standalone HTML document (scripts execute reliably, unlike HTML injected into the
   admin layout), and `static_dir` serves the picker script. Zero new dependencies;
   OSM raster tiles are loaded by the owner's browser. Cost: a small hand-written
   slippy map (~150 lines: Web Mercator tile grid, drag pan, integer zoom,
   click-to-place). Risk: bespoke map code needs browser verification — mitigated by
   keeping the interaction surface minimal and the lat/lng inputs authoritative.
2. **Next.js owner route reusing maplibre-gl.** Gives a polished picker with
   existing frontend deps, but creates the first frontend admin section: new
   owner-gated JSON API endpoints, OpenAPI contract export + regeneration, guard
   wiring, i18n, e2e. Rejected for this scope: a much larger contract/architecture
   surface for the same owner-only workflow, and it splits the admin panel across
   two stacks.
3. **Read-only list + CLI (status quo plus table).** The CLI batch-accept exists,
   but per-location manual placement on a map is impossible from a CLI, and the
   owner explicitly asked to set points manually. Rejected.
4. **starlette-admin generated `ModelView` for `locations`.** CRUD for free, but
   the geometry column, lineage append requirement, in-scope validation, and audit
   integration would all be bypassed or fight the abstraction. Rejected.

## Recommendation

Build the feature as two promoted tasks inside the admin feature, keeping every
transition on the lineage recipe:

- `ListLocations` (status filter defaulting to the pending queue
  `needs_review`+`ungeocoded`, plus `accepted`/`rejected`/`ungeocoded`/
  `needs_review`/`all`, address substring search, limit 100 newest-activity-first),
  `GetLocationForEdit` (detail incl. latest offers and candidate result),
  `AcceptPlaceCandidate`, `RejectPlace`, `UnresolvePlace`
  (`to_state=needs_review`, `manual_unresolve`), and `SetPlacePoint` (any
  from-state, `precision=building`, `confidence=1.00`, `manual_accept`,
  `geocode_result_id=null`, coordinates validated with `within_warsaw`).
- New `SQLAlchemyLocationAdminStore` in admin infrastructure implementing the
  reader/decision ports; every decision appends a lineage row
  (`actor_type="operator"`, `actor_id=<owner id>`, `selection_version+1`) inside
  one transaction and records an `AdminAuditEvent` (`target_type="location"`).
- `LocationsAdminView` at `/admin/places` (menu "Locations"): filter tabs, search
  box, table with per-row actions, and a full-page set-point picker route showing
  offer data beside a vanilla-JS slippy map served from the admin `static_dir`.

Consequences: no schema or contract changes; `main`-branch console gains one more
owner-only, audited page; manual placements are traceable and reversible through
the lineage and Unresolve; map eligibility keeps its invariants (accepted implies
in-scope point).

## Proposed task boundaries

- **E18-T1 (backend)**: ports, interactors, SQLAlchemy store, `AdminService`/
  composition wiring, unit + PostGIS integration tests. No HTML.
- **E18-T2 (console)**: `LocationsAdminView`, set-point picker page + static JS,
  action routes, admin HTTP tests, `AI/` documentation updates. Depends on E18-T1.

## Risks and open questions

- Bespoke picker JS correctness (pan/zoom/marker math) — verified manually in the
  browser during E18-T2; lat/lng inputs remain the authoritative fallback.
- Owner confusion between existing point and candidate — mitigated by rendering
  distinct markers and prefilling the form from the existing point.
- Large pending queues — list is capped at 100 rows like every admin view; search
  and filters are the navigation tools. Pagination is out of scope.
- Non-ASCII address search must behave case-insensitively for Polish diacritics;
  `LOWER()` substring matching is sufficient for owner triage (exact folding is not
  a goal here).

## Invalidation triggers

- A change to `locations`/`location_geocode_selections` schema or the review
  policy version that moves decision authority away from the lineage table.
- Replacing the Starlette Admin console with a different admin stack (ADR-016
  revision).
- Owner requiring bulk/programmatic edits beyond single-location operations, or
  editing of non-coordinate location fields (display name, district), which this
  epic explicitly excludes.

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Evidence and uncertainty are distinguishable.
- [x] Affected decisions and domain documents are linked.
- [x] Proposed task boundaries and dependencies are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner recorded the decision in the YAML `approval` object on 2026-08-30
(ZCode session owner instruction; see `evidence`). Approval of this spike revision
permits task refinement/promotion and implementation planning; it does not permit
code.
