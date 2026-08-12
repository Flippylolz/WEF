# Product Quality

## Quality attributes

### Performance

- The first useful map and controls should render within 2.5 seconds on a typical broadband mobile connection, excluding third-party tile outages.
- A filtered map response for the Warsaw viewport should target a 500 ms server response at the 95th percentile under expected MVP load.
- Map responses contain summaries, not full source text or full media arrays.
- Images are lazy-loaded and appropriately sized.

### Accessibility

- Core filtering and result inspection must be keyboard operable.
- Controls have accessible names and visible focus states.
- Color is not the only indicator of market type, confidence, or selection.
- Dialogs, drawers, and galleries manage focus correctly.
- Target WCAG 2.2 AA for the public flows.

### Responsive support

- Support current evergreen Chrome, Safari, Firefox, and Edge.
- Provide a usable layout from 360 px viewport width upward.
- If WebGL is unavailable, show a clear map-unavailable state and retain list/filter access.

### Language

- English is the initial interface language.
- Every user-visible interface string, including validation/auth/error text, is referenced through an i18n key rather than hardcoded in a component.
- Original Telegram source text remains in its source language except for server-side contact masking.
- Polish, Russian, and Ukrainian translations can be added without changing component contracts.

### Privacy and safety

- Phone numbers and personal contacts in source text are potential personal data.
- Anonymous APIs and pages mask phone numbers and Telegram handles.
- Unmasked contacts require an active logged-in account, a separate no-store backend call, per-user rate limits, and an account-linked audit record.
- A formal privacy notice/retention policy is out of scope, so the reveal audit is minimized to user/offer/request/outcome/timestamp and excludes contact values, IP addresses/hashes, and user-agent data.
- Logs must not contain full source posts, contact values, secrets, or Telegram session strings.

## MVP acceptance criteria

- A visitor can open Warsaw, apply every defined filter, share the resulting URL, and see only locations with at least one matching offer.
- A visitor can select a pin, inspect related dated offers and images, and open a verified Telegram source link when configured.
- An anonymous visitor sees only masked contacts; an active logged-in user can explicitly reveal a contact, and the backend records the user/offer event without logging the value or network fingerprint.
- The bootstrapped owner can administer users/password resets/sessions and inspect reveal audits without access to password hashes, session tokens, or contact values.
- Development posts and unit offers at one normalized place appear under one pin.
- Every visible offer displays its source publication date and avoids an unsupported availability claim.
- Out-of-area, unparsed, ungeocoded, duplicate, and missing-media records are reported rather than silently lost.
- The experience remains usable on mobile and with keyboard-only input.
- Map attribution is visible and production secrets or local media paths never reach the public API.
- The interface defaults to English and has no hardcoded user-facing component strings outside the i18n catalog.
