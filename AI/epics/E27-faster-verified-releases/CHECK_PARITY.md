# E27-T2 verification parity

Baseline: E27-T1 commit `f81fb7c10bd1800a059240c464d955e89622b840`.
The change retains the union of CI and release checks for the exact release SHA.
Shared verification is invoked separately for a PR merge candidate and the actual
main squash-merge SHA; these identities are never substituted.

| Previous owner | Checks retained | New owner |
| --- | --- | --- |
| CI Backend / release verify | Frozen uv dependencies; Ruff formatting and lint; mypy; import contracts and deliberate violation; PostGIS tests with 90% branch coverage; OpenAPI deterministic export; pip-audit | Shared `backend` job; one host PostGIS service |
| CI Frontend / release verify | Frozen pnpm dependencies; format/lint/type; 90% unit coverage; generated contract check/lint/docs; deliberate drift proof; compatibility against PR base and deliberate breaking-contract negative probe | Shared `frontend` job |
| CI Frontend | Normal production build, production dependency audit, separate map-disabled build and Playwright critical path | Shared `frontend` job; both environments retained |
| CI Repository safety | Script format/lint/strict types and complete baseline unittest list; relative Markdown links; tracked source/secret exclusion | Shared `repository` job, plus release reporting/ordering tests |
| CI Repository / release verify | Local Compose model, shared-edge merged Compose model, production topology and release-workflow proofs, healthy/failure/forced rollback proof, shared-edge topology/runtime proof, shell syntax and shellcheck, Caddy configuration | Shared `repository` through `make compose-config` and `make production-proof` |
| CI Runtime images | Backend/web runtime construction, non-root users, absence of development tools/contracts/source, production runtime recreation/persistence | Shared runtime-image action; PR `Runtime images`; release parallel component jobs then `Runtime proof` against pushed digests |
| CI Coverage badge | Both coverage artifacts and independent suite floors; badge rendering/upload | Shared `coverage`; PR status adapter keeps protected check name; publishing follows main release completion |
| CI Frontend | OpenAPI JSON, generated TypeScript and static contract documentation artifact | Shared `frontend`, named for exact source SHA |
| Release verify/publish | Migration revision, full source SHA, source timestamp, immutable image digests, release manifest and checksums, pinned actions, complete release configuration and merged-PR gate | Shared backend metadata, component jobs, assembly and unchanged deployment eligibility; verification fingerprint adds reuse evidence |
| Release deploy | Complete mode-0600 configuration, checksum/SSH validation, migration, health/version identity, rollback, shared-host inventory, owner bootstrap, registry/temporary-file cleanup | Entire deployment job under shared Actions concurrency; host lock and state guard retained; key deletion follows remote cleanup |

The protected PR check names remain unchanged through explicit status adapters.
Every adapter fails if the shared workflow is incomplete, skipped, cancelled or
failed. Additional nested workflow checks remain visible. The shared workflow
has only contents-read permissions; only main-release component jobs receive
package-write permission and only the deployment job receives production secrets.

`prove_release_workflow` checks the shared graph, required command inventory,
production lock placement, exact-SHA inputs, read-only PR boundary, and ordering
before transfer. `test_release_order` covers wrong/missing digests, missing or
expired artifact evidence, cancelled/foreign/manual verification, source ancestry,
duplicate identity, held host lock, changed current state, and interrupted
activation. The existing rollback proof runs the new guarded path and a read-only
same-SHA health proof with isolated fake commands.

No latency gain is claimed from code structure alone. T3 requires at least twenty
eligible real post-change observations, explicit missing/cold/warm/incident data,
and comparison against the T1 baseline. Ordinary releases may supersede queued
older candidates; cancelled/superseded releases remain visible in cohort counts.
