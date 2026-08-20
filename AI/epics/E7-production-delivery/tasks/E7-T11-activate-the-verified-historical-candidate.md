---
schema: ai-workflow/task@1
id: E7-T11
epic: E7
title: "Activate the verified historical candidate publicly"
status: done
revision: 1
priority: P1
size: M
milestone: M3
dependencies: [E7-T6, E7-T7, E7-T10]
requirement_ids: [P-001, P-002, P-005, P-007]
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015, ADR-019, ADR-020]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T11-activate-the-verified-historical-candidate.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T15:40:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T15:40:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 9
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T15:40:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T15:40:00Z"
  evidence:
    - "E7-T6 | done | PRs #88–#104"
    - "E7-T10 | done | PR #121 + live HTTPS"
    - "E7-T7 | done | PRs #123/#124/#125/#126"
branch:
  required: true
  name: feat/E7-T11-activate-historical-candidate
  task_id: E7-T11
  one_task_only: true
  created_at: "2026-08-20T15:40:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/127"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-20T16:11:40Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/127"
  evidence:
    - "Tooling: merged https://github.com/Flippylolz/WEF/pull/127 (activation under deploy.lock) and https://github.com/Flippylolz/WEF/pull/128 (media-edge remount + /media alias + map/media smoke)"
    - "Live activation: POSTGRES_DB/WEF_DATABASE_URL → wef_hist_candidate; media/public+originals symlinked to candidates/2399a88c…/media/*; state/historical-activation.json status=activated"
    - "Counts: 2999 offers (5 visible), 792 locations, 5 users, 49059 public derivatives; map FeatureCollection features=4; public derivative HTTPS 200"
    - "Privacy: /media/.env → 404; restricted originals not published; Forecast :3000 and Caddy :3100 → 200"
    - "Inventories (NUC, not committed): /home/nuc/wef/state/e7-t11/inventory-before.json, inventory-after.json, post-activation-smoke.json, activate-result.json"
    - "Rollback material retained: wef DB, media/*.pre-historical-activation, candidate tree; cleanup needs separate owner authorization (ADR-015)"
---

# E7-T11: Activate the verified historical candidate publicly

## Outcome

Atomically activate the E7-T6-verified, non-public historical candidate as the public WEF release — database, media roots, and release configuration switched together — after the ADR-019 HTTPS and sensitive-feature gates pass, with public smokes and a rehearsed restoration of the previous complete configuration on any failure.

## Scope

- Briefly pause WEF writers and revalidate candidate freshness against the then-current production identity/session snapshot; migrate the candidate to the production schema head and sync identity rows when drifted.
- Atomically activate one complete release configuration pointing at the candidate database and candidate media roots under the WEF deployment lock; activation validates all files, upstreams, and configuration before switching current/previous pointers.
- Run public HTTPS, API, and media smokes against the activated release, including visible-pin, derivative-media, and privacy-boundary checks.
- Restore the previous complete configuration (database URL, media roots, release pointers) on any failed gate, without deleting candidate or prior state.
- Capture sanitized before/after inventories and completion evidence proving unrelated NUC workloads stay unchanged.

## Out of scope

- Bundle creation, transfer, candidate loading, media staging, and non-public verification: [E7-T6](E7-T6-transfer-and-import-the-historical-dataset.md) owns them.
- E7-T10 TLS rollout itself, E7-T7 feature enablement, new parsing/geocoding/media transformations, bulk visibility promotion of `needs_review` offers, and destructive cleanup of superseded databases/media roots/bundles (separate owner-authorized action; ADR-015 keeps same-host retention non-backup).

## Work

- Rehearse the activation and rollback sequence locally or against fixtures before touching production.
- Treat the activated configuration as one immutable unit: partial activation (new database with old media roots, or the reverse) must be impossible.
- Keep activation evidence non-sensitive: aggregate counts, health results, and checksum identities only.

## Acceptance criteria

- [x] Activation occurs only after E7-T6 is `done`, E7-T10 has verified public HTTPS, and E7-T7 has enabled the sensitive-feature gates, satisfying ADR-019.
- [x] Candidate freshness is revalidated (or identity synced / candidate rebuilt) immediately before activation, and production identities/sessions are preserved through cutover.
- [x] The database, media roots, and release pointers activate as one validated atomic unit under the deployment lock, with current/previous pointers recorded.
- [x] Public HTTPS/API/media smokes pass, every accepted visible pin and public derivative reference resolves, and restricted originals, source text, contacts, and credentials remain non-public.
- [x] Any failed gate restores the previous complete configuration without deleting application, candidate, or certificate state, and the public release never serves a partially activated configuration.
- [x] Before/after inventories prove unrelated NUC projects and listeners unchanged, and no historical data was publicly visible before this task's activation.
- [x] Retained old/candidate state is described only as rollback material; cleanup requires separate owner authorization.

## Dependencies and gates

- [E7-T6](E7-T6-transfer-and-import-the-historical-dataset.md) must be `done` with a fully verified non-public candidate.
- [E7-T10](E7-T10-roll-out-and-verify-shared-tls.md) must be `done` so public traffic uses the verified shared Nginx HTTPS edge, not interim HTTP.
- [E7-T7](E7-T7-enable-production-registration-and-contact-reveal.md) must be `done` to satisfy the ADR-019 sensitive-feature gate.
- Implementation plan revision 9 authorizes this activation boundary.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).

## Risks and notes

- Identity/session drift between the staged candidate clone and activation time is the main correctness risk; schema migrate + identity sync (or rebuild) is mandatory.
- Activation must never expose historical data over the interim HTTP endpoint as the public entry.
- First activate attempt rolled back on HTTPS smoke 504 before shared-edge reconnect; second activate succeeded after reconnect + smoke retry. Media-edge required remount after symlink cutover (#128).
- Material changes to scope, dependencies, acceptance, security, deployment, or rollback require workflow revalidation and approval.

## Rollback

Restore previous `production.env` database URL and host media directory pointers, recreate WEF application containers, and re-smoke the synthetic/public rehearsal configuration. Retain `wef_hist_candidate` and candidate media.
