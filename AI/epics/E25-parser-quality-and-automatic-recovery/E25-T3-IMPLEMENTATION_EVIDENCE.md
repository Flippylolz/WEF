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
