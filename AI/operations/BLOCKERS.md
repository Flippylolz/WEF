# Overnight Blocker Log

This append-only log records blockers that could not be safely resolved autonomously. Resolved items remain for audit with their resolution evidence.

## Active blockers

### B-003: Telegram live acceptance evidence

- Impact: M4 cannot close without verified real entity/event delivery, gap reconciliation,
  and outage recovery evidence.
- Current state: API ID/hash and the first authorized string session are stored in gitignored
  local files and GitHub production secrets. Release `3ee56a5` created and started the
  production `telegram-worker` service on 2026-08-26. Do not paste session strings into chat
  or Git.
- Needed from owner: none for credential provisioning. Remaining work is to observe and record
  live entity/new/edit/delete behavior, reconcile gaps, and rehearse outage recovery.
- Safe workaround: historical adapter remains the source of truth if the worker is down.

### B-005: GitHub-enforced branch protection unavailable

- Impact: reviews/checks are procedural rather than platform-enforced.
- Current state: accepted under ADR-017; GitHub Pro is out of scope.
- Needed from owner: none unless account/repository eligibility changes.
- Safe workaround: one-task PRs, stable CI checks, base-first stack merging, and main-SHA deploy verification.

## Resolved during overnight work

### R-011 / B-004: Recurring production geocoder revalidation

- Resolution: E8-T4 retained Geoapify for recurring use after a 2026-08-21 pricing/terms recheck, resolved D-002, forbade public Nominatim for always-on jobs, and shipped defer/monitor contracts plus `wef-revalidate-recurring-geocoder` (AD-032).
- Effect: E8-T2/T3/T5 may proceed behind remaining Telegram secret and worker-enablement gates; paid Geoapify still needs a separate owner decision if free soft limits are exceeded.

- Resolution: E7-T7 enabled registration/sessions/admin/contact reveal on `https://2fa54e2405.duckdns.org` after E7-T10 HTTPS (PRs #123/#124/#125). Contact crypto keys in deploy; Uvicorn trusts forwarded proto; owner bootstrapped once then bootstrap secrets removed; `/admin` routed to API; `:3100` cannot hold Secure sessions; Forecast `:3000` unchanged.
- Effect: E7-T11 may proceed behind the remaining historical public-activation gate.

### R-009 / B-009: D-009 shared TLS hostnames and forwarding (E7-T10)

- Resolution: D-009 resolved WEF-only on `2fa54e2405.duckdns.org` (PR #119); plan revision 7 + tooling (PR #120/#121); live NUC cutover 2026-08-20 with production Let's Encrypt, HTTP→HTTPS redirect, renew dry-run, Forecast `:3000` unchanged.
- Effect: E7-T11 may proceed behind the remaining historical public-activation gate; anonymous HTTPS plus E7-T7 auth are live on the public WEF entry.

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
