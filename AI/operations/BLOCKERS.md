# Overnight Blocker Log

This append-only log records blockers that could not be safely resolved autonomously. Resolved items remain for audit with their resolution evidence.

## Active blockers

### B-001: Stacked PRs are not merged

- Impact: code, CI, and deployment workflows prepared in descendant branches are not active on `main`; main-only autodeploy cannot run.
- Current state: PRs #1–#3 were merged, but #2 and #3 targeted parent branches after those parents had already merged. [Roll-up PR #4](https://github.com/Flippylolz/WEF/pull/4) now safely propagates their changes to `main`; [E0-T1 PR #5](https://github.com/Flippylolz/WEF/pull/5) is its descendant.
- Needed from owner: review/merge PR #4, then continue merging/retargeting descendants base-first, or explicitly authorize autonomous merges.
- Safe workaround: continue preparing/testing descendants against their parent branches under ADR-018.

### B-002: Production HTTPS/authentication gate

- Impact: registration, sessions, owner administration, and contact reveal must remain disabled on interim HTTP port 3100.
- Current state: the router forwards 3100; standard HTTPS/domain certificate routing is not approved/configured.
- Needed from owner: confirm the public HTTPS hostname/ports when auth scope is ready.
- Safe workaround: deploy anonymous browsing/API only.

### B-003: Telegram client credentials/session

- Impact: live channel ingestion cannot run.
- Current state: public channel URL is known, but Telegram API ID/hash and an authorized Telethon session are not available.
- Needed from owner: provide credentials later through GitHub secrets, never chat/repository files.
- Safe workaround: use synthetic fixtures and later the historical local export.

### B-004: Recurring production geocoder revalidation

- Impact: live recurring geocoding cannot be enabled yet.
- Current state: Geoapify is the initial free recommendation; E8-T4 revalidation remains required before recurring live ingestion.
- Needed from owner: none for the synthetic MVP; later approve provider/quota after measured fixtures.
- Safe workaround: deterministic seeded coordinates/cache for the vertical MVP.

### B-005: GitHub-enforced branch protection unavailable

- Impact: reviews/checks are procedural rather than platform-enforced.
- Current state: accepted under ADR-017; GitHub Pro is out of scope.
- Needed from owner: none unless account/repository eligibility changes.
- Safe workaround: one-task PRs, stable CI checks, base-first stack merging, and main-SHA deploy verification.

## Resolved during overnight work

### R-001: HTTPS Git authentication failed

- Resolution: verified the existing GitHub SSH identity and changed `origin` to `git@github.com:Flippylolz/WEF.git`.

### R-002: Empty GitHub repository had no PR base

- Resolution: owner selected a minimal README bootstrap commit on `main`, followed by the documentation and E1-T1 PR layers.
