# E25-T1 local implementation evidence

## Result and remaining gates

E25-T1 detects source-evidenced gaps independently of parser warnings, records
source/parser/policy evaluations for unchanged and clean messages, retains
resolution/supersession history, and restricts expensive batch selection to
eligible current revisions. The original legacy issue outcomes remain readable.

The 75-case reviewed synthetic benchmark exposes 40 case/field failures in e2-v13,
including the audit-derived price/storage regression. Candidate precision is
56/56 and recall 56/60; these are synthetic regression results, not production
accuracy. T2 owns extraction repair. T3 owns scheduled validated AI exceptions.
T4 owns canonical historical convergence and remains gated on E24-T1.

This task remains in progress until its PR, CI/review, authorized merge and final
completion evidence exist. Publication was initially rejected by automatic approval review. The owner then
explicitly authorized publication: planning PR 327 and T1 PR 328 are now open.
No production mutation or provider activation occurred. The provider revision
requires approval-gate revalidation without changing these validation results.

## Validation

Validation used Python 3.13.2, Node 22.22.2 and pnpm 11.21.0. All dependencies
came from frozen manifests/lockfiles; no dependency was added.

| Command | Result |
| --- | --- |
| `UV_PYTHON=3.13.2 make install` | Passed |
| `make lint` | Passed, including all 17 architecture contracts |
| `make format-check` | Passed |
| `make typecheck` | Passed; 289 Python files plus frontend TypeScript |
| `make contract-check` | Passed; no committed public API/type drift |
| `COMPOSE_PROJECT_NAME=wef-e25-validation make test` | Passed: 827 backend tests, 169 frontend tests |
| Backend coverage | 90.38%, above required 90% |
| Frontend coverage | Statements 94.51%, branches 90.14%, lines 95.76%; required floors passed |
| `python3 scripts/check_markdown_links.py` | Passed |
| `git diff --check` | Passed |

The backend suite used real disposable PostGIS, migrations and rollback/re-upgrade.
New integration cases cover unchanged-revision deduplication, later successful
extraction and retained transitions, stale source revisions, old parser versions,
transaction rollback, bounded/resumable metadata backfill and current-revision
batch eligibility. Source fixture tests reject contact/source identity leakage;
new fixtures use `case_id` and do not relax the existing source-ID restrictions.

Existing tests needed updated assumptions for newly detected silent property-type
gaps and dependency-ordered fixture cleanup. Existing warning/resource-lifecycle
warnings remain visible (three warnings in the backend run); no unrelated warning
suppression or behavior refactoring was included.

## Migration and operations

Migration `20260905_0022` adds `parse_evaluations` and
`parse_evaluation_transitions`; deploy it before the new runtime readiness revision.
Metadata backfill defaults to 100 records and at most 10 records per transaction,
uses keyset pagination and skips durable completed evaluation identities.

No data backfill runs on migration. Classification metadata backfill does not
apply canonical fields or call providers. Admin exports add classification,
lifecycle, eligibility and policy metadata while retaining legacy outcome fields.
The manual AI batch selector now excludes unclassified/non-offer/deleted/stale
sources and deduplicates current source revisions rather than text prefixes.

Runtime rollback retains additive metadata/history. Explicit migration downgrade
removes the evaluation tables only; it is not a canonical-data restore. T4's
provenance-protected canonical rollback remains future work. No production
activation, live calibration, representative source sampling or runtime release
has been claimed as verified.

## Changed files

This inventory covers the T1 branch relative to planning commit `cc793bc`.

