# E25-T4 implementation evidence

## State and scope

Draft PR [337](https://github.com/Flippylolz/WEF/pull/337); implementation commit `61caba5`.

T4 implementation began only after readiness commit `a84ea07`. Every dependency is
an ancestor in the published stack: E24-T1 #331 → E25 planning #327 → T1 #328 →
T2 #330 → T3 #335 → T4. This was the original readiness stack; the refresh below records the current
baseline. No PR was merged into main by this work. Existing E25 approvals remain revision 2. Migration allocation was
reconciled as archive 0020, evaluation 0021, durable AI 0022, parser replay 0023.

The task remains in progress pending PR review, required checks, dependency
completion and production acceptance. Scheduling and application default off.
No production canonical history, provider configuration or paid allocation changed.

## Result

- Accepted `e2-v14` / `source-evidence-v1` release metadata, durable source-revision
  work and guarded field lineage. Unknown releases do not schedule; a persisted
  newer release pauses downgrade convergence.
- Original archive decoding checks retained source ID, checksum and text. Unsupported
  originals, absent source evidence, non-candidates, deleted/changed revisions and
  missing current offer links receive explicit finite outcomes.
- Keyset discovery selects at most 100 records in chunks of ten. One global claim,
  120-second leases, a five-second tick bound, live priority, fair anti-identity
  selection and persisted retry checkpoints bound repeated work.
- First 25 replayable records form a read-only canary; a smaller backlog uses all
  available records. Validated observations are applied later without re-generation.
  Queued work continues automatically after promotion and the application flag.
- Each write checks the current source, parser/AI origins and retained parser value.
  Unknown or changed canonical values and AI-owned fields remain protected. Coupled
  money/currency groups cannot be partially overwritten with incompatible values.
- Offer IDs, favorites, contact ciphertext, visibility and relationship IDs survive.
  Applied field values, extraction/source offsets, parser origins, duplicate
  fingerprint, evaluation lifecycle and work completion share a transaction.
- A second unchanged-source/release pass performs zero canonical updates or new
  lineage writes. Population reporting balances the selected denominator, counting
  pending/canary work as deferred and partial protected repairs once as conflicts.
- Explicit per-job rollback pauses the release and restores only unchanged,
  still-owned field groups. Later owner/source changes survive and reversal is
  idempotent with per-field reverted/conflict evidence.

## Verification

Final full isolated suite: 1,051 backend tests and 169 frontend tests passed,
with 90.28% backend coverage. All commands below passed.

Commands: `COMPOSE_PROJECT_NAME=wef-e25-validation make test`, `make lint`,
`make format-check`, `make typecheck`, `make contract-check`; root `scripts/` Ruff
format/lint and strict mypy; `python3 -m scripts.prove_release_workflow`,
`make production-proof`, `python3 scripts/check_markdown_links.py`, `git diff --check`.

New integration evidence covers a 30-record backlog with exactly 25 observations
before application, restarted/stale claims, simultaneous workers, a source revision
race, owner corrections, active AI origins, unchanged encrypted contacts and favorite
identity, canonical price/provenance readback, explicit exclusions, bounded failure
backoff, downgrade pause, no-op repeat and guarded rollback. Existing catalog/filter,
archive receipt, extraction benchmark and migration suites also run in full.
Provider preservation tests use fakes; no live request is sent.

The first test fixture omitted Telegram's required Unix timestamp and was corrected
to the real decoder contract. Transaction testing then identified the old origin
field-name constraint; migration 0024 extends it for parser-owned content/property
fields only. The AI preservation fixture explicitly enables its intended test
fields instead of inheriting a floor-only test allowlist.

## Remaining rollout evidence

Local fixture tests do not establish production prevalence or historical convergence.
Collect the representative live acceptance denominator, source exclusions,
protected/failed reasons, version distribution, actual provider spend (T3 only)
and human interventions after a reviewed release is activated. Do not mark E25 done
from green tests alone. T3's initial AI canary observations retain their separately
documented limitation; T4's deterministic canary observations do replay automatically.

Pause, aggregate diagnostics and the bounded rollback service are documented in
[operator commands](../../operations/OPERATOR_COMMANDS.md#historical-parser-replay-e25-t4).

## Changed files

- `.env.example`
- `.github/workflows/deploy-production.yml`
- `AI/data/QUALITY_AND_READINESS.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/IMPLEMENTATION_PLAN.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/README.md`
- `AI/epics/E25-parser-quality-and-automatic-recovery/tasks/E25-T4-converge-parser-versions-automatically.md`
- `AI/ingestion/PIPELINE.md`
- `AI/operations/OPERATOR_COMMANDS.md`
- `AI/security/AUTH_ADMIN_CONTACTS.md`
- `apps/backend/src/wef_backend/features/ingestion/application/persistence.py`
- `apps/backend/src/wef_backend/migration.py`
- `apps/backend/src/wef_backend/settings.py`
- `apps/backend/src/wef_backend/telegram_worker_command.py`
- `infra/compose.production.yaml`
- `scripts/deploy/build_release_config.py`
- `scripts/prove_release_workflow.py`
- `apps/backend/migrations/versions/20260905_0024_parser_replay.py`
- `apps/backend/src/wef_backend/features/ingestion/application/parser_replay.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/parser_replay.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/parser_replay_rollback.py`
- `apps/backend/src/wef_backend/parser_replay_worker.py`
- `apps/backend/tests/test_parser_replay.py`
- `apps/backend/tests/test_parser_replay_integration.py`
- `AI/epics/E25-parser-quality-and-automatic-recovery/E25-T4-IMPLEMENTATION_EVIDENCE.md`

## Current-main integration refresh

E24-T1/T2 are merged into main (`64da1bd` / `5fd175f`). Replacement planning
PR #338 restores the closed, unmerged #327 against main. E25 remains an ordered
ancestor stack #338 → #328 → #330 → #335 → #337. Migrations now run archive
0020 → progress 0021 → evaluations 0022 → durable AI 0023 → parser replay 0024.
The refreshed suite passed: 1,064 backend and 169 frontend tests, with 90.38%
backend coverage. Lint, format, type, contract, Markdown links and production
proof also passed. Existing
canary, application flags, owner guards, rollback and acceptance gates remain.

Refresh-specific files: replay migration renamed to `20260905_0024_parser_replay.py`,
`wef_backend/migration.py`, `AI/ingestion/PIPELINE.md`,
`AI/operations/OPERATOR_COMMANDS.md`, this evidence file, epic `README.md`,
`IMPLEMENTATION_PLAN.md`, and the T4 task dependency record. Upstream changes
remain owned by their corresponding parent PRs.
