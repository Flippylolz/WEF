# Autonomous Decision Log

This append-only log records choices made while the owner delegated overnight MVP/autodeploy preparation. Each entry states the question avoided, selected approach, rationale, scope, and reversal path. Accepted ADRs and approved epic artifacts remain higher-precedence sources of truth.

## AD-001: Continue through ordered stacked pull requests

- Time: 2026-08-12.
- Prompt avoided: wait for review/merge or continue dependent implementation.
- Selected approach: continue approved work in one-task branches and PRs stacked against their immediate parent; merge/completion still proceeds base-first after review and CI.
- Rationale: explicit owner direction not to wait for reviews.
- Governing record: [ADR-018](../decisions/adr/ADR-018-ordered-stacked-pull-requests.md).
- Reversal: stop creating descendants and retarget remaining PRs to `main` after their parents merge.

## AD-002: Bootstrap the empty repository with a minimal README and two initial PR layers

- Time: 2026-08-12.
- Prompt avoided: use an empty commit, put all docs directly on `main`, or defer PR creation.
- Selected approach: minimal README bootstrap on `main`, documentation foundation PR, then stacked E1-T1 repository-safety PR.
- Rationale: GitHub required a base ref, empty commits were disallowed, and the owner selected the stacked split.
- Evidence: [documentation PR #1](https://github.com/Flippylolz/WEF/pull/1), [E1-T1 PR #2](https://github.com/Flippylolz/WEF/pull/2).
- Reversal: close unmerged PRs and delete their branches; do not rewrite `main`.

## AD-003: Use SSH for Git transport

- Time: 2026-08-12.
- Prompt avoided: repair HTTPS token authentication or use the existing SSH identity.
- Selected approach: configure `origin` as `git@github.com:Flippylolz/WEF.git` and use SSH for fetch/push; keep GitHub CLI for PR/API operations.
- Rationale: explicit owner preference and verified SSH authentication.
- Reversal: change the repository remote transport without changing commit history.

## AD-004: Target a synthetic anonymous vertical MVP before historical/live data

- Time: 2026-08-12.
- Prompt avoided: attempt the complete import/auth/admin/live-Telegram scope or deliver the smallest reviewable product path first.
- Selected approach: first deliver a synthetic PostGIS-backed location/offer, grouped GeoJSON API, generated contract, and thin Next.js/MapLibre page; keep real export ingestion, contact reveal, admin, and Telegram credentials outside this overnight critical path.
- Rationale: this matches M1, avoids personal/source data risk, and validates architecture/deployment end to end.
- Reversal: promote and approve the remaining epic tasks without changing the vertical proof's contracts.

## AD-005: Keep the approved backend-centric modular monolith

- Time: 2026-08-12.
- Prompt avoided: collapse business behavior into Next.js for speed or preserve backend authority.
- Selected approach: FastAPI/Pydantic/SQLAlchemy/PostGIS backend owns filtering/grouping/visibility; Next.js renders generated API DTOs. Use interactors/query services, presenters, and inward-owned ports without generic repository/service frameworks.
- Rationale: owner-approved E0 spike revision 2 and ADR-012.
- Reversal: requires a new ADR and spike invalidation.

## AD-006: Use a non-destructive server deployment boundary

- Time: 2026-08-12.
- Prompt avoided: reuse existing server projects/ports or isolate WEF.
- Selected approach: use only `/home/nuc/wef`, Compose project `wef-production`, WEF-owned networks/volumes, and public port `3100`; never modify or delete non-WEF files, containers, networks, volumes, or services.
- Rationale: explicit owner safety instruction, ADR-010, and the inspected shared-host baseline.
- Reversal: remove only the WEF project/directory after an explicit owner request.

## AD-007: Prepare autodeploy without silently merging the stack

- Time: 2026-08-12.
- Prompt avoided: merge unreviewed PRs to activate deployment or prepare the complete workflow and report the merge gate.
- Selected approach: implement/test CI, production Compose, deploy workflow, GitHub configuration, and safe server directories as stacked PRs. Do not merge PRs unless explicitly requested; record main-activation as a blocker.
- Rationale: the owner asked to continue stacking, not to bypass review/merge history.
- Reversal: merge approved stack base-first to activate the main-only deployment workflow.

## AD-008: Repair merged stack propagation with a roll-up PR

- Time: 2026-08-12.
- Prompt avoided: rewrite shared history/force-push after PRs #1–#3 were merged into parent branches, or preserve history and explicitly propagate the descendants.
- Selected approach: open [roll-up PR #4](https://github.com/Flippylolz/WEF/pull/4) from the surviving E1-T1/workflow branch to `main`, then continue E0-T1 as [PR #5](https://github.com/Flippylolz/WEF/pull/5) against that branch.
- Rationale: PR #1 reached `main`, but PRs #2 and #3 were merged into already-merged parent branches, so their changes did not propagate. A roll-up PR is reviewable and avoids force-pushes, cherry-picks onto `main`, or history rewriting.
- Reversal: close PR #4 only if equivalent commits are independently confirmed on `main`; then retarget descendants to the verified base.

## AD-009: Treat the overnight MVP directive as approval for bounded plan revisions

- Time: 2026-08-12.
- Prompt avoided: pause for repeated owner approval of each already-spiked implementation plan or proceed through the requested MVP/autodeploy stack.
- Selected approach: use the owner's explicit instruction to prepare the MVP, set up autodeploy, choose safe defaults, log choices, and continue stacking as approval for new implementation-plan revisions that stay within existing approved spike/ADR boundaries. Each promoted task still receives its own branch, PR, tests, evidence, and base-first merge gate.
- Rationale: the owner explicitly delegated questions and requested uninterrupted overnight execution; requiring synchronous confirmation would contradict that instruction.
- Safety limit: a material architecture, security, data-handling, destructive-server, credential, or external-cost change still stops or remains blocked.
- Reversal: close unmerged descendant PRs and revise/reapprove the affected plan; do not rewrite shared history.

## AD-010: Use a two-network local edge topology and a bounded importer probe

- Time: 2026-08-12.
- Prompt avoided: publish each development service directly or provide one same-origin edge; mount the local export into a continuously running worker or expose it only to an on-demand command.
- Selected approach: Caddy alone binds `127.0.0.1:3100` on a normal edge network and also joins an internal application network; web, API, PostGIS, and importer stay on the internal network with no host ports. The importer is profile-gated, receives the source bind read-only with host-path creation disabled, and its E1 command only proves mount safety and reports a file count.
- Rationale: a service attached only to an internal Docker Desktop network did not receive a usable host forwarding path. Giving only Caddy a second edge network preserves database/application isolation while making the intended same-origin route reachable. The bounded probe verifies source safety without prematurely implementing E2 ingestion or reading file contents.
- Evidence: E1-T3 runtime checks reached the page and `/api/v1/health/live` through Caddy, found no API/database host bindings, proved PostGIS/media volume persistence across container recreation, and completed the read-only importer probe.
- Reversal: replace the local edge network or importer command in a later approved task without changing persisted database/media volumes.

## AD-011: Deliver the browser-visible synthetic map before historical ingestion

- Time: 2026-08-12.
- Prompt avoided: implement the complete parser/persistence/geocoder chain before any visible MVP or use a deterministic canonical seed to complete the public map/filter path first.
- Selected approach: M1 now migrates/seeds invented Warsaw locations/offers explicitly, then stacks grouped map/facet/location-result APIs and the MapLibre URL-filter UI. E2 historical parsing, idempotent source persistence, provider geocoding, media, auth/contacts, and real data remain separately gated.
- Rationale: the owner said local data and Telegram are later and asked for the best overnight MVP. A synthetic canonical seed exercises migrations, PostGIS, backend filter authority, generated contracts, browser interaction, Docker, and deployment without risking private source data or provider credentials.
- Safety limit: synthetic coordinates are fixed fixture facts and clearly labeled; this exception never authorizes a real address to bypass geocoding/review. The seed is explicit and refuses production.
- Reversal: implement the still-proposed E2/E3 ingestion tasks, replace seeded rows through reviewed idempotent persistence, and retire the seed command without changing public E4/E5 contracts.

## AD-012: Retire E0 persistence without a breaking contract deletion

- Time: 2026-08-12.
- Prompt avoided: delete `/api/v1/estates` immediately and fail additive compatibility checks, or let the old runtime keep querying an intentionally unmigrated proof table.
- Selected approach: make the grouped catalog map the active persistence path, mark `/api/v1/estates` deprecated, and route that compatibility endpoint to an inert empty adapter. E5 removes the old frontend consumer; endpoint deletion remains a separately reviewed compatibility change.
- Rationale: the E0 table is deliberately excluded from Alembic, so continuing to query it produced noisy runtime failures. Preserving the deprecated response shape keeps the current stack additive while stopping obsolete database access.
- Safety limit: no canonical location/offer is translated into the misleading E0 availability model.
- Reversal: remove the deprecated endpoint after all generated-client/frontend consumers migrate, or temporarily restore its isolated proof adapter only in a dedicated architecture test.

## AD-013: Rehearse anonymous production before the sensitive public launch

- Time: 2026-08-12.
- Prompt avoided: wait for unfinished auth/contact/security scope before testing production delivery, or deploy only the anonymous synthetic read path now.
- Selected approach: [ADR-019](../decisions/adr/ADR-019-anonymous-http-production-rehearsal.md) permits an interim HTTP rehearsal on port 3100 with synthetic data and no credentials, registration, sessions, contact reveal, historical source, or Telegram.
- Rationale: this proves isolated persistence, immutable images, GitHub configuration transfer, same-origin routing, health checks, and application rollback without exposing sensitive functionality.
- Safety limit: the rehearsal is not M3/public-launch completion; B-006 remains an operational autodeploy blocker until GitHub can start hosted jobs, and E7-T7 HTTPS remains mandatory for sensitive features.
- Reversal: stop only the `wef-production` project and retain its persistent paths, or remove `/home/nuc/wef` only after explicit owner authorization.

## AD-014: Keep automatic deployment disabled through the rollback rehearsal

- Time: 2026-08-13.
- Prompt avoided: enable every-main-merge deployment immediately or prepare the complete path behind an explicit enable gate.
- Selected approach: the release workflow verifies and publishes exact-SHA images, but SSH requires merged-PR association plus `AUTO_DEPLOY_ENABLED=true`; repository configuration starts with that variable `false`, while an owner-triggered exact-main-SHA rehearsal remains available.
- Rationale: this allows E7-T3 configuration and image delivery to be tested without turning an unproven rollback path into unattended production mutation.
- Safety limit: E7-T4 health/failure rehearsal and a successful hosted run are required before changing the variable to `true`.
- Reversal: set `AUTO_DEPLOY_ENABLED=false` to stop automatic SSH without changing image publication or release history.

## AD-015: Use the job-scoped token only for the deployment pull

- Time: 2026-08-13.
- Prompt avoided: persist a long-lived GHCR credential on the NUC or reuse the workflow's transient package token only while the job is active.
- Selected approach: the deploy job has `packages: read`, pipes its job-scoped `GITHUB_TOKEN` directly to remote `docker login`, pulls under the host lock, and logs out in the exit trap; the token is never written to release configuration or artifacts.
- Rationale: it removes a standing package credential while still allowing private GHCR images to be pulled during the authorized deployment.
- Safety limit: independent/manual host pulls outside the workflow are unavailable unless a separately scoped credential is approved later.
- Reversal: provision a dedicated read-only package token through GitHub secrets and rotate/remove it independently.

## AD-016: Rehearse rollback with a post-smoke failure gate

- Time: 2026-08-13.
- Prompt avoided: publish an intentionally broken image, alter production routing by hand, or add a bounded workflow failpoint after proving the candidate is otherwise healthy.
- Selected approach: an explicit manual-dispatch input requires a different active release, runs the complete real candidate smoke, then converts only that successful result into failure. The deploy script returns reserved code `42` only after automatic rollback and previous-release smoke pass; GitHub then verifies state/manifests and before/after host inventory.
- Rationale: this exercises the real activation failure and rollback path without putting deliberately vulnerable/broken code in GHCR or weakening ordinary deployment checks.
- Safety limit: the flag is never produced for push events, automatic deployment cannot set it, a missing/different previous release fails closed, and `AUTO_DEPLOY_ENABLED` remains false until hosted evidence passes.
- Reversal: remove the input/failpoint after a different reviewed rollback-injection mechanism supersedes it; normal health failures continue to fail with a nonzero status.

## AD-017: Initialize only the PostGIS bind-root owner in a bounded container

- Time: 2026-08-13.
- Prompt avoided: request sudo to chown the production data root, grant broad writable permissions, move persistence into an opaque named volume, or use a capability-limited one-shot initializer.
- Selected approach: before database startup, run the pinned PostGIS image once as root with no network, a read-only container root, and only `CHOWN`/`DAC_OVERRIDE` to set `/home/nuc/wef/postgres` itself to UID/GID 999. It is non-recursive and touches no path outside the WEF bind.
- Rationale: the native Linux host's `nuc:0700` directory is not writable by the image's `postgres` UID 999; this preserves the documented host path without persisting or requesting sudo credentials.
- Safety limit: topology proofs pin the exact command/capabilities/path; inventory permits UID 999 only for the PostgreSQL root.
- Reversal: an owner may perform and maintain the same narrow ownership through host provisioning, after which the initializer can be removed in a reviewed task.

## AD-018: Complete E5 as a green-gated documentation-first stack

- Time: 2026-08-13.
- Prompt avoided: implement only the already-ready E5-T2, combine the remaining frontend epic into one change, or authorize the complete E5 sequence while upstream E3/E4 work proceeds independently.
- Selected approach: approve E5 spike/plan revision 3, promote E5-T3 through E5-T5, and deliver documentation → E5-T2 → E5-T3 → E5-T4 → E5-T5 as one ordered stack in a separate worktree. Open each child only after fresh parent CI is green.
- Rationale: the owner explicitly requested full E5, one task per stacked branch, documentation first, and confirmed that E3/E4 dependencies are handled by parallel agents.
- Safety limit: E5-T3 and E5-T5 remain blocked until exact E4-T3/E4-T4 ancestry or completion is recorded. E5 cannot invent frontend contracts, weaken privacy/accessibility/performance acceptance, or absorb E3/E4 task scope.
- Reversal: close unmerged E5 descendants, keep promoted tasks in `draft`, and revise/reapprove E5 if parallel contract delivery materially changes the accepted boundary; do not rewrite shared history.

## AD-019: Sequence E6-T5 while parking live TLS on D-009

- Time: 2026-08-20.
- Prompt avoided: wait for owner hostname/router inputs before any further epic work, or invent DuckDNS names / mutate NUC 80/443 without D-009.
- Selected approach: document B-009 and proposed E7 plan revision 6 (E7-T10 awaiting D-009); approve E6 implementation-plan revision 3 and promote E6-T5 under AD-009; continue contact masking/reveal implementation without production auth activation.
- Rationale: E7-T8/E7-T9 are done; live TLS is a genuine owner-input gate; E6-T5 dependencies are satisfied and advance M3 without requiring D-009.
- Safety limit: no live shared-edge cutover, no autonomous DuckDNS registration, no E7-T7 enablement until HTTPS; `cryptography` addition stays within the E0 spike selection for E6-T5.
- Reversal: revise/reapprove E6 plan revision 3 and demote E6-T5 if contact encryption/reveal scope changes; resolve D-009 before approving E7 plan revision 6.

## AD-020: Sequence E6-T6 restricted-action UX after E6-T5

- Time: 2026-08-20.
- Prompt avoided: wait for D-009/E7-T10 before frontend reveal UX, or fold owner console into the same change.
- Selected approach: approve E6 implementation-plan revision 4 and promote E6-T6 only; extend the existing E9 account modal and offer detail drawer; keep E6-T7 proposed.
- Rationale: E5-T3/E6-T4/E6-T5 are done; AUTH_ADMIN_CONTACTS frontend behavior is the next M3 gap; live TLS remains an owner-input gate.
- Safety limit: no production auth enablement; no Starlette Admin in this task; revealed contacts stay in memory only.
- Reversal: revise/reapprove plan revision 4 and demote E6-T6 if UX scope changes materially.

## AD-027: Add operational diagnostics after E6-T2 (E6-T3)

- Time: 2026-08-20.
- Prompt avoided: leave operators without release/failure/disk/import visibility after public launch, or expand into Playwright (E6-T1) in the same plan.
- Selected approach: approve E6 plan revision 7; promote E6-T3; ship host `operator_diagnostics.py` plus configured structlog access logs with redaction proofs.
- Rationale: E6-T3 dependencies and E6-T2 are done; spike revision 2 already identified unconfigured structlog; AD-009 continue authority.
- Safety limit: no source text/contacts/secrets in diagnostics or logs; no metrics SaaS; no backups; E6-T1 remains separate.
- Reversal: prior API image and ignore/remove diagnostics script; state files unchanged.

## AD-026: Harden privacy/security after historical public activation (E6-T2)


- Time: 2026-08-20.
- Prompt avoided: leave HSTS deferred indefinitely after verified TLS, or expand into E6-T1/T3 Playwright/diagnostics in the same plan.
- Selected approach: approve E6 plan revision 6; promote E6-T2; enable HSTS on the WEF HTTPS shared-edge vhost; prove docs/OpenAPI denial, contact/media boundaries, and refresh synthetic-only public copy; keep E6-T1/T3 for later revisions.
- Rationale: E6-T2 dependencies and E7-T10/T7/T11 are done; DEPLOYMENT.md gated HSTS on verified certs; AD-009 continue authority.
- Safety limit: no `preload`; no HSTS on `:3100`; no bulk visibility promotion; no Forecast TLS; no OpenAPI exposure in production.
- Reversal: restore previous shared-edge release without HSTS; revert public copy with prior web image.

## AD-025: Activate verified historical candidate after E7-T7 (E7-T11)


- Time: 2026-08-20.
- Prompt avoided: leave historical data non-public indefinitely after ADR-019 gates, or activate without atomic DB+media+config / identity freshness.
- Selected approach: approve E7 plan revision 9; promote E7-T11; migrate candidate to production schema head; sync production identities/sessions; atomically switch `WEF_DATABASE_URL` and media roots under `deploy.lock` with rollback of the previous complete configuration.
- Rationale: E7-T6/T10/T7 done; spike revision 4 already describes this activation boundary; AD-009 continue authority.
- Safety limit: no destructive cleanup; no bulk `needs_review`→`visible`; no Forecast TLS; no public historical exposure on `:3100` as the entry.
- Reversal: restore previous production.env DB URL and media directory pointers; retain candidate and prior `wef` database.

## AD-024: Enable sensitive WEF features after live HTTPS (E7-T7)

- Time: 2026-08-20.
- Prompt avoided: leave registration/admin/reveal disabled indefinitely after E7-T10, or enable them without contact crypto keys / proxy trust.
- Selected approach: approve E7 plan revision 8; promote E7-T7; require contact encryption/HMAC secrets in deploy; trust forwarded HTTPS headers in production Uvicorn; optional one-time owner bootstrap secrets with idempotent `wef-bootstrap-owner`; route `/admin` on the shared edge to the API.
- Rationale: ADR-019 HTTPS gate is satisfied; E6 auth stack is done; continue mission under AD-009.
- Safety limit: do not activate historical public data (E7-T11); rotate/remove bootstrap password after first success; do not commit keys.
- Reversal: redeploy without contact keys / bootstrap; auth cookies remain Secure-only in production.
- Completion: PRs #123/#124/#125; B-002 cleared as R-010; live HTTPS auth/admin smokes passed 2026-08-20.


## AD-028: Sequence E6-T1 Playwright critical path (plan revision 8)

- Time: 2026-08-20.
- Prompt avoided: leave the spike-confirmed browser/e2e gap open after E6-T3, or expand into multi-browser load/Dependabot scope.
- Selected approach: approve E6 plan revision 8; promote E6-T1; add Chromium Playwright with route-mocked synthetic fixtures for pin/list/detail and error/missing-link states; wire CI.
- Rationale: E4-T3/E5-T3 done; lower pyramid layers already exist; AD-009 continue authority.
- Safety limit: synthetic fixtures only; Chromium-only; no live historical content assertions; no production dependency additions beyond Playwright test tooling (devDependency).
- Reversal: remove Playwright CI job and web e2e tooling; unit/contract/a11y layers remain.

## AD-029: Sequence E1-T6 Dependabot update PRs (plan revision 5)

- Time: 2026-08-20.
- Prompt avoided: leave Dependabot unconfigured after M3 quality/favorites work, or also ship the merge controller in the same change.
- Selected approach: approve E1 plan revision 5; promote E1-T6 only; add weekly npm/pip/docker/github-actions Dependabot config with patch/minor grouping and bounded open PRs; keep E1-T7 proposed.
- Rationale: E1 spike revision 2 already bounded this work; E1-T1/E1-T4 are done; REPOSITORY_RULES require the config; AD-009 continue authority.
- Safety limit: no merge-controller workflow, no PR checkout/execution, no dependency upgrades in the configuration PR itself.
- Reversal: remove `.github/dependabot.yml` and demote E1-T6 if ecosystems/grouping policy change.
- Completion: PR #140 merged; vulnerability alerts + automated security fixes enabled on the repository.

## AD-030: Sequence E1-T7 Dependabot merge controller (plan revision 6)

- Time: 2026-08-20.
- Prompt avoided: leave owner-labeled Dependabot PRs manual forever after E1-T6, or check out/execute PR code with a write token.
- Selected approach: approve E1 plan revision 6; promote E1-T7; add a 15-minute/manual default-branch controller with required-check allowlist, owner `automerge` actor gate, bot-only patch/minor rules, refetch, and `--match-head-commit` squash merge.
- Rationale: E1-T6 done; REPOSITORY_RULES already specify this compensating control under ADR-017; AD-009 continue authority.
- Safety limit: never checkout PR heads; never `--admin`; majors/indirect/human commits remain ineligible.
- Reversal: disable/delete `dependabot-merge.yml` and demote E1-T7 if gating policy changes.
- Completion: PR #148 merged; Dependabot already opened grouped patch/minor and separate major PRs after E1-T6.
- Follow-up: created repository `automerge` label for owner-gated controller eligibility.

## AD-031: Approve E8 spike revision 2 and sequence E8-T1 only

- Time: 2026-08-20.
- Prompt avoided: wait indefinitely after M3 for an explicit “approve E8 spike” phrase while `continue` was reissued; or start Telethon/live worker without gates.
- Selected approach: under AD-009 `continue`, approve E8 spike revision 2; approve implementation plan revision 1 authorizing **only E8-T1**; promote E8-T1; ship non-secret channel identity, worker secret-path contract, and redacted `wef-verify-telegram-channel` without Telethon.
- Rationale: M3 is done; spike research is complete; next milestone is M4; credential-free identity/contract work is the spike’s explicit first step; live secrets and Telethon remain later gates.
- Safety limit: no Telethon dependency; no worker Compose enablement; no credentials in Git; live entity resolve stays open until owner secrets + E8-T2.
- Reversal: demote E8-T1 / revert plan revision 1 if the owner rejects AD-031.
- Follow-up: owner supplies Telegram API ID/hash/session to approved secret paths; then E8-T4/T2 plan revisions.

## AD-032: Approve E8 plan revision 2 and sequence E8-T4

- Time: 2026-08-21.
- Prompt avoided: wait for a separate “approve E8-T4” phrase after E8-T1 while `continue` was reissued; or enable the live worker / Telethon under geocoder work.
- Selected approach: under AD-009 `continue`, approve implementation plan revision 2 authorizing **E8-T4** after E8-T1; promote E8-T4; retain Geoapify for recurring use after dated free-plan recheck; resolve D-002; ship defer/monitor contract and `wef-revalidate-recurring-geocoder` without Telethon or worker Compose enablement.
- Rationale: spike revision 2 already ordered E8-T1 → E8-T4; E3-T3 is done; recurring selection was the next gated step before Telethon.
- Safety limit: no Telethon dependency; no worker enablement; no paid Geoapify activation; no Nominatim recurring fallback; no credentials in Git.
- Reversal: demote E8-T4 / revert plan revision 2 and reopen D-002 if the owner rejects AD-032.
- Follow-up: E8-T2 after owner Telegram secrets; E8-T5 still owns production worker enablement.

## AD-033: Promote historical offers and hide synthetic M1 seed

- Time: 2026-08-21.
- Prompt avoided: leave the public map on five synthetic pins while ~2,994 imported offers stayed `needs_review`.
- Selected approach: on owner request, hide `synthetic-m1-v1` offers, reject synthetic location IDs, and set all other offers to `visible` on `wef_hist_candidate`; ship `wef-promote-public-catalog` for repeatable ops.
- Rationale: E7-T11 activated the candidate DB/media but intentionally deferred bulk visibility; the owner now asked to remove mock data and show historical records.
- Safety limit: map still requires accepted in-scope locations with points; ungeocoded/needs_review locations without points remain non-pinnable; no Telethon/worker enablement.
- Reversal: restore offer `needs_review` / synthetic `visible` from backup or reverse SQL if the owner wants the rehearsal-only map again.
- Follow-up: optional later curation UI for selective hiding; geocode remaining point-less locations if more pins are desired.

## AD-034: Accept in-scope pending geocode pins for public map coverage

- Time: 2026-08-21.
- Prompt avoided: leave ~306 in-scope geocoded locations unpinned (`needs_review` without `point`) after the owner asked for historical records to be visible; or start Telethon while B-003 remains open.
- Selected approach: under AD-009 `continue` after AD-033, accept in-scope `low_precision`/`low_confidence` geocode results onto locations with `manual_accept` lineage; ship `wef-accept-pending-geocode-pins`; leave out-of-scope and `no_result` ungeocoded rows unpinned.
- Rationale: coordinates already existed in `geocode_results`; auto-review correctly withheld pin acceptance, but public discovery needed pins; owner visibility request + AD-033 follow-up authorize operator acceptance.
- Safety limit: no Telethon; no worker enablement; out-of-scope results remain unpinned; city/district pins may be coarse and are reversible via review lineage.
- Reversal: set affected locations back to `needs_review` with `point` cleared using prior selection lineage if the owner wants stricter auto-only pins.
- Follow-up: E8-T2 still waits on B-003 Telegram secrets.

## AD-035: Approve E8 plan revision 3 and sequence E8-T2

- Time: 2026-08-21.
- Prompt avoided: wait indefinitely for live Telegram secrets before any Telethon/backfill scaffolding while `continue` was reissued; or enable the production worker Compose profile under E8-T2.
- Selected approach: under AD-009 `continue`, approve implementation plan revision 3 authorizing **E8-T2**; promote E8-T2; add the spike-selected `telethon` dependency; ship secret-file loading, Fake+Telethon clients, entity verify, advisory-lock backfill through E3 persistence, and `wef-telegram-backfill`; leave live acceptance and worker enablement gated on B-003 / E8-T5.
- Rationale: spike revision 2 ordered E8-T1 → E8-T4 → E8-T2; E8-T4 is done; fake-client acceptance unblocks reviewable progress without credentials; production activation remains E8-T5.
- Safety limit: no worker Compose enablement; no credentials in Git; live Telethon runs fail closed without owner-supplied mode-0600 secret files.
- Reversal: demote E8-T2 / revert plan revision 3 and remove the Telethon dependency if the owner rejects AD-035.
- Follow-up: owner supplies API ID/hash/session; then live backfill evidence; E8-T3 events; E8-T5 worker enablement.

## AD-036: Approve E8 plan revision 4 and sequence E8-T3

- Time: 2026-08-21.
- Prompt avoided: wait indefinitely for live Telegram secrets before any new/edit/delete processing while `continue` was reissued; or enable the production worker under E8-T3.
- Selected approach: under AD-009 `continue`, approve implementation plan revision 4 authorizing **E8-T3**; promote E8-T3; ship serialized live event processing, `persist_live_upsert`, `mark_source_deleted` (lineage-preserving hide), Fake-client convergence tests, and Telethon event adapters; leave live subscription and worker enablement gated on B-003 / E8-T5.
- Rationale: spike revision 2 ordered E8-T2 → E8-T3; E8-T2 scaffolding is merged; fake-client acceptance covers replay/edit/delete without credentials.
- Safety limit: no worker Compose enablement; no credentials in Git; worker health never gates public API readiness.
- Reversal: demote E8-T3 / revert plan revision 4 if the owner rejects AD-036.
- Follow-up: owner supplies Telegram secrets; then live event evidence; E8-T5 production worker enablement.

## AD-037: Approve E8 plan revision 5 and sequence E8-T5

- Time: 2026-08-21.
- Prompt avoided: wait indefinitely for live Telegram secrets before any worker ops scaffolding while `continue` was reissued; or enable the production worker Compose profile under E8-T5 before B-003 clears.
- Selected approach: under AD-009 `continue`, approve implementation plan revision 5 authorizing **E8-T5**; promote E8-T5; ship disabled-by-default `telegram-worker` Compose (local + production), `wef-telegram-worker-status` (freshness + checkpoint reconciliation), session-rotation dry-run, and fail-closed `wef-telegram-worker` behind `WEF_TELEGRAM_WORKER_ACTIVATE`; leave live activation and continuous loop gated on B-003.
- Rationale: spike revision 2 ordered E8-T3 → E8-T5; prior E8 tasks delivered scaffolding; credential-free ops contracts unblock reviewable production readiness without enabling the worker.
- Safety limit: do not start `--profile telegram-worker` or set activation/live-loop env vars in production until owner supplies secrets and records activation; worker freshness never gates API readiness.
- Reversal: demote E8-T5 / revert plan revision 5 and remove the Compose worker service if the owner rejects AD-037.
- Follow-up: owner supplies Telegram API ID/hash/session to NUC `secrets/current` (mode 0600); then activation evidence closes remaining E8 acceptance.

## AD-038: Approve E13 spike/plan and implement the dark map-first explorer

- Time: 2026-08-26.
- Prompt avoided: wait for a separate synchronous "approve E13 spike/plan" phrase after the owner explicitly assigned the epic, or redesign the frontend without the gated plan.
- Selected approach: treat the owner's explicit 2026-08-26 instruction ("implement the changes described in epic 13, merge the PR, make sure that production is deployed and run a test") as owner approval under the AD-009 continue authority: approve E13 spike revision 1 and implementation plan revision 1 authorizing E13-T1 → E13-T2 → E13-T3; promote all three tasks; implement each on its own branch/PR with full CI; merge base-first; verify the automatic production deploy and run the production smoke/GUI test.
- Rationale: the spike is complete and the owner named the epic and requested the full implement → merge → deploy → test cycle; requiring synchronous re-confirmation would contradict the instruction. The instruction adopts the spike's recommended Option C, resolving the "meaning of listing" open question in favor of dated-offer cards (E13-T2/T3) after the grouped-location first slice (E13-T1).
- Safety limit: no new production dependency, no map vendor change (verified OpenFreeMap `styles/dark`), no availability/relevance claims, backend keeps filtering/sort/pagination ownership, malformed facet values are not corrected in the frontend, and each task still passes its own PR CI before merge.
- Reversal: close unmerged E13 PRs and demote/invalidate the affected tasks; revert plan revision 1 if the owner rejects AD-038; production rolls back to the prior release image.

## AD-039: Approve E15 spike revision 1 and prepare the implementation plan

- Time: 2026-08-28.
- Owner decision: `I approve E15 spike revision 1.`
- Selected approach: record exact owner approval of E15 spike revision 1, promote the three spike-defined P0 task candidates, and prepare implementation plan revision 1 for separate owner review.
- Scope boundary: this decision authorizes task refinement, promotion, and implementation planning only. It does not authorize production/application code, tests, migrations, configuration, deployment, listener restart, backfill, or production repair.
- Rationale: E15 is the only selected blocker/P0 epic and its research-only spike completed the incident analysis and bounded recommendation. The repository workflow requires a distinct implementation-plan approval before task implementation can begin.
- Reversal: invalidate the spike and downstream planning artifacts if the owner withdraws approval or new evidence crosses a spike invalidation trigger.

## AD-040: Approve E15 implementation plan revision 1 and green-CI merge sequence

- Time: 2026-08-28.
- Owner decision: `please finish the epic, every change should be in it's own PR and you can merge them after the CI is green`.
- Selected approach: approve E15 implementation plan revision 1 and execute E15-T1 → E15-T2 → E15-T3, one dedicated PR per task, merging in dependency order only after required CI is complete and green. The planning/approval artifacts land first in their own documentation PR.
- Safety limit: the instruction does not waive task gates, review, CI, privacy, secret handling, immutable deployment health, rollback preflight, single-worker ownership, or bounded production-recovery controls. No raw Telegram content/session/contacts enter Git, logs, or evidence.
- Reversal: close unmerged PRs and invalidate the affected plan/task gate if material implementation evidence crosses a plan/spike trigger; after deployment, use the prior immutable release without rewinding committed checkpoints.

## AD-041: Approve E14 spike revision 1 and prepare the implementation plan

- Time: 2026-08-29.
- Owner decision: `I approve E14 spike revision 1.`
- Selected approach: record exact owner approval of E14 spike revision 1, refine and promote E14-T1 through E14-T8, and prepare implementation plan revision 1 for separate owner review.
- Scope boundary: this decision authorizes task refinement, promotion, and implementation planning only. It does not authorize application code, tests, dependencies, migrations, infrastructure, deployment, production mutation, or recovery operations.
- Recovery boundary: E14-T9 remains proposed and non-actionable while ADR-015 and E7-T5 defer off-host backups; a later owner decision must define that recovery scope before promotion.
- Rationale: E14 is the selected unfinished epic other than E17, its research-only spike is complete, and the owner supplied the exact revision-specific approval required by the workflow.
- Reversal: invalidate the spike and downstream planning artifacts if the owner withdraws approval or new evidence crosses a spike invalidation trigger.

## AD-042: Approve E19 spike revision 4

- Time: 2026-08-30.
- Owner decision: `I am the repository/product owner. I explicitly approve E19 SPIKE.md revision 4 and its recommendation.`
- Selected approach: record exact owner approval of E19 spike revision 4 and its dual-workflow recommendation (confirmed place review plus missing-only batch offer autofill), then promote E19-T1 through E19-T4 and write implementation plan revision 1. PR #224 had already squash-merged the awaiting-approval spike documentation (`5b76126`); this decision is recorded in the follow-up documentation PR rather than by amending the merged pull request.
- Scope boundary: this decision authorizes task refinement, promotion, and implementation planning. It does not by itself authorize production/application code, tests, migrations, configuration, deployment, Groq spend, secret creation, or production AI enablement.
- Rationale: the owner supplied the exact revision-specific approval required by the workflow and adopted the spike recommendation without changing ADR-022, P-009, or the four proposed task boundaries.
- Reversal: invalidate the spike and downstream planning artifacts if the owner withdraws approval or new evidence crosses a spike invalidation trigger.

## AD-043: Approve E19 implementation plan revision 1 and green-CI merge sequence

- Time: 2026-08-30.
- Owner decision: `I also authorize you under AD-009 to create and approve E19 IMPLEMENTATION_PLAN.md revision 1, provided it stays strictly within spike revision 4, ADR-022, P-009, and the four existing E19 task boundaries. Record this message as the owner decision.` The same message authorized completing E19-T1 through E19-T4, one dedicated PR per task, merging after required CI is green, and verifying the automatic production deploy without mutating real offers.
- Selected approach: approve E19 implementation plan revision 1 under AD-009 continue authority, then execute documentation PR → E19-T1 → parallel E19-T2/E19-T3 → E19-T4. Each change uses its own branch and pull request. Merge dependency-first only after required CI is complete and green. Provider transport uses existing `httpx`; no Groq or OpenAI SDK is added. Automated tests use a fake provider. Production AI remains disabled unless a Groq secret exists and Zero Data Retention has been verified.
- Safety limit: stop before implementation if a material deviation, new architecture, paid service, weaker privacy control, or broader data mutation is required. Do not recover or use the previously removed OpenAI key. Do not make paid provider calls, create external accounts, enable production AI processing, or mutate real offers merely to demonstrate the feature. Missing Groq credentials remain a documented activation requirement and must not block deploying the disabled-by-default implementation.
- Reversal: close unmerged PRs and invalidate the affected plan/task gate if material implementation evidence crosses a plan/spike trigger; after deployment, disable the feature flag and use the prior immutable release.
