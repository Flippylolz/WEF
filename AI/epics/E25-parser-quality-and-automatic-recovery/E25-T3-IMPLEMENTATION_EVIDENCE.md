# E25-T3 implementation evidence

## Review state

Draft PR: [335](https://github.com/Flippylolz/WEF/pull/335). Implementation commit: `6ece15f`.

Implementation under owner-approved spike and implementation plan revision 2.
The task remains in progress: upstream E25-T1 is open, required PR checks/review
and a representative live acceptance window are outstanding. No production
activation, paid provider call, historical canonical application or merge occurred.

## Behavior

Migration 0021 adds minimized durable attempts, shared owner allocation and
versioned recovery claims. All composed provider entry points reserve before
single-item inference under ZDR: at most 20 generation attempts per owner UTC day,
one in flight, 60-second start spacing and a 30-second whole-request deadline.
Legacy daily usage is included at cutover. Drain older writers before adoption.
429 defers until the later of Retry-After and the next UTC day. An ambiguous
transport outcome retains its budget and becomes one exception without resending.
Known-safe transient server failures receive one separately reserved retry.

The optional worker yields to live ingestion, selects source-evidenced missing
fields, reuses saved proposals/cohorts and persists bounded local backoff.
Application checks independent source semantics, current source revision,
protected origins, missing-only fields and consistent bounds/currency. New offers
require deterministic property type and fully supported literal listing evidence;
creation and proposal application checkpoint commit atomically. Existing contact
encryption is wired into creation. No new production dependency was added.

## Local verification

- `COMPOSE_PROJECT_NAME=wef-e25-validation make test`: 996 backend tests and
  169 frontend tests passed; backend coverage 90.11%.
- `make lint`: passed, including all 17 architecture contracts.
- Root `scripts/` Ruff format/lint and strict mypy: passed after correcting
  release-script formatting caught by the initial repository-safety CI run.
- `make format-check`, `make typecheck`, `make contract-check`: passed.
- `python3 -m scripts.prove_release_workflow`: passed, including disabled defaults,
  explicit activation values and invalid boolean/owner configuration rejection.
- `python3 -m scripts.prove_production_topology`: passed.
- `python3 -m scripts.prove_deploy_rollback`: passed.

Provider tests use fakes; transaction and race tests use isolated PostgreSQL.
Coverage includes concurrent allocation, exhausted budgets, rollover, abandoned
leases, uncertain attempts, 429, known-safe retry, malformed/unsupported evidence,
source deletion/replacement, claim expiry, stale claims, protected fields,
atomic creation and repeated application. Each calibrated scalar family has at
least ten positive and ten negative synthetic semantic cases.

## Rollout and remaining evidence

Submission, activation verification and auto-apply default off. Operators must
verify account ZDR, free allocation and writer cutover before activation. The
first ten fully validated distinct revisions are observations; later eligible
work may apply once the separate application flag is enabled. Initial canary
observations remain saved and are not automatically replayed after promotion.
The current implementation therefore does not demonstrate complete live queue
convergence. Report eligible denominator, unresolved reasons, spend and human
interventions during the outstanding representative acceptance window.

T4 owns automatic historical deterministic replay. It cannot start in the current
stack: E24-T1 PR 331 is open outside the E25 ancestry, and T2/T3 are sibling PRs.
Reconcile the dependency ancestry or merge reviewed upstreams before starting it.
Task completion remains unchecked; passing local tests does not satisfy these gates.

Pause and rollback: disable application/submission flags, retain audit and proposal
checkpoints, and use provenance-aware reversal only for unchanged automatic fields.
Do not drop ledger tables to reset quota or resend uncertain attempts.

## Changed files

- `.env.example`
- `.github/workflows/deploy-production.yml`
- `AI/data/QUALITY_AND_READINESS.md`
- `AI/decisions/adr/ADR-022-use-groq-gpt-oss-for-place-review-and-offer-enrichment.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/IMPLEMENTATION_PLAN.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/PROVIDER_PRIVACY_REVISION.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/README.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/SPIKE.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/tasks/E25-T1-benchmark-source-evidence-and-triage.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/tasks/E25-T2-repair-deterministic-extraction.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/tasks/E25-T3-automate-validated-ai-exceptions.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/tasks/E25-T4-converge-parser-versions-automatically.md`
- `AI/ingestion/PIPELINE.md`
- `AI/operations/OPERATOR_COMMANDS.md`
- `AI/security/AUTH_ADMIN_CONTACTS.md`
- `apps/backend/src/wef_backend/composition.py`
- `apps/backend/src/wef_backend/features/admin/application/ai_review.py`
- `apps/backend/src/wef_backend/features/admin/application/ingestion_ai_parse.py`
- `apps/backend/src/wef_backend/features/admin/application/offer_enrichment.py`
- `apps/backend/src/wef_backend/features/admin/infrastructure/ai_enrichment_store.py`
- `apps/backend/src/wef_backend/features/admin/infrastructure/groq_provider.py`
- `apps/backend/src/wef_backend/features/ingestion/application/extraction.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/persistence_adapter.py`
- `apps/backend/src/wef_backend/migration.py`
- `apps/backend/src/wef_backend/settings.py`
- `apps/backend/src/wef_backend/telegram_worker_command.py`
- `apps/backend/tests/fakes.py`
- `apps/backend/tests/test_groq_provider.py`
- `apps/backend/tests/test_ingestion_ai_parse_integration.py`
- `apps/backend/tests/test_persistence_application.py`
- `apps/backend/tests/test_telegram_live_backfill.py`
- `apps/backend/tests/test_telegram_live_events.py`
- `infra/compose.production.yaml`
- `scripts/deploy/build_release_config.py`
- `scripts/prove_release_workflow.py`
- `apps/backend/migrations/versions/20260905_0023_durable_ai_recovery.py`
- `apps/backend/src/wef_backend/automatic_recovery_worker.py`
- `apps/backend/src/wef_backend/features/admin/application/automatic_recovery.py`
- `apps/backend/src/wef_backend/features/admin/application/provider_budget.py`
- `apps/backend/src/wef_backend/features/admin/application/provider_context.py`
- `apps/backend/src/wef_backend/features/admin/application/recovery_validation.py`
- `apps/backend/src/wef_backend/features/admin/infrastructure/provider_budget_store.py`
- `apps/backend/src/wef_backend/features/admin/infrastructure/recovery_queue.py`
- `apps/backend/tests/test_automatic_recovery.py`
- `apps/backend/tests/test_automatic_recovery_worker.py`
- `apps/backend/tests/test_provider_budget.py`
- `apps/backend/tests/test_provider_budget_integration.py`
- `apps/backend/tests/test_recovery_queue_integration.py`
- `apps/backend/tests/test_recovery_validation.py`
- `AI/epics/E25-parser-quality-and-automatic-recovery/E25-T3-IMPLEMENTATION_EVIDENCE.md`

## Current-main integration refresh

The E24 archive and progress changes merged as `64da1bd` and `5fd175f`.
The E25 planning PR #327 closed without merging when its former base disappeared;
replacement #338 targets main. T1 #328 → T2 #330 → T3 #335 remain an ordered
ancestor stack. This supersedes the original sibling/dependency limitation above.
Migrations now follow ingestion progress `0021`, evaluations `0022`, and durable
AI recovery `0023`. Revision 2 approval and disabled rollout flags are preserved.

## Production release and remaining activation gates

PR #335 merged as `81cd983` after all required current-head checks passed.
[Release 33974422623](https://github.com/Flippylolz/WEF/actions/runs/33974422623)
succeeded. Both API and worker reported schema `20260905_0023`, recovery enabled
false, activation verified false, auto-apply false and no configured recovery owner.
The approved model, key presence and deployed ZDR flag were present. Recovery work,
provider attempts and account reservations were all empty. No scheduled provider
request or automatic AI application occurred.

Post-deploy verification found worker liveness probes exceeding the existing
three-second timeout despite fresh heartbeats and active ingestion. Independently
merged E24-T2 correction #341 (`f700ee3`) removes ORM imports from that path while
preserving the same health semantics and timeout. Its release 33975004167 passed.
The subsequent probe completed in 2.018 seconds but correctly failed while the
first reconciliation completion remained absent; durable polling continued
(11,461 → 11,574) with fresh commit timestamps. This is not accepted worker health
or T3 acceptance. Recovery remains disabled until stable worker readiness and the
provider prerequisites are verified. No E24 runtime setting or checkpoint was reset.

The Groq console was signed out. Current free-plan evidence was requested from the
owner; the deployed ZDR flag alone does not prove free allocation or current billing.
After that evidence and worker readiness, run the approved provider canary and
representative 24-hour window. T3 remains in progress; T4 cannot merge or activate
until this dependency is done. Paid capacity remains unauthorized.

## Minimal-use activation preflight

On 2026-09-05 the owner confirmed in Codex task
`01a0710e-e877-7ab2-ad03-c6008aaf16e9` that the production Groq account uses the
free plan with Zero Data Retention enabled, and instructed that Groq remain a
minimal-use fallback. The owner selected `flipstar` as the account owning the
shared recovery budget. This confirms the previously missing account prerequisite;
20 daily generation items remains a ceiling, never a target. No paid allocation,
new account, provider Batch API or automatic application is authorized by this
confirmation.

PR #335 merged as `81cd983` and deployed with recovery disabled. Production release
`0df1260` subsequently had healthy API and worker containers, current reconciliation
and active ingestion. The preflight found zero provider attempts, reservations or
pending owner cohorts, and one current eligible evaluation. Its parking label
described availability without stating a monetary amount. The `source-evidence-v1`
classifier incorrectly treated any nonempty price label as an extraction miss.
No provider request was sent for that record.

The T3 follow-up introduces `source-evidence-v2`: missing price fields require
an explicit currency-bearing amount or a bare numeric amount before they qualify
for recovery. Availability prose and unrelated numbered spaces remain unclassified;
explicit absence, inclusion evidence, parser warnings and successfully extracted
values retain their existing classifications. The new policy identity makes old
eligibility stale and allows bounded metadata reclassification without changing
canonical offers or deleting evaluation history. Regression fixtures are invented
and contain no production source text.

Scheduling and automatic application remain off during this correction. After
release, repeat the eligible-backlog check before the authorized observation
canary; never generate unnecessary requests to reach ten observations. The real
provider canary and representative 24-hour acceptance remain outstanding. T4 must
accept the reviewed policy version before its separately gated replay rollout.

Validation: `make lint`, `make format-check`, `make typecheck` and
`make contract-check` passed. `make test`, using dedicated E25 Docker image names
to avoid shared-worktree tag collisions, passed 1,071 backend and 169 frontend
tests with 90.26% backend coverage. The focused classifier suite passed 26 tests,
including absent amounts, unrelated digits, real monetary evidence and existing
inclusion behavior. No schema migration or production dependency was added.
