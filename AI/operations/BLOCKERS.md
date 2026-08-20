# Overnight Blocker Log

This append-only log records blockers that could not be safely resolved autonomously. Resolved items remain for audit with their resolution evidence.

## Active blockers

### B-009: D-009 shared TLS hostnames and forwarding (E7-T10)

- Impact: live shared Nginx/Certbot cutover (E7-T10) can proceed once plan revision 7 is approved and WEF-only edge tooling lands; E7-T7/E7-T11 still wait on completed HTTPS.
- Current state (2026-08-20): [D-009](../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md) is **resolved** — WEF hostname `2fa54e2405.duckdns.org`; Forecast stays on public `:3000` only; Funbox forwards 80/443 to the NUC. Public `:80`/`:443` time out until Nginx binds (expected). Proposed [E7 plan revision 7](../epics/E7-production-delivery/PROPOSED_IMPLEMENTATION_PLAN-revision-7.md) awaits approval.
- Needed from owner: approve E7 implementation-plan revision 7 and authorize live E7-T10 WEF-only cutover.
- Safe workaround until cutover: anonymous HTTP on `:3100`; keep auth/admin/reveal disabled (B-002).
- Related: B-002 remains until E7-T7 after verified WEF HTTPS.

### B-002: Production HTTPS/authentication gate

- Impact: registration, sessions, owner administration, and contact reveal must remain disabled on interim HTTP port 3100.
- Current state: the router forwards 3100; standard HTTPS/domain certificate routing is not approved/configured. E7-T9 cutover automation is ready in-repo; live TLS still waits on B-009/D-009 then E7-T10.
- Needed from owner: resolve D-009 (hostnames/DNS/80+443 forwarding) when ready for shared TLS; E7-T7 enables sensitive features after that HTTPS gate.
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

### R-006 / B-008: Historical geocoder selection

- Resolution: the owner selected Geoapify for the historical import in merged [PR #59](https://github.com/Flippylolz/WEF/pull/59) after reviewing current pricing, rate, storage, attribution, and a successful bounded readiness call. LocationIQ is no longer a mandatory historical comparator.
- Effect: E3-T3 may complete after the revised E3 spike/plan gates are approved. E3-T5 owns Geoapify-only aggregate quality and manual-review evidence over private ignored inputs. D-002 and E8-T4 still gate recurring production use.

### R-005 / B-007: E3 complete-import upstream audit

- Resolution: E2-T5 completed the authoritative export audit and merged through [PR #42](https://github.com/Flippylolz/WEF/pull/42).
- Effect: E2-T5 no longer blocks E3-T5. E3-T2 and E3-T4 are done; revised E3-T3 completion and E3-T5 implementation await owner approval of spike/plan revision 4.

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
