# Authentication, Administration, and Contact Reveal

## Product boundary

All map browsing, filtering, location/offer details, dated posts, media, and verified Telegram source links remain available anonymously.

Authentication is required only for explicitly restricted actions. The first restricted action is revealing masked phone numbers or Telegram contact handles.

## Initial authentication model

Use in-house username/password registration in FastAPI:

- Public self-registration with a unique normalized username.
- Login and logout.
- Change password.
- View minimal account/session state.
- Revoke current/all sessions.
- Disable/delete own account.
- Owner-forced password reset when a user cannot sign in.

Email address collection, email verification, transactional email, and self-service forgotten-password recovery are out of scope.

FastAPI Users with SQLAlchemy remains the recommended authentication foundation, wrapped by the `identity` module:

- Project was active and unarchived when checked on 2026-08-12.
- Latest release observed: v15.0.5, published 2026-03-27.
- It provides password hashing through `pwdlib`, cookie transport, and database token strategy.
- Project-owned routers/schemas adapt its email-oriented defaults to the accepted username-only public contract.

If adapting FastAPI Users requires maintaining more custom surface than it removes, [E0-T2](../epics/E0-architecture-dependency-spike/tasks/E0-T2-execute-and-lock-the-architecture-proof.md) must replace it with a small project-owned identity implementation using `pwdlib[argon2]`; public API/application contracts do not change.

## Identity meaning

A self-selected username is a pseudonymous account identifier. It does not prove a legal name, email, phone ownership, or real-world person.

The contact-reveal audit answers “which account requested this contact?” It does not claim “which verified person requested this contact?”

## User model

Minimum fields:

- `id`: UUID.
- `username_normalized`: unique, never mutable after registration.
- `username_display`: validated display form.
- `hashed_password`.
- `role`: `user` or `owner`.
- `is_active`.
- `must_change_password`.
- `created_at`, `updated_at`.
- `last_login_at`: nullable.
- `disabled_at`, `deleted_at`: nullable.

Do not collect email, name, phone, address, or social profile initially.

Passwords:

- Hash with Argon2 using current `pwdlib` recommended parameters.
- Enforce server-side minimum and maximum input length.
- Never log passwords, temporary passwords, session tokens, or password hashes.
- User password change or owner-forced reset revokes all existing user sessions.
- An owner reset sets `must_change_password=true`; the temporary password can only establish the restricted change-password flow.

## Owner bootstrap

The owner role is fixed application authorization, but owner credentials are never hardcoded in source, migrations, images, or committed configuration.

Bootstrap flow:

1. Store one-time `BOOTSTRAP_OWNER_USERNAME` and `BOOTSTRAP_OWNER_PASSWORD` in GitHub Actions secrets.
2. First deployment runs an idempotent `admin bootstrap-owner` command.
3. The command succeeds only when no owner exists, hashes the password with Argon2, and records an admin audit event.
4. Remove/rotate the bootstrap password secret immediately after success.
5. Later owner password changes occur through the authenticated owner flow or an explicit console recovery runbook.

The owner cannot demote/delete the last active owner through the admin UI.

## Session model

Use opaque, database-backed session tokens rather than long-lived stateless browser JWTs:

- Random token returned only in a cookie.
- Store only a secure hash of the token in PostgreSQL.
- Associate user, creation, expiry, last-used time, and revocation.
- Logout deletes/revokes the session.
- Password change/reset, account disable/delete, and “logout all” revoke all sessions.

Cookie requirements in production:

- `HttpOnly`.
- `Secure`.
- `SameSite=Lax` for the public app; the admin session may use `Strict` after flow testing.
- Host-only cookie where possible.
- Explicit short/renewable lifetime.
- No token access from browser JavaScript.
- Separate cookie names/scopes for public and admin sessions if Starlette Admin cannot safely reuse the public session.

The interim plain-HTTP deployment cannot safely authenticate users or owners. Registration, login, admin console, and contact reveal remain disabled until HTTPS.

