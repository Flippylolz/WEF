# Overnight Blocker Log

This append-only log records blockers that could not be safely resolved autonomously. Resolved items remain for audit with their resolution evidence.

## Active blockers

### B-003: Telegram live acceptance evidence

- Impact: M4 still cannot claim production passive edit/delete callback semantics.
  Live media acquisition through the shared pipeline is now verified (see
  [E8 live media production evidence](../epics/E8-telegram-live-ingestion/PRODUCTION_EVIDENCE.md)).
  Source completeness, gap repair, and truthful worker-health/outage behavior are no
  longer blocked.
- Current state: E15 release `7184cc2d67a` reconciled the 2026-08-27 incident through
  head `29335`. E8 release `b71c99f` (PR #243, deploy run `33420585501`) reconciled
  message IDs `29415`–`29434` on 2026-08-31 with bounded temp downloads, restricted
  originals, and public derivatives for all 20 IDs. Credentials, authorized session,
  channel identity, transport, consumer, reconciliation, database, and redacted log
  safety remain verified. Passive edit/delete watch is active on the NUC (15-minute
  cron via PR #250, log at `/home/nuc/wef/state/passive-event-check.log`). As of
  `2026-08-31T18:17Z` release `ab4f17a` remains aligned at head `29434` with
  `last_event_received_at` null. No real passive edit/delete callback has occurred yet.
  Exact redacted recovery evidence is in
  [E15 production recovery evidence](../epics/E15-telegram-ingestion-reliability/PRODUCTION_EVIDENCE.md).
- Needed from owner: no E15 action. Closing the residual blocker requires a safely
  observable real edit/delete sequence (organic or explicitly coordinated); do not
  create or alter source-channel posts without separate authority. When an event occurs,
  follow [B003 observation runbook](../epics/E8-telegram-live-ingestion/B003_OBSERVATION_RUNBOOK.md).
- Safe workaround: checkpoint polling remains the source-completeness boundary for new
  messages, while passive events remain the latency path. Operators use the redacted
  worker status for remote/local alignment. Absence-based polling never infers deletion,
  so production edit/delete claims remain withheld until E8 evidence exists.

## Resolved during overnight work

### R-012 / B-005: GitHub-enforced branch protection

- Resolution: the public repository became eligible and `main` branch protection was enabled on 2026-09-02 under ADR-023 with pull requests, resolved conversations, strict required CI, linear history, and force-push/deletion blocking. Approving reviews are not required while the owner is the sole maintainer, and repository-level native auto-merge is enabled.
- Effect: ordinary updates are platform-gated. The owner-only administrator bypass and merged-PR deployment verification remain audited defense-in-depth controls.

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
