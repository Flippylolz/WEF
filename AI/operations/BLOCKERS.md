# Overnight Blocker Log

This append-only log records blockers that could not be safely resolved autonomously. Resolved items remain for audit with their resolution evidence.

## Active blockers

### B-002: Production HTTPS/authentication gate

- Impact: registration, sessions, owner administration, and contact reveal must remain disabled on interim HTTP port 3100.
- Current state: the router forwards 3100; standard HTTPS/domain certificate routing is not approved/configured.
- Needed from owner: confirm the public HTTPS hostname/ports when auth scope is ready.
- Safe workaround: deploy anonymous browsing/API only.

### B-003: Telegram client credentials/session

- Impact: live channel ingestion cannot run.
- Current state: public channel URL is known, but Telegram API ID/hash and an authorized
  Telethon session are not available. The GitHub Actions secret inventory checked on
  2026-08-13 contains no Telegram credential/session names.
- Needed from owner: provide credentials later through GitHub secrets, never chat/repository files.
- Safe workaround: use synthetic/fake-client fixtures and the historical adapter for
  deterministic implementation checks; keep the production worker disabled.

### B-004: Recurring production geocoder revalidation

- Impact: live recurring geocoding cannot be enabled yet.
- Current state: Geoapify is the initial free recommendation; E3-T3 remains an external
  prerequisite and E8-T4 revalidation remains required before recurring live ingestion.
- Needed from owner: none for the synthetic MVP; later approve provider/quota after measured fixtures.
- Safe workaround: deterministic seeded coordinates/cache for the vertical MVP.

### B-005: GitHub-enforced branch protection unavailable

- Impact: reviews/checks are procedural rather than platform-enforced.
- Current state: accepted under ADR-017; GitHub Pro is out of scope.
- Needed from owner: none unless account/repository eligibility changes.
- Safe workaround: one-task PRs, stable CI checks, base-first stack merging, and main-SHA deploy verification.

## Resolved during overnight work

### R-003 / B-001: Stacked PRs merged

- Resolution: the ordered task stack and [roll-up PR #4](https://github.com/Flippylolz/WEF/pull/4) reached `main`; every task PR through [E7-T4 PR #19](https://github.com/Flippylolz/WEF/pull/19) is merged.
- Evidence: integrated `main` SHA `ad4d6de` contains the stack and passed all CI jobs in [run 31726996540](https://github.com/Flippylolz/WEF/actions/runs/31726996540).

### R-004 / B-006: Hosted Actions recovered

- Resolution: hosted CI, immutable image publication, and verified deployment now start and complete successfully.
- Evidence: all four CI jobs passed in [run 31726996540](https://github.com/Flippylolz/WEF/actions/runs/31726996540), and the production release completed in [run 31726996659](https://github.com/Flippylolz/WEF/actions/runs/31726996659).

### R-001: HTTPS Git authentication failed

- Resolution: verified the existing GitHub SSH identity and changed `origin` to `git@github.com:Flippylolz/WEF.git`.

### R-002: Empty GitHub repository had no PR base

- Resolution: owner selected a minimal README bootstrap commit on `main`, followed by the documentation and E1-T1 PR layers.