## CSRF and abuse controls

Cookie-authenticated state-changing requests require:

- Synchronizer/double-submit CSRF token or equivalent reviewed defense.
- Same-origin `Origin`/`Referer` validation.
- JSON-only content type for API mutations.
- Explicit protection for server-rendered admin forms/actions.
- Per-account rate limits for registration, login, password change/reset, and contact reveal.
- Coarse edge-level abusive-IP throttling without persisting an IP hash in application audit data.

Return generic login failures to reduce username enumeration. Registration may report that a chosen username is unavailable because users must select another.

## Public masking

The anonymous offer/detail API never returns an unmasked contact in:

- Parsed fields.
- Original/source text.
- Search/map payloads.
- HTML metadata.
- Logs or analytics.

Masking happens server-side before serialization. Client-side CSS/JavaScript masking is not security because the value would already be downloadable.

Examples:

- Phone: `+48 ••• ••• 42` or fully masked when too short.
- Telegram handle: `@ir••••••`.

Store raw source text internally for lineage and derive a public masked rendering. If a phone/handle cannot be masked reliably, omit that span from public rendering.

## Contact reveal endpoint

Use a separate mutation:

```text
POST /api/v1/offers/{offer_id}/contacts/reveal
```

Requirements:

- Authenticated active user whose `must_change_password` is false.
- CSRF/origin validation.
- Offer is publicly visible.
- Per-user rate limits.
- Returns only contact fields for that offer, not unrestricted raw source text.
- `Cache-Control: no-store, private`.
- Never placed in server/CDN/browser shared cache or static Next.js output.
- Response is rendered in memory and not persisted by the frontend.

Do not reveal merely because a caller can guess a source message/offer UUID.

## Reveal audit

Create `ContactReveal` with:

- `id`: UUID.
- `user_id`.
- `offer_id`.
- `source_message_id` or contact-set version.
- `revealed_at`.
- `request_id`.
- `outcome`: allowed, rate-limited, forbidden, or unavailable.

Do not store the raw contact, IP address/hash, or user-agent in the audit row or logs.

Audit access is owner-only and not exposed through the public API. A privacy notice and formal retention policy are out of scope; data minimization is therefore mandatory. Retention/deletion can be added later without changing reveal authorization.

Authenticated visit and viewed-offer history stores only account, public offer,
timestamps, a client-generated visit UUID, and an aggregate count. It stores no
IP address, user-agent, raw source text, or contact value. Anonymous visits stay
in browser storage. Account deletion cascades both history tables, visit rows
are bounded to the latest 50 per account, and list responses omit offers that
are no longer public.

## ActiveAdmin-like owner console

Use Starlette Admin as the initial server-rendered administration foundation:

- Current release observed on 2026-08-12: 0.17.1, published 2026-07-20; repository active on 2026-08-10.
- Supports SQLAlchemy, custom `AuthProvider`, per-view permissions, custom views/actions, and role checks.
- FastAPI Admin is rejected because it requires TortoiseORM and Redis.
- SQLAdmin is a fallback; its documented session defaults require explicit hardening and its stock login form lacks CSRF protection.

Mount the console at `/admin` only after HTTPS. It is not part of the public OpenAPI contract and does not expose generic CRUD over sensitive models.

Owner capabilities:

- List/search users by username/status/date.
- Disable/reactivate users.
- Revoke one/all user sessions.
- Force-reset a password to a temporary value and require change on next login.
- View reveal audits by user/offer/date/outcome.
- View admin action history.
- Browse every canonical location under `/admin/places` with review-status
  filters (pending queue by default) and address search (E18).
- Place a location's map point manually from a full-page map picker showing the
  retained offer evidence, accept an in-scope geocode candidate, reject a
  location, or send a decided location back to review (E18). Every decision
  appends a `location_geocode_selections` lineage row
  (`actor_type="operator"`, `actor_id=<owner>`) and an admin audit event
  (`target_type="location"`).

Not allowed:

