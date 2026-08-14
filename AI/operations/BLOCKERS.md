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

### B-008: Hosted geocoder credentials and reviewed Warsaw fixture

- Impact: the hosted Geoapify/LocationIQ comparison cannot run and no provider can be selected/activated from repository evidence. E3-T3 cannot complete without that comparison.
- Current state: E3 spike revision 3 is approved; implementation-plan revision 3 awaits owner approval. ADR-021 remains proposed and D-002 remains deferred. No provider key or owner-reviewed redacted Warsaw fixture is stored in the repository.
- Needed from owner: later provide keys through approved secret channels and approve a redacted fixture; never put credentials or private source addresses in Git/chat.
- Safe workaround: keep CI network-free and treat provider terms/quality/selection as unresolved. Missing inputs are not acceptance evidence and cannot replace the hard E3-T3 hosted-comparison gate.

## Resolved during overnight work

### R-005 / B-007: E3 complete-import upstream audit

- Resolution: E2-T5 completed the authoritative export audit and merged through [PR #42](https://github.com/Flippylolz/WEF/pull/42).
- Effect: E2-T5 no longer blocks E3-T5. E3-T5 is promoted/draft under `tasks/` with spike revision 3 satisfied; it remains non-actionable until implementation-plan revision 3 is approved and E3-T2/T3/T4 complete.

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
