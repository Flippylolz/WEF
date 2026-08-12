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