- View/edit password hashes or session tokens.
- View contact ciphertext/plaintext through generic model forms.
- Reveal a contact through the audit screen.
- Edit non-coordinate location fields (display name, district, normalized
  address) or apply bulk location changes (E18 scope boundary).
- Change immutable usernames.
- Delete/demote the last owner.
- Perform generic writes directly from a Starlette Admin `ModelView`.

Admin actions invoke owner-authorized interactors such as:

- `DisableUser`.
- `ReactivateUser`.
- `RevokeUserSessions`.
- `ForceResetUserPassword`.
- `ListContactRevealAudit`.

Each mutation creates `AdminAuditEvent` with owner user ID, target user/entity, action, timestamp, request ID, and outcome. It never stores passwords, tokens, or contact values.

Starlette Admin security is project-owned:

- Custom auth provider delegates credential/session checks to the identity application service.
- Every view/action checks the `owner` role server-side.
- Secure/HttpOnly/SameSite cookie flags are explicit.
- Login and mutation forms/actions receive CSRF protection and origin validation.
- Login/admin actions are rate-limited.
- Responses use `Cache-Control: no-store`.
- Admin routes are covered by authorization/CSRF/IDOR tests.

## Anonymous, user, and owner authorization

Anonymous:

- Read map locations, facets, offers, masked source text, media, and Telegram source links.
- Register and login after HTTPS.

User:

- Everything anonymous users can do.
- Reveal contacts within rate limits.
- Change password, view/revoke own sessions, and disable/delete own account.

Owner:

- Everything a user can do.
- Enter `/admin`.
- Execute only the audited user/session/password-reset/audit actions listed above.
- No automatic access to plaintext passwords, session tokens, or contacts.

Authorization is enforced in FastAPI/application interactors. Hiding a frontend/admin control is not authorization.

## Frontend behavior

- All public authentication/contact strings are English i18n keys.
- A masked contact has an accessible `Reveal contact` action.
- Anonymous click opens sign-in/register and returns to the selected offer.
- `must_change_password` users are directed only to password change/logout.
- Successful reveal requires an explicit click and is not triggered by hover, page load, prefetch, or crawler.
- Loading, rate-limit, forbidden, and unavailable states do not leak hidden contact existence beyond the masked public representation.
- Starlette Admin owns owner-console HTML; Next.js does not duplicate admin CRUD/business logic.

## Security tests

- Username normalization/uniqueness/enumeration behavior.
- Password hash/input policy and temporary-password forced-change flow.
- Login/registration/rate-limit behavior.
- Session fixation, rotation, logout, revocation, disable/delete.
- Cookie flags under HTTP development and HTTPS production.
- CSRF/origin rejection for API and admin forms/actions.
- Anonymous/disabled/forced-change users cannot reveal.
- Masked APIs/source text contain no raw phone/handle.
- Reveal response has no-store headers.
- Reveal audit contains user/offer/request/outcome but no contact/IP/user-agent.
- Contact reveal IDOR attempts fail.
- Non-owner cannot access any admin route/action.
- Owner actions use interactors and produce redacted admin audit events.
- Owner bootstrap is one-time/idempotent and no default credential remains.

## Launch gates

Anonymous browsing can launch before authentication.

Registration, login, admin, and contact reveal remain disabled until:

- HTTPS is active.
- Registration/login/change-password/session-revocation flows pass tests.
- One-time owner bootstrap is complete and its secret removed/rotated.
- Starlette Admin authentication, owner authorization, secure cookies, CSRF, rate limits, and admin audit pass tests.
- Masking is tested against source fixtures.
- Reveal rate limits/audit behavior are confirmed.

[E7-T10](../epics/E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md) provides the verified live Nginx HTTPS origin after E7-T8/E7-T9 topology and automation; [E7-T7](../epics/E7-production-delivery/tasks/E7-T7-enable-production-registration-and-contact-reveal.md) enabled production registration, sessions, owner `/admin`, and contact reveal on that origin (PRs #123/#124/#125).