- [AI/data/QUALITY_AND_READINESS.md](../../../AI/data/QUALITY_AND_READINESS.md)
- [AI/epics/E25-parser-quality-and-automatic-recovery/E25-T1-IMPLEMENTATION_EVIDENCE.md](../../../AI/epics/E25-parser-quality-and-automatic-recovery/E25-T1-IMPLEMENTATION_EVIDENCE.md)
- [AI/epics/E25-parser-quality-and-automatic-recovery/README.md](../../../AI/epics/E25-parser-quality-and-automatic-recovery/README.md)
- [AI/epics/E25-parser-quality-and-automatic-recovery/tasks/E25-T1-benchmark-source-evidence-and-triage.md](../../../AI/epics/E25-parser-quality-and-automatic-recovery/tasks/E25-T1-benchmark-source-evidence-and-triage.md)
- [AI/epics/README.md](../../../AI/epics/README.md)
- [AI/ingestion/PIPELINE.md](../../../AI/ingestion/PIPELINE.md)
- [AI/milestones/M5-production-maturity.md](../../../AI/milestones/M5-production-maturity.md)
- [AI/operations/OPERATOR_COMMANDS.md](../../../AI/operations/OPERATOR_COMMANDS.md)
- [apps/backend/migrations/versions/20260905_0022_parse_evaluations.py](../../../apps/backend/migrations/versions/20260905_0022_parse_evaluations.py)
- [apps/backend/src/wef_backend/backfill_parse_issues_command.py](../../../apps/backend/src/wef_backend/backfill_parse_issues_command.py)
- [apps/backend/src/wef_backend/batch_ingestion_ai_parse_command.py](../../../apps/backend/src/wef_backend/batch_ingestion_ai_parse_command.py)
- [apps/backend/src/wef_backend/features/admin/interface/parse_issue_views.py](../../../apps/backend/src/wef_backend/features/admin/interface/parse_issue_views.py)
- [apps/backend/src/wef_backend/features/ingestion/application/parse_issue_serialization.py](../../../apps/backend/src/wef_backend/features/ingestion/application/parse_issue_serialization.py)
- [apps/backend/src/wef_backend/features/ingestion/application/parse_quality.py](../../../apps/backend/src/wef_backend/features/ingestion/application/parse_quality.py)
- [apps/backend/src/wef_backend/features/ingestion/domain/parse_issue.py](../../../apps/backend/src/wef_backend/features/ingestion/domain/parse_issue.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/models.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/models.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/parse_evaluation_store.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/parse_evaluation_store.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/parse_issue_backfill.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/parse_issue_backfill.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/parse_issue_store.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/parse_issue_store.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/persistence_adapter.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/persistence_adapter.py)
- [apps/backend/src/wef_backend/migration.py](../../../apps/backend/src/wef_backend/migration.py)
- [apps/backend/tests/fixtures/telegram_export/parser-quality-v1-baseline.json](../../../apps/backend/tests/fixtures/telegram_export/parser-quality-v1-baseline.json)
- [apps/backend/tests/fixtures/telegram_export/parser-quality-v1.json](../../../apps/backend/tests/fixtures/telegram_export/parser-quality-v1.json)
- [apps/backend/tests/parser_benchmark.py](../../../apps/backend/tests/parser_benchmark.py)
- [apps/backend/tests/test_admin_parse_issues.py](../../../apps/backend/tests/test_admin_parse_issues.py)
- [apps/backend/tests/test_backfill_parse_issues.py](../../../apps/backend/tests/test_backfill_parse_issues.py)
- [apps/backend/tests/test_parse_evaluation_integration.py](../../../apps/backend/tests/test_parse_evaluation_integration.py)
- [apps/backend/tests/test_parse_issue_ledger.py](../../../apps/backend/tests/test_parse_issue_ledger.py)
- [apps/backend/tests/test_parse_quality.py](../../../apps/backend/tests/test_parse_quality.py)
- [apps/backend/tests/test_persistence_integration.py](../../../apps/backend/tests/test_persistence_integration.py)
- [apps/backend/tests/test_place_ai_review_integration.py](../../../apps/backend/tests/test_place_ai_review_integration.py)
- [apps/backend/tests/test_raw_replay_integration.py](../../../apps/backend/tests/test_raw_replay_integration.py)
- [apps/backend/tests/test_telegram_fixture_safety.py](../../../apps/backend/tests/test_telegram_fixture_safety.py)
